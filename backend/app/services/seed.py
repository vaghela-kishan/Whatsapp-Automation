"""Demo data seeding.

Populates a fresh database with believable customers, orders, FAQs, and a few
seeded conversations so the dashboard looks alive on first run. Idempotent:
does nothing if customers already exist.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.enums import (
    ConversationStatus,
    Intent,
    MessageDirection,
    OrderStatus,
    SenderType,
)
from app.models.faq import FAQ
from app.models.message import Message
from app.models.order import Order
from app.models.order_event import OrderEvent

logger = logging.getLogger("app.seed")


def _now() -> datetime:
    return datetime.now(timezone.utc)


_FAQS = [
    # ------------------------------------------------------------------ Orders
    {
        "question": "How do I track my order?",
        "answer": (
            "Easy! 📦 Just send me your order number (like *AUR-10432*) and I'll share "
            "the live status instantly. You also get a tracking link over WhatsApp the "
            "moment your order ships."
        ),
        "category": "Orders",
        "keywords": "track tracking order status where is my package parcel find locate link",
    },
    {
        "question": "What do the order statuses mean?",
        "answer": (
            "Here's the journey your order takes:\n"
            "🕐 *Pending* – received, awaiting confirmation\n"
            "✅ *Confirmed* – being prepared\n"
            "📦 *Packed* – ready to ship\n"
            "🚚 *Shipped* – on the way\n"
            "🛵 *Out for delivery* – arriving today\n"
            "🎉 *Delivered* – all done!"
        ),
        "category": "Orders",
        "keywords": "status meaning confirmed packed shipped delivered pending stages what does mean",
    },
    {
        "question": "How do I cancel my order?",
        "answer": (
            "You can cancel any order *before it ships* for a full refund. Share your "
            "order number and I'll check if it's still cancellable, then connect you "
            "with our team to process it. ❌"
        ),
        "category": "Orders",
        "keywords": "cancel cancellation stop order remove undo",
    },
    {
        "question": "Can I change my delivery address?",
        "answer": (
            "Yes — as long as your order *hasn't shipped yet*. 📍 Tell me your order "
            "number and the new address, and I'll get it updated for you."
        ),
        "category": "Orders",
        "keywords": "change edit update delivery address shipping location move pincode",
    },
    {
        "question": "Can I modify my order after placing it?",
        "answer": (
            "If your order is still *Confirmed* or *Packed*, we can often add, remove, or "
            "swap items. 🛍️ Send your order number and what you'd like to change."
        ),
        "category": "Orders",
        "keywords": "modify change edit add remove swap items order after placing update",
    },
    {
        "question": "My order is delayed — what should I do?",
        "answer": (
            "So sorry about the wait! ⏳ Share your order number and I'll check exactly "
            "where it is. If it's stuck, I'll escalate it to our team right away to sort "
            "it out."
        ),
        "category": "Orders",
        "keywords": "delayed late slow not arrived stuck taking long overdue where",
    },
    {
        "question": "How will I know when my order ships?",
        "answer": (
            "The moment your order is dispatched, you'll get a WhatsApp message with the "
            "*tracking number* and a live link. 🔔 No need to check manually!"
        ),
        "category": "Orders",
        "keywords": "notification shipped dispatch update alert sms know when notify",
    },
    {
        "question": "What if I received the wrong or damaged item?",
        "answer": (
            "That's not the experience we want for you. 😟 Send your order number and a "
            "quick note about the issue — I'll arrange a free replacement or refund and "
            "loop in a human teammate."
        ),
        "category": "Orders",
        "keywords": "wrong damaged defective broken incorrect missing item received faulty",
    },
    {
        "question": "Can I reorder something I bought before?",
        "answer": (
            "Absolutely! 🔁 Tell me the previous order number or the product name and I'll "
            "help you place the same order again in seconds."
        ),
        "category": "Orders",
        "keywords": "reorder buy again repeat previous order same purchase repurchase",
    },
    {
        "question": "How do I get an invoice or bill for my order?",
        "answer": (
            "Happy to help! 🧾 Share your order number and I'll send you the GST invoice "
            "for that order as a PDF over WhatsApp."
        ),
        "category": "Orders",
        "keywords": "invoice bill receipt gst tax document proof purchase pdf",
    },
    {
        "question": "Can I schedule my delivery for a specific date?",
        "answer": (
            "For most pin codes, yes! 📅 You can pick a preferred delivery date at "
            "checkout, or tell me your order number and the date you'd like."
        ),
        "category": "Orders",
        "keywords": "schedule choose preferred date time slot delivery specific when book",
    },
    {
        "question": "What if I'm not available at delivery?",
        "answer": (
            "No worries — our courier will *reattempt delivery up to 3 times*. 🛵 You can "
            "also reschedule or leave delivery instructions via the tracking link."
        ),
        "category": "Orders",
        "keywords": "not home available missed delivery reattempt reschedule absent nobody",
    },
    # ---------------------------------------------------------------- Shipping
    {
        "question": "What are your delivery charges?",
        "answer": (
            "Delivery is *free* on all orders above ₹499. 🚚 For orders below that, "
            "a flat ₹49 fee applies. Most orders arrive within 3–5 business days."
        ),
        "category": "Shipping",
        "keywords": "delivery charge shipping fee cost free postage price",
    },
    {
        "question": "How long does delivery take?",
        "answer": (
            "Standard delivery takes *3–5 business days*. Metro cities often get it in "
            "2–3 days. You'll get a tracking link the moment your order ships. 📦"
        ),
        "category": "Shipping",
        "keywords": "how long delivery time days arrive when shipping duration fast",
    },
    {
        "question": "Do you offer same-day or express delivery?",
        "answer": (
            "In select metro cities, yes! ⚡ Choose *Express* at checkout for same-day or "
            "next-day delivery. Availability is shown based on your pin code."
        ),
        "category": "Shipping",
        "keywords": "same day express fast urgent quick delivery next day speed priority",
    },
    {
        "question": "Do you deliver on weekends and holidays?",
        "answer": (
            "Yes 📆 — we deliver *Monday to Saturday*, and on most public holidays in "
            "major cities. Sundays are limited to express orders."
        ),
        "category": "Shipping",
        "keywords": "weekend sunday saturday holiday delivery days deliver public",
    },
    {
        "question": "Do you ship internationally?",
        "answer": (
            "Right now we ship *across India only* 🇮🇳. International shipping is coming "
            "soon — I can add you to the waitlist if you'd like!"
        ),
        "category": "Shipping",
        "keywords": "international abroad overseas outside country global worldwide ship",
    },
    # ----------------------------------------------------------------- Returns
    {
        "question": "What is your return policy?",
        "answer": (
            "You can return most items within *7 days* of delivery for a full refund. "
            "Items must be unused and in original packaging. Start a return from "
            "'My Orders' or just tell me your order number and I'll help. ↩️"
        ),
        "category": "Returns",
        "keywords": "return policy refund exchange replace 7 days money back send",
    },
    {
        "question": "When will I receive my refund?",
        "answer": (
            "Once we receive and inspect your return, refunds are processed within "
            "*5–7 business days* 💸 to your original payment method. I'll notify you at "
            "each step."
        ),
        "category": "Returns",
        "keywords": "refund time money back processed days when receive credited return",
    },
    {
        "question": "How do I return part of my order?",
        "answer": (
            "You can return individual items — no need to send the whole order back. 📦 "
            "Just tell me your order number and which item(s) you'd like to return."
        ),
        "category": "Returns",
        "keywords": "return part partial single item one product order some",
    },
    # ---------------------------------------------------------------- Payments
    {
        "question": "Which payment methods do you accept?",
        "answer": (
            "We accept UPI, all major credit/debit cards, net banking, popular wallets, "
            "and Cash on Delivery (COD) on eligible orders. 💳"
        ),
        "category": "Payments",
        "keywords": "payment methods upi card cod cash delivery wallet netbanking pay how",
    },
    {
        "question": "Is Cash on Delivery (COD) available?",
        "answer": (
            "Yes! 💵 COD is available on most orders up to ₹20,000. You'll see the option "
            "at checkout if your pin code and cart qualify."
        ),
        "category": "Payments",
        "keywords": "cod cash on delivery pay later available option checkout",
    },
    {
        "question": "Is it safe to pay online?",
        "answer": (
            "100%. 🔒 All payments run through *PCI-DSS compliant, encrypted* gateways. "
            "We never store your card details on our servers."
        ),
        "category": "Payments",
        "keywords": "safe secure online payment encryption trust card details fraud",
    },
    # ---------------------------------------------------------------- Warranty
    {
        "question": "Do you offer a warranty?",
        "answer": (
            "Yes! Electronics come with a *1-year manufacturer warranty*. Keep your "
            "order confirmation as proof of purchase. Need to claim it? I can start that "
            "for you. 🛡️"
        ),
        "category": "Warranty",
        "keywords": "warranty guarantee repair defect broken electronics claim year",
    },
    # ----------------------------------------------------------------- General
    {
        "question": "What are your customer support hours?",
        "answer": (
            "Our human team is available *Mon–Sat, 9am–8pm IST*. I'm here 24/7 though, so "
            "ask me anything anytime! 🌙"
        ),
        "category": "General",
        "keywords": "support hours timing open available contact time when human team",
    },
]


# (name, wa_id, email)
_CUSTOMERS = [
    ("Priya Sharma", "919876500001", "priya@example.com"),
    ("Arjun Mehta", "919876500002", "arjun@example.com"),
    ("Neha Verma", "919876500003", "neha@example.com"),
    ("Rohan Kapoor", "919876500004", None),
    ("Ananya Iyer", "919876500005", "ananya@example.com"),
]


def _seed_orders(db: Session, customers: dict[str, Customer]) -> None:
    now = _now()
    orders = [
        Order(
            order_number="AUR-10432",
            customer_id=customers["919876500001"].id,
            status=OrderStatus.SHIPPED,
            items=[{"name": "Wireless Earbuds Pro", "qty": 1, "price": 3499.0}],
            total=3499.0,
            tracking_number="TRK889201NYC",
            carrier="BlueDart",
            estimated_delivery=now + timedelta(days=2),
        ),
        Order(
            order_number="AUR-10455",
            customer_id=customers["919876500002"].id,
            status=OrderStatus.OUT_FOR_DELIVERY,
            items=[
                {"name": "Smart Watch Series 6", "qty": 1, "price": 8999.0},
                {"name": "Watch Strap (Black)", "qty": 2, "price": 499.0},
            ],
            total=9997.0,
            tracking_number="TRK773100DEL",
            carrier="Delhivery",
            estimated_delivery=now,
        ),
        Order(
            order_number="AUR-10478",
            customer_id=customers["919876500003"].id,
            status=OrderStatus.DELIVERED,
            items=[{"name": "Bluetooth Speaker Mini", "qty": 1, "price": 1999.0}],
            total=1999.0,
            tracking_number="TRK551204MUM",
            carrier="Ekart",
            estimated_delivery=now - timedelta(days=1),
        ),
        Order(
            order_number="AUR-10501",
            customer_id=customers["919876500004"].id,
            status=OrderStatus.PACKED,
            items=[{"name": "USB-C Fast Charger 65W", "qty": 1, "price": 1499.0}],
            total=1499.0,
        ),
        Order(
            order_number="AUR-10533",
            customer_id=customers["919876500005"].id,
            status=OrderStatus.CONFIRMED,
            items=[{"name": "Noise Cancelling Headphones", "qty": 1, "price": 5999.0}],
            total=5999.0,
        ),
    ]
    demo_rng = random.Random(4242)
    for o in orders:
        _finalize_order(o, demo_rng, now)
    # Make AUR-10478 recently delivered so return/refund demos work on it.
    orders[2].delivered_at = now - timedelta(days=2)
    orders[2].delivery_attempts = 1
    orders[2].return_eligible = True
    db.add_all(orders)


def _seed_conversations(db: Session, customers: dict[str, Customer]) -> None:
    """A couple of pre-baked threads so the inbox isn't empty."""
    now = _now()

    # Thread 1: resolved order-status chat with Priya.
    c1 = Conversation(
        customer_id=customers["919876500001"].id,
        status=ConversationStatus.RESOLVED,
        subject="Order status — AUR-10432",
        last_message_at=now - timedelta(hours=3),
        last_message_preview="🚚 Your order has shipped and is on its way!",
    )
    db.add(c1)
    db.flush()
    db.add_all([
        Message(
            conversation_id=c1.id,
            direction=MessageDirection.INBOUND,
            sender=SenderType.CUSTOMER,
            content="Hi, where is my order AUR-10432?",
            intent=Intent.ORDER_STATUS,
            created_at=now - timedelta(hours=3, minutes=2),
        ),
        Message(
            conversation_id=c1.id,
            direction=MessageDirection.OUTBOUND,
            sender=SenderType.AI,
            content=(
                "Here's the latest on *AUR-10432*:\n\n🚚 Your order has shipped and is "
                "on its way!\n📍 Tracking: TRK889201NYC (BlueDart)"
            ),
            confidence=0.92,
            created_at=now - timedelta(hours=3),
        ),
    ])

    # Thread 2: escalated complaint from Arjun waiting on a human.
    c2 = Conversation(
        customer_id=customers["919876500002"].id,
        status=ConversationStatus.NEEDS_HUMAN,
        subject="Refund request",
        last_message_at=now - timedelta(minutes=25),
        last_message_preview="Connecting you with a human teammate…",
    )
    db.add(c2)
    db.flush()
    db.add_all([
        Message(
            conversation_id=c2.id,
            direction=MessageDirection.INBOUND,
            sender=SenderType.CUSTOMER,
            content="I received a damaged speaker and want a refund!",
            intent=Intent.SUPPORT,
            created_at=now - timedelta(minutes=26),
        ),
        Message(
            conversation_id=c2.id,
            direction=MessageDirection.OUTBOUND,
            sender=SenderType.AI,
            content=(
                "I'm so sorry to hear that! 😟 I'm connecting you with a human teammate "
                "who'll sort out your refund right away."
            ),
            confidence=0.45,
            created_at=now - timedelta(minutes=25),
        ),
    ])


