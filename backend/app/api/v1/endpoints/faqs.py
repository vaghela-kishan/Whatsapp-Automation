"""FAQ knowledge-base management endpoints."""

from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.crud.faq import faq as faq_crud
from app.models.faq import FAQ
from app.models.faq_suggestion import FAQSuggestion
from app.schemas.common import Message
from app.schemas.faq import FAQCreate, FAQRead, FAQUpdate

router = APIRouter(prefix="/faqs", tags=["FAQs"])


class SuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    ask_count: int
    status: str
    created_at: datetime.datetime


class SuggestionApprove(BaseModel):
    answer: str
    category: str = "General"


@router.get(
    "/suggestions",
    response_model=list[SuggestionRead],
    summary="Customer questions the bot couldn't answer (self-learning)",
)
def list_suggestions(db: Session = Depends(get_db)) -> list[SuggestionRead]:
    rows = db.execute(
        select(FAQSuggestion)
        .where(FAQSuggestion.status == "pending")
        .order_by(FAQSuggestion.ask_count.desc(), FAQSuggestion.created_at.desc())
    ).scalars().all()
    return [SuggestionRead.model_validate(s) for s in rows]


@router.post(
    "/suggestions/{suggestion_id}/approve",
    response_model=FAQRead,
    summary="Approve a suggestion → publish it as a live FAQ",
)
def approve_suggestion(
    suggestion_id: uuid.UUID, payload: SuggestionApprove, db: Session = Depends(get_db)
) -> FAQRead:
    s = db.get(FAQSuggestion, suggestion_id)
    if s is None:
        raise NotFoundError("Suggestion not found.")
    entry = FAQ(
        question=s.question,
        answer=payload.answer,
        category=payload.category,
        keywords=s.normalized,
        is_active=True,
    )
    faq_crud.create(db, entry, commit=False)
    s.status = "approved"
    db.commit()
    db.refresh(entry)
    return FAQRead.model_validate(entry)


@router.post(
    "/suggestions/{suggestion_id}/dismiss",
    response_model=Message,
    summary="Dismiss a suggestion",
)
def dismiss_suggestion(suggestion_id: uuid.UUID, db: Session = Depends(get_db)) -> Message:
    s = db.get(FAQSuggestion, suggestion_id)
    if s is None:
        raise NotFoundError("Suggestion not found.")
    s.status = "dismissed"
    db.commit()
    return Message(message="Suggestion dismissed.")


@router.get("", response_model=list[FAQRead], summary="List all FAQ entries")
def list_faqs(db: Session = Depends(get_db)) -> list[FAQRead]:
    return [FAQRead.model_validate(f) for f in faq_crud.list_all(db)]


@router.post(
    "",
    response_model=FAQRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an FAQ entry",
)
def create_faq(payload: FAQCreate, db: Session = Depends(get_db)) -> FAQRead:
    entry = FAQ(**payload.model_dump())
    faq_crud.create(db, entry)
    return FAQRead.model_validate(entry)


@router.patch("/{faq_id}", response_model=FAQRead, summary="Update an FAQ entry")
def update_faq(
    faq_id: uuid.UUID, payload: FAQUpdate, db: Session = Depends(get_db)
) -> FAQRead:
    entry = faq_crud.get(db, faq_id)
    if entry is None:
        raise NotFoundError("FAQ not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    faq_crud.save(db, entry)
    return FAQRead.model_validate(entry)


@router.delete("/{faq_id}", response_model=Message, summary="Delete an FAQ entry")
def delete_faq(faq_id: uuid.UUID, db: Session = Depends(get_db)) -> Message:
    entry = faq_crud.get(db, faq_id)
    if entry is None:
        raise NotFoundError("FAQ not found.")
    faq_crud.delete(db, entry)
    return Message(message="FAQ deleted.")
