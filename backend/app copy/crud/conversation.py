"""Conversation repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.crud.base import CRUDBase
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus


class CRUDConversation(CRUDBase[Conversation]):
    def get_with_messages(
        self, db: Session, conversation_id: uuid.UUID
    ) -> Conversation | None:
        return db.execute(
            select(Conversation)
            .options(
                joinedload(Conversation.customer),
                selectinload(Conversation.messages),
            )
            .where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

    def get_active_for_customer(
        self, db: Session, customer_id: uuid.UUID
    ) -> Conversation | None:
        """The most recent non-resolved conversation, if one exists."""
        return db.execute(
            select(Conversation)
            .where(
                Conversation.customer_id == customer_id,
                Conversation.status != ConversationStatus.RESOLVED,
            )
            .order_by(Conversation.last_message_at.desc())
        ).scalars().first()

    def list_summaries(
        self,
        db: Session,
        *,
        status: ConversationStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Conversation]:
        stmt = select(Conversation).options(joinedload(Conversation.customer))
        if status is not None:
            stmt = stmt.where(Conversation.status == status)
        # Priority (angry) conversations first, then most recent.
        stmt = (
            stmt.order_by(
                Conversation.priority.desc(), Conversation.last_message_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())


conversation = CRUDConversation(Conversation)
