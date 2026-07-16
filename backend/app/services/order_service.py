"""Order-status resolution and customer-friendly formatting."""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.crud.order import order as order_crud
from app.models.customer import Customer
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.order_event import OrderEvent


def latest_returnable_order(db: Session, customer: Customer) -> Order | None:
    """The customer's most recent delivered, still-returnable order."""
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(Order)
        .options(joinedload(Order.customer))
        .where(Order.customer_id == customer.id, Order.status == OrderStatus.DELIVERED)
        .order_by(Order.delivered_at.desc())
    ).scalars().all()
    for o in rows:
        if o.return_eligible and not o.return_id and o.is_within_return_window(now):
            return o
    return None


def create_return(db: Session, order: Order, *, reason: str, resolution: str = "refund") -> dict:
    """Create a return/replacement on an order and log it. Reused by the agent
    and the photo (vision) flow. Assumes eligibility already checked."""
    now = datetime.now(timezone.utc)
    order.return_id = f"RET-{random.randint(100000, 999999)}"
    order.return_reason = reason
    order.pickup_date = now + timedelta(days=2)
    result = {"return_id": order.return_id, "pickup_date": order.pickup_date.strftime("%d %b %Y")}
    if resolution.lower().startswith("replace"):
        order.return_status = "Replacement Scheduled"
        order.replacement_id = f"REP-{random.randint(100000, 999999)}"
        result["replacement_id"] = order.replacement_id
        event_type = "replacement_requested"
    else:
        order.return_status = "Pickup Scheduled"
        order.refund_status = "initiated"
        order.refund_amount = order.total
        order.refund_method = order.payment_method or "Original payment method"
        order.refund_reference = f"RFND{random.randint(10_000_000, 99_999_999)}"
        result["refund_amount"] = order.total
        result["refund_reference"] = order.refund_reference
        event_type = "return_requested"
    db.add(
        OrderEvent(
            order_id=order.id,
            order_number=order.order_number,
            customer_name=order.customer.name if order.customer else None,
            event_type=event_type,
            reason=reason,
            summary=f"Return {order.return_id} for {order.order_number} ({reason})",
            actor="ai",
            channel="whatsapp",
            data=result,
        )
    )
    db.commit()
    return result

# Human-friendly, emoji-tagged status lines used in chat replies.
_STATUS_LINE: dict[OrderStatus, str] = {
    OrderStatus.PENDING: "🕐 We've received your order and it's awaiting confirmation.",
    OrderStatus.CONFIRMED: "✅ Your order is confirmed and being prepared.",
    OrderStatus.PACKED: "📦 Your order is packed and ready to ship.",
    OrderStatus.SHIPPED: "🚚 Your order has shipped and is on its way!",
    OrderStatus.OUT_FOR_DELIVERY: "🛵 Out for delivery — it should reach you today!",
    OrderStatus.DELIVERED: "🎉 Your order has been delivered. We hope you love it!",
    OrderStatus.CANCELLED: "❌ This order was cancelled. Let us know if that's unexpected.",
    OrderStatus.RETURNED: "↩️ This order has been returned and is being processed.",
}


def format_status_reply(order: Order) -> str:
    """Build a friendly multi-line WhatsApp reply describing an order."""
    lines = [
        f"Here's the latest on *{order.order_number}*:",
        "",
        _STATUS_LINE.get(order.status, f"Status: {order.status}"),
    ]

    if order.items:
        item_names = ", ".join(
            f"{it.get('name', 'item')} ×{it.get('qty', 1)}" for it in order.items
        )
        lines.append(f"🛍️ Items: {item_names}")

    if order.status in (OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY):
        if order.tracking_number:
            carrier = order.carrier or "the courier"
            lines.append(f"📍 Tracking: {order.tracking_number} ({carrier})")
        if order.estimated_delivery:
            lines.append(
                f"📅 Estimated delivery: {order.estimated_delivery.strftime('%d %b %Y')}"
            )

    lines.append("")
    lines.append("Anything else I can help you with? 😊")
    return "\n".join(lines)


def resolve_status(db: Session, order_number: str) -> tuple[Order | None, str]:
    """Look up an order and return ``(order, reply_text)``.

    ``order`` is ``None`` when the number isn't found, in which case the reply
    politely asks the customer to re-check the number.
    """
    order = order_crud.get_by_number(db, order_number)
    if order is None:
        reply = (
            f"I couldn't find an order matching *{order_number}*. 🤔\n\n"
            "Could you double-check the number? It usually looks like *AUR-10432* "
            "and is in your confirmation message."
        )
        return None, reply
    return order, format_status_reply(order)


# ---------------------------------------------------------------------------
# Aggregate "order query" answering (list / count / by-price / by-status)
# ---------------------------------------------------------------------------

_STATUS_KEYWORDS: dict[str, OrderStatus] = {
    "delivered": OrderStatus.DELIVERED,
    "shipped": OrderStatus.SHIPPED,
    "out for delivery": OrderStatus.OUT_FOR_DELIVERY,
    "packed": OrderStatus.PACKED,
    "confirmed": OrderStatus.CONFIRMED,
    "pending": OrderStatus.PENDING,
    "cancelled": OrderStatus.CANCELLED,
    "canceled": OrderStatus.CANCELLED,
    "returned": OrderStatus.RETURNED,
}
_ABOVE_WORDS = ("above", "over", "more than", "greater", "worth more", "upar", "vadhare", "than")
_BELOW_WORDS = ("under", "below", "less than", "cheaper", "niche", "ochha")
_COUNT_WORDS = ("how many", "how much", "count", "number of", "total number", "ketla", "kul", "ketla")
_SALES_WORDS = ("total sales", "total revenue", "total value", "revenue", "sales", "order value")
_MONEY_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]{1,})(\s*k)?", re.IGNORECASE)


