"""
Product Repository Implementation
"""

from typing import Sequence, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import SQLAlchemyBaseRepository
from app.repositories.interfaces import IProductRepository
from app.models.product import Product, ProductVariant


class ProductRepository(SQLAlchemyBaseRepository[Product], IProductRepository):
    """
    SQLAlchemy implementation for Product data access.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Product)

    async def get_with_variants(self, product_id: str) -> Optional[Product]:
        """Fetch a product along with all its variants eagerly loaded."""
        stmt = (
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.id == product_id, Product.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_products(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[Product]:
        """Fetch all products that are active."""
        stmt = (
            select(Product)
            .where(Product.is_active == True, Product.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_variant_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Fetch a specific product variant by SKU code."""
        stmt = select(ProductVariant).where(
            ProductVariant.sku == sku, ProductVariant.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
