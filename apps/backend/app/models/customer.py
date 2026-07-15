"""
Customer Domain Models
======================

Domain: Customer (B2B Dealer network)

Entities:
  - Dealer          : The primary B2B buyer entity. Maps to an ERP account.
  - DealerAddress   : Multiple geographic addresses per dealer (billing, delivery, HQ).
  - DealerContact   : Multiple named contact persons per dealer.
  - DealerCreditLimit : Versioned credit limit records for audit trail.
  - DealerLanguagePreference : Ordered list of preferred languages for voice AI.
  - DealerPreferredWarehouse : Ordered list of warehouses a dealer sources from.

Normalization Decisions:
  - Addresses are 1:N to support dealers with multiple delivery sites.
  - Contacts are 1:N because different people (owner, accountant, store manager)
    may interact with the system in different capacities.
  - Credit limit is versioned (not a single column) so Finance can audit changes over time.
  - Language preferences are stored as an ordered list to support primary + fallback languages.
  - Preferred warehouses are ordered so the AI picks the nearest/preferred one first.

Relationships:
  Dealer 1─── N DealerAddress
  Dealer 1─── N DealerContact
  Dealer 1─── N DealerCreditLimit
  Dealer 1─── N DealerLanguagePreference
  Dealer 1─── N DealerPreferredWarehouse
"""

import uuid
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase


class Dealer(TimestampedBase):
    """
    The primary B2B buyer entity.
    One Dealer = one customer account in the ERP.
    """

    __tablename__ = "dealers"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    erp_account_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Reference code in the external ERP (SAP/NetSuite)",
    )

    # Authentication (for voice caller ID matching)
    phone_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Primary phone used for Twilio caller ID authentication",
    )
    pin_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Hashed 4-digit PIN for voice authentication fallback",
    )

    # Business identity
    gst_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, unique=True
    )
    pan_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    dealer_tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="standard",
        comment="Pricing tier: standard, silver, gold, platinum",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    # Region / classification
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    addresses: Mapped[list["DealerAddress"]] = relationship(
        "DealerAddress", back_populates="dealer", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["DealerContact"]] = relationship(
        "DealerContact", back_populates="dealer", cascade="all, delete-orphan"
    )
    credit_limits: Mapped[list["DealerCreditLimit"]] = relationship(
        "DealerCreditLimit",
        back_populates="dealer",
        cascade="all, delete-orphan",
        order_by="DealerCreditLimit.created_at.desc()",
    )
    language_preferences: Mapped[list["DealerLanguagePreference"]] = relationship(
        "DealerLanguagePreference",
        back_populates="dealer",
        cascade="all, delete-orphan",
        order_by="DealerLanguagePreference.priority",
    )
    preferred_warehouses: Mapped[list["DealerPreferredWarehouse"]] = relationship(
        "DealerPreferredWarehouse",
        back_populates="dealer",
        cascade="all, delete-orphan",
        order_by="DealerPreferredWarehouse.priority",
    )

    __table_args__ = (
        CheckConstraint(
            "dealer_tier IN ('standard', 'silver', 'gold', 'platinum')",
            name="ck_dealer_tier",
        ),
        Index("ix_dealers_is_active_region", "is_active", "region"),
    )

    def __repr__(self) -> str:
        return f"<Dealer id={self.id} name={self.name} tier={self.dealer_tier}>"


class DealerAddress(TimestampedBase):
    """
    Physical addresses for a dealer. 1 dealer : N addresses.
    Address types: billing, delivery, headquarters.
    """

    __tablename__ = "dealer_addresses"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    address_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="billing | delivery | headquarters"
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    address_line_1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line_2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    landmark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="addresses")

    __table_args__ = (
        CheckConstraint(
            "address_type IN ('billing', 'delivery', 'headquarters')",
            name="ck_dealer_address_type",
        ),
        Index("ix_dealer_addresses_dealer_type", "dealer_id", "address_type"),
    )


class DealerContact(TimestampedBase):
    """
    Named contact persons associated with a dealer.
    The AI uses this to address the caller by name.
    """

    __tablename__ = "dealer_contacts"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="e.g. Owner, Manager, Accountant"
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="contacts")

    __table_args__ = (Index("ix_dealer_contacts_phone", "phone"),)


class DealerCreditLimit(TimestampedBase):
    """
    Versioned credit limit records. Append-only.
    The current credit limit is the most recently created record.
    Never update — always insert a new row on credit limit change.
    """

    __tablename__ = "dealer_credit_limits"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, comment="Approved credit limit in base currency"
    )
    outstanding_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    set_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who approved this credit limit change",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="credit_limits")

    __table_args__ = (
        CheckConstraint("credit_limit >= 0", name="ck_credit_limit_non_negative"),
        CheckConstraint("outstanding_balance >= 0", name="ck_outstanding_non_negative"),
        Index("ix_dealer_credit_limits_dealer_created", "dealer_id", "created_at"),
    )


class DealerLanguagePreference(TimestampedBase):
    """
    Ordered list of language codes preferred by a dealer.
    Priority 1 = primary language, Priority 2 = first fallback, etc.
    The voice AI reads this to select the correct language model and TTS voice.
    """

    __tablename__ = "dealer_language_preferences"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="BCP-47 language code: en-IN, hi-IN, mr-IN, ta-IN, etc.",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Lower number = higher priority. 1 = primary language.",
    )

    # Relationships
    dealer: Mapped["Dealer"] = relationship(
        "Dealer", back_populates="language_preferences"
    )

    __table_args__ = (
        UniqueConstraint("dealer_id", "language_code", name="uq_dealer_language"),
        UniqueConstraint("dealer_id", "priority", name="uq_dealer_language_priority"),
    )


class DealerPreferredWarehouse(TimestampedBase):
    """
    Ordered list of warehouses a dealer prefers to source from.
    Priority 1 = first choice, Priority 2 = overflow warehouse.
    The AI checks availability at priority-1 first, then falls over.
    """

    __tablename__ = "dealer_preferred_warehouses"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    dealer: Mapped["Dealer"] = relationship(
        "Dealer", back_populates="preferred_warehouses"
    )

    __table_args__ = (
        UniqueConstraint("dealer_id", "warehouse_id", name="uq_dealer_warehouse"),
        UniqueConstraint("dealer_id", "priority", name="uq_dealer_warehouse_priority"),
    )
