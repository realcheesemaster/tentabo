"""
Order API endpoints

Provides order management with state machine and multi-tenant filtering
"""

import logging
from typing import Union
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser
from app.models.billing import Order, OrderStatus
from app.models.system import Note
from app.auth.dependencies import get_current_user
from app.api.dependencies import PaginationParams, MultiTenantFilter, get_multi_tenant_filter
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderResponse, OrderDetailResponse, OrderListResponse,
    OrderStatusUpdate, OrderNoteCreate, OrderNoteResponse, OrderQuoteResponse,
)
from app.schemas.common import PaginationInfo
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/orders", response_model=OrderListResponse, tags=["Orders"])
async def list_orders(
    pagination: PaginationParams = Depends(),
    status_filter: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """
    List orders with multi-tenant filtering

    - Admins/Fulfillers see all orders
    - Distributors see their orders
    - Partners see their orders
    """
    query = db.query(Order)
    query = mt_filter.filter_orders_query(query, current_user, Order)

    if status_filter:
        query = query.filter(Order.status == status_filter)

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(pagination.skip).limit(pagination.limit).all()

    import math
    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1
    pagination_info = PaginationInfo(
        page=pagination.page, page_size=pagination.page_size,
        total_items=total, total_pages=total_pages,
        has_next=pagination.page < total_pages, has_prev=pagination.page > 1
    )

    return OrderListResponse(
        items=[OrderResponse.from_orm(o) for o in orders],
        pagination=pagination_info.dict()
    )


@router.get("/orders/{order_id}", response_model=OrderDetailResponse, tags=["Orders"])
async def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """Get order details with items and notes"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Check access (simplified - use mt_filter for production)
    query = db.query(Order).filter(Order.id == order_id)
    query = mt_filter.filter_orders_query(query, current_user, Order)
    if not query.first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return OrderDetailResponse.from_orm(order)


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Create a new order from cart/items

    Validates items, calculates totals, and creates order with status 'created'
    """
    try:
        # Prepare items data
        items_data = [
            {
                'product_id': item.product_id,
                'quantity': item.quantity,
                'duration_id': item.duration_id,
            }
            for item in order_data.items
        ]

        order = OrderService.create_order(
            items=items_data,
            current_user=current_user,
            partner_id=order_data.partner_id,
            distributor_id=order_data.distributor_id,
            lead_id=order_data.lead_id,
            notes_internal=order_data.notes_internal,
            db=db,
        )

        return OrderResponse.from_orm(order)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating order"
        )


@router.put("/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
async def update_order(
    order_id: UUID,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Update order notes (limited updates allowed)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    update_data = order_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    db.commit()
    db.refresh(order)

    logger.info(f"Updated order {order.order_number} by user {current_user.id}")
    return OrderResponse.from_orm(order)


@router.put("/orders/{order_id}/status", response_model=OrderResponse, tags=["Orders"])
async def update_order_status(
    order_id: UUID,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Update order status with validation

    Implements state machine transitions:
    - created -> sent | cancelled
    - sent -> in_fulfillment | cancelled
    - in_fulfillment -> fulfilled | cancelled
    - fulfilled/cancelled: terminal states
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    new_status = OrderStatus(status_data.status)

    try:
        order = OrderService.transition_status(
            order=order,
            new_status=new_status,
            current_user=current_user,
            reason=status_data.reason,
            db=db,
        )

        return OrderResponse.from_orm(order)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating order status"
        )


@router.post("/orders/{order_id}/notes", response_model=OrderNoteResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
async def add_order_note(
    order_id: UUID,
    note_data: OrderNoteCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Add a note to an order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    note = Note(
        order_id=order_id,
        content=note_data.content,
        is_internal=note_data.is_internal,
        is_pinned=note_data.is_pinned,
        created_by=current_user.id,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info(f"Added note to order {order.order_number} by user {current_user.id}")
    return OrderNoteResponse.from_orm(note)


@router.get("/orders/{order_id}/quote", response_model=OrderQuoteResponse, tags=["Orders"])
async def generate_order_quote(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Generate quote for an order (placeholder for Pennylane integration)

    Currently returns mock data. Will be integrated with actual billing provider.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Mock quote response
    # TODO: Integrate with actual billing provider (Pennylane)
    return OrderQuoteResponse(
        order_id=order.id,
        order_number=order.order_number,
        quote_id=None,
        quote_url=None,
        quote_pdf_url=None,
        provider="mock",
        generated_at=datetime.utcnow(),
        message="Quote generation will be integrated with Pennylane billing provider",
    )