def _detect_status(lowered: str) -> OrderStatus | None:
    for kw, status in _STATUS_KEYWORDS.items():
        if kw in lowered:
            return status
    return None


def _detect_price(lowered: str) -> tuple[float | None, float | None]:
    """Return (min_price, max_price) parsed from phrases like 'above 5000'."""
    match = _MONEY_RE.search(lowered)
    if not match:
        return None, None
    value = float(match.group(1).replace(",", ""))
    if match.group(2):  # a trailing 'k' → thousands
        value *= 1000
    if any(w in lowered for w in _BELOW_WORDS):
        return None, value
    if any(w in lowered for w in _ABOVE_WORDS):
        return value, None
    # Bare number with no direction → treat as a floor ("orders 5000").
    return value, None


def _fmt_money(v: float) -> str:
    return f"₹{v:,.0f}"


def _status_label(status: OrderStatus | str) -> str:
    """Human-readable status ('out for delivery') without underscores, which
    would otherwise render as italics in the WhatsApp-markdown UI."""
    return str(status).replace("_", " ")


def _line(o: Order) -> str:
    first = o.items[0].get("name", "item") if o.items else "item"
    extra = f" +{len(o.items) - 1} more" if len(o.items) > 1 else ""
    return f"• *{o.order_number}* — {first}{extra} · {_fmt_money(o.total)} · {_status_label(o.status)}"


def format_customer_orders(db: Session, customer) -> str:
    """List the caller's own orders (looked up by their phone/wa_id)."""
    if customer is None:
        return (
            "I don't see any orders linked to your number yet. 🤔 If you have an "
            "order, share the order number (like *AUR-10432*) and I'll check it."
        )
    orders = order_crud.list_for_customer(db, customer.id)
    first_name = (customer.name or "there").split()[0]
    if not orders:
        return (
            f"Hi {first_name}! 👋 I don't see any orders under your number yet. "
            "Once you place one, just message me and I'll track it for you. 😊"
        )
    shown = orders[:10]
    lines = "\n".join(_line(o) for o in shown)
    more = f"\n…and {len(orders) - len(shown)} more" if len(orders) > len(shown) else ""
    return (
        f"Hi {first_name}! 👋 You have *{len(orders)}* order(s) with us:\n"
        f"{lines}{more}\n\n"
        "Which one would you like details on? Tell me the order number, or ask me "
        "anything about them. 😊"
    )


def answer_order_query(db: Session, text: str) -> str:
    """Answer an aggregate question about the order book, straight from the DB."""
    lowered = text.lower()
    status = _detect_status(lowered)
    min_price, max_price = _detect_price(lowered)
    has_price = min_price is not None or max_price is not None

    # 1) Total sales / revenue.
    if any(w in lowered for w in _SALES_WORDS) and "how many" not in lowered:
        total = order_crud.total_sales(db, status=status)
        count = order_crud.count_where(db, status=status)
        label = f" {status} " if status else " "
        return (
            f"💰 Total sales across *{count}*{label}orders: *{_fmt_money(total)}*."
            + ("" if not status else "")
        )

    # 2) Counting questions.
    if any(w in lowered for w in _COUNT_WORDS):
        count = order_crud.count_where(
            db, status=status, min_price=min_price, max_price=max_price
        )
        if status and has_price:
            desc = f"{_status_label(status)} orders {'above' if min_price else 'under'} {_fmt_money(min_price or max_price)}"
        elif status:
            desc = f"*{_status_label(status)}* orders"
        elif has_price:
            desc = f"orders {'above' if min_price else 'under'} {_fmt_money(min_price or max_price)}"
        else:
            desc = "orders in total"
        return f"📊 There are *{count}* {desc}."

    # 3) Listing — by price (sorted high→low) or recent, optionally by status.
    order_by_total = has_price or any(
        w in lowered for w in ("expensive", "highest", "top", "costliest", "biggest", "largest")
    )
    matches = order_crud.query(
        db,
        status=status,
        min_price=min_price,
        max_price=max_price,
        order_by_total_desc=order_by_total,
        limit=8,
    )
    total_count = order_crud.count_where(
        db, status=status, min_price=min_price, max_price=max_price
    )
    if not matches:
        return "I couldn't find any orders matching that. Try a different filter? 🔎"

    bits = []
    if status:
        bits.append(f"*{_status_label(status)}*")
    if min_price is not None:
        bits.append(f"above {_fmt_money(min_price)}")
    if max_price is not None:
        bits.append(f"under {_fmt_money(max_price)}")
    scope = (" " + " ".join(bits)) if bits else ""

    header = f"🧾 Here are{scope} orders ({len(matches)} of *{total_count}*):"
    lines = "\n".join(_line(o) for o in matches)
    footer = "\n\nWant me to filter by status, price, or a specific order number? 😊"
    return f"{header}\n{lines}{footer}"
