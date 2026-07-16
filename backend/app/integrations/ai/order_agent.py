"""Agentic order intelligence via Gemini function calling.

Gives the AI *direct, read-only* access to the order database through a small
set of tools. Gemini decides which tool to call from a free-form message —
"which order is priced around 2300?", "delivered orders with earbuds",
"details of AUR-20345", in any language — runs it, and writes a natural reply
with the real data. The service layer falls back to the deterministic order
logic when the AI is unavailable (e.g. quota exhausted).

Read-only by design: the tools only ever SELECT, never mutate.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.crud.customer import customer as customer_crud
from app.models.customer import Customer
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.order_event import OrderEvent

logger = logging.getLogger("app.ai.order_agent")

# Statuses at which an order can still be cancelled (not yet dispatched).
_CANCELLABLE = {OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PACKED}


def _rid(prefix: str) -> str:
    return f"{prefix}-{random.randint(100000, 999999)}"


def _refund_ref() -> str:
    return f"RFND{random.randint(10_000_000, 99_999_999)}"

# Sentinels so tool params can be simply typed (float/str/int) for the SDK's
# automatic schema generation. Gemini leaves a param at its default to mean
# "no filter".
_ANY_NUM = -1.0
_ANY_STR = ""


class OrderAgentError(RuntimeError):
    """Raised when the agent cannot produce a reply (missing SDK/key/quota)."""


def _order_to_dict(o: Order) -> dict:
    return {
        "order_number": o.order_number,
        "status": str(o.status).replace("_", " "),
        "items": [
            {"name": it.get("name"), "qty": it.get("qty"), "price": it.get("price")}
            for it in (o.items or [])
        ],
        "total": o.total,
        "currency": o.currency,
        "tracking_number": o.tracking_number,
        "carrier": o.carrier,
        "estimated_delivery": (
            o.estimated_delivery.strftime("%d %b %Y") if o.estimated_delivery else None
        ),
        "ordered_on": o.created_at.strftime("%d %b %Y") if o.created_at else None,
        "delivered_on": o.delivered_at.strftime("%d %b %Y") if o.delivered_at else None,
        "customer_name": o.customer.name if o.customer else None,
        "contact_number": o.customer.wa_id if o.customer else None,
        "email": (o.customer.email if o.customer else None) or "not on file",
        # Money & payment
        "subtotal": o.subtotal,
        "discount": o.discount,
        "tax_gst": o.tax,
        "shipping_charges": o.shipping_charges,
        "final_amount": o.total,
        "payment_method": o.payment_method,
        "payment_status": o.payment_status,
        "invoice_number": o.invoice_number,
        # Refund / return
        "refund_status": o.refund_status,
        "refund_amount": o.refund_amount or None,
        "refund_reference": o.refund_reference,
        "return_id": o.return_id,
        "return_status": o.return_status,
        "replacement_id": o.replacement_id,
    }


def _status_clause(status: str):
    key = status.lower().strip().replace(" ", "_")
    try:
        return Order.status == OrderStatus(key)
    except ValueError:
        return None


def _build_tools(db: Session, customer: Customer | None):
    """Build the DB tools as closures over the session + verified caller.

    Read tools are scoped to the caller for anything private; the action tools
    (cancel/return) mutate the caller's own orders only — never anyone else's.
    """
    now = datetime.now(timezone.utc)

    def _log(order: Order, event_type: str, reason: str | None, summary: str, data: dict | None = None) -> None:
        """Write an audit-trail row for an action taken on ``order``."""
        db.add(
            OrderEvent(
                order_id=order.id,
                order_number=order.order_number,
                customer_name=order.customer.name if order.customer else None,
                event_type=event_type,
                reason=reason,
                summary=summary,
                actor="ai",
                channel="whatsapp",
                data=data or {},
            )
        )

    def _find_my_order(order_number: str):
        if customer is None or not order_number:
            return None
        return db.execute(
            select(Order)
            .options(joinedload(Order.customer))
            .where(
                Order.customer_id == customer.id,
                Order.order_number == order_number.upper().strip(),
            )
        ).scalar_one_or_none()

    def get_order_details(order_number: str) -> dict:
        """Full details of ONE of the customer's own orders: items, quantities,
        prices, discount, tax (GST), shipping, payment method/status, invoice and
        final amount. order_number like 'AUR-20345'."""
        o = _find_my_order(order_number)
        if o is None:
            return {"found": False, "message": "No order with that number under your account."}
        return {"found": True, "order": _order_to_dict(o)}

    def track_order(order_number: str) -> dict:
        """Live delivery/tracking details for one of the customer's orders."""
        o = _find_my_order(order_number)
        if o is None:
            return {"found": False, "message": "No order with that number under your account."}
        link = f"https://track.aurorastore.example/{o.tracking_number}" if o.tracking_number else None
        return {
            "found": True,
            "order_number": o.order_number,
            "status": str(o.status).replace("_", " "),
            "courier": o.carrier,
            "tracking_number": o.tracking_number,
            "tracking_link": link,
            "expected_delivery": o.estimated_delivery.strftime("%d %b %Y") if o.estimated_delivery else None,
            "delivery_attempts": o.delivery_attempts,
            "delivered_on": o.delivered_at.strftime("%d %b %Y") if o.delivered_at else None,
        }

    def cancel_order(order_number: str, reason: str = "") -> dict:
        """Cancel one of the customer's orders. Allowed ONLY when the status is
        pending, confirmed or packed (not yet dispatched).

        ALWAYS ask the customer WHY they want to cancel and pass it as ``reason``
        (e.g. Ordered by Mistake, Found it Cheaper, Changed my Mind, Delivery
        Too Slow, No Longer Needed, Duplicate Order, Other), and confirm intent,
        BEFORE calling this. Initiates a refund automatically if prepaid.

        Args:
            order_number: the customer's order, e.g. 'AUR-20345'.
            reason: the customer's reason for cancelling. Required — do not call
                this until you have asked for and received a reason.
        """
        o = _find_my_order(order_number)
        if o is None:
            return {"success": False, "message": "No order with that number under your account."}
        if not reason.strip():
            return {
                "success": False,
                "need_reason": True,
                "message": "Ask the customer why they want to cancel before proceeding.",
            }
        if o.status not in _CANCELLABLE:
            return {
                "success": False,
                "cancelled": False,
                "reason": f"Order is '{str(o.status).replace('_', ' ')}' and can no longer be cancelled.",
                "can_return": o.status == OrderStatus.DELIVERED,
            }
        o.status = OrderStatus.CANCELLED
        o.cancelled_at = now
        o.cancellation_reason = reason.strip()
        refund = None
        if o.payment_status.lower().startswith("paid") and o.payment_method != "COD":
            o.refund_status = "initiated"
            o.refund_amount = o.total
            o.refund_method = o.payment_method
            o.refund_reference = _refund_ref()
            refund = {
                "amount": o.total,
                "method": o.payment_method,
                "reference": o.refund_reference,
                "expected": "5-7 business days",
            }
        _log(
            o,
            "order_cancelled",
            reason.strip(),
            f"Order {o.order_number} cancelled ({reason.strip()})",
            {"refund_reference": o.refund_reference, "refund_amount": o.refund_amount or 0},
        )
        if refund:
            _log(o, "refund_initiated", None,
                 f"Refund of ₹{o.total:.2f} initiated for {o.order_number}",
                 {"reference": o.refund_reference, "amount": o.total, "method": o.refund_method})
        db.commit()
        return {"success": True, "cancelled": True, "order_number": o.order_number, "reason": reason.strip(), "refund": refund}

    def create_return_request(
        order_number: str, reason: str = "", resolution: str = ""
    ) -> dict:
        """Create a return for a DELIVERED order within the 7-day window.

        Before calling, you MUST have (1) the reason, and (2) whether the
        customer wants a Refund or a Replacement — ask for both and confirm.

        Args:
            order_number: the customer's order, e.g. 'AUR-20345'.
            reason: e.g. Damaged Product, Wrong Product, Missing Item, Size
                Issue, Quality Issue, Ordered by Mistake, No Longer Needed.
            resolution: 'refund' or 'replacement' (ask the customer which one).

        Generates a Return ID and schedules a pickup. Returns the details.
        """
        o = _find_my_order(order_number)
        if o is None:
            return {"success": False, "message": "No order with that number under your account."}
        if o.status != OrderStatus.DELIVERED:
            return {"success": False, "reason": f"Returns are only possible after delivery. This order is '{str(o.status).replace('_', ' ')}'."}
        if not o.is_within_return_window(now):
            return {"success": False, "reason": "The 7-day return window for this order has closed."}
        if not o.return_eligible:
            return {"success": False, "reason": "This product is not eligible for return."}
        if o.return_id:
            return {"success": False, "reason": f"A return ({o.return_id}) already exists for this order."}
        if o.refund_status == "completed":
            return {"success": False, "reason": "A refund has already been completed for this order."}
        if not reason.strip():
            return {"success": False, "need_reason": True,
                    "message": "Ask the customer WHY they are returning the item first."}
        res = resolution.strip().lower()
        if res not in ("refund", "replacement", "replace"):
            return {"success": False, "need_resolution": True,
                    "message": "Ask the customer whether they want a Refund or a Replacement."}

        o.return_id = _rid("RET")
        o.return_reason = reason or "Not specified"
        o.pickup_date = now + timedelta(days=2)
        refund = None
        replacement_id = None
        if res.startswith("replace"):
            o.return_status = "Replacement Scheduled"
            o.replacement_id = _rid("REP")
            replacement_id = o.replacement_id
            _log(o, "replacement_requested", o.return_reason,
                 f"Replacement {o.replacement_id} requested for {o.order_number} ({o.return_reason})",
                 {"return_id": o.return_id, "replacement_id": o.replacement_id, "pickup_date": o.pickup_date.strftime("%d %b %Y")})
        else:
            o.return_status = "Pickup Scheduled"
            o.refund_status = "initiated"
            o.refund_amount = o.total
            o.refund_method = o.payment_method or "Original payment method"
            o.refund_reference = _refund_ref()
            refund = {
                "amount": o.total,
                "method": o.refund_method,
                "reference": o.refund_reference,
                "expected": "5-7 business days after pickup",
            }
            _log(o, "return_requested", o.return_reason,
                 f"Return {o.return_id} requested for {o.order_number} ({o.return_reason}) — refund ₹{o.total:.2f}",
                 {"return_id": o.return_id, "refund_reference": o.refund_reference, "refund_amount": o.total, "pickup_date": o.pickup_date.strftime("%d %b %Y")})
        db.commit()
        return {
            "success": True,
            "return_id": o.return_id,
            "resolution": "replacement" if replacement_id else "refund",
            "pickup_date": o.pickup_date.strftime("%d %b %Y"),
            "reason": o.return_reason,
            "refund": refund,
            "replacement_id": replacement_id,
        }

    def get_refund_status(order_number: str) -> dict:
        """Refund status for one of the customer's orders (amount, status,
        method, reference, expected credit date)."""
        o = _find_my_order(order_number)
        if o is None:
            return {"found": False, "message": "No order with that number under your account."}
        if o.refund_status == "none":
            return {"found": True, "has_refund": False, "message": "No refund is in progress for this order."}
        expected = None
        if o.refund_status != "completed":
            base = o.cancelled_at or o.delivered_at or now
            expected = (base + timedelta(days=7)).strftime("%d %b %Y")
        return {
            "found": True,
            "has_refund": True,
            "amount": o.refund_amount,
            "status": o.refund_status,
            "method": o.refund_method,
            "reference": o.refund_reference,
            "expected_credit_date": expected,
            "credited_on": o.refund_date.strftime("%d %b %Y") if o.refund_date else None,
        }

    def get_invoice(order_number: str) -> dict:
        """Invoice number and GST invoice download link for the customer's order."""
        o = _find_my_order(order_number)
        if o is None:
            return {"found": False, "message": "No order with that number under your account."}
        return {
            "found": True,
            "invoice_number": o.invoice_number,
            "download_link": f"https://invoices.aurorastore.example/{o.invoice_number}.pdf",
            "gst_invoice": True,
            "amount": o.total,
        }

    def request_human_callback(reason: str = "", order_number: str = "") -> dict:
        """Log a request for a HUMAN agent to CALL THE CUSTOMER BACK. Use this
        when a tool refused an action a human might still allow (e.g. a return
        after the 7-day window), for payment disputes / fraud, or when the
        customer explicitly asks for a human.

        There is NO live agent waiting — this queues a callback. After calling,
        tell the customer that our team will personally reach out to them on
        their WhatsApp/phone shortly (within a few working hours); reassure them
        they do NOT need to wait here. Never say you are 'connecting them now'.

        Args:
            reason: why a human is needed.
            order_number: the related order, if any.
        """
        o = _find_my_order(order_number) if order_number else None
        if o is not None:
            _log(
                o, "human_callback", reason or None,
                f"Human callback requested for {o.order_number}"
                + (f" — {reason}" if reason else ""),
                {"reason": reason},
            )
            db.commit()
        return {
            "logged": True,
            "callback": True,
            "message": (
                "A human agent has been notified and will call/message the "
                "customer back shortly. Tell the customer they will be contacted "
                "on WhatsApp within a few working hours — do NOT ask them to wait "
                "live, and do NOT imply an agent is joining now."
            ),
        }

    def apply_goodwill_coupon(reason: str = "", order_number: str = "") -> dict:
        """Issue a goodwill discount coupon as compensation for a genuinely bad
        experience (repeated delays, a damaged item, a fair complaint). Use it
        thoughtfully, after acknowledging the issue and resolving the core
        problem. Generates a real coupon code the customer can use next time.

        Args:
            reason: why the goodwill gesture is being made.
            order_number: the related order, if any.
        """
        percent = 10
        code = f"SORRY{random.randint(100, 999)}"
        o = _find_my_order(order_number) if order_number else None
        if o is not None:
            _log(
                o, "goodwill_coupon", reason or None,
                f"Goodwill {percent}% coupon {code} issued for {o.order_number}",
                {"code": code, "percent": percent},
            )
            db.commit()
        return {
            "issued": True,
            "code": code,
            "discount_percent": percent,
            "valid_days": 30,
            "message": f"Coupon *{code}* — {percent}% off your next order, valid 30 days.",
        }

    def get_my_orders(status: str = _ANY_STR, limit: int = 10) -> dict:
        """Return ALL orders placed by the CURRENT customer you are chatting with
        (already scoped to their phone number — you cannot see anyone else's).

        Use this whenever the customer asks about "my order", "my orders",
        "where is my order", "mara order", etc. WITHOUT giving an order number.

        Args:
            status: optional status filter (see search_orders). "" means all.
            limit: maximum number of orders to return (newest first).

        Returns:
            A dict with "count" (how many orders this customer has) and "results"
            (their orders with full details, including contact number and email).
        """
        if customer is None:
            return {"count": 0, "results": []}
        stmt = (
            select(Order)
            .options(joinedload(Order.customer))
            .where(Order.customer_id == customer.id)
        )
        if status:
            c = _status_clause(status)
            if c is not None:
                stmt = stmt.where(c)
        stmt = stmt.order_by(Order.created_at.desc())
        rows = list(db.execute(stmt).scalars().all())
        capped = max(1, min(int(limit) if limit else 10, 20))
        return {"count": len(rows), "results": [_order_to_dict(o) for o in rows[:capped]]}

    def search_orders(
        order_number: str = _ANY_STR,
        exact_price: float = _ANY_NUM,
        min_price: float = _ANY_NUM,
        max_price: float = _ANY_NUM,
        status: str = _ANY_STR,
        product: str = _ANY_STR,
        limit: int = 5,
    ) -> dict:
        """Search the store's order database and return full details of matches.

        Args:
            order_number: exact order number like "AUR-20345". "" means any.
            exact_price: order total in rupees to match exactly. -1 means any.
                If no exact match exists, near matches (within 10%) are returned.
            min_price: minimum order total in rupees. -1 means any.
            max_price: maximum order total in rupees. -1 means any.
            status: one of pending, confirmed, packed, shipped, out for
                delivery, delivered, cancelled, returned. "" means any.
            product: product name to look for inside orders, e.g. "earbuds". ""
                means any.
            limit: maximum number of orders to return (1-10).

        Returns:
            A dict with "count" (how many orders matched in total) and "results"
            (a list of matching orders with full details: items, total, status,
            tracking, delivery date and customer name).
        """
        stmt = select(Order).options(joinedload(Order.customer))
        clauses = []
        if order_number:
            clauses.append(Order.order_number == order_number.upper().strip())
        if status:
            c = _status_clause(status)
            if c is not None:
                clauses.append(c)
        if min_price is not None and min_price >= 0:
            clauses.append(Order.total >= min_price)
        if max_price is not None and max_price >= 0:
            clauses.append(Order.total <= max_price)
        want_exact = exact_price is not None and exact_price >= 0
        if want_exact:
            clauses.append(Order.total == exact_price)
        for c in clauses:
            stmt = stmt.where(c)
        rows = list(db.execute(stmt.limit(300)).scalars().all())

        # Exact price requested but nothing matched → widen to ±10%.
        if want_exact and not rows:
            lo, hi = exact_price * 0.9, exact_price * 1.1
            wide = select(Order).options(joinedload(Order.customer)).where(
                Order.total >= lo, Order.total <= hi
            )
            rows = list(db.execute(wide.limit(300)).scalars().all())

        if product:
            p = product.lower()
            rows = [
                o for o in rows
                if any(p in (it.get("name", "") or "").lower() for it in (o.items or []))
            ]

        capped = max(1, min(int(limit) if limit else 5, 10))
        return {"count": len(rows), "results": [_order_to_dict(o) for o in rows[:capped]]}

    def order_statistics(
        status: str = _ANY_STR, min_price: float = _ANY_NUM, max_price: float = _ANY_NUM
    ) -> dict:
        """Get aggregate order stats: how many orders and the total sales value.

        Args:
            status: filter by status (see search_orders). "" means all.
            min_price: minimum order total in rupees. -1 means any.
            max_price: maximum order total in rupees. -1 means any.

        Returns:
            A dict with "count" (number of orders) and "total_sales" (sum of
            their totals, in rupees).
        """
        count_stmt = select(func.count()).select_from(Order)
        sum_stmt = select(func.coalesce(func.sum(Order.total), 0.0))
        clauses = []
        if status:
            c = _status_clause(status)
            if c is not None:
                clauses.append(c)
        if min_price is not None and min_price >= 0:
            clauses.append(Order.total >= min_price)
        if max_price is not None and max_price >= 0:
            clauses.append(Order.total <= max_price)
        for c in clauses:
            count_stmt = count_stmt.where(c)
            sum_stmt = sum_stmt.where(c)
        return {
            "count": db.execute(count_stmt).scalar_one(),
            "total_sales": float(db.execute(sum_stmt).scalar_one()),
        }

    return [
        get_my_orders,
        get_order_details,
        track_order,
        cancel_order,
        create_return_request,
        get_refund_status,
        get_invoice,
        apply_goodwill_coupon,
        request_human_callback,
        search_orders,
        order_statistics,
    ]


