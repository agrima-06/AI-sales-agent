"""
Unit of Work Pattern
====================

The Unit of Work pattern manages database transactions (commit/rollback)
and exposes all domain repositories as properties. This ensures that
multiple repository calls within a service share a single transaction.
"""

from abc import ABC, abstractmethod
from typing import Any
import sys

from sqlalchemy.ext.asyncio import AsyncSession

# Import Interfaces
from app.repositories.interfaces import (
    ICustomerRepository,
    IProductRepository,
    IInventoryRepository,
    IOrderRepository,
    ICampaignRepository,
    IUserRepository,
    IAIRepository,
)


class IUnitOfWork(ABC):
    """
    Abstract Unit of Work Interface.
    Must be used as an async context manager:

    async with uow:
        uow.customers.create(...)
        await uow.commit()
    """

    customers: ICustomerRepository
    products: IProductRepository
    inventory: IInventoryRepository
    orders: IOrderRepository
    campaigns: ICampaignRepository
    users: IUserRepository
    ai: IAIRepository

    async def __aenter__(self) -> "IUnitOfWork":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, traceback: Any) -> None:
        if exc_type:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """
    SQLAlchemy implementation of the Unit of Work.
    Binds an AsyncSession and instantiates domain-specific SQLAlchemy repositories.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

        # Local import to prevent circular dependencies
        from app.repositories.impl.customer_repo import CustomerRepository
        from app.repositories.impl.product_repo import ProductRepository
        from app.repositories.impl.inventory_repo import InventoryRepository
        from app.repositories.impl.order_repo import OrderRepository
        from app.repositories.impl.campaign_repo import CampaignRepository
        from app.repositories.impl.user_repo import UserRepository
        from app.repositories.impl.ai_repo import AIRepository

        self.customers = CustomerRepository(self.session)
        self.products = ProductRepository(self.session)
        self.inventory = InventoryRepository(self.session)
        self.orders = OrderRepository(self.session)
        self.campaigns = CampaignRepository(self.session)
        self.users = UserRepository(self.session)
        self.ai = AIRepository(self.session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
