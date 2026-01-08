"""
Contract API endpoints

Provides contract management with activation from fulfilled orders
"""

import logging
from typing import Union
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser
from app.models.billing import Contract, ContractStatus
from app.models.system import Note
from app.auth.dependencies import get_current_user
from app.api.dependencies import PaginationParams, MultiTenantFilter, get_multi_tenant_filter
from app.schemas.contract import (
    ContractResponse, ContractDetailResponse, ContractListResponse,
    ContractActivateRequest, ContractStatusUpdate,
    ContractNoteCreate, ContractNoteResponse, ContractInvoiceResponse,
)
from app.schemas.common import PaginationInfo
from app.services.contract_service import ContractService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/contracts", response_model=ContractListResponse, tags=["Contracts"])
async def list_contracts(
    pagination: PaginationParams = Depends(),
    status_filter: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """
    List contracts with multi-tenant filtering

    - Admins/Fulfillers see all contracts
    - Distributors see their contracts
    - Partners see their contracts
    """
    query = db.query(Contract)
    query = mt_filter.filter_contracts_query(query, current_user, Contract)

    if status_filter:
        query = query.filter(Contract.status == status_filter)

    total = query.count()
    contracts = query.order_by(Contract.created_at.desc()).offset(pagination.skip).limit(pagination.limit).all()

    import math
    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1
    pagination_info = PaginationInfo(
        page=pagination.page, page_size=pagination.page_size,
        total_items=total, total_pages=total_pages,
        has_next=pagination.page < total_pages, has_prev=pagination.page > 1
    )

    return ContractListResponse(
        items=[ContractResponse.from_orm(c) for c in contracts],
        pagination=pagination_info.dict()
    )


@router.get("/contracts/{contract_id}", response_model=ContractDetailResponse, tags=["Contracts"])
async def get_contract(
    contract_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """Get contract details with notes"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    # Check access
    query = db.query(Contract).filter(Contract.id == contract_id)
    query = mt_filter.filter_contracts_query(query, current_user, Contract)
    if not query.first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return ContractDetailResponse.from_orm(contract)


@router.post("/orders/{order_id}/activate", response_model=ContractResponse, status_code=status.HTTP_201_CREATED, tags=["Contracts"])
async def activate_order_to_contract(
    order_id: UUID,
    activation_data: ContractActivateRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Activate a fulfilled order into a contract

    Only admins and fulfillers can activate contracts.
    Order must be in 'fulfilled' status and not already have a contract.
    """
    try:
        contract = ContractService.activate_order(
            order_id=order_id,
            current_user=current_user,
            activation_date=activation_data.activation_date,
            expiration_date=activation_data.expiration_date,
            notes_internal=activation_data.notes_internal,
            db=db,
        )

        return ContractResponse.from_orm(contract)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating contract: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error activating contract"
        )


@router.put("/contracts/{contract_id}/status", response_model=ContractResponse, tags=["Contracts"])
async def update_contract_status(
    contract_id: UUID,
    status_data: ContractStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Update contract status

    Only admins can change contract status.
    Validates state transitions according to business rules.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    new_status = ContractStatus(status_data.status)

    try:
        contract = ContractService.transition_status(
            contract=contract,
            new_status=new_status,
            current_user=current_user,
            reason=status_data.reason,
            db=db,
        )

        return ContractResponse.from_orm(contract)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating contract status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating contract status"
        )


@router.post("/contracts/{contract_id}/notes", response_model=ContractNoteResponse, status_code=status.HTTP_201_CREATED, tags=["Contracts"])
async def add_contract_note(
    contract_id: UUID,
    note_data: ContractNoteCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Add a note to a contract"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    note = Note(
        contract_id=contract_id,
        content=note_data.content,
        is_internal=note_data.is_internal,
        is_pinned=note_data.is_pinned,
        created_by=current_user.id,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info(f"Added note to contract {contract.contract_number} by user {current_user.id}")
    return ContractNoteResponse.from_orm(note)


@router.get("/contracts/{contract_id}/invoices", response_model=ContractInvoiceResponse, tags=["Contracts"])
async def list_contract_invoices(
    contract_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    List invoices for a contract (placeholder for Pennylane integration)

    Currently returns mock data. Will be integrated with actual billing provider.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    # Mock invoice response
    # TODO: Integrate with actual billing provider (Pennylane)
    mock_invoices = []
    if contract.billing_invoices:
        for invoice_id in contract.billing_invoices:
            mock_invoices.append({
                "invoice_id": invoice_id,
                "invoice_number": f"INV-{invoice_id[:8].upper()}",
                "status": "paid",
                "amount": float(contract.total_value),
                "currency": contract.currency,
                "created_at": contract.activation_date.isoformat() if contract.activation_date else None,
            })

    return ContractInvoiceResponse(
        contract_id=contract.id,
        contract_number=contract.contract_number,
        invoices=mock_invoices,
        provider="mock",
        message="Invoice data will be integrated with Pennylane billing provider",
    )
