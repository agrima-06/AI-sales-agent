"""
Inventory Repository Implementation
"""

from typing import Sequence, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import SQLAlchemyBaseRepository
from app.repositories.interfaces import IInventoryRepository
from app.models.inventory import Inventory, Warehouse


class InventoryRepository(SQLAlchemyBaseRepository[Inventory], IInventoryRepository):
    """
    SQLAlchemy implementation for Inventory data access.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Inventory)

    async def get_stock_by_warehouse(
        self, warehouse_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Inventory]:
        """Fetch all inventory records for a specific warehouse."""
        stmt = (
            select(Inventory)
            .where(
                Inventory.warehouse_id == warehouse_id, Inventory.deleted_at.is_(None)
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_variant_stock(
        self, product_variant_id: uuid.UUID
    ) -> Sequence[Inventory]:
        """Fetch stock levels for a specific product variant across all warehouses."""
        stmt = select(Inventory).where(
            Inventory.product_variant_id == product_variant_id,
            Inventory.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_warehouses(self) -> Sequence[Warehouse]:
        """Fetch all active warehouses."""
        stmt = select(Warehouse).where(
            Warehouse.is_active == True, Warehouse.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
