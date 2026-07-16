"""Dashboard analytics.

Aggregates counts for the dashboard. Time-bucketing is done in Python (over a
bounded recent window) to stay database-agnostic across SQLite and Postgres.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.enums import ConversationStatus, MessageDirection, SenderType
from app.models.faq import FAQ
from app.models.message import Message
from app.models.order import Order
from app.schemas.stats import DailyVolume, DashboardStats, IntentCount


def _count(db: Session, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for clause in where:
        stmt = stmt.where(clause)
    return db.execute(stmt).scalar_one()


def build_dashboard(db: Session) -> DashboardStats:
    total_conversations = _count(db, Conversation)
    open_conversations = _count(db, Conversation, Conversation.status == ConversationStatus.OPEN)
    needs_human = _count(db, Conversation, Conversation.status == ConversationStatus.NEEDS_HUMAN)
    resolved = _count(db, Conversation, Conversation.status == ConversationStatus.RESOLVED)

    total_messages = _count(db, Message)
    total_customers = _count(db, Customer)
    total_orders = _count(db, Order)

    # AI resolution rate = share of conversations not sitting with a human.
    handled_by_ai = total_conversations - needs_human
    ai_resolution_rate = (
        round(100.0 * handled_by_ai / total_conversations, 1) if total_conversations else 0.0
    )

    # Average confidence across AI-authored replies.
    avg_conf = db.execute(
        select(func.avg(Message.confidence)).where(Message.sender == SenderType.AI)
    ).scalar_one()
    avg_confidence = round(100.0 * float(avg_conf), 1) if avg_conf is not None else 0.0

    # Intent distribution over inbound messages.
    intent_rows = db.execute(
        select(Message.intent, func.count())
        .where(Message.direction == MessageDirection.INBOUND, Message.intent.is_not(None))
        .group_by(Message.intent)
    ).all()
    intents = [IntentCount(intent=str(i), count=c) for i, c in intent_rows if i]
    intents.sort(key=lambda x: x.count, reverse=True)

    daily_volume = _daily_volume(db, days=7)

    top_faqs = [
        {"question": f.question, "category": f.category, "hits": f.hit_count}
        for f in db.execute(
            select(FAQ).order_by(FAQ.hit_count.desc()).limit(5)
        ).scalars().all()
    ]

    return DashboardStats(
        total_conversations=total_conversations,
        open_conversations=open_conversations,
        needs_human=needs_human,
        resolved_conversations=resolved,
        total_messages=total_messages,
        total_customers=total_customers,
        total_orders=total_orders,
        ai_resolution_rate=ai_resolution_rate,
        avg_confidence=avg_confidence,
        intents=intents,
        daily_volume=daily_volume,
        top_faqs=top_faqs,
    )


def _daily_volume(db: Session, *, days: int) -> list[DailyVolume]:
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    rows = db.execute(
        select(Message.created_at, Message.direction).where(Message.created_at >= since)
    ).all()

    inbound: dict[str, int] = defaultdict(int)
    outbound: dict[str, int] = defaultdict(int)
    for created_at, direction in rows:
        key = created_at.date().isoformat()
        if direction == MessageDirection.INBOUND:
            inbound[key] += 1
        else:
            outbound[key] += 1

    result: list[DailyVolume] = []
    for offset in range(days):
        day = (since + timedelta(days=offset)).date().isoformat()
        result.append(DailyVolume(date=day, inbound=inbound.get(day, 0), outbound=outbound.get(day, 0)))
    return result