# --- Bulk catalogue for generating a realistic, large order book -----------

# (name, base_price)
_PRODUCTS = [
    ("Wireless Earbuds Pro", 3499), ("Smart Watch Series 6", 8999),
    ("Bluetooth Speaker Mini", 1999), ("USB-C Fast Charger 65W", 1499),
    ("Noise Cancelling Headphones", 5999), ("Power Bank 20000mAh", 2499),
    ("Mechanical Keyboard RGB", 4499), ("Wireless Mouse", 1299),
    ("4K Action Camera", 12999), ("Fitness Band", 2999),
    ("Smart LED Bulb", 799), ("Portable SSD 1TB", 7999),
    ("Gaming Headset", 3999), ("1080p Webcam", 2299),
    ("Phone Gimbal Stabilizer", 6499), ("Aviator Sunglasses", 1799),
    ("Leather Wallet", 1299), ("Travel Backpack 25L", 2199),
    ("Steel Water Bottle", 699), ("LED Desk Lamp", 1499),
    ("Ceramic Coffee Mug Set", 999), ("Scented Candle Trio", 599),
    ("Mechanical Pencil Set", 449), ("Wireless Charger Pad", 1599),
    ("Smartphone Tripod", 1199), ("Laptop Sleeve 14\"", 899),
]

