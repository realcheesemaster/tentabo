"""
System Models
- ProviderConfig: Configuration for external providers (auth, CRM, billing)
- ProviderSyncLog: Audit log of provider synchronization operations
- Note: Polymorphic notes for orders, contracts, and leads
- AuditLog: System-wide audit trail
- WebhookEvent: Incoming webhook events from external systems
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, Enum as SQLEnum, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.database import Base


class ProviderType(str, enum.Enum):
    """Types of external providers"""
    AUTH = "auth"
    CRM = "crm"
    BILLING = "billing"


class ProviderConfig(Base):
    """
    Configuration for external service providers.
    Supports multiple provider types: authentication, CRM, billing.
    Only one provider per type can be active at a time.
    """
    __tablename__ = "provider_configs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Provider identification
    provider_type = Column(SQLEnum(ProviderType), nullable=False, index=True)
    provider_name = Column(String(50), nullable=False, index=True)  # 'oxiadmin_ldap', 'pipedrive', 'pennylane', etc.

    # Status
    is_active = Column(Boolean, default=False, nullable=False, index=True)

    # Configuration (non-sensitive settings)
    configuration = Column(JSONB, nullable=False, default={})

    # Credentials (sensitive data - should be encrypted at application level)
    credentials = Column(JSONB, default={})

    # Health monitoring
    health_status = Column(String(20), default='unknown')  # 'healthy', 'degraded', 'offline', 'unknown'
    last_health_check = Column(DateTime(timezone=True))
    health_check_error = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    sync_logs = relationship("ProviderSyncLog", back_populates="provider", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("provider_type", "provider_name", name="unique_provider_type_name"),
        # Ensure only one active provider per type (partial unique index)
        Index("idx_provider_configs_active", "provider_type", "is_active", unique=True, postgresql_where=(Column("is_active") == True)),
        Index("idx_provider_configs_configuration", "configuration", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<ProviderConfig(type='{self.provider_type.value}', name='{self.provider_name}', active={self.is_active})>"


class ProviderSyncLog(Base):
    """
    Audit log for provider synchronization operations.
    Tracks all sync attempts with success/failure details.
    """
    __tablename__ = "provider_sync_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_configs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Sync details
    sync_type = Column(String(50), nullable=False)  # 'full', 'incremental', 'webhook', 'manual'
    entity_type = Column(String(50), nullable=False, index=True)  # 'lead', 'user', 'invoice', 'customer', etc.
    direction = Column(String(20), nullable=False)  # 'pull' (from provider), 'push' (to provider), 'bidirectional'

    # Results
    records_synced = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_details = Column(JSONB, default={})

    # Status
    status = Column(String(20), nullable=False, index=True)  # 'success', 'partial', 'failed'

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    provider = relationship("ProviderConfig", back_populates="sync_logs")

    __table_args__ = (
        Index("idx_sync_logs_provider_entity", "provider_id", "entity_type"),
        Index("idx_sync_logs_status_started", "status", "started_at"),
    )

    def __repr__(self):
        return f"<ProviderSyncLog(entity='{self.entity_type}', status='{self.status}', synced={self.records_synced})>"


class Note(Base):
    """
    Polymorphic notes that can be attached to orders, contracts, or leads.
    Supports visibility control based on user roles.
    """
    __tablename__ = "notes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Polymorphic relationship - can belong to order, contract, or lead
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), index=True)

    # Note content
    content = Column(Text, nullable=False)

    # Visibility control
    is_internal = Column(Boolean, default=False, nullable=False)  # Internal notes not visible to customers
    is_pinned = Column(Boolean, default=False)  # Pin important notes to top

    # Author
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="notes", foreign_keys=[order_id])
    contract = relationship("Contract", back_populates="notes", foreign_keys=[contract_id])
    created_by_user = relationship("User", back_populates="notes")

    __table_args__ = (
        # At least one foreign key must be set
        CheckConstraint(
            "order_id IS NOT NULL OR contract_id IS NOT NULL",
            name="check_note_has_parent"
        ),
        Index("idx_notes_order_created", "order_id", "created_at"),
        Index("idx_notes_contract_created", "contract_id", "created_at"),
    )

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Note(content='{preview}', internal={self.is_internal})>"


class AuditLog(Base):
    """
    System-wide audit trail for tracking all important actions.
    Records who did what, when, and on which resource.
    """
    __tablename__ = "audit_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Who performed the action
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), index=True)

    # What action was performed
    action = Column(String(100), nullable=False, index=True)  # 'create', 'update', 'delete', 'activate', etc.
    entity_type = Column(String(50), nullable=False, index=True)  # 'order', 'contract', 'user', 'provider_config', etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Details of the change
    changes = Column(JSONB, default={})  # Before/after values for updates

    # Request context
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(255))

    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    admin_user = relationship("AdminUser", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_action_created", "action", "created_at"),
        Index("idx_audit_logs_user_created", "user_id", "created_at"),
        Index("idx_audit_logs_changes", "changes", postgresql_using="gin"),
    )

    def __repr__(self):
        actor = f"user:{self.user_id}" if self.user_id else f"admin:{self.admin_user_id}"
        return f"<AuditLog(action='{self.action}', entity='{self.entity_type}:{self.entity_id}', by={actor})>"


class WebhookEvent(Base):
    """
    Incoming webhook events from external systems (Pipedrive, Pennylane, etc.)
    Stores raw payload for processing and debugging.
    """
    __tablename__ = "webhook_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Provider identification
    provider_name = Column(String(50), nullable=False, index=True)
    provider_type = Column(SQLEnum(ProviderType), nullable=False, index=True)

    # Event details
    event_type = Column(String(100), nullable=False, index=True)  # Provider-specific event type
    event_id = Column(String(255), index=True)  # Provider's event ID (for deduplication)

    # Payload
    payload = Column(JSONB, nullable=False)  # Raw webhook payload

    # Processing status
    status = Column(String(20), nullable=False, default='pending', index=True)  # 'pending', 'processing', 'processed', 'failed'
    processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    # Request metadata
    ip_address = Column(String(45))
    headers = Column(JSONB)  # Request headers for debugging

    # Timestamps
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_webhook_events_provider_type", "provider_name", "event_type"),
        Index("idx_webhook_events_status_received", "status", "received_at"),
        Index("idx_webhook_events_event_id", "provider_name", "event_id"),  # For deduplication
        Index("idx_webhook_events_payload", "payload", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<WebhookEvent(provider='{self.provider_name}', type='{self.event_type}', status='{self.status}')>"
