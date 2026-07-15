"""
Campaign & Promotion Domain Models
==================================

Domain: Campaigns (Promotions, Discounts, and Schemes)

Entities:
  - Campaign            : The root promotion entity defining validity, limits, and stackability.
  - CampaignRule        : The trigger conditions (e.g., min quantity, Buy X, min cart value).
  - CampaignReward      : The benefit provided (e.g., flat discount, percentage, free product).
  - CampaignEligibility : General broad rules (inclusion/exclusion).
  - CampaignTarget      : What the campaign applies to (entire cart, specific category/brand).
  - CampaignProduct     : Explicit list of product variants included in the campaign.
  - CampaignRegion      : Geographic limits (by region string).
  - CampaignWarehouse   : Supply limits (by warehouse).
  - CampaignDealerGroup : Dealer tier limits (standard, gold, platinum).
  - CampaignUsage       : Audit log tracking redemptions per order and dealer.

Design Decisions:
  - 'Campaign' vs 'Scheme': 'Scheme' is often culturally limited to B2B volume rebates. 'Campaign'
    is an industry-standard term in modern enterprise architectures (e.g., Salesforce, SAP)
    that encompasses discounts, coupons, B2B schemes, and targeted promotions under one engine.
  - EAV & JSONB: `CampaignRule` and `CampaignReward` use a type string combined with a
    `JSONB` configuration column. This avoids schema sprawl (adding columns every time Marketing
    invents a new promotion type) while maintaining strict type boundaries.
  - Modular Junctions: Instead of one massive eligibility table, we use targeted junction tables
    (`CampaignProduct`, `CampaignRegion`, `CampaignWarehouse`, `CampaignDealerGroup`). This ensures
    referential integrity (FKs to Warehouses/Products) and allows ultra-fast indexed lookups when
    the AI evaluates active campaigns for a specific dealer.
  - Stackability: The `is_stackable` and `priority` fields determine resolution order when
    multiple campaigns apply to the same cart.

Relationships:
  Campaign 1─── N CampaignRule
  Campaign 1─── N CampaignReward
  Campaign 1─── N CampaignEligibility
  Campaign 1─── N CampaignTarget
  Campaign 1─── N CampaignProduct
  Campaign 1─── N CampaignRegion
  Campaign 1─── N CampaignWarehouse
  Campaign 1─── N CampaignDealerGroup
  Campaign 1─── N CampaignUsage
"""

import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase


class Campaign(TimestampedBase):
    """
    The root promotion entity.
    Defines when the campaign is active, its priority, and redemption limits.
    """

    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    is_stackable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Can be combined with other campaigns",
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, comment="Lower number = higher priority"
    )

    max_redemptions: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Total allowed uses across all dealers"
    )
    current_redemptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    rules: Mapped[list["CampaignRule"]] = relationship(
        "CampaignRule", back_populates="campaign", cascade="all, delete-orphan"
    )
    rewards: Mapped[list["CampaignReward"]] = relationship(
        "CampaignReward", back_populates="campaign", cascade="all, delete-orphan"
    )
    eligibilities: Mapped[list["CampaignEligibility"]] = relationship(
        "CampaignEligibility", back_populates="campaign", cascade="all, delete-orphan"
    )
    targets: Mapped[list["CampaignTarget"]] = relationship(
        "CampaignTarget", back_populates="campaign", cascade="all, delete-orphan"
    )
    products: Mapped[list["CampaignProduct"]] = relationship(
        "CampaignProduct", back_populates="campaign", cascade="all, delete-orphan"
    )
    regions: Mapped[list["CampaignRegion"]] = relationship(
        "CampaignRegion", back_populates="campaign", cascade="all, delete-orphan"
    )
    warehouses: Mapped[list["CampaignWarehouse"]] = relationship(
        "CampaignWarehouse", back_populates="campaign", cascade="all, delete-orphan"
    )
    dealer_groups: Mapped[list["CampaignDealerGroup"]] = relationship(
        "CampaignDealerGroup", back_populates="campaign", cascade="all, delete-orphan"
    )
    usages: Mapped[list["CampaignUsage"]] = relationship(
        "CampaignUsage", back_populates="campaign", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "current_redemptions >= 0", name="ck_campaign_redemptions_positive"
        ),
        Index("ix_campaigns_active_dates", "is_active", "start_date", "end_date"),
    )


class CampaignRule(TimestampedBase):
    """
    Conditions that must be met to trigger the campaign.
    Examples: Minimum quantity, Minimum order value, Buy X.
    """

    __tablename__ = "campaign_rules"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="min_quantity | min_value | buy_x_get_y | bundle",
    )
    configuration: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Flexible JSON definition, e.g., {'min_qty': 100, 'variant_id': '...'}",
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="rules")


class CampaignReward(TimestampedBase):
    """
    The benefit provided if the rules are met.
    """

    __tablename__ = "campaign_rewards"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reward_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="flat_discount | percent_discount | free_product",
    )
    value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Discount amount, percentage, or free product quantity",
    )
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Cap on percentage discounts"
    )
    free_product_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Required only if reward_type is free_product",
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="rewards")


class CampaignEligibility(TimestampedBase):
    """
    High-level inclusion/exclusion criteria for evaluating applicability.
    """

    __tablename__ = "campaign_eligibilities"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    eligibility_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="dealer_tier | region | warehouse | global"
    )
    is_inclusive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True = allow listed, False = block listed",
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="eligibilities"
    )


class CampaignTarget(TimestampedBase):
    """
    Specifies what the reward applies to (e.g., the whole cart, or a specific brand).
    """

    __tablename__ = "campaign_targets"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="cart_total | category | brand | product_variant",
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of the Category or Brand if applicable",
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="targets")


# -----------------------------------------------------------------------------
# Modular Junction Tables for High-Speed Lookups
# -----------------------------------------------------------------------------


class CampaignProduct(TimestampedBase):
    """Explicitly allowed product variants for this campaign."""

    __tablename__ = "campaign_products"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="products")

    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "product_variant_id", name="uq_campaign_product"
        ),
    )


class CampaignRegion(TimestampedBase):
    """Explicitly allowed regions (maps to Dealer.region)."""

    __tablename__ = "campaign_regions"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    region_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="regions")

    __table_args__ = (
        UniqueConstraint("campaign_id", "region_name", name="uq_campaign_region"),
    )


class CampaignWarehouse(TimestampedBase):
    """Campaign applies only to orders sourced from specific warehouses."""

    __tablename__ = "campaign_warehouses"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="warehouses")

    __table_args__ = (
        UniqueConstraint("campaign_id", "warehouse_id", name="uq_campaign_warehouse"),
    )


class CampaignDealerGroup(TimestampedBase):
    """Campaign applies only to specific dealer tiers."""

    __tablename__ = "campaign_dealer_groups"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    dealer_tier: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="dealer_groups"
    )

    __table_args__ = (
        UniqueConstraint("campaign_id", "dealer_tier", name="uq_campaign_dealer_tier"),
    )


# -----------------------------------------------------------------------------
# Usage & Audit Logging
# -----------------------------------------------------------------------------


class CampaignUsage(TimestampedBase):
    """
    Audit log of every time a campaign is applied to an order.
    Used for analytics and enforcing max_redemption limits.
    """

    __tablename__ = "campaign_usages"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discount_applied: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Total monetary value saved by the dealer on this usage",
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="usages")

    __table_args__ = (
        CheckConstraint(
            "discount_applied >= 0", name="ck_campaign_usage_discount_positive"
        ),
        # A campaign can only be used once per order
        UniqueConstraint("campaign_id", "order_id", name="uq_campaign_usage_per_order"),
    )
