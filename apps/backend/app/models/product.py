"""
Product Domain Models
=====================

Domain: Product (Catalog & Pricing)

Entities:
  - Brand           : Manufacturer or brand entity.
  - Category        : Hierarchical product categorization.
  - Unit            : Unit of measurement (e.g., Box, KG, Piece).
  - GSTCategory     : Tax slabs based on HSN codes.
  - Product         : Canonical item definition.
  - ProductVariant  : Sellable item with SKU, Barcode, and specific attributes.
  - ProductPricing  : Versioned, tier-based pricing for variants.
  - ProductAlias    : Multilingual alternative names for AI matching.

Normalization & Design Decisions:
  - Hierarchical Categories: Self-referencing parent_id allows N-deep category trees.
  - Variant-Level Pricing: Prices are tied to Product Variants (SKUs), not Products, because a 10kg bag and 50kg bag have different prices.
  - Versioned Pricing: `valid_from` and `valid_to` columns allow tracking price history and scheduling future prices.
  - Centralized Tax: GST is separated into `gst_categories` via HSN codes so tax rule changes apply uniformly.
  - AI Optimization: `product_aliases` supports phonetic, regional, and multilingual names to resolve voice inputs to canonical products.

Relationships:
  Brand 1─── N Product
  Category 1─── N Product (and Category 1─── N Category for hierarchy)
  Unit 1─── N Product (base unit)
  GSTCategory 1─── N Product
  Product 1─── N ProductVariant
  Product 1─── N ProductAlias
  ProductVariant 1─── N ProductPricing
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
    UniqueConstraint,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase


class Brand(TimestampedBase):
    """
    Brand or manufacturer of the products.
    """

    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="brand", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Brand name={self.name}>"


class Category(TimestampedBase):
    """
    Hierarchical product categories.
    """

    __tablename__ = "categories"

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Null for top-level categories",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    # Relationships
    sub_categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent_category"
    )
    parent_category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="sub_categories", remote_side="Category.id"
    )
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_category_parent_name"),
    )

    def __repr__(self) -> str:
        return f"<Category name={self.name}>"


class Unit(TimestampedBase):
    """
    Unit of measure (e.g., Piece, Box, Pallet, KG, Ltr).
    """

    __tablename__ = "units"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    abbreviation: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="base_unit"
    )

    def __repr__(self) -> str:
        return f"<Unit abbrev={self.abbreviation}>"


class GSTCategory(TimestampedBase):
    """
    Tax slabs corresponding to specific HSN codes.
    """

    __tablename__ = "gst_categories"

    hsn_code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    gst_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, comment="Total GST percentage (e.g. 18.00)"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="gst_category"
    )

    __table_args__ = (
        CheckConstraint("gst_percentage >= 0", name="ck_gst_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<GSTCategory HSN={self.hsn_code} Rate={self.gst_percentage}>"


class Product(TimestampedBase):
    """
    The canonical product entity holding shared attributes.
    """

    __tablename__ = "products"

    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    gst_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gst_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    base_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    is_discontinued: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    # Relationships
    brand: Mapped["Brand"] = relationship("Brand", back_populates="products")
    category: Mapped["Category"] = relationship("Category", back_populates="products")
    gst_category: Mapped["GSTCategory"] = relationship(
        "GSTCategory", back_populates="products"
    )
    base_unit: Mapped["Unit"] = relationship("Unit", back_populates="products")

    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )
    aliases: Mapped[list["ProductAlias"]] = relationship(
        "ProductAlias", back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product name={self.name}>"


class ProductVariant(TimestampedBase):
    """
    The actual sellable unit (SKU).
    A product can have multiple variants (e.g., sizes, colors, weights).
    """

    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Specific variant name, e.g., '10L Bucket', 'Red'",
    )
    sku: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    barcode: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    pricing: Mapped[list["ProductPricing"]] = relationship(
        "ProductPricing",
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="ProductPricing.valid_from.desc()",
    )

    def __repr__(self) -> str:
        return f"<ProductVariant SKU={self.sku}>"


class ProductPricing(TimestampedBase):
    """
    Tier-based, versioned pricing for variants.
    Keeps historical records for audit and allows scheduling future prices.
    """

    __tablename__ = "product_pricing"

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dealer_tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Pricing tier: standard, silver, gold, platinum, distributor",
    )

    mrp: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, comment="Maximum Retail Price"
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, comment="Actual selling price for this tier"
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When this price takes effect",
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When this price expires (NULL means currently active)",
    )

    # Relationships
    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="pricing"
    )

    __table_args__ = (
        CheckConstraint("mrp >= 0", name="ck_pricing_mrp_non_negative"),
        CheckConstraint("price >= 0", name="ck_pricing_price_non_negative"),
        CheckConstraint("mrp >= price", name="ck_pricing_mrp_gte_price"),
        Index(
            "ix_product_pricing_variant_tier_dates",
            "product_variant_id",
            "dealer_tier",
            "valid_from",
            "valid_to",
        ),
    )


class ProductAlias(TimestampedBase):
    """
    Multilingual, phonetic, or regional alternative names for products.
    Used by the AI to resolve fuzzy voice inputs to actual canonical products.
    """

    __tablename__ = "product_aliases"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alias_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Alternative name, e.g., 'danda cement' or regional translations",
    )
    language_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        comment="BCP-47 language code for the alias",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint(
            "product_id", "alias_name", "language_code", name="uq_product_alias"
        ),
    )

    def __repr__(self) -> str:
        return f"<ProductAlias alias={self.alias_name}>"
