"""
Customer Repository Implementation
"""

from typing import Sequence, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import SQLAlchemyBaseRepository
from app.repositories.interfaces import ICustomerRepository
from app.models.customer import Dealer


class CustomerRepository(SQLAlchemyBaseRepository[Dealer], ICustomerRepository):
    """
    SQLAlchemy implementation for Customer (Dealer) data access.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Dealer)

    async def get_by_phone(self, phone: str) -> Optional[Dealer]:
        """Fetch a dealer by their primary phone number."""
        stmt = select(Dealer).where(
            Dealer.primary_phone == phone, Dealer.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_erp_code(self, code: str) -> Optional[Dealer]:
        """Fetch a dealer by their ERP system code."""
        stmt = select(Dealer).where(
            Dealer.erp_code == code, Dealer.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_dealers(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[Dealer]:
        """Fetch all dealers that are currently active."""
        stmt = (
            select(Dealer)
            .where(Dealer.status == "active", Dealer.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
