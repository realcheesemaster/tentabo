"""
Product API endpoints

Provides CRUD operations for products and price tiers:
- GET /products - List products with pagination
- GET /products/{id} - Get product details
- POST /products - Create product (admin only)
- PUT /products/{id} - Update product (admin only)
- DELETE /products/{id} - Delete product (admin only)
- POST /products/{id}/price-tiers - Add price tiers
- GET /products/{id}/calculate-price - Calculate price for quantity
"""

import logging
from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser
from app.models.core import Product, PriceTier, Duration
from app.auth.dependencies import get_current_user, require_admin
from app.api.dependencies import PaginationParams
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    PriceTierCreate,
    PriceTierResponse,
    PriceCalculationRequest,
    PriceCalculationResponse,
    DurationResponse,
)
from app.schemas.common import SuccessResponse, PaginationInfo
from app.services.pricing_service import PricingService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/products", response_model=ProductListResponse, tags=["Products"])
async def list_products(
    pagination: PaginationParams = Depends(),
    is_active: bool = Query(True, description="Filter by active status"),
    product_type: str = Query(None, description="Filter by product type"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    List products with pagination

    Returns all active products by default. Authenticated users can access.
    """
    # Build query
    query = db.query(Product)

    # Apply filters
    if is_active is not None:
        # Handle string 'true'/'false' from database
        active_str = 'true' if is_active else 'false'
        query = query.filter(Product.is_active == active_str)

    if product_type:
        query = query.filter(Product.type == product_type)

    # Count total
    total = query.count()

    # Apply pagination
    products = query.offset(pagination.skip).limit(pagination.limit).all()

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

    return ProductListResponse(
        items=[ProductResponse.from_orm(p) for p in products],
        pagination=pagination_info.dict(),
    )


@router.get("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
async def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Get product details with price tiers

    Returns detailed product information including all price tiers.
    """
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    return ProductResponse.from_orm(product)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["Products"])
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Create a new product (admin only)

    Creates a product without price tiers. Use POST /products/{id}/price-tiers
    to add price tiers after creation.
    """
    # Check if product with same name exists
    existing = db.query(Product).filter(Product.name == product_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with name '{product_data.name}' already exists",
        )

    # Convert is_active boolean to string for database
    is_active_str = 'true' if product_data.is_active else 'false'

    # Create product
    product = Product(
        name=product_data.name,
        type=product_data.type,
        unit=product_data.unit,
        description=product_data.description,
        is_active=is_active_str,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    logger.info(f"Created product {product.name} by user {current_user.id}")

    return ProductResponse.from_orm(product)


@router.put("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Update a product (admin only)

    Updates product fields. Omitted fields are not changed.
    """
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    # Update fields
    update_data = product_data.dict(exclude_unset=True)

    # Convert is_active boolean to string if present
    if 'is_active' in update_data:
        update_data['is_active'] = 'true' if update_data['is_active'] else 'false'

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    logger.info(f"Updated product {product.name} by user {current_user.id}")

    return ProductResponse.from_orm(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
async def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Delete a product (admin only)

    Deletes product and all associated price tiers (cascade).
    """
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    db.delete(product)
    db.commit()

    logger.info(f"Deleted product {product.name} by user {current_user.id}")

    return None


@router.post("/products/{product_id}/price-tiers", response_model=PriceTierResponse, status_code=status.HTTP_201_CREATED, tags=["Products"])
async def add_price_tier(
    product_id: UUID,
    tier_data: PriceTierCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Add a price tier to a product (admin only)

    Creates a new price tier for progressive pricing.
    """
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    # Create price tier
    tier = PriceTier(
        product_id=product_id,
        min_quantity=tier_data.min_quantity,
        max_quantity=tier_data.max_quantity,
        price_per_unit=tier_data.price_per_unit,
        period=tier_data.period,
    )

    db.add(tier)
    db.commit()
    db.refresh(tier)

    logger.info(f"Added price tier to product {product.name} by user {current_user.id}")

    return PriceTierResponse.from_orm(tier)


@router.post("/products/{product_id}/calculate-price", response_model=PriceCalculationResponse, tags=["Products"])
async def calculate_price(
    product_id: UUID,
    request: PriceCalculationRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Calculate price for a product with quantity and duration

    Returns detailed price breakdown including tier pricing and duration discounts.
    """
    try:
        result = PricingService.calculate_progressive_price(
            product_id=product_id,
            quantity=request.quantity,
            duration_id=request.duration_id,
            db=db,
        )

        return PriceCalculationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating price",
        )


@router.get("/durations", response_model=List[DurationResponse], tags=["Products"])
async def list_durations(
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    List all available subscription durations

    Returns all duration options with their discount percentages.
    """
    durations = db.query(Duration).order_by(Duration.months).all()
    return [DurationResponse.from_orm(d) for d in durations]
