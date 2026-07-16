"""Customer listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud.customer import customer as customer_crud
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.customer import CustomerRead

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=list[CustomerRead], summary="List customers")
def list_customers(
    limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)
) -> list[CustomerRead]:
    customers = customer_crud.list(db, limit=limit, order_by=Customer.created_at.desc())
    return [CustomerRead.model_validate(c) for c in customers]


class DemoIdentity(BaseModel):
    name: str
    wa_id: str
    email: str | None = None
    order_count: int


@router.get(
    "/with-orders",
    response_model=list[DemoIdentity],
    summary="Customers who have orders (demo identities for Live Chat)",
)
def customers_with_orders(
    limit: int = Query(default=8, ge=1, le=50), db: Session = Depends(get_db)
) -> list[DemoIdentity]:
    """Return a few customers who own several orders, so the Live Chat can let
    you 'chat as' a real number and see per-customer order lookups work."""
    rows = db.execute(
        select(Customer, func.count(Order.id).label("n"))
        .join(Order, Order.customer_id == Customer.id)
        .group_by(Customer.id)
        .having(func.count(Order.id) >= 2)
        .order_by(func.count(Order.id).desc())
        .limit(limit)
    ).all()
    return [
        DemoIdentity(name=c.name, wa_id=c.wa_id, email=c.email, order_count=n)
        for c, n in rows
    ]
