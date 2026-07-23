"""
Repository Interfaces
=====================

Abstract base classes defining the contracts for data access.
By depending on these interfaces rather than concrete implementations,
the application architecture remains decoupled from SQLAlchemy.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Sequence
import uuid

# T is the generic type variable representing a SQLAlchemy Model
T = TypeVar("T")


class IBaseRepository(Generic[T], ABC):
    """Generic interface for standard CRUD operations."""

    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        pass

    @abstractmethod
    async def create(self, obj_in: dict) -> T:
        pass

    @abstractmethod
    async def update(self, db_obj: T, obj_in: dict) -> T:
        pass

    @abstractmethod
    async def delete(self, id: uuid.UUID) -> bool:
        """Soft deletes the record."""
        pass

    @abstractmethod
    async def hard_delete(self, id: uuid.UUID) -> bool:
        """Permanently deletes the record."""
        pass


class ICustomerRepository(IBaseRepository, ABC):
    """Interface for Customer Domain data access."""

    pass


class IProductRepository(IBaseRepository, ABC):
    """Interface for Product Domain data access."""

    pass


class IInventoryRepository(IBaseRepository, ABC):
    """Interface for Inventory Domain data access."""

    pass


class IOrderRepository(IBaseRepository, ABC):
    """Interface for Order Domain data access."""

    pass


class ICampaignRepository(IBaseRepository, ABC):
    """Interface for Campaign Domain data access."""

    pass


class IUserRepository(IBaseRepository, ABC):
    """Interface for Identity & Access Domain data access."""

    pass


class IAIRepository(IBaseRepository, ABC):
    """Interface for AI Platform Domain data access."""

    pass
