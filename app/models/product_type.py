"""
ProductType Model

Defines product types that can be assigned to products.
Examples: appliance, service, software, hardware, etc.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class ProductType(Base):
    """
    Product type for categorizing products.
    Can be managed by admins through the UI.
    """
    __tablename__ = "product_types"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Type information
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="product_type")

    def __repr__(self):
        return f"<ProductType(name='{self.name}', is_active={self.is_active})>"
