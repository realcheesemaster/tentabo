"""
CRM Models (Provider-Agnostic)
- Lead: Sales opportunities from any CRM provider
- LeadActivity: Activities/interactions tracked for leads
- LeadNote: Notes attached to leads
- LeadStatusHistory: Audit trail of status changes
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Numeric, Integer, Enum as SQLEnum, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.database import Base


class LeadStatus(str, enum.Enum):
    """Standard lead status across all CRM providers"""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class Lead(Base):
    """
    Provider-agnostic lead model.
    Stores leads from any CRM system (Pipedrive, Salesforce, HubSpot, etc.)
    with provider-specific data in JSONB metadata field.
    """
    __tablename__ = "leads"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Provider tracking
    provider_name = Column(String(50), nullable=False, index=True)  # 'pipedrive', 'salesforce', etc.
    provider_id = Column(String(255), index=True)  # External ID from CRM provider
    provider_metadata = Column(JSONB, default={})  # Provider-specific data

    # Core lead information
    title = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False, index=True)

    # Contact information
    contact_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), index=True)
    contact_phone = Column(String(50))

    # Financial information
    value = Column(Numeric(12, 2))  # Estimated deal value
    currency = Column(String(3), default='EUR')  # ISO 4217 currency code

    # Status and probability
    status = Column(SQLEnum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    probability = Column(Integer)  # 0-100

    # Expected close date
    expected_close_date = Column(DateTime(timezone=True))

    # Ownership and relationships
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), index=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), index=True)

    # Sync tracking
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='synced')  # 'synced', 'pending', 'error'
    sync_error = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="created_leads", foreign_keys=[owner_id])
    partner = relationship("Partner", back_populates="leads")
    distributor = relationship("Distributor", back_populates="leads")

    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    status_history = relationship("LeadStatusHistory", back_populates="lead", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="lead")

    # Constraints
    __table_args__ = (
        CheckConstraint("probability IS NULL OR (probability >= 0 AND probability <= 100)", name="check_probability_range"),
        # Compound indexes for common queries
        Index("idx_leads_owner_status", "owner_id", "status"),
        Index("idx_leads_distributor_partner", "distributor_id", "partner_id"),
        Index("idx_leads_provider", "provider_name", "provider_id"),
        Index("idx_leads_status_created", "status", "created_at"),
        # GIN index for JSONB metadata queries
        Index("idx_leads_metadata", "provider_metadata", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<Lead(title='{self.title}', organization='{self.organization}', status='{self.status.value}')>"


class LeadActivity(Base):
    """
    Activities and interactions related to leads.
    Synced from CRM providers (calls, emails, meetings, etc.)
    """
    __tablename__ = "lead_activities"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)

    # Provider tracking
    provider_name = Column(String(50), nullable=False)
    provider_id = Column(String(255), index=True)
    provider_metadata = Column(JSONB, default={})

    # Activity details
    activity_type = Column(String(50), nullable=False, index=True)  # 'call', 'email', 'meeting', 'note', etc.
    subject = Column(String(255))
    description = Column(Text)

    # Activity timing
    due_date = Column(DateTime(timezone=True))
    done = Column(String(10), default='false')  # 'true' or 'false' as string
    done_at = Column(DateTime(timezone=True))

    # Associated user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="activities")
    user = relationship("User")

    __table_args__ = (
        Index("idx_lead_activities_lead_type", "lead_id", "activity_type"),
        Index("idx_lead_activities_due_date", "due_date"),
    )

    def __repr__(self):
        return f"<LeadActivity(type='{self.activity_type}', subject='{self.subject}')>"


class LeadNote(Base):
    """
    Notes attached to leads.
    Can be created internally or synced from CRM provider.
    """
    __tablename__ = "lead_notes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)

    # Provider tracking (NULL if created internally)
    provider_name = Column(String(50))
    provider_id = Column(String(255))

    # Note content
    content = Column(Text, nullable=False)

    # Author
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="notes")
    created_by = relationship("User")

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<LeadNote(lead_id={self.lead_id}, content='{preview}')>"


class LeadStatusHistory(Base):
    """
    Audit trail of lead status changes.
    Tracks who changed the status, when, and from what to what.
    """
    __tablename__ = "lead_status_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status change details
    old_status = Column(SQLEnum(LeadStatus))
    new_status = Column(SQLEnum(LeadStatus), nullable=False)

    # Who made the change
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Optional reason/note
    reason = Column(Text)

    # Timestamp
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="status_history")
    changed_by = relationship("User")

    __table_args__ = (
        Index("idx_lead_status_history_lead_date", "lead_id", "changed_at"),
    )

    def __repr__(self):
        return f"<LeadStatusHistory(lead_id={self.lead_id}, {self.old_status} -> {self.new_status})>"
