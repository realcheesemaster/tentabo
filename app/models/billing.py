"""
Billing Models
- Order: Customer orders with items and billing integration
- OrderItem: Individual items in an order (product + duration + quantity)
- Contract: Activated orders with billing and invoicing
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Numeric, Integer, Enum as SQLEnum, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.database import Base


class OrderStatus(str, enum.Enum):
    """Order lifecycle status"""
    CREATED = "created"
    CANCELLED = "cancelled"
    SENT = "sent"
    IN_FULFILLMENT = "in_fulfillment"
    FULFILLED = "fulfilled"


class ContractStatus(str, enum.Enum):
    """Contract lifecycle status"""
    ACTIVE = "active"
    LOST = "lost"
    UPGRADED = "upgraded"
    DOWNGRADED = "downgraded"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ContractType(str, enum.Enum):
    """Contract type classification"""
    MSP = "msp"
    RESELLER = "reseller"
    END_CUSTOMER = "end_customer"
    OTHER = "other"


class Order(Base):
    """
    Customer orders with provider-agnostic billing integration.
    Links to external billing system (Pennylane, QuickBooks, etc.)
    and optionally to CRM system.
    """
    __tablename__ = "orders"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Order reference
    order_number = Column(String(100), unique=True, nullable=False, index=True)

    # Status
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.CREATED, index=True)

    # Billing provider tracking
    billing_provider = Column(String(50))  # 'pennylane', 'quickbooks', 'xero', etc.
    billing_quote_id = Column(String(255))  # External quote ID from billing system
    billing_metadata = Column(JSONB, default={})  # Provider-specific billing data

    # CRM provider tracking (optional link to deal/opportunity)
    crm_provider = Column(String(50))  # 'pipedrive', 'salesforce', etc.
    crm_deal_id = Column(String(255))  # External deal/opportunity ID
    crm_metadata = Column(JSONB, default={})  # Provider-specific CRM data

    # Relationships
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), index=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), index=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), index=True)  # Originating lead

    # Financial totals (calculated from items)
    subtotal = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), default=0)

    # Notes
    notes_internal = Column(Text)  # Internal notes (not visible to customer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True))
    fulfilled_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))

    # Relationships
    created_by_user = relationship("User", back_populates="created_orders")
    partner = relationship("Partner", back_populates="orders")
    distributor = relationship("Distributor", back_populates="orders")
    lead = relationship("Lead", back_populates="orders")

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    contract = relationship("Contract", back_populates="order", uselist=False)
    notes = relationship("Note", back_populates="order", foreign_keys="Note.order_id")

    __table_args__ = (
        Index("idx_orders_status_created", "status", "created_at"),
        Index("idx_orders_partner_status", "partner_id", "status"),
        Index("idx_orders_distributor_status", "distributor_id", "status"),
        Index("idx_orders_billing_metadata", "billing_metadata", postgresql_using="gin"),
        Index("idx_orders_crm_metadata", "crm_metadata", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<Order(number='{self.order_number}', status='{self.status.value}', total={self.total_amount})>"


class OrderItem(Base):
    """
    Individual line items in an order.
    Each item represents a product subscription with duration and quantity.
    """
    __tablename__ = "order_items"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    duration_id = Column(UUID(as_uuid=True), ForeignKey("durations.id"), nullable=False)

    # Quantity and pricing
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 4), nullable=False)  # Price per unit at time of order
    discount_percentage = Column(Numeric(5, 2), default=0)  # Duration discount applied

    # Calculated amounts
    subtotal = Column(Numeric(12, 2), nullable=False)  # quantity * unit_price
    discount_amount = Column(Numeric(12, 2), default=0)  # Applied discount
    total = Column(Numeric(12, 2), nullable=False)  # After discount

    # Item description (snapshot at time of order)
    product_name = Column(String(255), nullable=False)
    product_type = Column(String(100), nullable=False)
    product_unit = Column(String(50), nullable=False)
    duration_months = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    duration = relationship("Duration", back_populates="order_items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_unit_price_positive"),
        CheckConstraint("discount_percentage >= 0 AND discount_percentage <= 100", name="check_discount_range"),
    )

    def __repr__(self):
        return f"<OrderItem(product='{self.product_name}', qty={self.quantity}, total={self.total})>"


class Contract(Base):
    """
    Activated contracts from fulfilled orders.
    Linked to billing provider for invoice tracking.
    """
    __tablename__ = "contracts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Contract reference
    contract_number = Column(String(100), unique=True, nullable=False, index=True)

    # Order this contract came from (optional - contracts can exist without orders)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True, index=True)

    # Status
    status = Column(SQLEnum(ContractStatus), nullable=False, default=ContractStatus.ACTIVE, index=True)

    # Contract type
    contract_type = Column(SQLEnum(ContractType), nullable=False, default=ContractType.OTHER)

    # Billing provider tracking
    billing_provider = Column(String(50), nullable=False)  # 'pennylane', 'quickbooks', etc.
    billing_customer_id = Column(String(255))  # External customer ID in billing system
    billing_invoices = Column(JSONB, default=[])  # Array of invoice IDs from billing provider
    billing_metadata = Column(JSONB, default={})  # Provider-specific data

    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("pennylane_customers.id", ondelete="SET NULL"), nullable=False, index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), index=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), index=True)

    # Contract dates
    activation_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expiration_date = Column(DateTime(timezone=True))
    renewed_from_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"))  # If this is a renewal

    # Financial information
    periodicity_months = Column(Integer, nullable=True)  # Number of months between invoices (e.g., 1, 3, 6, 12)
    value_per_period = Column(Numeric(12, 2), nullable=True)  # Value charged each period
    total_value = Column(Numeric(12, 2), nullable=False)  # Calculated from periodicity and value_per_period
    currency = Column(String(3), default='EUR')

    # Notes
    notes_internal = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    cancelled_at = Column(DateTime(timezone=True))

    # Relationships
    order = relationship("Order", back_populates="contract")
    user = relationship("User", back_populates="contracts")
    customer = relationship("PennylaneCustomer", back_populates="contracts")
    partner = relationship("Partner", back_populates="contracts")
    distributor = relationship("Distributor", back_populates="contracts")
    notes = relationship("Note", back_populates="contract", foreign_keys="Note.contract_id")
    pennylane_invoices = relationship("PennylaneInvoice", back_populates="contract")

    # Self-referential relationship for renewals
    renewed_from = relationship("Contract", remote_side=[id], foreign_keys=[renewed_from_id])

    __table_args__ = (
        Index("idx_contracts_status_activation", "status", "activation_date"),
        Index("idx_contracts_partner_status", "partner_id", "status"),
        Index("idx_contracts_distributor_status", "distributor_id", "status"),
        Index("idx_contracts_expiration", "expiration_date"),
        Index("idx_contracts_billing_metadata", "billing_metadata", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<Contract(number='{self.contract_number}', status='{self.status.value}', value={self.total_value})>"