_FIRST_NAMES = (
    "Priya Arjun Neha Rohan Ananya Vikram Sneha Karan Pooja Rahul Divya Amit "
    "Kavya Sanjay Meera Nikhil Riya Aditya Isha Varun Tara Dev Sara Manish "
    "Anjali Rohit Simran Yash Nisha Gaurav Kiran Deepak Aarti Suresh Ritu "
    "Vishal Preeti Ajay Sunita Rajesh Naina Harsh Payal Mohit Shreya Akash"
).split()
_LAST_NAMES = (
    "Sharma Mehta Verma Kapoor Iyer Patel Shah Reddy Nair Gupta Singh Desai "
    "Joshi Rao Chopra Malhotra Bose Das Kulkarni Pillai Agarwal Bhatt Menon"
).split()

# Status distribution — most orders end up delivered, a few in earlier stages.
_STATUS_WEIGHTS = [
    (OrderStatus.DELIVERED, 46),
    (OrderStatus.SHIPPED, 14),
    (OrderStatus.OUT_FOR_DELIVERY, 8),
    (OrderStatus.PACKED, 8),
    (OrderStatus.CONFIRMED, 10),
    (OrderStatus.PENDING, 6),
    (OrderStatus.CANCELLED, 5),
    (OrderStatus.RETURNED, 3),
]
_CARRIERS = ["BlueDart", "Delhivery", "Ekart", "DTDC", "XpressBees", "Shadowfax"]

