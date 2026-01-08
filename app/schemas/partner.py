"""
Partner and Distributor Pydantic schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from uuid import UUID


class PartnerBase(BaseModel):
    """Base partner schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    legal_name: Optional[str] = Field(None, max_length=255, description="Legal company name")
    registration_number: Optional[str] = Field(None, max_length=100, description="Company registration number")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="France", max_length=100)
    is_active: bool = Field(default=True, description="Whether partner is active")
    notes: Optional[str] = Field(None, description="Internal notes")


class PartnerCreate(PartnerBase):
    """Schema for creating a partner"""
    pass


class PartnerUpdate(BaseModel):
    """Schema for updating a partner"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    registration_number: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PartnerResponse(PartnerBase):
    """Schema for partner response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PartnerListResponse(BaseModel):
    """Schema for paginated partner list"""
    items: List[PartnerResponse]
    pagination: dict


class DistributorBase(BaseModel):
    """Base distributor schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    legal_name: Optional[str] = Field(None, max_length=255, description="Legal company name")
    registration_number: Optional[str] = Field(None, max_length=100, description="Company registration number")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="France", max_length=100)
    is_active: bool = Field(default=True, description="Whether distributor is active")
    notes: Optional[str] = Field(None, description="Internal notes")


class DistributorCreate(DistributorBase):
    """Schema for creating a distributor"""
    pass


class DistributorUpdate(BaseModel):
    """Schema for updating a distributor"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    registration_number: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class DistributorResponse(DistributorBase):
    """Schema for distributor response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DistributorListResponse(BaseModel):
    """Schema for paginated distributor list"""
    items: List[DistributorResponse]
    pagination: dict


class DistributorPartnerLinkRequest(BaseModel):
    """Request to link a partner to a distributor"""
    partner_id: UUID = Field(..., description="Partner ID to link")
    notes: Optional[str] = Field(None, description="Notes about this relationship")


class DistributorPartnerResponse(BaseModel):
    """Schema for distributor-partner association response"""
    id: UUID
    distributor_id: UUID
    partner_id: UUID
    partner: PartnerResponse
    assigned_at: datetime
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
