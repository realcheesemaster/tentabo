"""
Pennylane Sync Models
- PennylaneConnection: API connection configurations for Pennylane
- PennylaneInvoice: Synced invoice data from Pennylane
- PennylaneQuote: Synced quote data from Pennylane
- PennylaneSubscription: Synced billing subscription data from Pennylane
- PennylaneCustomer: Synced customer data from Pennylane
"""
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Numeric,
    Date,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class PennylaneConnection(Base):
    """
    Stores API connection configurations for Pennylane.
    Each connection represents a separate Pennylane account/company.
    """
    __tablename__ = "pennylane_connections"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Connection identification
    name = Column(String(255), unique=True, nullable=False, index=True)
    api_token = Column(String(500), nullable=False)  # Bearer token (will be encrypted later)
    company_name = Column(String(255))  # Fetched from /me endpoint

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Last sync information
    last_sync_at = Column(DateTime(timezone=True))
    last_sync_status = Column(String(50))  # success, failed, partial
    last_sync_error = Column(Text)

    # Sync configuration flags
    sync_invoices = Column(Boolean, default=True, nullable=False)
    sync_quotes = Column(Boolean, default=True, nullable=False)
    sync_subscriptions = Column(Boolean, default=True, nullable=False)
    sync_customers = Column(Boolean, default=True, nullable=False)

    # Audit fields
    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id"),
        nullable=True,  # Nullable to allow creation without strict FK
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    created_by = relationship("AdminUser", foreign_keys=[created_by_id])
    invoices = relationship(
        "PennylaneInvoice",
        back_populates="connection",
        cascade="all, delete-orphan",
    )
    quotes = relationship(
        "PennylaneQuote",
        back_populates="connection",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship(
        "PennylaneSubscription",
        back_populates="connection",
        cascade="all, delete-orphan",
    )
    customers = relationship(
        "PennylaneCustomer",
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_pennylane_connections_active_sync", "is_active", "last_sync_at"),
    )

    def __repr__(self):
        return f"<PennylaneConnection(name='{self.name}', active={self.is_active})>"


class PennylaneInvoice(Base):
    """
    Synced invoice data from Pennylane API.
    Stores both essential fields and full raw API response.
    """
    __tablename__ = "pennylane_invoices"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Connection reference
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pennylane_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pennylane identifiers
    pennylane_id = Column(String(255), nullable=False, index=True)
    invoice_number = Column(String(100), index=True)

    # Invoice status
    status = Column(String(50), index=True)  # draft, finalized, paid, etc.

    # Customer information
    customer_name = Column(String(255), index=True)
    customer_id = Column(String(255), index=True)  # Pennylane customer ID

    # Financial information
    amount = Column(Numeric(12, 2))
    currency = Column(String(3), default="EUR")

    # Dates
    issue_date = Column(Date, index=True)
    due_date = Column(Date, index=True)
    paid_date = Column(Date)

    # Document URL
    pdf_url = Column(String(1000))

    # Full API response for reference
    raw_data = Column(JSONB, default={})

    # Sync tracking
    synced_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Link to internal Contract (optional)
    contract_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # True if invoice is explicitly marked as having no associated contract
    # (distinguishes between "not yet linked" and "explicitly no contract")
    no_contract = Column(Boolean, default=False, nullable=False)

    # Relationships
    connection = relationship("PennylaneConnection", back_populates="invoices")
    contract = relationship("Contract", back_populates="pennylane_invoices")

    __table_args__ = (
        UniqueConstraint("connection_id", "pennylane_id", name="uq_pennylane_invoice_connection_id"),
        Index("idx_pennylane_invoices_status_date", "status", "issue_date"),
        Index("idx_pennylane_invoices_customer", "connection_id", "customer_id"),
        Index("idx_pennylane_invoices_raw_data", "raw_data", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<PennylaneInvoice(number='{self.invoice_number}', status='{self.status}', amount={self.amount})>"


class PennylaneQuote(Base):
    """
    Synced quote data from Pennylane API.
    Stores both essential fields and full raw API response.
    """
    __tablename__ = "pennylane_quotes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Connection reference
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pennylane_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pennylane identifiers
    pennylane_id = Column(String(255), nullable=False, index=True)
    quote_number = Column(String(100), index=True)

    # Quote status
    status = Column(String(50), index=True)  # draft, sent, accepted, rejected

    # Customer information
    customer_name = Column(String(255), index=True)
    customer_id = Column(String(255), index=True)  # Pennylane customer ID

    # Financial information
    amount = Column(Numeric(12, 2))
    currency = Column(String(3), default="EUR")

    # Dates
    issue_date = Column(Date, index=True)
    valid_until = Column(Date)
    accepted_at = Column(DateTime(timezone=True))

    # Full API response for reference
    raw_data = Column(JSONB, default={})

    # Sync tracking
    synced_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    connection = relationship("PennylaneConnection", back_populates="quotes")

    __table_args__ = (
        UniqueConstraint("connection_id", "pennylane_id", name="uq_pennylane_quote_connection_id"),
        Index("idx_pennylane_quotes_status_date", "status", "issue_date"),
        Index("idx_pennylane_quotes_customer", "connection_id", "customer_id"),
        Index("idx_pennylane_quotes_raw_data", "raw_data", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<PennylaneQuote(number='{self.quote_number}', status='{self.status}', amount={self.amount})>"


class PennylaneSubscription(Base):
    """
    Synced billing subscription data from Pennylane API.
    Stores both essential fields and full raw API response.
    """
    __tablename__ = "pennylane_subscriptions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Connection reference
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pennylane_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pennylane identifiers
    pennylane_id = Column(String(255), nullable=False, index=True)

    # Customer information
    customer_name = Column(String(255), index=True)
    customer_id = Column(String(255), index=True)  # Pennylane customer ID

    # Subscription status
    status = Column(String(50), index=True)  # active, paused, cancelled

    # Financial information
    amount = Column(Numeric(12, 2))  # Recurring amount
    currency = Column(String(3), default="EUR")
    interval = Column(String(50))  # monthly, yearly, etc.

    # Dates
    start_date = Column(Date, index=True)
    next_billing_date = Column(Date, index=True)
    cancelled_at = Column(DateTime(timezone=True))

    # Full API response for reference
    raw_data = Column(JSONB, default={})

    # Sync tracking
    synced_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    connection = relationship("PennylaneConnection", back_populates="subscriptions")

    __table_args__ = (
        UniqueConstraint("connection_id", "pennylane_id", name="uq_pennylane_subscription_connection_id"),
        Index("idx_pennylane_subscriptions_status", "status", "start_date"),
        Index("idx_pennylane_subscriptions_customer", "connection_id", "customer_id"),
        Index("idx_pennylane_subscriptions_next_billing", "next_billing_date"),
        Index("idx_pennylane_subscriptions_raw_data", "raw_data", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<PennylaneSubscription(customer='{self.customer_name}', status='{self.status}', amount={self.amount})>"


class PennylaneCustomer(Base):
    """
    Synced customer data from Pennylane API.
    Stores both essential fields and full raw API response.
    """
    __tablename__ = "pennylane_customers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Connection reference
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pennylane_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pennylane identifier
    pennylane_id = Column(String(255), nullable=False, index=True)

    # Customer information
    name = Column(String(255), index=True)  # Customer/company name
    first_name = Column(String(255))
    last_name = Column(String(255))
    email = Column(String(255), index=True)
    phone = Column(String(100))

    # Address information
    address = Column(String(500))
    city = Column(String(255))
    postal_code = Column(String(50))
    country_code = Column(String(10))

    # Business information
    vat_number = Column(String(100))
    customer_type = Column(String(50))  # individual or company

    # Delivery address fields
    delivery_address = Column(String(500), nullable=True)
    delivery_city = Column(String(200), nullable=True)
    delivery_postal_code = Column(String(20), nullable=True)
    delivery_country_code = Column(String(10), nullable=True)

    # Additional business fields
    reg_no = Column(String(50), nullable=True)  # SIRET/SIREN registration number
    recipient = Column(String(200), nullable=True)  # Recipient name
    reference = Column(String(100), nullable=True)  # Customer reference
    external_reference = Column(String(100), nullable=True)  # External system reference
    billing_language = Column(String(10), nullable=True)  # e.g., "fr_FR"
    payment_conditions = Column(String(50), nullable=True)  # e.g., "30_days"
    notes = Column(Text, nullable=True)  # Customer notes
    billing_iban = Column(String(50), nullable=True)  # Billing IBAN

    # Timestamps from Pennylane
    pennylane_created_at = Column(DateTime(timezone=True), nullable=True)
    pennylane_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Full API response for reference
    raw_data = Column(JSONB, default={})

    # Sync tracking
    synced_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    connection = relationship("PennylaneConnection", back_populates="customers")
    contracts = relationship("Contract", back_populates="customer")

    __table_args__ = (
        UniqueConstraint("connection_id", "pennylane_id", name="uq_pennylane_customer_connection_id"),
        Index("idx_pennylane_customers_name", "name"),
        Index("idx_pennylane_customers_email", "email"),
        Index("idx_pennylane_customers_raw_data", "raw_data", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<PennylaneCustomer(name='{self.name}', type='{self.customer_type}', email='{self.email}')>"
