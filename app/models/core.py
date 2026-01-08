"""
Core Business Models
- Product: Products with types and units
- PriceTier: Progressive pricing based on quantity
- Duration: Subscription durations with discounts
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Product(Base):
    """
    Products available for subscription.
    Supports progressive pricing through price tiers.
    """
    __tablename__ = "products"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Product identification
    name = Column(String(255), nullable=False, unique=True)
    type_id = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=False, index=True)
    unit = Column(String(50), nullable=False)  # 'TB', 'GB', 'user', 'seat', etc.

    # Description
    description = Column(Text)
    is_active = Column(String(10), nullable=False, default='true')  # 'true' or 'false' as string

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    product_type = relationship("ProductType", back_populates="products")
    price_tiers = relationship(
        "PriceTier",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="PriceTier.min_quantity",
    )
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product(name='{self.name}', type_id='{self.type_id}', unit='{self.unit}')>"


class PriceTier(Base):
    """
    Progressive pricing tiers for products.
    Price per unit decreases as quantity increases.
    """
    __tablename__ = "price_tiers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Quantity range for this tier
    min_quantity = Column(Integer, nullable=False)
    max_quantity = Column(Integer)  # NULL means unlimited

    # Price in EUR with 4 decimal precision
    price_per_unit = Column(Numeric(10, 4), nullable=False)

    # Period for pricing
    period = Column(String(20), nullable=False, default='month')  # 'month' or 'year'

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="price_tiers")

    # Constraints
    __table_args__ = (
        CheckConstraint("min_quantity >= 0", name="check_min_quantity_positive"),
        CheckConstraint("max_quantity IS NULL OR max_quantity > min_quantity", name="check_max_greater_than_min"),
        CheckConstraint("price_per_unit > 0", name="check_price_positive"),
        CheckConstraint("period IN ('month', 'year')", name="check_valid_period"),
    )

    def __repr__(self):
        max_qty = self.max_quantity if self.max_quantity else "unlimited"
        return f"<PriceTier(product={self.product.name if self.product else 'N/A'}, {self.min_quantity}-{max_qty}, {self.price_per_unit}/{self.period})>"


class Duration(Base):
    """
    Subscription duration options with discount percentages.
    Longer commitments get better discounts.
    """
    __tablename__ = "durations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Duration in months
    months = Column(Integer, nullable=False, unique=True)

    # Discount percentage (0-100)
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=0)

    # Display name
    name = Column(String(100), nullable=False)  # '12 months', '24 months', etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    order_items = relationship("OrderItem", back_populates="duration")

    # Constraints
    __table_args__ = (
        CheckConstraint("months > 0", name="check_months_positive"),
        CheckConstraint("discount_percentage >= 0 AND discount_percentage <= 100", name="check_discount_range"),
    )

    def __repr__(self):
        return f"<Duration(months={self.months}, discount={self.discount_percentage}%)>"
