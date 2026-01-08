"""
Contract Service

Handles contract activation and management
"""

import logging
from datetime import datetime
from typing import Union, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.auth import User, AdminUser, UserRole
from app.models.billing import Contract, ContractStatus, Order, OrderStatus
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class ContractService:
    """
    Service for managing contracts

    Handles:
    - Contract activation from fulfilled orders
    - Contract status transitions
    - Contract validations
    """

    # Valid state transitions
    STATE_TRANSITIONS = {
        ContractStatus.ACTIVE: [
            ContractStatus.UPGRADED,
            ContractStatus.DOWNGRADED,
            ContractStatus.EXPIRED,
            ContractStatus.CANCELLED,
        ],
        ContractStatus.UPGRADED: [ContractStatus.CANCELLED],
        ContractStatus.DOWNGRADED: [ContractStatus.CANCELLED],
        ContractStatus.EXPIRED: [ContractStatus.CANCELLED],
        ContractStatus.CANCELLED: [],  # Terminal state
        ContractStatus.LOST: [],  # Terminal state
    }

    @staticmethod
    def _generate_contract_number() -> str:
        """
        Generate unique contract number

        Format: CNT-YYYYMMDD-XXXXXX
        """
        from uuid import uuid4
        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = uuid4().hex[:6].upper()
        return f"CNT-{date_part}-{random_part}"

    @staticmethod
    def activate_order(
        order_id: UUID,
        current_user: Union[User, AdminUser],
        activation_date: Optional[datetime],
        expiration_date: Optional[datetime],
        notes_internal: Optional[str],
        db: Session
    ) -> Contract:
        """
        Activate a fulfilled order into a contract

        Args:
            order_id: Order UUID to activate
            current_user: User performing activation
            activation_date: Optional activation date (defaults to now)
            expiration_date: Optional expiration date
            notes_internal: Optional internal notes
            db: Database session

        Returns:
            Created Contract object

        Raises:
            HTTPException: If validation fails or order cannot be activated
        """
        # Check permissions - only admins and fulfillers can activate contracts
        if isinstance(current_user, User):
            if current_user.role not in [UserRole.ADMIN, UserRole.FULFILLER]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins and fulfillers can activate contracts"
                )

        # Get order with items
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )

        # Check if order can be activated
        can_activate, reason = OrderService.can_activate_order(order)
        if not can_activate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot activate order: {reason}"
            )

        # Set activation date
        if activation_date is None:
            activation_date = datetime.utcnow()

        # Validate expiration date
        if expiration_date and expiration_date <= activation_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expiration date must be after activation date"
            )

        # Create contract
        contract = Contract(
            contract_number=ContractService._generate_contract_number(),
            order_id=order.id,
            status=ContractStatus.ACTIVE,
            user_id=current_user.id,
            partner_id=order.partner_id,
            distributor_id=order.distributor_id,
            activation_date=activation_date,
            expiration_date=expiration_date,
            total_value=order.total_amount,
            currency="EUR",
            notes_internal=notes_internal,
            billing_provider="mock",  # Will be set when integrated with real billing
        )

        db.add(contract)
        db.commit()
        db.refresh(contract)

        logger.info(
            f"Activated contract {contract.contract_number} from order "
            f"{order.order_number} by user {current_user.id}"
        )

        return contract

    @staticmethod
    def can_transition(current_status: ContractStatus, new_status: ContractStatus) -> bool:
        """
        Check if status transition is valid

        Args:
            current_status: Current contract status
            new_status: Desired new status

        Returns:
            True if transition is valid, False otherwise
        """
        allowed_transitions = ContractService.STATE_TRANSITIONS.get(current_status, [])
        return new_status in allowed_transitions

    @staticmethod
    def transition_status(
        contract: Contract,
        new_status: ContractStatus,
        current_user: Union[User, AdminUser],
        reason: Optional[str],
        db: Session
    ) -> Contract:
        """
        Transition contract to a new status

        Args:
            contract: Contract to update
            new_status: New status
            current_user: User performing the transition
            reason: Optional reason for transition
            db: Database session

        Returns:
            Updated Contract object

        Raises:
            HTTPException: If transition is invalid
        """
        # Parse current status
        current_status = ContractStatus(contract.status) if isinstance(contract.status, str) else contract.status

        # Check if transition is valid
        if not ContractService.can_transition(current_status, new_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from {current_status.value} to {new_status.value}"
            )

        # Check permissions - only admins can transition contracts
        if isinstance(current_user, User):
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can change contract status"
                )

        # Perform transition
        old_status = contract.status
        contract.status = new_status

        # Update timestamps
        now = datetime.utcnow()
        if new_status == ContractStatus.CANCELLED:
            contract.cancelled_at = now

        # Add note about status change
        if reason:
            from app.models.system import Note
            note = Note(
                contract_id=contract.id,
                content=f"Status changed from {old_status.value} to {new_status.value}\nReason: {reason}",
                is_internal=True,
                created_by=current_user.id,
            )
            db.add(note)

        db.commit()
        db.refresh(contract)

        logger.info(
            f"Contract {contract.contract_number} status changed: "
            f"{old_status.value} -> {new_status.value} by user {current_user.id}"
        )

        return contract

    @staticmethod
    def can_renew_contract(contract: Contract) -> tuple[bool, Optional[str]]:
        """
        Check if a contract can be renewed

        Args:
            contract: Contract to check

        Returns:
            Tuple of (can_renew, reason_if_not)
        """
        status = ContractStatus(contract.status) if isinstance(contract.status, str) else contract.status

        # Can only renew active or expired contracts
        if status not in [ContractStatus.ACTIVE, ContractStatus.EXPIRED]:
            return False, f"Can only renew active or expired contracts (current status: {status.value})"

        # Check if contract has expiration date
        if not contract.expiration_date:
            return False, "Contract has no expiration date set"

        return True, None
