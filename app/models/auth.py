"""
Authentication Models
- AdminUser: Independent admin accounts with bcrypt password
- User: Provider-based users with roles managed in DB
"""
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.database import Base


class UserRole(str, enum.Enum):
    """User roles for authorization"""
    ADMIN = "admin"
    RESTRICTED_ADMIN = "restricted_admin"
    PARTNER = "partner"
    DISTRIBUTOR = "distributor"
    FULFILLER = "fulfiller"


class AdminUser(Base):
    """
    Independent admin account stored in database.
    Password hashed with bcrypt.
    No dependency on external auth providers.
    Used for system administration and emergency access.
    """
    __tablename__ = "admin_users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    enabled_users = relationship("User", back_populates="enabled_by_admin", foreign_keys="User.enabled_by")
    audit_logs = relationship("AuditLog", back_populates="admin_user")
    api_keys = relationship("APIKey", foreign_keys="APIKey.admin_user_id", back_populates="admin_user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AdminUser(username='{self.username}', email='{self.email}')>"


class User(Base):
    """
    Regular user accounts authenticated via external providers.
    Authorization (roles) managed in our database.
    Users must be enabled by admin after first login.
    """
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Provider tracking
    provider = Column(String(50), nullable=False)  # 'ldap', 'google', 'saml', etc.
    provider_id = Column(String(255), nullable=False)  # Provider-specific user ID

    # User information
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255))
    username = Column(String(100), index=True)

    # Authorization (managed in our DB, not from provider)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.PARTNER)
    is_enabled = Column(Boolean, default=False, nullable=False, index=True)

    # Admin who enabled this user
    enabled_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"))
    enabled_at = Column(DateTime(timezone=True))

    # Partner/Distributor association
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"))
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    enabled_by_admin = relationship("AdminUser", back_populates="enabled_users", foreign_keys=[enabled_by])
    partner = relationship("Partner", back_populates="users")
    distributor = relationship("Distributor", back_populates="users")

    # Business relationships
    created_leads = relationship("Lead", back_populates="owner", foreign_keys="Lead.owner_id")
    created_orders = relationship("Order", back_populates="created_by_user")
    contracts = relationship("Contract", back_populates="user")
    notes = relationship("Note", back_populates="created_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    api_keys = relationship("APIKey", foreign_keys="APIKey.user_id", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role.value}', provider='{self.provider}')>"

    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.role in [UserRole.ADMIN, UserRole.RESTRICTED_ADMIN]

    @property
    def can_manage_contracts(self):
        """Check if user can manage contracts"""
        return self.role == UserRole.ADMIN

    @property
    def can_activate_contracts(self):
        """Check if user can activate contracts"""
        return self.role in [UserRole.ADMIN, UserRole.FULFILLER]
