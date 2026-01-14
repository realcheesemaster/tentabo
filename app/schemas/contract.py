"""
Contract-related Pydantic schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from uuid import UUID

from app.models.billing import ContractType


class ContractNoteBase(BaseModel):
    """Base contract note schema"""
    content: str = Field(..., min_length=1, description="Note content")
    is_internal: bool = Field(default=False, description="Internal note (not visible to customer)")
    is_pinned: bool = Field(default=False, description="Pin note to top")


class ContractNoteCreate(ContractNoteBase):
    """Schema for creating a contract note"""
    pass


class ContractNoteResponse(ContractNoteBase):
    """Schema for contract note response"""
    id: UUID
    contract_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContractActivateRequest(BaseModel):
    """Request to activate a contract from an order"""
    activation_date: Optional[datetime] = Field(None, description="Contract activation date (defaults to now)")
    expiration_date: Optional[datetime] = Field(None, description="Contract expiration date")
    notes_internal: Optional[str] = Field(None, description="Internal notes")


class ContractStatusUpdate(BaseModel):
    """Schema for updating contract status"""
    status: str = Field(..., description="New status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['active', 'lost', 'upgraded', 'downgraded', 'expired', 'cancelled']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class ContractCreateRequest(BaseModel):
    """Schema for creating a contract directly (without an order)"""
    contract_number: Optional[str] = Field(None, description="Contract number (auto-generated if not provided)")
    customer_id: UUID = Field(..., description="Customer ID (required)")
    partner_id: Optional[UUID] = Field(None, description="Partner ID")
    distributor_id: Optional[UUID] = Field(None, description="Distributor ID")
    contract_type: ContractType = Field(ContractType.OTHER, description="Contract type (msp, reseller, end_customer, other)")
    periodicity_months: Optional[int] = Field(None, description="Number of months between invoices (e.g., 1, 3, 6, 12)")
    value_per_period: Optional[float] = Field(None, description="Value charged each period")
    currency: str = Field("EUR", description="Currency code")
    activation_date: Optional[datetime] = Field(None, description="Activation date (defaults to now)")
    expiration_date: Optional[datetime] = Field(None, description="Expiration date")
    notes_internal: Optional[str] = Field(None, description="Internal notes")


class ContractResponse(BaseModel):
    """Schema for contract response"""
    id: UUID
    contract_number: str
    order_id: Optional[UUID] = None
    status: str
    contract_type: ContractType
    user_id: UUID
    customer_id: UUID
    customer_name: Optional[str] = None
    partner_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None
    activation_date: datetime
    expiration_date: Optional[datetime] = None
    renewed_from_id: Optional[UUID] = None
    periodicity_months: Optional[int] = None
    value_per_period: Optional[Decimal] = None
    total_value: Decimal
    currency: str
    notes_internal: Optional[str] = None
    billing_provider: str
    billing_customer_id: Optional[str] = None
    billing_invoices: List[str] = []
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class ContractDetailResponse(ContractResponse):
    """Schema for detailed contract response with notes"""
    notes: List[ContractNoteResponse] = []


class ContractListResponse(BaseModel):
    """Schema for paginated contract list"""
    items: List[ContractResponse]
    pagination: dict


class ContractInvoiceResponse(BaseModel):
    """Schema for contract invoice response (placeholder for billing integration)"""
    contract_id: UUID
    contract_number: str
    invoices: List[dict] = Field(default_factory=list, description="List of invoices")
    provider: str = Field(default="mock", description="Billing provider")
    message: str = Field(default="Invoice data is not yet integrated with billing provider")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
