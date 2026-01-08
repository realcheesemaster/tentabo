"""
Partner and Distributor Models
- Partner: End customers/resellers
- Distributor: Manage partners and their contracts
- DistributorPartner: Junction table for many-to-many relationship
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Partner(Base):
    """
    Partner companies that create orders and hold contracts.
    Can be associated with one or more distributors.
    """
    __tablename__ = "partners"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Company information
    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255))
    registration_number = Column(String(100), unique=True)  # SIRET, VAT, etc.

    # Contact information
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))

    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), default='France')

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="partner")
    distributor_associations = relationship("DistributorPartner", back_populates="partner")
    leads = relationship("Lead", back_populates="partner")
    orders = relationship("Order", back_populates="partner")
    contracts = relationship("Contract", back_populates="partner")

    def __repr__(self):
        return f"<Partner(name='{self.name}', registration='{self.registration_number}')>"


class Distributor(Base):
    """
    Distributor companies that manage partners.
    Multi-tenant: Each distributor sees only their attached partners.
    """
    __tablename__ = "distributors"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Company information
    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255))
    registration_number = Column(String(100), unique=True)

    # Contact information
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))

    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), default='France')

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="distributor")
    partner_associations = relationship("DistributorPartner", back_populates="distributor")
    leads = relationship("Lead", back_populates="distributor")
    orders = relationship("Order", back_populates="distributor")
    contracts = relationship("Contract", back_populates="distributor")

    def __repr__(self):
        return f"<Distributor(name='{self.name}', registration='{self.registration_number}')>"


class DistributorPartner(Base):
    """
    Junction table for many-to-many relationship between distributors and partners.
    A partner can be managed by multiple distributors.
    A distributor manages multiple partners.
    """
    __tablename__ = "distributor_partners"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    distributor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Association metadata
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"))
    is_active = Column(Boolean, default=True, nullable=False)

    # Notes about this relationship
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    distributor = relationship("Distributor", back_populates="partner_associations")
    partner = relationship("Partner", back_populates="distributor_associations")
    assigned_by_admin = relationship("AdminUser")

    # Ensure unique distributor-partner pairs
    __table_args__ = (
        UniqueConstraint("distributor_id", "partner_id", name="unique_distributor_partner"),
    )

    def __repr__(self):
        return f"<DistributorPartner(distributor_id={self.distributor_id}, partner_id={self.partner_id})>"
