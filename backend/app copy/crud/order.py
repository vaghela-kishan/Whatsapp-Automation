"""Order repository."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.enums import OrderStatus
from app.models.order import Order


class CRUDOrder(CRUDBase[Order]):
    def get_by_number(self, db: Session, order_number: str) -> Order | None:
        return db.execute(
            select(Order).where(Order.order_number == order_number.upper().strip())
        ).scalar_one_or_none()

    def list_for_customer(self, db: Session, customer_id: uuid.UUID) -> list[Order]:
        return list(
            db.execute(
                select(Order)
                .where(Order.customer_id == customer_id)
                .order_by(Order.created_at.desc())
            ).scalars().all()
        )

    def list_all(self, db: Session, *, offset: int = 0, limit: int = 100) -> list[Order]:
        return self.list(db, offset=offset, limit=limit, order_by=Order.created_at.desc())

    # --- Aggregate / analytics queries (power the chat "order query" feature) -

    def _filtered(
        self,
        *,
        status: OrderStatus | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ):
        clauses = []
        if status is not None:
            clauses.append(Order.status == status)
        if min_price is not None:
            clauses.append(Order.total >= min_price)
        if max_price is not None:
            clauses.append(Order.total <= max_price)
        return clauses

    def count_where(
        self,
        db: Session,
        *,
        status: OrderStatus | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Order)
        for c in self._filtered(status=status, min_price=min_price, max_price=max_price):
            stmt = stmt.where(c)
        return db.execute(stmt).scalar_one()

    def total_sales(self, db: Session, *, status: OrderStatus | None = None) -> float:
        stmt = select(func.coalesce(func.sum(Order.total), 0.0))
        if status is not None:
            stmt = stmt.where(Order.status == status)
        return float(db.execute(stmt).scalar_one())

    def counts_by_status(self, db: Session) -> dict[str, int]:
        rows = db.execute(
            select(Order.status, func.count()).group_by(Order.status)
        ).all()
        return {str(s): c for s, c in rows}

    def query(
        self,
        db: Session,
        *,
        status: OrderStatus | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        order_by_total_desc: bool = False,
        limit: int = 8,
    ) -> list[Order]:
        stmt = select(Order)
        for c in self._filtered(status=status, min_price=min_price, max_price=max_price):
            stmt = stmt.where(c)
        stmt = stmt.order_by(
            Order.total.desc() if order_by_total_desc else Order.created_at.desc()
        ).limit(limit)
        return list(db.execute(stmt).scalars().all())


order = CRUDOrder(Order)
