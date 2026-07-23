"""
Campaign Repository Implementation
"""

from typing import Sequence, Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import SQLAlchemyBaseRepository
from app.repositories.interfaces import ICampaignRepository
from app.models.campaign import Campaign


class CampaignRepository(SQLAlchemyBaseRepository[Campaign], ICampaignRepository):
    """
    SQLAlchemy implementation for Campaign data access.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Campaign)

    async def get_active_campaigns(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[Campaign]:
        """Fetch campaigns that are active and currently within their valid date range."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Campaign)
            .where(
                Campaign.is_active == True,
                Campaign.start_date <= now,
                Campaign.end_date >= now,
                Campaign.deleted_at.is_(None),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_campaign_by_code(self, code: str) -> Optional[Campaign]:
        """Fetch a specific campaign by its promo code."""
        stmt = select(Campaign).where(
            Campaign.code == code, Campaign.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
