"""
AI Platform Repository Implementation
"""

from typing import Sequence, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import SQLAlchemyBaseRepository
from app.repositories.interfaces import IAIRepository
from app.models.ai import Conversation, PromptTemplate, PromptVersion


class AIRepository(SQLAlchemyBaseRepository[Conversation], IAIRepository):
    """
    SQLAlchemy implementation for AI Platform data access.
    Operates primarily on Conversation as the aggregate root.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Conversation)

    async def get_active_conversations_by_dealer(
        self, dealer_id: uuid.UUID
    ) -> Sequence[Conversation]:
        """Fetch all ongoing conversations for a given dealer."""
        stmt = select(Conversation).where(
            Conversation.dealer_id == dealer_id,
            Conversation.status == "active",
            Conversation.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_turns(
        self, conversation_id: uuid.UUID
    ) -> Optional[Conversation]:
        """Fetch a conversation along with its full transcript history (turns)."""
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.turns))
            .where(
                Conversation.id == conversation_id, Conversation.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_prompt_version(
        self, template_name: str
    ) -> Optional[PromptVersion]:
        """Fetch the currently active prompt version by template name."""
        stmt = select(PromptTemplate).where(
            PromptTemplate.name == template_name, PromptTemplate.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template or not template.active_version_id:
            return None

        stmt_version = select(PromptVersion).where(
            PromptVersion.id == template.active_version_id,
            PromptVersion.deleted_at.is_(None),
        )
        version_result = await self.session.execute(stmt_version)
        return version_result.scalar_one_or_none()
