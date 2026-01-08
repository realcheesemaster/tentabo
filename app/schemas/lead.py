"""
Lead-related Pydantic schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from decimal import Decimal
from uuid import UUID


class LeadActivityBase(BaseModel):
    """Base lead activity schema"""
    activity_type: str = Field(..., min_length=1, max_length=50, description="Activity type (call, email, meeting, etc.)")
    subject: Optional[str] = Field(None, max_length=255, description="Activity subject")
    description: Optional[str] = Field(None, description="Activity description")
    due_date: Optional[datetime] = Field(None, description="Due date for the activity")
    done: bool = Field(default=False, description="Whether activity is completed")


class LeadActivityCreate(LeadActivityBase):
    """Schema for creating a lead activity"""
    pass


class LeadActivityResponse(LeadActivityBase):
    """Schema for lead activity response"""
    id: UUID
    lead_id: UUID
    provider_name: str
    provider_id: Optional[str] = None
    done_at: Optional[datetime] = None
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @validator('done', pre=True)
    def convert_done(cls, v):
        """Convert string 'true'/'false' to boolean"""
        if isinstance(v, str):
            return v.lower() == 'true'
        return v


class LeadNoteBase(BaseModel):
    """Base lead note schema"""
    content: str = Field(..., min_length=1, description="Note content")


class LeadNoteCreate(LeadNoteBase):
    """Schema for creating a lead note"""
    pass


class LeadNoteResponse(LeadNoteBase):
    """Schema for lead note response"""
    id: UUID
    lead_id: UUID
    provider_name: Optional[str] = None
    provider_id: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadBase(BaseModel):
    """Base lead schema"""
    title: str = Field(..., min_length=1, max_length=255, description="Lead title")
    organization: str = Field(..., min_length=1, max_length=255, description="Organization name")
    contact_name: str = Field(..., min_length=1, max_length=255, description="Contact person name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    value: Optional[Decimal] = Field(None, description="Estimated deal value")
    currency: str = Field(default="EUR", max_length=3, description="Currency code")
    status: str = Field(..., description="Lead status")
    probability: Optional[int] = Field(None, ge=0, le=100, description="Win probability (0-100)")
    expected_close_date: Optional[datetime] = Field(None, description="Expected close date")
    partner_id: Optional[UUID] = Field(None, description="Associated partner")
    distributor_id: Optional[UUID] = Field(None, description="Associated distributor")

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class LeadCreate(LeadBase):
    """Schema for creating a lead"""
    provider_name: str = Field(default="manual", description="CRM provider name")
    provider_id: Optional[str] = Field(None, description="External provider ID")


class LeadUpdate(BaseModel):
    """Schema for updating a lead"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    organization: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_name: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    value: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=3)
    status: Optional[str] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    expected_close_date: Optional[datetime] = None
    partner_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class LeadResponse(LeadBase):
    """Schema for lead response"""
    id: UUID
    provider_name: str
    provider_id: Optional[str] = None
    owner_id: UUID
    last_sync_at: Optional[datetime] = None
    sync_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadDetailResponse(LeadResponse):
    """Schema for detailed lead response with relationships"""
    activities: List[LeadActivityResponse] = []
    notes: List[LeadNoteResponse] = []


class LeadListResponse(BaseModel):
    """Schema for paginated lead list"""
    items: List[LeadResponse]
    pagination: dict


class LeadConvertRequest(BaseModel):
    """Request to convert lead to order"""
    partner_id: Optional[UUID] = Field(None, description="Partner for the order (if not already set)")
    distributor_id: Optional[UUID] = Field(None, description="Distributor for the order (if not already set)")
    items: List[dict] = Field(..., description="Order items (product_id, quantity, duration_id)")


class LeadStatusChangeRequest(BaseModel):
    """Request to change lead status"""
    status: str = Field(..., description="New status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v
