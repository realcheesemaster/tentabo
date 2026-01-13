"""
Pennylane API endpoints

Provides connection management and data access for Pennylane integration.
All routes require admin authentication.
"""

import logging
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import PaginationParams
from app.auth.dependencies import require_admin
from app.database import get_db
from app.models.auth import AdminUser, User
from app.models.billing import Contract
from app.models.pennylane import (
    PennylaneConnection,
    PennylaneCustomer,
    PennylaneInvoice,
    PennylaneQuote,
    PennylaneSubscription,
)
from app.services.pennylane_service import (
    PennylaneAPIError,
    PennylaneAuthError,
    PennylaneClient,
    PennylaneSyncService,
    SyncResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pennylane", tags=["Pennylane"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class PennylaneConnectionCreate(BaseModel):
    """Schema for creating a Pennylane connection"""
    name: str = Field(..., min_length=1, max_length=255, description="Connection name")
    api_token: str = Field(..., min_length=1, description="Pennylane API bearer token")
    sync_customers: bool = Field(default=True, description="Sync customers")
    sync_invoices: bool = Field(default=True, description="Sync invoices")
    sync_quotes: bool = Field(default=True, description="Sync quotes")
    sync_subscriptions: bool = Field(default=True, description="Sync subscriptions")


class PennylaneConnectionUpdate(BaseModel):
    """Schema for updating a Pennylane connection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Connection name")
    api_token: Optional[str] = Field(None, min_length=1, description="Pennylane API bearer token")
    is_active: Optional[bool] = Field(None, description="Connection active status")
    sync_customers: Optional[bool] = Field(None, description="Sync customers")
    sync_invoices: Optional[bool] = Field(None, description="Sync invoices")
    sync_quotes: Optional[bool] = Field(None, description="Sync quotes")
    sync_subscriptions: Optional[bool] = Field(None, description="Sync subscriptions")


class PennylaneConnectionResponse(BaseModel):
    """Schema for Pennylane connection response (excludes api_token)"""
    id: UUID
    name: str
    company_name: Optional[str] = None
    is_active: bool
    masked_token: str = Field(..., description="Masked API token for display")
    sync_customers: bool
    sync_invoices: bool
    sync_quotes: bool
    sync_subscriptions: bool
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_connection(cls, connection: PennylaneConnection) -> "PennylaneConnectionResponse":
        """Create response from connection model, masking the token"""
        token = connection.api_token
        masked_token = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"

        return cls(
            id=connection.id,
            name=connection.name,
            company_name=connection.company_name,
            is_active=connection.is_active,
            masked_token=masked_token,
            sync_customers=connection.sync_customers,
            sync_invoices=connection.sync_invoices,
            sync_quotes=connection.sync_quotes,
            sync_subscriptions=connection.sync_subscriptions,
            last_sync_at=connection.last_sync_at,
            last_sync_status=connection.last_sync_status,
            last_sync_error=connection.last_sync_error,
            created_by_id=connection.created_by_id,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


class PennylaneConnectionListResponse(BaseModel):
    """Schema for paginated connection list"""
    items: List[PennylaneConnectionResponse]
    pagination: dict


class ConnectionTestResponse(BaseModel):
    """Schema for connection test response"""
    success: bool
    company_name: Optional[str] = None
    message: str
    details: Optional[dict] = None


class SyncEntityResult(BaseModel):
    """Schema for sync result of a single entity type"""
    entity_type: str
    total_fetched: int
    created: int
    updated: int
    success: bool
    errors: List[str] = []


class SyncResultResponse(BaseModel):
    """Schema for sync operation response"""
    connection_id: UUID
    connection_name: str
    sync_started_at: datetime
    sync_completed_at: datetime
    overall_success: bool
    results: dict[str, SyncEntityResult]
    message: str


# Customer Schemas
class PennylaneCustomerResponse(BaseModel):
    """Schema for Pennylane customer response"""
    id: UUID
    connection_id: UUID
    pennylane_id: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    vat_number: Optional[str] = None
    customer_type: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_postal_code: Optional[str] = None
    delivery_country_code: Optional[str] = None
    reg_no: Optional[str] = None
    recipient: Optional[str] = None
    reference: Optional[str] = None
    external_reference: Optional[str] = None
    billing_language: Optional[str] = None
    payment_conditions: Optional[str] = None
    notes: Optional[str] = None
    billing_iban: Optional[str] = None
    pennylane_created_at: Optional[datetime] = None
    pennylane_updated_at: Optional[datetime] = None
    synced_at: datetime

    class Config:
        from_attributes = True


class PennylaneCustomerDetailResponse(PennylaneCustomerResponse):
    """Schema for Pennylane customer detail response with raw data"""
    raw_data: dict = Field(default_factory=dict)


class PennylaneCustomerListResponse(BaseModel):
    """Schema for paginated customer list"""
    items: List[PennylaneCustomerResponse]
    pagination: dict


# Invoice Schemas
class PennylaneInvoiceResponse(BaseModel):
    """Schema for Pennylane invoice response"""
    id: UUID
    connection_id: UUID
    pennylane_id: str
    invoice_number: Optional[str] = None
    status: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "EUR"
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    pdf_url: Optional[str] = None
    synced_at: datetime
    contract_id: Optional[UUID] = None
    contract_number: Optional[str] = None
    no_contract: bool = False

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }


class PennylaneInvoiceDetailResponse(PennylaneInvoiceResponse):
    """Schema for Pennylane invoice detail response with raw data"""
    raw_data: dict = Field(default_factory=dict)


class PennylaneInvoiceListResponse(BaseModel):
    """Schema for paginated invoice list"""
    items: List[PennylaneInvoiceResponse]
    pagination: dict


# Quote Schemas
class PennylaneQuoteResponse(BaseModel):
    """Schema for Pennylane quote response"""
    id: UUID
    connection_id: UUID
    pennylane_id: str
    quote_number: Optional[str] = None
    status: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "EUR"
    issue_date: Optional[date] = None
    valid_until: Optional[date] = None
    accepted_at: Optional[datetime] = None
    synced_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }


class PennylaneQuoteDetailResponse(PennylaneQuoteResponse):
    """Schema for Pennylane quote detail response with raw data"""
    raw_data: dict = Field(default_factory=dict)


class PennylaneQuoteListResponse(BaseModel):
    """Schema for paginated quote list"""
    items: List[PennylaneQuoteResponse]
    pagination: dict


# Subscription Schemas
class PennylaneSubscriptionResponse(BaseModel):
    """Schema for Pennylane subscription response"""
    id: UUID
    connection_id: UUID
    pennylane_id: str
    status: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "EUR"
    interval: Optional[str] = None
    start_date: Optional[date] = None
    next_billing_date: Optional[date] = None
    cancelled_at: Optional[datetime] = None
    synced_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }


class PennylaneSubscriptionDetailResponse(PennylaneSubscriptionResponse):
    """Schema for Pennylane subscription detail response with raw data"""
    raw_data: dict = Field(default_factory=dict)


class PennylaneSubscriptionListResponse(BaseModel):
    """Schema for paginated subscription list"""
    items: List[PennylaneSubscriptionResponse]
    pagination: dict


# =============================================================================
# Helper Functions
# =============================================================================


def build_pagination_info(total: int, pagination: PaginationParams) -> dict:
    """Build pagination info dict"""
    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1
    return {
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": pagination.page < total_pages,
        "has_prev": pagination.page > 1,
    }


# =============================================================================
# Connection Management Routes
# =============================================================================


@router.get("/connections", response_model=PennylaneConnectionListResponse)
async def list_connections(
    pagination: PaginationParams = Depends(),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    List all Pennylane connections

    Returns connections with last_sync information (admin only).
    """
    query = db.query(PennylaneConnection)

    if is_active is not None:
        query = query.filter(PennylaneConnection.is_active == is_active)

    total = query.count()
    connections = (
        query.order_by(PennylaneConnection.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )

    return PennylaneConnectionListResponse(
        items=[PennylaneConnectionResponse.from_connection(c) for c in connections],
        pagination=build_pagination_info(total, pagination),
    )


@router.get("/connections/{connection_id}", response_model=PennylaneConnectionResponse)
async def get_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Get a single Pennylane connection

    Returns connection details with masked API token (admin only).
    """
    connection = db.query(PennylaneConnection).filter(
        PennylaneConnection.id == connection_id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    return PennylaneConnectionResponse.from_connection(connection)


@router.post(
    "/connections",
    response_model=PennylaneConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    connection_data: PennylaneConnectionCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Create a new Pennylane connection

    Creates a new connection configuration for syncing with Pennylane (admin only).
    """
    # Check for duplicate name
    existing = db.query(PennylaneConnection).filter(
        PennylaneConnection.name == connection_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Connection with name '{connection_data.name}' already exists",
        )

    # Create connection
    connection = PennylaneConnection(
        name=connection_data.name,
        api_token=connection_data.api_token,
        sync_customers=connection_data.sync_customers,
        sync_invoices=connection_data.sync_invoices,
        sync_quotes=connection_data.sync_quotes,
        sync_subscriptions=connection_data.sync_subscriptions,
        created_by_id=current_user.id,
    )

    db.add(connection)
    db.commit()
    db.refresh(connection)

    logger.info(f"Created Pennylane connection '{connection.name}' by user {current_user.id}")
    return PennylaneConnectionResponse.from_connection(connection)


@router.put("/connections/{connection_id}", response_model=PennylaneConnectionResponse)
async def update_connection(
    connection_id: UUID,
    connection_data: PennylaneConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Update a Pennylane connection

    Updates connection settings including name, sync flags, and optionally the API token (admin only).
    """
    connection = db.query(PennylaneConnection).filter(
        PennylaneConnection.id == connection_id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    # Check for duplicate name if name is being changed
    if connection_data.name and connection_data.name != connection.name:
        existing = db.query(PennylaneConnection).filter(
            PennylaneConnection.name == connection_data.name,
            PennylaneConnection.id != connection_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Connection with name '{connection_data.name}' already exists",
            )

    # Update fields
    update_data = connection_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connection, field, value)

    db.commit()
    db.refresh(connection)

    logger.info(f"Updated Pennylane connection '{connection.name}' by user {current_user.id}")
    return PennylaneConnectionResponse.from_connection(connection)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Delete a Pennylane connection

    Deletes the connection and all associated synced data (cascades to customers,
    invoices, quotes, subscriptions) (admin only).
    """
    connection = db.query(PennylaneConnection).filter(
        PennylaneConnection.id == connection_id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    connection_name = connection.name
    db.delete(connection)
    db.commit()

    logger.info(f"Deleted Pennylane connection '{connection_name}' by user {current_user.id}")
    return None


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Test a Pennylane connection

    Tests the connection by calling the Pennylane /me endpoint (admin only).
    """
    connection = db.query(PennylaneConnection).filter(
        PennylaneConnection.id == connection_id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    try:
        async with PennylaneClient(connection.api_token) as client:
            result = await client.test_connection()

        # Extract company name from response
        company_name = result.get("company", {}).get("name") if isinstance(result, dict) else None

        # Update connection with company name if we got one
        if company_name and company_name != connection.company_name:
            connection.company_name = company_name
            db.commit()

        logger.info(f"Connection test successful for '{connection.name}'")
        return ConnectionTestResponse(
            success=True,
            company_name=company_name,
            message="Connection test successful",
            details=result,
        )

    except PennylaneAuthError as e:
        logger.warning(f"Connection test failed for '{connection.name}': {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"Authentication failed: {e.message}",
        )

    except PennylaneAPIError as e:
        logger.error(f"Connection test failed for '{connection.name}': {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"API error: {e.message}",
        )

    except Exception as e:
        logger.error(f"Unexpected error testing connection '{connection.name}': {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
        )


@router.post("/connections/{connection_id}/sync", response_model=SyncResultResponse)
async def sync_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Trigger a manual sync for a Pennylane connection

    Syncs all enabled entity types (customers, invoices, quotes, subscriptions)
    and returns the results (admin only).
    """
    connection = db.query(PennylaneConnection).filter(
        PennylaneConnection.id == connection_id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    if not connection.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sync inactive connection",
        )

    sync_started_at = datetime.utcnow()

    try:
        sync_service = PennylaneSyncService(db, connection)
        results = await sync_service.sync_all()

        sync_completed_at = datetime.utcnow()

        # Convert SyncResult objects to response format
        results_dict = {}
        overall_success = True
        for entity_type, result in results.items():
            results_dict[entity_type] = SyncEntityResult(
                entity_type=result.entity_type,
                total_fetched=result.total_fetched,
                created=result.created,
                updated=result.updated,
                success=result.success,
                errors=result.errors,
            )
            if not result.success:
                overall_success = False

        # Build summary message
        total_created = sum(r.created for r in results.values())
        total_updated = sum(r.updated for r in results.values())
        message = f"Sync completed: {total_created} created, {total_updated} updated"
        if not overall_success:
            message += " (with some errors)"

        logger.info(f"Sync completed for connection '{connection.name}': {message}")

        return SyncResultResponse(
            connection_id=connection.id,
            connection_name=connection.name,
            sync_started_at=sync_started_at,
            sync_completed_at=sync_completed_at,
            overall_success=overall_success,
            results=results_dict,
            message=message,
        )

    except PennylaneAuthError as e:
        logger.error(f"Authentication error during sync for '{connection.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Pennylane authentication failed: {e.message}",
        )

    except PennylaneAPIError as e:
        logger.error(f"API error during sync for '{connection.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Pennylane API error: {e.message}",
        )

    except Exception as e:
        logger.error(f"Unexpected error during sync for '{connection.name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


# =============================================================================
# Synced Data Routes - Customers
# =============================================================================


@router.get("/customers", response_model=PennylaneCustomerListResponse)
async def list_customers(
    pagination: PaginationParams = Depends(),
    connection_id: Optional[UUID] = Query(None, description="Filter by connection ID"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    customer_type: Optional[str] = Query(None, description="Filter by customer type (individual/company)"),
    pennylane_id: Optional[str] = Query(None, description="Filter by Pennylane customer ID"),
    sort: Optional[str] = Query(None, description="Sort field (prefix with - for descending, e.g. -name, synced_at)"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    List all synced Pennylane customers

    Supports filtering by connection_id, search, customer_type, pennylane_id and sorting (admin only).
    Sort examples: name, -name, email, -email, city, -city, country_code, -country_code, synced_at, -synced_at
    """
    query = db.query(PennylaneCustomer)

    if connection_id:
        query = query.filter(PennylaneCustomer.connection_id == connection_id)

    if pennylane_id:
        query = query.filter(PennylaneCustomer.pennylane_id == pennylane_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (PennylaneCustomer.name.ilike(search_filter)) |
            (PennylaneCustomer.email.ilike(search_filter))
        )

    if customer_type:
        query = query.filter(PennylaneCustomer.customer_type == customer_type)

    # Handle sorting
    sort_column_map = {
        'name': PennylaneCustomer.name,
        'email': PennylaneCustomer.email,
        'city': PennylaneCustomer.city,
        'country_code': PennylaneCustomer.country_code,
        'customer_type': PennylaneCustomer.customer_type,
        'synced_at': PennylaneCustomer.synced_at,
    }

    if sort:
        descending = sort.startswith('-')
        sort_field = sort[1:] if descending else sort
        if sort_field in sort_column_map:
            column = sort_column_map[sort_field]
            query = query.order_by(column.desc().nullslast() if descending else column.asc().nullsfirst())
        else:
            query = query.order_by(PennylaneCustomer.synced_at.desc())
    else:
        query = query.order_by(PennylaneCustomer.synced_at.desc())

    total = query.count()
    customers = (
        query.offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )

    return PennylaneCustomerListResponse(
        items=[PennylaneCustomerResponse.from_orm(c) for c in customers],
        pagination=build_pagination_info(total, pagination),
    )


@router.get("/customers/{customer_id}", response_model=PennylaneCustomerDetailResponse)
async def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Get a single synced Pennylane customer with raw data

    Returns full customer details including the raw API response (admin only).
    """
    customer = db.query(PennylaneCustomer).filter(
        PennylaneCustomer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    return PennylaneCustomerDetailResponse.from_orm(customer)


# =============================================================================
# Synced Data Routes - Invoices
# =============================================================================


@router.get("/invoices", response_model=PennylaneInvoiceListResponse)
async def list_invoices(
    pagination: PaginationParams = Depends(),
    connection_id: Optional[UUID] = Query(None, description="Filter by connection ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    date_from: Optional[date] = Query(None, description="Filter by issue date (from)"),
    date_to: Optional[date] = Query(None, description="Filter by issue date (to)"),
    search: Optional[str] = Query(None, description="Search by invoice number or customer name"),
    sort: Optional[str] = Query(None, description="Sort field (prefix with - for descending)"),
    contract_filter: Optional[UUID] = Query(None, alias="contract_id", description="Filter by contract ID"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    List all synced Pennylane invoices

    Supports filtering by connection_id, status, date range, search, contract_id and sorting (admin only).
    Sort examples: invoice_number, -invoice_number, customer_name, -customer_name, amount, -amount, issue_date, -issue_date, due_date, -due_date
    """
    # Join with Contract to get contract_number
    query = db.query(PennylaneInvoice, Contract.contract_number).outerjoin(
        Contract, PennylaneInvoice.contract_id == Contract.id
    )

    if connection_id:
        query = query.filter(PennylaneInvoice.connection_id == connection_id)

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',') if s.strip()]
        if len(statuses) == 1:
            query = query.filter(PennylaneInvoice.status == statuses[0])
        elif len(statuses) > 1:
            query = query.filter(PennylaneInvoice.status.in_(statuses))

    if date_from:
        query = query.filter(PennylaneInvoice.issue_date >= date_from)

    if date_to:
        query = query.filter(PennylaneInvoice.issue_date <= date_to)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (PennylaneInvoice.invoice_number.ilike(search_filter)) |
            (PennylaneInvoice.customer_name.ilike(search_filter))
        )

    if contract_filter:
        query = query.filter(PennylaneInvoice.contract_id == contract_filter)

    # Handle sorting
    sort_column_map = {
        'invoice_number': PennylaneInvoice.invoice_number,
        'customer_name': PennylaneInvoice.customer_name,
        'status': PennylaneInvoice.status,
        'amount': PennylaneInvoice.amount,
        'issue_date': PennylaneInvoice.issue_date,
        'due_date': PennylaneInvoice.due_date,
        'synced_at': PennylaneInvoice.synced_at,
    }

    if sort:
        descending = sort.startswith('-')
        sort_field = sort[1:] if descending else sort
        if sort_field in sort_column_map:
            column = sort_column_map[sort_field]
            query = query.order_by(column.desc().nullslast() if descending else column.asc().nullsfirst())
        else:
            query = query.order_by(PennylaneInvoice.issue_date.desc().nullslast())
    else:
        query = query.order_by(PennylaneInvoice.issue_date.desc().nullslast())

    total = query.count()
    results = (
        query.offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )

    # Build response items with contract_number from the join
    items = []
    for invoice, contract_number in results:
        item = PennylaneInvoiceResponse.from_orm(invoice)
        item.contract_number = contract_number
        items.append(item)

    return PennylaneInvoiceListResponse(
        items=items,
        pagination=build_pagination_info(total, pagination),
    )


@router.get("/invoices/{invoice_id}", response_model=PennylaneInvoiceDetailResponse)
async def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Get a single synced Pennylane invoice with raw data

    Returns full invoice details including the raw API response (admin only).
    """
    # Join with Contract to get contract_number
    result = db.query(PennylaneInvoice, Contract.contract_number).outerjoin(
        Contract, PennylaneInvoice.contract_id == Contract.id
    ).filter(
        PennylaneInvoice.id == invoice_id
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    invoice, contract_number = result
    response = PennylaneInvoiceDetailResponse.from_orm(invoice)
    response.contract_number = contract_number
    return response


@router.put("/invoices/{invoice_id}/contract")
async def link_invoice_to_contract(
    invoice_id: UUID,
    contract_id: Optional[UUID] = None,  # None to unlink
    no_contract: bool = False,  # True to explicitly mark as having no contract
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Link or unlink a Pennylane invoice to an internal contract.

    Pass a contract_id to link, no_contract=True to explicitly mark as having no contract,
    or both null/False to unlink (admin only).
    """
    # Find the invoice
    invoice = db.query(PennylaneInvoice).filter(PennylaneInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if no_contract:
        # Explicitly mark as having no contract
        invoice.no_contract = True
        invoice.contract_id = None
    elif contract_id:
        # Link to a contract
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found",
            )
        invoice.contract_id = contract.id
        invoice.no_contract = False
    else:
        # Unlink (set both to None/False)
        invoice.contract_id = None
        invoice.no_contract = False

    db.commit()
    return {
        "message": "Invoice updated",
        "contract_id": str(invoice.contract_id) if invoice.contract_id else None,
        "no_contract": invoice.no_contract,
    }


# =============================================================================
# Synced Data Routes - Quotes
# =============================================================================


@router.get("/quotes", response_model=PennylaneQuoteListResponse)
async def list_quotes(
    pagination: PaginationParams = Depends(),
    connection_id: Optional[UUID] = Query(None, description="Filter by connection ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by quote number or customer name"),
    sort: Optional[str] = Query(None, description="Sort field (prefix with - for descending)"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    List all synced Pennylane quotes

    Supports filtering by connection_id, status, search and sorting (admin only).
    Sort examples: quote_number, -quote_number, customer_name, -customer_name, amount, -amount, issue_date, -issue_date, valid_until, -valid_until
    """
    query = db.query(PennylaneQuote)

    if connection_id:
        query = query.filter(PennylaneQuote.connection_id == connection_id)

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',') if s.strip()]
        if len(statuses) == 1:
            query = query.filter(PennylaneQuote.status == statuses[0])
        elif len(statuses) > 1:
            query = query.filter(PennylaneQuote.status.in_(statuses))

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (PennylaneQuote.quote_number.ilike(search_filter)) |
            (PennylaneQuote.customer_name.ilike(search_filter))
        )

    # Handle sorting
    sort_column_map = {
        'quote_number': PennylaneQuote.quote_number,
        'customer_name': PennylaneQuote.customer_name,
        'status': PennylaneQuote.status,
        'amount': PennylaneQuote.amount,
        'issue_date': PennylaneQuote.issue_date,
        'valid_until': PennylaneQuote.valid_until,
        'synced_at': PennylaneQuote.synced_at,
    }

    if sort:
        descending = sort.startswith('-')
        sort_field = sort[1:] if descending else sort
        if sort_field in sort_column_map:
            column = sort_column_map[sort_field]
            query = query.order_by(column.desc().nullslast() if descending else column.asc().nullsfirst())
        else:
            query = query.order_by(PennylaneQuote.issue_date.desc().nullslast())
    else:
        query = query.order_by(PennylaneQuote.issue_date.desc().nullslast())

    total = query.count()
    quotes = (
        query.offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )

    return PennylaneQuoteListResponse(
        items=[PennylaneQuoteResponse.from_orm(q) for q in quotes],
        pagination=build_pagination_info(total, pagination),
    )


@router.get("/quotes/{quote_id}", response_model=PennylaneQuoteDetailResponse)
async def get_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Get a single synced Pennylane quote with raw data

    Returns full quote details including the raw API response (admin only).
    """
    quote = db.query(PennylaneQuote).filter(
        PennylaneQuote.id == quote_id
    ).first()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote {quote_id} not found",
        )

    return PennylaneQuoteDetailResponse.from_orm(quote)


# =============================================================================
# Synced Data Routes - Subscriptions
# =============================================================================


@router.get("/subscriptions", response_model=PennylaneSubscriptionListResponse)
async def list_subscriptions(
    pagination: PaginationParams = Depends(),
    connection_id: Optional[UUID] = Query(None, description="Filter by connection ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    interval: Optional[str] = Query(None, description="Filter by billing interval (monthly/yearly)"),
    search: Optional[str] = Query(None, description="Search by customer name"),
    sort: Optional[str] = Query(None, description="Sort field (prefix with - for descending)"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    List all synced Pennylane subscriptions

    Supports filtering by connection_id, status, interval, search and sorting (admin only).
    Sort examples: customer_name, -customer_name, amount, -amount, start_date, -start_date, next_billing_date, -next_billing_date
    """
    query = db.query(PennylaneSubscription)

    if connection_id:
        query = query.filter(PennylaneSubscription.connection_id == connection_id)

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',') if s.strip()]
        if len(statuses) == 1:
            query = query.filter(PennylaneSubscription.status == statuses[0])
        elif len(statuses) > 1:
            query = query.filter(PennylaneSubscription.status.in_(statuses))

    if interval:
        query = query.filter(PennylaneSubscription.interval == interval)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(PennylaneSubscription.customer_name.ilike(search_filter))

    # Handle sorting
    sort_column_map = {
        'customer_name': PennylaneSubscription.customer_name,
        'status': PennylaneSubscription.status,
        'amount': PennylaneSubscription.amount,
        'interval': PennylaneSubscription.interval,
        'start_date': PennylaneSubscription.start_date,
        'next_billing_date': PennylaneSubscription.next_billing_date,
        'synced_at': PennylaneSubscription.synced_at,
    }

    if sort:
        descending = sort.startswith('-')
        sort_field = sort[1:] if descending else sort
        if sort_field in sort_column_map:
            column = sort_column_map[sort_field]
            query = query.order_by(column.desc().nullslast() if descending else column.asc().nullsfirst())
        else:
            query = query.order_by(PennylaneSubscription.start_date.desc().nullslast())
    else:
        query = query.order_by(PennylaneSubscription.start_date.desc().nullslast())

    total = query.count()
    subscriptions = (
        query.offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )

    return PennylaneSubscriptionListResponse(
        items=[PennylaneSubscriptionResponse.from_orm(s) for s in subscriptions],
        pagination=build_pagination_info(total, pagination),
    )


@router.get("/subscriptions/{subscription_id}", response_model=PennylaneSubscriptionDetailResponse)
async def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Get a single synced Pennylane subscription with raw data

    Returns full subscription details including the raw API response (admin only).
    """
    subscription = db.query(PennylaneSubscription).filter(
        PennylaneSubscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )

    return PennylaneSubscriptionDetailResponse.from_orm(subscription)
