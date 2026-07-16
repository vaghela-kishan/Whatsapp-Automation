"""Order endpoints — list for the dashboard, look up by number."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.core.exceptions import BadRequestError, NotFoundError
from app.crud.order import order as order_crud
from app.integrations.whatsapp import get_whatsapp_provider
from app.models.order import Order
from app.models.order_event import OrderEvent
from app.schemas.order import OrderRead

logger = logging.getLogger("app.orders")

router = APIRouter(prefix="/orders", tags=["Orders"])


class OrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    customer_name: str | None = None
    event_type: str
    reason: str | None = None
    summary: str | None = None
    actor: str
    channel: str
    created_at: datetime


@router.get(
    "/events/recent",
    response_model=list[OrderEventRead],
    summary="Recent order actions (audit trail): cancellations, returns, refunds",
)
def recent_events(
    limit: int = Query(default=30, ge=1, le=200), db: Session = Depends(get_db)
) -> list[OrderEventRead]:
    rows = db.execute(
        select(OrderEvent).order_by(OrderEvent.created_at.desc()).limit(limit)
    ).scalars().all()
    return [OrderEventRead.model_validate(e) for e in rows]


class PendingRefund(BaseModel):
    order_number: str
    customer_name: str | None = None
    contact_number: str | None = None
    amount: float
    method: str | None = None
    reference: str | None = None
    refund_status: str
    order_status: str
    reason: str | None = None
    requested_on: datetime | None = None


@router.get(
    "/refunds/pending",
    response_model=list[PendingRefund],
    summary="Refunds awaiting a human to review & pay out",
)
def pending_refunds(
    limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)
) -> list[PendingRefund]:
    """The AI *initiates* refunds on cancel/return; a human reviews & pays them
    out here. Lists refunds in 'initiated' or 'processing' state."""
    rows = db.execute(
        select(Order)
        .options(joinedload(Order.customer))
        .where(Order.refund_status.in_(["initiated", "processing"]))
        .order_by(Order.updated_at.desc())
        .limit(limit)
    ).scalars().all()
    out = []
    for o in rows:
        out.append(
            PendingRefund(
                order_number=o.order_number,
                customer_name=o.customer.name if o.customer else None,
                contact_number=o.customer.wa_id if o.customer else None,
                amount=o.refund_amount,
                method=o.refund_method,
                reference=o.refund_reference,
                refund_status=o.refund_status,
                order_status=str(o.status),
                reason=o.cancellation_reason or o.return_reason,
                requested_on=o.cancelled_at or o.delivered_at or o.created_at,
            )
        )
    return out


@router.post(
    "/{order_number}/refund/complete",
    response_model=PendingRefund,
    summary="Human action: mark a refund as paid out (completed)",
)
def complete_refund(order_number: str, db: Session = Depends(get_db)) -> PendingRefund:
    """A human agent reviews the refund and pays it out. Marks it completed,
    stamps the date, logs an audit event, and notifies the customer on WhatsApp."""
    order = db.execute(
        select(Order).options(joinedload(Order.customer)).where(
            Order.order_number == order_number.upper().strip()
        )
    ).scalar_one_or_none()
    if order is None:
        raise NotFoundError(f"Order {order_number} not found.")
    if order.refund_status not in ("initiated", "processing"):
        raise BadRequestError(
            f"No pending refund for {order_number} (status: {order.refund_status})."
        )

    now = datetime.now(timezone.utc)
    order.refund_status = "completed"
    order.refund_date = now
    db.add(
        OrderEvent(
            order_id=order.id,
            order_number=order.order_number,
            customer_name=order.customer.name if order.customer else None,
            event_type="refund_completed",
            reason=None,
            summary=f"Refund of ₹{order.refund_amount:.2f} paid out for {order.order_number}",
            actor="agent",
            channel="dashboard",
            data={"reference": order.refund_reference, "amount": order.refund_amount},
        )
    )
    db.commit()
    db.refresh(order)

    # Notify the customer on WhatsApp (mock transport in demo).
    if order.customer:
        try:
            get_whatsapp_provider().send_text(
                to=order.customer.wa_id,
                text=(
                    f"✅ Your refund of ₹{order.refund_amount:,.0f} for order "
                    f"*{order.order_number}* has been processed to your "
                    f"{order.refund_method or 'original payment method'} "
                    f"(Ref: {order.refund_reference}). It should reflect shortly. "
                    "Thank you for shopping with us! 💚"
                ),
            )
        except Exception as exc:  # pragma: no cover - never fail on notify
            logger.warning("refund_notify_failed order=%s error=%s", order_number, exc)

    return PendingRefund(
        order_number=order.order_number,
        customer_name=order.customer.name if order.customer else None,
        contact_number=order.customer.wa_id if order.customer else None,
        amount=order.refund_amount,
        method=order.refund_method,
        reference=order.refund_reference,
        refund_status=order.refund_status,
        order_status=str(order.status),
        reason=order.cancellation_reason or order.return_reason,
        requested_on=order.cancelled_at or order.delivered_at or order.created_at,
    )


@router.get("", response_model=list[OrderRead], summary="List recent orders")
def list_orders(
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[OrderRead]:
    return [
        OrderRead.model_validate(o)
        for o in order_crud.list_all(db, offset=offset, limit=limit)
    ]


@router.get("/meta/count", summary="Total order count")
def order_count(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"total": order_crud.count(db)}


@router.get(
    "/{order_number}",
    response_model=OrderRead,
    summary="Look up a single order by its number",
)
def get_order(order_number: str, db: Session = Depends(get_db)) -> OrderRead:
    order = order_crud.get_by_number(db, order_number)
    if order is None:
        raise NotFoundError(f"Order {order_number} not found.")
    return OrderRead.model_validate(order)
