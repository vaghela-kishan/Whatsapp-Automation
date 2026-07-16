"""Customer repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.customer import Customer


class CRUDCustomer(CRUDBase[Customer]):
    def get_by_wa_id(self, db: Session, wa_id: str) -> Customer | None:
        return db.execute(
            select(Customer).where(Customer.wa_id == wa_id)
        ).scalar_one_or_none()

    def get_or_create(
        self, db: Session, *, wa_id: str, name: str | None = None
    ) -> Customer:
        """Return the customer for ``wa_id``, creating them on first contact."""
        customer = self.get_by_wa_id(db, wa_id)
        if customer:
            if name and customer.name in ("", "WhatsApp User"):
                customer.name = name
                db.commit()
                db.refresh(customer)
            return customer

        customer = Customer(wa_id=wa_id, name=name or "WhatsApp User")
        return self.create(db, customer)


customer = CRUDCustomer(Customer)
