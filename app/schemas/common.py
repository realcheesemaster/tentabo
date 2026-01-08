"""
Common Pydantic schemas used across the application
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal


class PaginationInfo(BaseModel):
    """Pagination metadata for list responses"""
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel):
    """Base paginated response"""
    pagination: PaginationInfo

    @classmethod
    def create(cls, items: List, page: int, page_size: int, total_items: int):
        """
        Create paginated response with calculated metadata

        Args:
            items: List of items for current page
            page: Current page number
            page_size: Items per page
            total_items: Total number of items

        Returns:
            PaginatedResponse instance
        """
        import math
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

        return cls(items=items, pagination=pagination)


class MoneyAmount(BaseModel):
    """Money amount with currency"""
    amount: Decimal = Field(..., description="Amount")
    currency: str = Field(default="EUR", description="ISO 4217 currency code")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[dict] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel):
    """Standard success response for operations without return data"""
    success: bool = Field(default=True, description="Operation success")
    message: str = Field(..., description="Success message")