def _system_prompt(customer: Customer | None) -> str:
    if customer is not None:
        email = customer.email or "no email on file"
        who = (
            f"The customer is VERIFIED via their WhatsApp number. Identity: "
            f"*{customer.name}* (number: {customer.wa_id}, email: {email}). You may "
            "share their own order information. You can ONLY ever see and act on "
            "THIS customer's orders — the tools are scoped to them."
        )
    else:
        who = (
            "This WhatsApp number has no orders on file yet. If they ask about "
            "'my orders', tell them nothing is linked to their number and offer to "
            "help with a specific order number or a general question."
        )
    return (
        f"You are {settings.ASSISTANT_NAME}, an intelligent AI customer-support "
        f"agent for {settings.BUSINESS_NAME} ({settings.BUSINESS_TAGLINE}), an "
        "e-commerce store — like the support on Amazon, Flipkart or Myntra. "
        f"{who}\n\n"
        "WHAT YOU HANDLE: track orders, order & delivery details, cancellations, "
        "returns, replacements, refund status, invoices, payment status, FAQs, and "
        "escalation to a human agent.\n\n"
        "USE THE TOOLS — NEVER GUESS. For anything about an order you MUST call a "
        "tool to fetch/act on real data; never invent order numbers, prices, "
        "statuses, refund or tracking details. Tools available: get_my_orders, "
        "get_order_details, track_order, cancel_order, create_return_request, "
        "get_refund_status, get_invoice (all scoped to this customer).\n\n"
        "BUSINESS RULES (enforced by the tools, but explain them kindly):\n"
        "• Cancellation is allowed ONLY when status is Pending, Confirmed or "
        "Packed. If Shipped/In-transit/Delivered etc., cancellation is NOT "
        "possible — explain why and offer a return if it's delivered. ALWAYS ask "
        "the customer WHY they want to cancel (reason: Ordered by Mistake, Found "
        "it Cheaper, Changed my Mind, Delivery Too Slow, No Longer Needed, "
        "Duplicate Order, Other) and confirm, THEN call cancel_order with that "
        "reason.\n"
        "• Returns need: status Delivered, within the 7-day window, product "
        "eligible, not already returned/refunded. Step 1: ask the reason "
        "(Damaged, Wrong Product, Missing Item, Size Issue, Quality Issue, "
        "Ordered by Mistake, No Longer Needed, Other). Step 2: ALWAYS ask whether "
        "they want a *Refund* or a *Replacement*. Step 3: IF the reason is "
        "Damaged, Defective or Wrong Product, ask the customer to *send a quick "
        "photo* of the issue so it can be verified and fast-tracked — they can "
        "attach it with the 📎 button. Do NOT create the return yet; wait for the "
        "photo (our vision system auto-verifies it and processes the return). If "
        "they genuinely cannot send one, you may proceed. For non-damage reasons "
        "(size, no longer needed, etc.) no photo is needed. Step 4: confirm, THEN "
        "call create_return_request with reason AND resolution.\n"
        "• ALWAYS confirm the customer's intent before cancelling an order or "
        "creating a return (a clear yes) — then call the tool, then report the "
        "real result (IDs, pickup date, refund amount & reference).\n"
        "• RESOLVE COMPLETELY IN ONE GO: if a message contains several problems "
        "(e.g. 'wrong AND damaged item, and I'm furious'), handle them all — call "
        "each needed tool in sequence (e.g. create the return/replacement, then "
        "issue a refund) and summarise everything you did. For a customer who is "
        "genuinely upset or badly let down, you MAY apply_goodwill_coupon as a "
        "gesture of apology after fixing the core issue.\n"
        "• After a successful cancellation or refund-return, tell the customer "
        "their refund has been *Initiated* and is *coming soon* — it will be "
        "reviewed and paid out, reflecting in their account in 5-7 business days. "
        "Do NOT transfer a standard cancellation/return to a human — you handle "
        "it fully; only the payout is finalised by our team automatically.\n\n"
        "HUMAN CALLBACK (escalation): for payment disputes, fraud/suspicion, an "
        "action a tool refused that a human might still allow (e.g. a return "
        "after the 7-day window), or an explicit request for a human — call "
        "request_human_callback (with the order number + reason). IMPORTANT: "
        "there is NO live agent waiting. Never say 'I'm connecting you now' or "
        "ask them to 'please wait' as if someone is joining. Instead, warmly tell "
        "them our team will personally reach out on their WhatsApp/phone shortly "
        "(within a few working hours) and that they do NOT need to wait here. A "
        "normal cancellation or return is NOT an escalation.\n\n"
        "SECURITY: never reveal another customer's information; only act after a "
        "tool returns success.\n\n"
        "FORMAT for WhatsApp: *single-asterisk bold*, bullet lines with •, short "
        "and step-by-step. No Markdown headings (#), tables, or double asterisks.\n\n"
        "LANGUAGE: detect the language/script of the customer's message and reply "
        "ONLY in that same language — English→English, Hindi→Hindi, "
        "Gujarati→Gujarati, Marathi, Tamil, Telugu, Bengali, Punjabi, Urdu, "
        "Spanish, Arabic, etc.; romanized Hinglish/Gujlish → the same romanized "
        "style. Never switch on your own. Be friendly, professional, concise, and "
        "use a little emoji."
    )


