"""
ProductType Pydantic schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class ProductTypeBase(BaseModel):
    """Base product type schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Product type name")
    description: Optional[str] = Field(None, description="Product type description")
    is_active: bool = Field(default=True, description="Whether product type is active")


class ProductTypeCreate(ProductTypeBase):
    """Schema for creating a product type"""
    pass


class ProductTypeUpdate(BaseModel):
    """Schema for updating a product type"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductTypeResponse(ProductTypeBase):
    """Schema for product type response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductTypeListResponse(BaseModel):
    """Schema for paginated product type list"""
    items: List[ProductTypeResponse]
    pagination: dict