TOTAL_ORDERS_TARGET = 1000  # total orders in a freshly seeded database

_PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Wallet", "COD"]
_RETURN_REASONS = [
    "Damaged Product", "Wrong Product", "Missing Item", "Size Issue",
    "Quality Issue", "Ordered by Mistake", "No Longer Needed",
]
_CANCEL_REASONS = [
    "Ordered by Mistake", "Found it Cheaper", "Changed my Mind",
    "Delivery Too Slow", "No Longer Needed", "Duplicate Order",
]


def _finalize_order(order: Order, rng: random.Random, now: datetime) -> Order:
    """Fill the money breakdown, payment, invoice and status-dependent fields
    (delivery/refund/return) so every order looks like a real e-commerce order."""
    subtotal = round(
        sum(float(it.get("price", 0)) * int(it.get("qty", 1)) for it in (order.items or [])),
        2,
    )
    discount = round(subtotal * rng.choice([0, 0, 0, 0.05, 0.10, 0.15]), 2)
    taxable = subtotal - discount
    tax = round(taxable * 0.18, 2)  # 18% GST
    shipping = 0.0 if subtotal >= 499 else 49.0
    order.subtotal = subtotal
    order.discount = discount
    order.tax = tax
    order.shipping_charges = shipping
    order.total = round(taxable + tax + shipping, 2)

    pm = rng.choice(_PAYMENT_METHODS)
    order.payment_method = pm
    if pm == "COD":
        order.payment_status = "Paid" if order.status == OrderStatus.DELIVERED else "Pending (COD)"
    else:
        order.payment_status = "Paid"
    year = order.created_at.year if order.created_at else now.year
    order.invoice_number = f"INV-{year}-{rng.randint(100000, 999999)}"

    if order.status == OrderStatus.DELIVERED:
        base = order.created_at or (now - timedelta(days=rng.randint(2, 20)))
        delivered = min(base + timedelta(days=rng.randint(1, 4)), now - timedelta(hours=2))
        order.delivered_at = delivered
        order.delivery_attempts = rng.choice([1, 1, 1, 2])
        order.return_eligible = rng.random() < 0.9
    elif order.status in (OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY):
        order.delivery_attempts = rng.choice([0, 0, 1])

    if order.status == OrderStatus.CANCELLED:
        order.cancelled_at = (order.created_at or now) + timedelta(days=rng.randint(0, 2))
        order.cancellation_reason = rng.choice(_CANCEL_REASONS)
        if pm != "COD":
            st = rng.choice(["completed", "processing", "initiated"])
            order.refund_status = st
            order.refund_amount = order.total
            order.refund_method = pm
            order.refund_reference = f"RFND{rng.randint(10_000_000, 99_999_999)}"
            if st == "completed":
                order.refund_date = order.cancelled_at + timedelta(days=rng.randint(3, 7))

    if order.status == OrderStatus.RETURNED:
        order.delivered_at = now - timedelta(days=rng.randint(8, 30))
        order.return_id = f"RET-{rng.randint(100000, 999999)}"
        order.return_status = "Completed"
        order.return_reason = rng.choice(_RETURN_REASONS)
        order.refund_status = "completed"
        order.refund_amount = order.total
        order.refund_method = pm if pm != "COD" else "Bank Transfer"
        order.refund_reference = f"RFND{rng.randint(10_000_000, 99_999_999)}"
        order.refund_date = order.delivered_at + timedelta(days=rng.randint(3, 7))
    return order


