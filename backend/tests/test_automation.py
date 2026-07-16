"""Tests for the WhatsApp automation pipeline."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.enums import Intent
from app.services import intent as intent_svc


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Where is my order AUR-10432?", Intent.ORDER_STATUS),
        ("track my order", Intent.ORDER_STATUS),
        ("What is your return policy?", Intent.FAQ),
        ("How long does delivery take?", Intent.FAQ),
        ("Do you accept UPI?", Intent.FAQ),
        ("My product arrived damaged, I want a refund", Intent.SUPPORT),
        ("I want to cancel my order AUR-10432", Intent.SUPPORT),
        ("hello", Intent.GREETING),
        ("hi there", Intent.GREETING),
        # Aggregate order-book queries.
        ("how many orders do you have?", Intent.ORDER_QUERY),
        ("list all orders", Intent.ORDER_QUERY),
        ("show me orders above 5000", Intent.ORDER_QUERY),
        ("how many delivered orders?", Intent.ORDER_QUERY),
        ("what is the total sales?", Intent.ORDER_QUERY),
        ("list out for delivery orders", Intent.ORDER_QUERY),
    ],
)
def test_intent_classification(text: str, expected: Intent) -> None:
    assert intent_svc.classify(text) == expected


def test_order_query_counts_from_db(client: TestClient) -> None:
    """An aggregate order query is answered straight from the database."""
    import uuid

    from app.api.deps import get_db
    from app.main import app
    from app.models.customer import Customer
    from app.models.enums import OrderStatus
    from app.models.order import Order

    db = next(app.dependency_overrides[get_db]())
    customer = Customer(wa_id="910000009999", name="Bulk Buyer")
    db.add(customer)
    db.flush()
    for i in range(3):
        db.add(
            Order(
                order_number=f"QRY-{9000 + i}",
                customer_id=customer.id,
                status=OrderStatus.DELIVERED,
                items=[{"name": "Widget", "qty": 1, "price": 100.0}],
                total=100.0,
            )
        )
    db.commit()

    res = client.post(
        "/api/v1/chat/send",
        json={"wa_id": "910000008888", "text": "how many orders do you have?"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["intent"] == "order_query"
    assert "3" in body["reply"]["content"]


def test_extract_order_number() -> None:
    assert intent_svc.extract_order_number("where is AUR-10432 now?") == "AUR-10432"
    assert intent_svc.extract_order_number("no number here") is None


def test_chat_greeting_flow(client: TestClient) -> None:
    """A greeting round-trips through the pipeline and is handled by AI."""
    res = client.post(
        "/api/v1/chat/send",
        json={"wa_id": "910000000001", "name": "Tester", "text": "hello"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["intent"] == "greeting"
    assert body["reply"]["content"]  # a non-empty reply was generated
    assert body["reply"]["sender"] == "ai"
    assert body["escalated"] is False


def test_chat_complaint_escalates(client: TestClient) -> None:
    """A complaint is routed to a human and flips the conversation status."""
    res = client.post(
        "/api/v1/chat/send",
        json={"wa_id": "910000000002", "text": "my item is broken, I want a refund"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["intent"] == "support"
    assert body["escalated"] is True

    # The conversation should now surface under the needs_human filter.
    convos = client.get("/api/v1/conversations?status=needs_human").json()
    assert any(c["id"] == body["conversation_id"] for c in convos)


def test_order_lookup_reply(client: TestClient) -> None:
    """Seeding an order lets the assistant answer a status question with facts."""
    import uuid

    from app.api.deps import get_db
    from app.main import app
    from app.models.customer import Customer
    from app.models.enums import OrderStatus
    from app.models.order import Order

    # Insert a customer + order through the overridden (in-memory) session.
    db = next(app.dependency_overrides[get_db]())
    customer = Customer(wa_id="910000000003", name="Buyer")
    db.add(customer)
    db.flush()
    db.add(
        Order(
            order_number="TST-55501",
            customer_id=customer.id,
            status=OrderStatus.SHIPPED,
            items=[{"name": "Test Item", "qty": 1, "price": 100.0}],
            total=100.0,
            tracking_number="TRKTEST",
        )
    )
    db.commit()

    res = client.post(
        "/api/v1/chat/send",
        json={"wa_id": "910000000003", "text": "status of order TST-55501?"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["intent"] == "order_status"
    assert "TST-55501" in body["reply"]["content"]
    assert "shipped" in body["reply"]["content"].lower()
