"""
Order Service

Handles order creation, updates, and state transitions
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Union, Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.auth import User, AdminUser, UserRole
from app.models.billing import Order, OrderItem, OrderStatus
from app.models.core import Product, Duration
from app.models.partner import Partner, Distributor
from app.services.pricing_service import PricingService

logger = logging.getLogger(__name__)


class OrderService:
    """
    Service for managing orders

    Handles:
    - Order creation with validation
    - Order status transitions with state machine
    - Order item calculations
    """

    # Valid state transitions
    STATE_TRANSITIONS = {
        OrderStatus.CREATED: [OrderStatus.SENT, OrderStatus.CANCELLED],
        OrderStatus.SENT: [OrderStatus.IN_FULFILLMENT, OrderStatus.CANCELLED],
        OrderStatus.IN_FULFILLMENT: [OrderStatus.FULFILLED, OrderStatus.CANCELLED],
        OrderStatus.FULFILLED: [],  # Terminal state
        OrderStatus.CANCELLED: [],  # Terminal state
    }

    @staticmethod
    def _generate_order_number() -> str:
        """
        Generate unique order number

        Format: ORD-YYYYMMDD-XXXXXX
        """
        from uuid import uuid4
        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = uuid4().hex[:6].upper()
        return f"ORD-{date_part}-{random_part}"

    @staticmethod
    def create_order(
        items: List[Dict[str, Any]],
        current_user: Union[User, AdminUser],
        partner_id: Optional[UUID],
        distributor_id: Optional[UUID],
        lead_id: Optional[UUID],
        notes_internal: Optional[str],
        db: Session
    ) -> Order:
        """
        Create a new order with items

        Args:
            items: List of dicts with product_id, quantity, duration_id
            current_user: User creating the order
            partner_id: Optional partner ID
            distributor_id: Optional distributor ID
            lead_id: Optional lead ID
            notes_internal: Optional internal notes
            db: Database session

        Returns:
            Created Order object

        Raises:
            HTTPException: If validation fails
        """
        # Validate at least one item
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order must have at least one item"
            )

        # Validate partner and distributor if provided
        if partner_id:
            partner = db.query(Partner).filter(Partner.id == partner_id).first()
            if not partner:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Partner {partner_id} not found"
                )
            if not partner.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Partner {partner.name} is not active"
                )

        if distributor_id:
            distributor = db.query(Distributor).filter(Distributor.id == distributor_id).first()
            if not distributor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Distributor {distributor_id} not found"
                )
            if not distributor.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Distributor {distributor.name} is not active"
                )

        # Calculate order totals
        totals = PricingService.calculate_order_totals(items, db)

        # Create order
        order = Order(
            order_number=OrderService._generate_order_number(),
            status=OrderStatus.CREATED,
            created_by=current_user.id,
            partner_id=partner_id,
            distributor_id=distributor_id,
            lead_id=lead_id,
            subtotal=totals['subtotal'],
            discount_amount=totals['discount_amount'],
            tax_amount=totals['tax_amount'],
            total_amount=totals['total_amount'],
            notes_internal=notes_internal,
            billing_provider="mock",  # Will be set when quote is generated
            crm_provider="manual",  # Will be updated if synced from CRM
        )

        db.add(order)
        db.flush()  # Get order ID

        # Create order items
        for item_data in items:
            # Calculate price for this item
            price_calc = PricingService.calculate_progressive_price(
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                duration_id=item_data.get('duration_id'),
                db=db
            )

            # Get product and duration for snapshot
            product = db.query(Product).filter(Product.id == item_data['product_id']).first()
            duration = db.query(Duration).filter(Duration.id == item_data['duration_id']).first()

            if not duration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Duration {item_data['duration_id']} not found"
                )

            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data['product_id'],
                duration_id=item_data['duration_id'],
                quantity=item_data['quantity'],
                unit_price=price_calc['unit_price'],
                discount_percentage=price_calc['discount_percentage'],
                subtotal=price_calc['subtotal'],
                discount_amount=price_calc['discount_amount'],
                total=price_calc['total'],
                # Snapshot product/duration data at time of order
                product_name=product.name,
                product_type=product.type,
                product_unit=product.unit,
                duration_months=duration.months,
            )

            db.add(order_item)

        db.commit()
        db.refresh(order)

        logger.info(
            f"Created order {order.order_number} by user {current_user.id}: "
            f"{len(items)} items, total={order.total_amount}"
        )

        return order

    @staticmethod
    def can_transition(current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """
        Check if status transition is valid

        Args:
            current_status: Current order status
            new_status: Desired new status

        Returns:
            True if transition is valid, False otherwise
        """
        allowed_transitions = OrderService.STATE_TRANSITIONS.get(current_status, [])
        return new_status in allowed_transitions

    @staticmethod
    def transition_status(
        order: Order,
        new_status: OrderStatus,
        current_user: Union[User, AdminUser],
        reason: Optional[str],
        db: Session
    ) -> Order:
        """
        Transition order to a new status

        Args:
            order: Order to update
            new_status: New status
            current_user: User performing the transition
            reason: Optional reason for transition
            db: Database session

        Returns:
            Updated Order object

        Raises:
            HTTPException: If transition is invalid
        """
        # Parse current status
        current_status = OrderStatus(order.status) if isinstance(order.status, str) else order.status

        # Check if transition is valid
        if not OrderService.can_transition(current_status, new_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from {current_status.value} to {new_status.value}"
            )

        # Check permissions for specific transitions
        if isinstance(current_user, User):
            # Only admins and fulfillers can mark as fulfilled
            if new_status == OrderStatus.FULFILLED:
                if current_user.role not in [UserRole.ADMIN, UserRole.FULFILLER]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only admins and fulfillers can mark orders as fulfilled"
                    )

            # Only admins can cancel orders
            if new_status == OrderStatus.CANCELLED:
                if current_user.role != UserRole.ADMIN:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only admins can cancel orders"
                    )

        # Perform transition
        old_status = order.status
        order.status = new_status

        # Update timestamps
        now = datetime.utcnow()
        if new_status == OrderStatus.SENT:
            order.sent_at = now
        elif new_status == OrderStatus.FULFILLED:
            order.fulfilled_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now

        # Add note about status change
        if reason:
            from app.models.system import Note
            note = Note(
                order_id=order.id,
                content=f"Status changed from {old_status.value} to {new_status.value}\nReason: {reason}",
                is_internal=True,
                created_by=current_user.id,
            )
            db.add(note)

        db.commit()
        db.refresh(order)

        logger.info(
            f"Order {order.order_number} status changed: "
            f"{old_status.value} -> {new_status.value} by user {current_user.id}"
        )

        return order

    @staticmethod
    def can_activate_order(order: Order) -> tuple[bool, Optional[str]]:
        """
        Check if an order can be activated into a contract

        Args:
            order: Order to check

        Returns:
            Tuple of (can_activate, reason_if_not)
        """
        status = OrderStatus(order.status) if isinstance(order.status, str) else order.status

        # Order must be fulfilled
        if status != OrderStatus.FULFILLED:
            return False, f"Order must be fulfilled (current status: {status.value})"

        # Order must not already have a contract
        if order.contract:
            return False, "Order already has an active contract"

        # Order must have a partner
        if not order.partner_id:
            return False, "Order must have a partner to create a contract"

        return True, None
