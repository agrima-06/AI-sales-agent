"""
Inventory Domain Models
=======================

Domain: Inventory (Warehouse & Stock Management)

Entities:
  - Warehouse          : Physical warehouse location.
  - Inventory          : Current stock snapshot per (warehouse × product_variant).
  - InventoryMovement  : Immutable ledger of every stock change.

Design Decisions:
  - Warehouse is in the Inventory domain (not Customer) because it is a
    supply-side entity shared across dealers and products.
  - Inventory stores pre-computed available_quantity to avoid expensive
    joins during real-time voice queries.
  - InventoryMovement is append-only and never updated or deleted.
    It is a ledger: the sum of all movements always equals current_stock.

Relationships:
  Warehouse 1─── N Inventory
  Inventory 1─── N InventoryMovement
  ProductVariant 1─── N Inventory       (defined in product.py)
"""

import uuid
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase


class Warehouse(TimestampedBase):
    """
    Physical warehouse location from which inventory is sourced.
    """

    __tablename__ = "warehouses"

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Short unique warehouse code used in voice responses: 'Mumbai Central'",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line_1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    manager_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    inventory_records: Mapped[list["Inventory"]] = relationship(
        "Inventory", back_populates="warehouse"
    )

    def __repr__(self) -> str:
        return f"<Warehouse code={self.code} name={self.name}>"


class Inventory(TimestampedBase):
    """
    Current stock snapshot for one product variant at one warehouse.
    One record per (warehouse_id, product_variant_id) pair.

    available_quantity is a computed property:
        available_quantity = current_stock - reserved_quantity

    current_stock is updated by the InventoryMovement ledger via workers.
    Never update this directly — always write an InventoryMovement.
    """

    __tablename__ = "inventory"

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Stock quantities
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        default=Decimal("0.000"),
        comment="Total physical units currently in warehouse",
    )
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        default=Decimal("0.000"),
        comment="Quantity reserved by pending/confirmed orders not yet dispatched",
    )
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        default=Decimal("0.000"),
        comment="Threshold at which replenishment outbound call is triggered",
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse", back_populates="inventory_records"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="inventory_record"
    )

    @property
    def available_quantity(self) -> Decimal:
        """Real-time available quantity. Never stored — always computed."""
        return max(Decimal("0.000"), self.current_stock - self.reserved_quantity)

    __table_args__ = (
        # The combination of warehouse + variant must be unique — one record per location+product
        Index(
            "ix_inventory_warehouse_variant",
            "warehouse_id",
            "product_variant_id",
            unique=True,
        ),
        CheckConstraint("current_stock >= 0", name="ck_inventory_stock_non_negative"),
        CheckConstraint(
            "reserved_quantity >= 0", name="ck_inventory_reserved_non_negative"
        ),
        CheckConstraint(
            "reserved_quantity <= current_stock", name="ck_inventory_reserved_lte_stock"
        ),
    )


class InventoryMovement(TimestampedBase):
    """
    Immutable ledger record for every stock change.
    This is the source of truth. Never deleted. Never updated.

    Movement types:
      - inbound         : Stock received from supplier
      - outbound        : Stock dispatched for a dealer order
      - reservation     : Quantity reserved when order confirmed
      - reservation_release : Reservation released when order cancelled/modified
      - adjustment      : Manual stock correction (damaged goods, counting error)
      - transfer_in     : Received from another warehouse
      - transfer_out    : Sent to another warehouse
    """

    __tablename__ = "inventory_movements"

    inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity_delta: Mapped[Decimal] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Positive = stock increase, Negative = stock decrease",
    )
    quantity_before: Mapped[Decimal] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Snapshot of current_stock before this movement",
    )
    quantity_after: Mapped[Decimal] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Snapshot of current_stock after this movement",
    )
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Source entity type: order, purchase_order, adjustment_ticket",
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID of the source entity (e.g. order_id that triggered outbound)",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    inventory_record: Mapped["Inventory"] = relationship(
        "Inventory", back_populates="movements"
    )

    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('inbound', 'outbound', 'reservation', 'reservation_release', 'adjustment', 'transfer_in', 'transfer_out')",
            name="ck_movement_type",
        ),
        Index("ix_inventory_movements_inventory_created", "inventory_id", "created_at"),
        Index("ix_inventory_movements_reference", "reference_type", "reference_id"),
    )
