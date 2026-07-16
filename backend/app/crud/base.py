"""Generic CRUD repository.

A thin, typed wrapper over common SQLAlchemy operations so per-model
repositories only add the queries that are actually specific to them.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUDBase(Generic[ModelT]):
    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    def get(self, db: Session, id: uuid.UUID) -> ModelT | None:
        return db.get(self.model, id)

    def list(
        self,
        db: Session,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: Any | None = None,
    ) -> list[ModelT]:
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def count(self, db: Session) -> int:
        return db.execute(select(func.count()).select_from(self.model)).scalar_one()

    def create(self, db: Session, obj: ModelT, *, commit: bool = True) -> ModelT:
        db.add(obj)
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
        return obj

    def save(self, db: Session, obj: ModelT) -> ModelT:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, obj: ModelT) -> None:
        db.delete(obj)
        db.commit()
