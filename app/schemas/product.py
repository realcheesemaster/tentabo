"""
Product-related Pydantic schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from uuid import UUID


class PriceTierBase(BaseModel):
    """Base price tier schema"""
    min_quantity: int = Field(..., ge=0, description="Minimum quantity for this tier")
    max_quantity: Optional[int] = Field(None, ge=1, description="Maximum quantity (null for unlimited)")
    price_per_unit: Decimal = Field(..., gt=0, description="Price per unit in EUR")
    period: str = Field(default="month", description="Pricing period (month or year)")

    @validator('period')
    def validate_period(cls, v):
        if v not in ['month', 'year']:
            raise ValueError("Period must be 'month' or 'year'")
        return v

    @validator('max_quantity')
    def validate_max_quantity(cls, v, values):
        if v is not None and 'min_quantity' in values:
            if v <= values['min_quantity']:
                raise ValueError("max_quantity must be greater than min_quantity")
        return v

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class PriceTierCreate(PriceTierBase):
    """Schema for creating a price tier"""
    pass


class PriceTierResponse(PriceTierBase):
    """Schema for price tier response"""
    id: UUID
    product_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    """Base product schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    type_id: UUID = Field(..., description="Product type ID (FK to product_types)")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement (TB, GB, user, seat, etc.)")
    description: Optional[str] = Field(None, description="Product description")
    is_active: bool = Field(default=True, description="Whether product is active")


class ProductCreate(ProductBase):
    """Schema for creating a product"""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type_id: Optional[UUID] = Field(None, description="Product type ID")
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema for product response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    price_tiers: List[PriceTierResponse] = []

    class Config:
        from_attributes = True

    @validator('is_active', pre=True)
    def convert_is_active(cls, v):
        """Convert string 'true'/'false' to boolean"""
        if isinstance(v, str):
            return v.lower() == 'true'
        return v


class ProductListResponse(BaseModel):
    """Schema for paginated product list"""
    items: List[ProductResponse]
    pagination: dict


class DurationBase(BaseModel):
    """Base duration schema"""
    months: int = Field(..., gt=0, description="Duration in months")
    discount_percentage: Decimal = Field(default=0, ge=0, le=100, description="Discount percentage")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class DurationCreate(DurationBase):
    """Schema for creating a duration"""
    pass


class DurationResponse(DurationBase):
    """Schema for duration response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceCalculationRequest(BaseModel):
    """Request to calculate price for a product"""
    quantity: int = Field(..., gt=0, description="Quantity")
    duration_id: Optional[UUID] = Field(None, description="Duration ID for discount")


class PriceCalculationResponse(BaseModel):
    """Response with calculated price breakdown"""
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    duration_months: Optional[int] = None
    discount_percentage: Decimal = Field(default=Decimal('0'))
    discount_amount: Decimal = Field(default=Decimal('0'))
    total: Decimal
    currency: str = Field(default="EUR")
    breakdown: dict = Field(default_factory=dict, description="Detailed price breakdown")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
