"""
Order-related Pydantic schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from uuid import UUID


class OrderItemBase(BaseModel):
    """Base order item schema"""
    product_id: UUID = Field(..., description="Product ID")
    duration_id: UUID = Field(..., description="Duration ID")
    quantity: int = Field(..., gt=0, description="Quantity")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class OrderItemCreate(OrderItemBase):
    """Schema for creating an order item"""
    pass


class OrderItemResponse(BaseModel):
    """Schema for order item response"""
    id: UUID
    order_id: UUID
    product_id: UUID
    duration_id: UUID
    quantity: int
    unit_price: Decimal
    discount_percentage: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    product_name: str
    product_type: str
    product_unit: str
    duration_months: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class OrderNoteBase(BaseModel):
    """Base order note schema"""
    content: str = Field(..., min_length=1, description="Note content")
    is_internal: bool = Field(default=False, description="Internal note (not visible to customer)")
    is_pinned: bool = Field(default=False, description="Pin note to top")


class OrderNoteCreate(OrderNoteBase):
    """Schema for creating an order note"""
    pass


class OrderNoteResponse(OrderNoteBase):
    """Schema for order note response"""
    id: UUID
    order_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    """Base order schema"""
    partner_id: Optional[UUID] = Field(None, description="Partner ID")
    distributor_id: Optional[UUID] = Field(None, description="Distributor ID")
    lead_id: Optional[UUID] = Field(None, description="Originating lead ID")
    notes_internal: Optional[str] = Field(None, description="Internal notes")


class OrderCreate(OrderBase):
    """Schema for creating an order"""
    items: List[OrderItemCreate] = Field(..., min_items=1, description="Order items")

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v


class OrderUpdate(BaseModel):
    """Schema for updating an order"""
    notes_internal: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    status: str = Field(..., description="New status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['created', 'cancelled', 'sent', 'in_fulfillment', 'fulfilled']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: UUID
    order_number: str
    status: str
    created_by: UUID
    partner_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes_internal: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    billing_provider: Optional[str] = None
    billing_quote_id: Optional[str] = None
    crm_provider: Optional[str] = None
    crm_deal_id: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class OrderDetailResponse(OrderResponse):
    """Schema for detailed order response with items and notes"""
    items: List[OrderItemResponse] = []
    notes: List[OrderNoteResponse] = []


class OrderListResponse(BaseModel):
    """Schema for paginated order list"""
    items: List[OrderResponse]
    pagination: dict


class OrderQuoteResponse(BaseModel):
    """Schema for order quote response (placeholder for billing integration)"""
    order_id: UUID
    order_number: str
    quote_id: Optional[str] = None
    quote_url: Optional[str] = None
    quote_pdf_url: Optional[str] = None
    provider: str = Field(default="mock", description="Billing provider")
    generated_at: datetime
    message: str = Field(default="Quote generation is not yet integrated with billing provider")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
