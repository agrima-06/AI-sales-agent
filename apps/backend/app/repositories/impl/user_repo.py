"""
User Repository Implementation
"""

from typing import Sequence, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import SQLAlchemyBaseRepository
from app.repositories.interfaces import IUserRepository
from app.models.user import User


class UserRepository(SQLAlchemyBaseRepository[User], IUserRepository):
    """
    SQLAlchemy implementation for User (Identity & Access) data access.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by their exact email address."""
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch a user and eagerly load their roles (for RBAC evaluation)."""
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
