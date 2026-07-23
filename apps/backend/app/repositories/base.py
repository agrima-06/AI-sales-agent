"""
SQLAlchemy Base Repository
==========================

Generic repository implementation using SQLAlchemy 2.0 AsyncSessions.
Handles common CRUD operations, pagination, and soft-delete filtering natively.
"""

from typing import Type, TypeVar, Generic, Optional, Sequence, Any
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interfaces import IBaseRepository

# T is the SQLAlchemy model class
T = TypeVar("T")


class SQLAlchemyBaseRepository(IBaseRepository[T], Generic[T]):
    """
    Base generic repository for SQLAlchemy models.
    Expects the model to inherit from TimestampedBase (which has an id and deleted_at).
    """

    def __init__(self, session: AsyncSession, model_cls: Type[T]):
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        """Fetch a single record by UUID. Ignores soft-deleted records."""
        stmt = select(self.model_cls).where(
            self.model_cls.id == id, self.model_cls.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        """Fetch a paginated list of records. Ignores soft-deleted records."""
        stmt = (
            select(self.model_cls)
            .where(self.model_cls.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: dict[str, Any]) -> T:
        """Create a new record and add it to the session."""
        db_obj = self.model_cls(**obj_in)
        self.session.add(db_obj)
        # Flush to get the generated UUID without committing
        await self.session.flush()
        return db_obj

    async def update(self, db_obj: T, obj_in: dict[str, Any]) -> T:
        """Update an existing record with new dictionary values."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        # If model tracks updated_at, we bump it (though SQLAlchemy might do this via onupdate)
        if hasattr(db_obj, "updated_at"):
            db_obj.updated_at = datetime.now(timezone.utc)

        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def delete(self, id: uuid.UUID) -> bool:
        """Soft delete a record by setting deleted_at."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False

        if hasattr(db_obj, "deleted_at"):
            db_obj.deleted_at = datetime.now(timezone.utc)
            self.session.add(db_obj)
            await self.session.flush()
            return True
        return False

    async def hard_delete(self, id: uuid.UUID) -> bool:
        """Permanently delete a record from the database."""
        # For hard delete we bypass the soft-delete filter
        stmt = select(self.model_cls).where(self.model_cls.id == id)
        result = await self.session.execute(stmt)
        db_obj = result.scalar_one_or_none()

        if not db_obj:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True
