"""
ProductType API endpoints

Provides CRUD operations for product types:
- GET /product-types - List product types (public for dropdown)
- POST /product-types - Create product type (admin only)
- PUT /product-types/{id} - Update product type (admin only)
- DELETE /product-types/{id} - Delete product type (admin only)
"""

import logging
from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser
from app.models.product_type import ProductType
from app.auth.dependencies import get_current_user, require_admin
from app.api.dependencies import PaginationParams
from app.schemas.product_type import (
    ProductTypeCreate,
    ProductTypeUpdate,
    ProductTypeResponse,
    ProductTypeListResponse,
)
from app.schemas.common import PaginationInfo

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== PRODUCT TYPE ENDPOINTS ====================


@router.get("/product-types", response_model=ProductTypeListResponse, tags=["ProductTypes"])
async def list_product_types(
    pagination: PaginationParams = Depends(),
    is_active: bool = Query(None, description="Filter by active status"),
    search: str = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
):
    """
    List product types

    No authentication required - needed for product type dropdown.
    Returns only active types by default.
    """
    # Build query
    query = db.query(ProductType)

    # Apply filters
    if is_active is not None:
        query = query.filter(ProductType.is_active == is_active)
    elif is_active is None:
        # Default to active only when no filter is specified
        query = query.filter(ProductType.is_active == True)

    if search:
        query = query.filter(ProductType.name.ilike(f"%{search}%"))

    # Order by name
    query = query.order_by(ProductType.name)

    # Count total
    total = query.count()

    # Apply pagination
    product_types = query.offset(pagination.skip).limit(pagination.limit).all()

    # Calculate pagination info
    import math
    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1

    pagination_info = PaginationInfo(
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
        total_pages=total_pages,
        has_next=pagination.page < total_pages,
        has_prev=pagination.page > 1,
    )

    return ProductTypeListResponse(
        items=[ProductTypeResponse.from_orm(pt) for pt in product_types],
        pagination=pagination_info.dict(),
    )


@router.get("/product-types/{product_type_id}", response_model=ProductTypeResponse, tags=["ProductTypes"])
async def get_product_type(
    product_type_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Get product type details (admin only)
    """
    product_type = db.query(ProductType).filter(ProductType.id == product_type_id).first()

    if not product_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product type {product_type_id} not found",
        )

    return ProductTypeResponse.from_orm(product_type)


@router.post("/product-types", response_model=ProductTypeResponse, status_code=status.HTTP_201_CREATED, tags=["ProductTypes"])
async def create_product_type(
    product_type_data: ProductTypeCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Create a new product type (admin only)
    """
    # Check if product type with same name exists
    existing = db.query(ProductType).filter(
        ProductType.name == product_type_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product type with name '{product_type_data.name}' already exists",
        )

    # Create product type
    product_type = ProductType(**product_type_data.dict())

    db.add(product_type)
    db.commit()
    db.refresh(product_type)

    logger.info(f"Created product type {product_type.name} by user {current_user.id}")

    return ProductTypeResponse.from_orm(product_type)


@router.put("/product-types/{product_type_id}", response_model=ProductTypeResponse, tags=["ProductTypes"])
async def update_product_type(
    product_type_id: UUID,
    product_type_data: ProductTypeUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Update a product type (admin only)
    """
    product_type = db.query(ProductType).filter(ProductType.id == product_type_id).first()

    if not product_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product type {product_type_id} not found",
        )

    # Check for name conflict if name is being updated
    if product_type_data.name and product_type_data.name != product_type.name:
        existing = db.query(ProductType).filter(
            ProductType.name == product_type_data.name
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product type with name '{product_type_data.name}' already exists",
            )

    # Update fields
    update_data = product_type_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product_type, field, value)

    db.commit()
    db.refresh(product_type)

    logger.info(f"Updated product type {product_type.name} by user {current_user.id}")

    return ProductTypeResponse.from_orm(product_type)


@router.delete("/product-types/{product_type_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["ProductTypes"])
async def delete_product_type(
    product_type_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Delete a product type (admin only)

    Note: This will fail if there are products using this type.
    """
    product_type = db.query(ProductType).filter(ProductType.id == product_type_id).first()

    if not product_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product type {product_type_id} not found",
        )

    # Check if any products are using this type
    # This will be enforced by the database foreign key constraint
    # but we can provide a better error message
    from app.models.core import Product
    products_using_type = db.query(Product).filter(Product.type_id == product_type_id).count()

    if products_using_type > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete product type '{product_type.name}' because {products_using_type} product(s) are using it. Please reassign those products first.",
        )

    db.delete(product_type)
    db.commit()

    logger.info(f"Deleted product type {product_type.name} by user {current_user.id}")

    return None
