"""FAQ repository."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.faq import FAQ


class CRUDFAQ(CRUDBase[FAQ]):
    def list_active(self, db: Session) -> list[FAQ]:
        return list(
            db.execute(
                select(FAQ).where(FAQ.is_active.is_(True)).order_by(FAQ.category)
            ).scalars().all()
        )

    def list_all(self, db: Session) -> list[FAQ]:
        return list(
            db.execute(select(FAQ).order_by(FAQ.category, FAQ.question)).scalars().all()
        )

    def top_by_hits(self, db: Session, limit: int = 5) -> list[FAQ]:
        return list(
            db.execute(
                select(FAQ).order_by(desc(FAQ.hit_count)).limit(limit)
            ).scalars().all()
        )


faq = CRUDFAQ(FAQ)