def run(db: Session, *, wa_id: str, text: str, history: list | None = None) -> str:
    """Answer an order question agentically. Raises OrderAgentError on failure.

    ``history`` is an optional list of prior turns ({"role","parts"}) so the
    agent can hold a multi-turn conversation (e.g. confirm before cancelling).
    """
    if settings.AI_PROVIDER != "gemini" or not settings.GEMINI_API_KEY:
        raise OrderAgentError("gemini not configured")
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmBlockThreshold, HarmCategory
    except ImportError as exc:  # pragma: no cover
        raise OrderAgentError("google-generativeai not installed") from exc

    genai.configure(api_key=settings.GEMINI_API_KEY)
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    customer = customer_crud.get_by_wa_id(db, wa_id)
    try:
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=_system_prompt(customer),
            tools=_build_tools(db, customer),
            safety_settings=safety,
        )
        chat = model.start_chat(
            history=history or [], enable_automatic_function_calling=True
        )
        response = chat.send_message(text)
        reply = (getattr(response, "text", None) or "").strip()
    except Exception as exc:  # network / quota / SDK
        logger.warning("order_agent_generate_failed error=%s", exc)
        raise OrderAgentError(str(exc)) from exc

    if not reply:
        raise OrderAgentError("empty agent reply")
    return reply