def _generate_bulk(db: Session, named_customers: list[Customer], existing_orders: int) -> int:
    """Create a large, believable set of customers and orders. Returns #orders."""
    rng = random.Random(20260709)  # deterministic → reproducible dataset
    now = _now()

    statuses = [s for s, _ in _STATUS_WEIGHTS]
    weights = [w for _, w in _STATUS_WEIGHTS]

    # ~250 customers total; reuse the 5 named ones and add the rest.
    extra_customers = 245
    customers: list[Customer] = list(named_customers)
    for i in range(extra_customers):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        wa = f"9190{i:08d}"
        has_email = rng.random() < 0.7
        customers.append(
            Customer(
                name=f"{first} {last}",
                wa_id=wa,
                email=f"{first.lower()}.{last.lower()}{i}@example.com" if has_email else None,
            )
        )
    db.add_all(customers[len(named_customers):])
    db.flush()

    to_create = max(0, TOTAL_ORDERS_TARGET - existing_orders)
    orders: list[Order] = []
    for n in range(to_create):
        cust = rng.choice(customers)
        # 1–3 line items
        n_items = rng.choices([1, 2, 3], weights=[70, 22, 8])[0]
        items = []
        for _ in range(n_items):
            name, base = rng.choice(_PRODUCTS)
            qty = rng.choices([1, 2, 3], weights=[80, 15, 5])[0]
            items.append({"name": name, "qty": qty, "price": float(base)})

        status = rng.choices(statuses, weights=weights)[0]
        created = now - timedelta(days=rng.randint(0, 74), hours=rng.randint(0, 23))

        order = Order(
            order_number=f"AUR-{20001 + n}",
            customer_id=cust.id,
            status=status,
            items=items,
            currency="INR",
        )
        order.created_at = created
        if status in (OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED):
            order.tracking_number = f"TRK{rng.randint(100000, 999999)}IN"
            order.carrier = rng.choice(_CARRIERS)
            order.estimated_delivery = created + timedelta(days=rng.randint(2, 6))
        _finalize_order(order, rng, now)
        orders.append(order)

    # Batch the inserts so SQLite stays snappy.
    for start in range(0, len(orders), 200):
        db.add_all(orders[start:start + 200])
        db.flush()

    # Audit-trail history for orders that were already cancelled or returned,
    # so the activity feed isn't empty on first run.
    id_to_name = {c.id: c.name for c in customers}
    events: list[OrderEvent] = []
    for o in orders:
        name = id_to_name.get(o.customer_id)
        if o.status == OrderStatus.CANCELLED:
            ev = OrderEvent(
                order_id=o.id, order_number=o.order_number, customer_name=name,
                event_type="order_cancelled", reason=o.cancellation_reason,
                summary=f"Order {o.order_number} cancelled ({o.cancellation_reason})",
                data={"refund_reference": o.refund_reference, "refund_amount": o.refund_amount or 0},
            )
            ev.created_at = o.cancelled_at or now
            events.append(ev)
        elif o.status == OrderStatus.RETURNED:
            ev = OrderEvent(
                order_id=o.id, order_number=o.order_number, customer_name=name,
                event_type="return_requested", reason=o.return_reason,
                summary=f"Return {o.return_id} for {o.order_number} ({o.return_reason}) — refund ₹{o.total:.0f}",
                data={"return_id": o.return_id, "refund_reference": o.refund_reference},
            )
            ev.created_at = o.refund_date or o.delivered_at or now
            events.append(ev)
    db.add_all(events)
    db.flush()
    logger.info("seeded_order_events count=%d", len(events))

    return len(orders)


