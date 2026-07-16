"""Conversation inbox endpoints powering the agent dashboard."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud.conversation import conversation as conversation_crud
from app.core.exceptions import NotFoundError
from app.models.enums import ConversationStatus
from app.schemas.conversation import (
    AgentReply,
    ConversationDetail,
    ConversationStatusUpdate,
    ConversationSummary,
)
from app.schemas.message import MessageRead
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationSummary], summary="List conversations")
def list_conversations(
    status: ConversationStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ConversationSummary]:
    convos = conversation_crud.list_summaries(db, status=status, limit=limit)
    return [ConversationSummary.model_validate(c) for c in convos]


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get a conversation with its full message thread",
)
def get_conversation(
    conversation_id: uuid.UUID, db: Session = Depends(get_db)
) -> ConversationDetail:
    convo = conversation_crud.get_with_messages(db, conversation_id)
    if convo is None:
        raise NotFoundError("Conversation not found.")
    return ConversationDetail.model_validate(convo)


@router.post(
    "/{conversation_id}/reply",
    response_model=MessageRead,
    summary="Post a human agent reply",
)
def agent_reply(
    conversation_id: uuid.UUID, payload: AgentReply, db: Session = Depends(get_db)
) -> MessageRead:
    convo = conversation_crud.get_with_messages(db, conversation_id)
    if convo is None:
        raise NotFoundError("Conversation not found.")
    message = conversation_service.post_agent_reply(db, convo=convo, text=payload.content)
    return MessageRead.model_validate(message)


@router.patch(
    "/{conversation_id}/status",
    response_model=ConversationSummary,
    summary="Update a conversation's status",
)
def update_status(
    conversation_id: uuid.UUID,
    payload: ConversationStatusUpdate,
    db: Session = Depends(get_db),
) -> ConversationSummary:
    convo = conversation_crud.get_with_messages(db, conversation_id)
    if convo is None:
        raise NotFoundError("Conversation not found.")
    convo.status = payload.status
    db.commit()
    db.refresh(convo)
    return ConversationSummary.model_validate(convo)
