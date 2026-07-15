"""
Order Domain Models
===================

Domain: Orders (Transaction & Fulfillment Lifecycle)

Entities:
  - DraftOrder         : Volatile shopping cart during active AI voice calls.
  - DraftOrderItem     : Line items in the active draft.
  - Order              : The master confirmed document.
  - OrderVersion       : Immutable snapshot of an order state.
  - OrderItem          : Line items tied to a specific OrderVersion.
  - OrderItemRemark    : Specific notes tied to a line item (e.g., "pack separately").
  - OrderStatusHistory : Immutable audit trail of lifecycle transitions.
  - ERPJob             : Tracks synchronization state with external ERPs (SAP/NetSuite).
  - DeliveryTracking   : Fulfillment and logistics tracking.
  - PaymentStatus      : Financial settlement tracking.

Design Decisions:
  - Draft Orders: Voice interactions are highly fluid. Users add, remove, and change quantities
    rapidly. We write these to a Draft order rather than polluting the real Order tables.
  - True Versioning: Once an Order is confirmed (Version 1), any subsequent modifications
    (e.g., dealer calls back to add an item, or warehouse adjusts stock) creates a Version 2.
    `OrderItem` belongs to `OrderVersion`, ensuring true historical immutability.
  - ERP Decoupling: `ERPJob` exists separately because ERP syncs are asynchronous. If a sync
    fails, the Order remains valid, and the ERPJob handles retries and error logging.

Relationships:
  DraftOrder 1─── N DraftOrderItem
  Order 1─── N OrderVersion
  OrderVersion 1─── N OrderItem
  OrderItem 1─── N OrderItemRemark
  Order 1─── N OrderStatusHistory
  Order 1─── 1 ERPJob
  Order 1─── 1 DeliveryTracking
  Order 1─── 1 PaymentStatus
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
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase


# -----------------------------------------------------------------------------
# Draft Models (The "Cart" phase during AI conversation)
# -----------------------------------------------------------------------------


class DraftOrder(TimestampedBase):
    """
    Volatile shopping cart used during the AI conversation.
    Only converted to a final Order upon explicit voice confirmation.
    """

    __tablename__ = "draft_orders"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="FK to AI conversations (will be defined in ai.py)",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="in_progress",
        comment="in_progress, abandoned, converted",
    )
    ai_confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="Average confidence score of AI intent parsing for this draft",
    )

    # Relationships
    items: Mapped[list["DraftOrderItem"]] = relationship(
        "DraftOrderItem", back_populates="draft_order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'abandoned', 'converted')",
            name="ck_draft_order_status",
        ),
    )


class DraftOrderItem(TimestampedBase):
    """
    Line items for a DraftOrder. Subject to rapid changes during the call.
    """

    __tablename__ = "draft_order_items"

    draft_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Estimated price quoted by AI during the call",
    )

    # Relationships
    draft_order: Mapped["DraftOrder"] = relationship(
        "DraftOrder", back_populates="items"
    )


# -----------------------------------------------------------------------------
# Confirmed Order Models (The finalized transactions)
# -----------------------------------------------------------------------------


class Order(TimestampedBase):
    """
    The master confirmed order header.
    Acts as a container for OrderVersions and lifecycle tracking.
    """

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable unique order identifier (e.g., ORD-2026-0001)",
    )
    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, confirmed, processing, shipped, delivered, cancelled",
    )

    confirmed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User or AI System ID that explicitly confirmed this order",
    )
    confirmation_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    versions: Mapped[list["OrderVersion"]] = relationship(
        "OrderVersion",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderVersion.version_number.desc()",
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at.asc()",
    )
    erp_job: Mapped[Optional["ERPJob"]] = relationship(
        "ERPJob", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
    delivery_tracking: Mapped[Optional["DeliveryTracking"]] = relationship(
        "DeliveryTracking",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )
    payment_status: Mapped[Optional["PaymentStatus"]] = relationship(
        "PaymentStatus",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled')",
            name="ck_order_status",
        ),
        Index("ix_orders_dealer_created", "dealer_id", "created_at"),
    )


class OrderVersion(TimestampedBase):
    """
    An immutable snapshot of the order's state.
    Modifying a confirmed order requires creating a new version.
    """

    __tablename__ = "order_versions"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_tax: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )

    reason_for_change: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Why this version was created (e.g., 'Dealer requested quantity increase')",
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="versions")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("order_id", "version_number", name="uq_order_version"),
    )


class OrderItem(TimestampedBase):
    """
    Line items tied to a specific OrderVersion.
    """

    __tablename__ = "order_items"

    order_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    # Relationships
    version: Mapped["OrderVersion"] = relationship(
        "OrderVersion", back_populates="items"
    )
    remarks: Mapped[list["OrderItemRemark"]] = relationship(
        "OrderItemRemark", back_populates="order_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_price"),
    )


class OrderItemRemark(TimestampedBase):
    """
    Specific conversational remarks tied to a line item.
    Crucial for AI voice scenarios ("for the red paint, pack it separately").
    """

    __tablename__ = "order_item_remarks"

    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    remark: Mapped[str] = mapped_column(Text, nullable=False)
    added_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    order_item: Mapped["OrderItem"] = relationship(
        "OrderItem", back_populates="remarks"
    )


class OrderStatusHistory(TimestampedBase):
    """
    Immutable audit log of every lifecycle transition.
    """

    __tablename__ = "order_status_history"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="status_history")


# -----------------------------------------------------------------------------
# Integrations and Tracking
# -----------------------------------------------------------------------------


class ERPJob(TimestampedBase):
    """
    Tracks the synchronization state with external ERPs.
    """

    __tablename__ = "erp_jobs"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    erp_reference_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="ID assigned by SAP/NetSuite once synced",
    )

    sync_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, success, failed, retrying",
    )
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="erp_job")

    __table_args__ = (
        CheckConstraint(
            "sync_status IN ('pending', 'success', 'failed', 'retrying')",
            name="ck_erp_job_status",
        ),
    )


class DeliveryTracking(TimestampedBase):
    """
    Fulfillment and logistics tracking.
    """

    __tablename__ = "delivery_tracking"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    carrier_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="preparing",
        comment="preparing, dispatched, in_transit, delivered, returned",
    )

    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_delivery: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="delivery_tracking")


class PaymentStatus(TimestampedBase):
    """
    Financial settlement tracking.
    """

    __tablename__ = "payment_status"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="pending, partial, paid, refunded",
    )

    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    last_payment_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="payment_status")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'partial', 'paid', 'refunded')",
            name="ck_payment_status",
        ),
        CheckConstraint("amount_paid >= 0", name="ck_payment_amount"),
    )
