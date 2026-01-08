"""
User-related Pydantic schemas
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    provider: str
    provider_id: str
    email: EmailStr
    full_name: Optional[str] = None
    username: Optional[str] = None
    role: str
    is_enabled: bool
    partner_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None
    enabled_by: Optional[UUID] = None
    enabled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list"""
    items: list[UserResponse]
    pagination: dict


class UserEnableRequest(BaseModel):
    """Request to enable/disable a user"""
    enabled: bool = Field(..., description="Enable or disable the user")
    reason: Optional[str] = Field(None, description="Reason for the change")


class UserRoleUpdateRequest(BaseModel):
    """Request to update user role"""
    role: str = Field(..., description="New role")
    reason: Optional[str] = Field(None, description="Reason for the change")

    def validate_role(cls, v):
        valid_roles = ['admin', 'restricted_admin', 'partner', 'distributor', 'fulfiller']
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v
