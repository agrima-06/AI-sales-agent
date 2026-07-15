"""
Shared base model for all SQLAlchemy models in the platform.

Every domain model inherits from TimestampedBase, which provides:
  - UUID primary key (database-generated for performance, no application-level UUID generation)
  - created_at: immutable creation timestamp
  - updated_at: auto-updated on every write
  - deleted_at: soft-delete support — NULL means active, timestamp means logically deleted

Soft delete design decision:
  Entities that are referenced by transactional records (orders, inventory movements, call logs)
  must never be physically deleted. Deleting a product that exists on a historical invoice
  would break foreign key integrity and destroy audit trails. Soft delete solves this cleanly.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampedBase(Base):
    """
    Abstract base for all domain models.
    Provides: id (UUID), created_at, updated_at, deleted_at.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,  # Indexed to efficiently filter active vs deleted records
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
