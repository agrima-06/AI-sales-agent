"""
Order Repository Implementation
"""

from typing import Sequence, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import SQLAlchemyBaseRepository
from app.repositories.interfaces import IOrderRepository
from app.models.order import Order, DraftOrder


class OrderRepository(SQLAlchemyBaseRepository[Order], IOrderRepository):
    """
    SQLAlchemy implementation for Order data access.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Order)

    async def get_with_items(self, order_id: uuid.UUID) -> Optional[Order]:
        """Fetch an order along with its items and version history."""
        stmt = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.versions))
            .where(Order.id == order_id, Order.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_orders_by_dealer(
        self, dealer_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Order]:
        """Fetch all finalized orders for a given dealer."""
        stmt = (
            select(Order)
            .where(Order.dealer_id == dealer_id, Order.deleted_at.is_(None))
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_drafts_by_dealer(
        self, dealer_id: uuid.UUID
    ) -> Sequence[DraftOrder]:
        """Fetch all pending draft orders for a given dealer."""
        stmt = select(DraftOrder).where(
            DraftOrder.dealer_id == dealer_id,
            DraftOrder.status == "pending",
            DraftOrder.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
