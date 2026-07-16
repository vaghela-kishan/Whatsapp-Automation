"""Proactive, event-driven automation.

A background worker periodically advances in-progress orders along their
fulfilment journey (confirmed → packed → shipped → out for delivery →
delivered) and *proactively* messages the customer on WhatsApp at each step —
without anyone asking. Every step is logged to the audit trail.

In production these transitions would be driven by real courier webhooks; here
a timer simulates them so the automation is visible in the demo.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.integrations.whatsapp import get_whatsapp_provider
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.order_event import OrderEvent

logger = logging.getLogger("app.automation")

_NEXT_STATUS: dict[OrderStatus, OrderStatus] = {
    OrderStatus.CONFIRMED: OrderStatus.PACKED,
    OrderStatus.PACKED: OrderStatus.SHIPPED,
    OrderStatus.SHIPPED: OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.OUT_FOR_DELIVERY: OrderStatus.DELIVERED,
}
_CARRIERS = ["BlueDart", "Delhivery", "Ekart", "DTDC", "XpressBees"]


def _notification(order: Order, new_status: OrderStatus) -> str:
    n = order.order_number
    if new_status is OrderStatus.PACKED:
        return f"📦 Good news! Your order *{n}* is packed and will ship soon."
    if new_status is OrderStatus.SHIPPED:
        track = f"\n📍 Track: {order.tracking_number} ({order.carrier})" if order.tracking_number else ""
        return f"🚚 Your order *{n}* has shipped and is on its way!{track}"
    if new_status is OrderStatus.OUT_FOR_DELIVERY:
        return f"🛵 Your order *{n}* is out for delivery — it should reach you today!"
    if new_status is OrderStatus.DELIVERED:
        return (
            f"🎉 Your order *{n}* has been delivered! We hope you love it. "
            "Reply here anytime if you need help. ⭐"
        )
    return f"Your order *{n}* is now {new_status}."


def advance_orders(db: Session, limit: int | None = None) -> int:
    """Advance a few in-progress orders one step and notify each customer.
    Returns how many orders were progressed."""
    limit = limit or settings.AUTOMATION_BATCH
    now = datetime.now(timezone.utc)
    rows = list(
        db.execute(
            select(Order)
            .options(joinedload(Order.customer))
            .where(Order.status.in_(list(_NEXT_STATUS.keys())))
            .order_by(Order.updated_at.asc())
            .limit(limit)
        ).scalars().all()
    )

    provider = get_whatsapp_provider()
    changed = 0
    for order in rows:
        new_status = _NEXT_STATUS.get(order.status)
        if new_status is None:
            continue
        order.status = new_status
        if new_status is OrderStatus.SHIPPED and not order.tracking_number:
            order.tracking_number = f"TRK{random.randint(100000, 999999)}IN"
            order.carrier = random.choice(_CARRIERS)
        if new_status is OrderStatus.DELIVERED:
            order.delivered_at = now
            order.delivery_attempts = max(1, order.delivery_attempts)

        text = _notification(order, new_status)
        if order.customer:
            try:
                provider.send_text(to=order.customer.wa_id, text=text)
            except Exception as exc:  # pragma: no cover - never fail the tick
                logger.warning("proactive_notify_failed order=%s err=%s", order.order_number, exc)

        db.add(
            OrderEvent(
                order_id=order.id,
                order_number=order.order_number,
                customer_name=order.customer.name if order.customer else None,
                event_type="status_update",
                reason=None,
                summary=f"{order.order_number} → {str(new_status).replace('_', ' ')} · customer notified",
                actor="automation",
                channel="whatsapp",
                data={"new_status": str(new_status)},
            )
        )
        changed += 1

    if changed:
        db.commit()
        logger.info("automation_advanced orders=%d", changed)
    return changed


_started = False


def start_worker() -> None:
    """Start the background automation loop once (idempotent)."""
    global _started
    if _started or not settings.AUTOMATION_ENABLED:
        return
    _started = True

    interval = max(5, settings.AUTOMATION_INTERVAL_SECONDS)

    def _loop() -> None:
        from app.db.session import SessionLocal

        while True:
            time.sleep(interval)
            try:
                db = SessionLocal()
                try:
                    advance_orders(db)
                finally:
                    db.close()
            except Exception:  # pragma: no cover - keep the loop alive
                logger.exception("automation_tick_error")

    threading.Thread(target=_loop, name="automation-worker", daemon=True).start()
    logger.info("proactive_automation_started interval=%ds", interval)
