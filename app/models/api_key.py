"""
API Key model for long-lived authentication tokens

API keys allow programmatic access to the Tentabo PRM API without storing passwords.
Users can generate multiple named keys with optional expiration and scopes.
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
import uuid

from app.database import Base


class APIKey(Base):
    """
    Personal Access Tokens for API authentication

    These are long-lived bearer tokens that users can generate
    for programmatic API access without storing passwords.
    """
    __tablename__ = 'api_keys'

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys - can belong to either a regular user or admin
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey('admin_users.id', ondelete='CASCADE'), nullable=True)

    # Key information
    name = Column(String(100), nullable=False)  # User-friendly name: "Mobile App", "CI/CD Pipeline"
    key_hash = Column(String(255), nullable=False)  # bcrypt hash of the actual key
    key_prefix = Column(String(12), nullable=False, index=True)  # "tnt_xxxx" for quick lookup
    description = Column(Text, nullable=True)  # Optional longer description

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    last_used_user_agent = Column(String(255), nullable=True)
    usage_count = Column(Integer, default=0)

    # Expiration and status
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Permissions
    scopes = Column(JSONB, default=list, nullable=False)
    # Examples: ["read:leads", "write:orders", "admin:users"]
    # Special scopes: ["*"] for full access, ["read:*"] for read all

    # Revocation tracking
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    revoked_by_admin_id = Column(UUID(as_uuid=True), ForeignKey('admin_users.id'), nullable=True)
    revoked_reason = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="api_keys")
    admin_user = relationship("AdminUser", foreign_keys=[admin_user_id], back_populates="api_keys")

    # Add these relationships to User and AdminUser models:
    # api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    # api_keys = relationship("APIKey", back_populates="admin_user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(name='{self.name}', prefix='{self.key_prefix}', active={self.is_active})>"

    @property
    def owner(self):
        """Get the owner of this API key (either user or admin)"""
        return self.user or self.admin_user

    @property
    def owner_type(self):
        """Get the type of owner"""
        if self.admin_user_id:
            return "admin"
        elif self.user_id:
            return "user"
        return None

    @property
    def is_expired(self):
        """Check if the key has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def is_valid(self):
        """Check if the key is valid for use"""
        return self.is_active and not self.is_expired

    def has_scope(self, required_scope: str) -> bool:
        """
        Check if this key has a specific scope

        Args:
            required_scope: The scope to check (e.g., "read:leads")

        Returns:
            True if the key has the scope or a wildcard that covers it
        """
        if "*" in self.scopes:  # Full access
            return True

        if required_scope in self.scopes:
            return True

        # Check for wildcard scopes like "read:*" or "*:leads"
        action, resource = required_scope.split(":", 1) if ":" in required_scope else (required_scope, "")

        if f"{action}:*" in self.scopes:  # e.g., "read:*" covers "read:leads"
            return True

        if f"*:{resource}" in self.scopes:  # e.g., "*:leads" covers "read:leads", "write:leads"
            return True

        return False

    def record_usage(self, ip_address: str = None, user_agent: str = None):
        """Record that this key was used"""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1
        if ip_address:
            self.last_used_ip = ip_address
        if user_agent:
            self.last_used_user_agent = user_agent[:255]  # Truncate if too long

    def revoke(self, revoked_by, reason: str = None):
        """Revoke this API key"""
        self.is_active = False
        self.revoked_at = datetime.utcnow()
        self.revoked_reason = reason

        if hasattr(revoked_by, '__tablename__'):
            if revoked_by.__tablename__ == 'admin_users':
                self.revoked_by_admin_id = revoked_by.id
            elif revoked_by.__tablename__ == 'users':
                self.revoked_by_user_id = revoked_by.id


# Indexes for performance (defined at table level)
# Compound index for finding active keys by prefix
Index('idx_api_keys_prefix_active', APIKey.key_prefix, APIKey.is_active)

# Index for finding keys by owner
Index('idx_api_keys_user_active', APIKey.user_id, APIKey.is_active)
Index('idx_api_keys_admin_active', APIKey.admin_user_id, APIKey.is_active)

# Index for cleanup of expired keys
Index('idx_api_keys_expires_active', APIKey.expires_at, APIKey.is_active)