def seed_if_empty(db: Session) -> bool:
    """Seed demo data when the customers table is empty. Returns True if seeded."""
    existing = db.execute(select(Customer.id).limit(1)).first()
    if existing is not None:
        return False

    logger.info("seeding_demo_data")

    db.add_all([FAQ(**f) for f in _FAQS])

    customer_objs: dict[str, Customer] = {}
    named: list[Customer] = []
    for name, wa_id, email in _CUSTOMERS:
        c = Customer(name=name, wa_id=wa_id, email=email)
        db.add(c)
        customer_objs[wa_id] = c
        named.append(c)
    db.flush()  # assign ids

    _seed_orders(db, customer_objs)  # 5 specific demo orders (AUR-10432, …)
    _seed_conversations(db, customer_objs)

    # Fill out the order book to ~1000 orders across ~250 customers.
    bulk = _generate_bulk(db, named, existing_orders=5)

    db.commit()
    logger.info(
        "seed_complete customers=%d orders=%d faqs=%d",
        250,
        5 + bulk,
        len(_FAQS),
    )
    return True


def sync_faqs(db: Session) -> int:
    """Insert any catalog FAQ not already present (matched by question text).

    Idempotent and safe to run on every startup — this lets us ship new FAQs
    (e.g. more order questions) to an *existing* database without a reseed,
    preserving all live conversations and hit counts.
    """
    existing_questions = {
        q for (q,) in db.execute(select(FAQ.question)).all()
    }
    added = [FAQ(**f) for f in _FAQS if f["question"] not in existing_questions]
    if added:
        db.add_all(added)
        db.commit()
        logger.info("faqs_synced added=%d", len(added))
    return len(added)
