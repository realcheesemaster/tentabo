"""
Partner and Distributor API endpoints

Provides CRUD operations for partners and distributors with multi-tenant filtering:
- GET /partners - List partners (filtered by role)
- GET /partners/{id} - Get partner details
- POST /partners - Create partner (admin only)
- PUT /partners/{id} - Update partner (admin only)
- DELETE /partners/{id} - Delete partner (admin only)
- GET /distributors - List distributors (filtered by role)
- GET /distributors/{id} - Get distributor details
- POST /distributors - Create distributor (admin only)
- PUT /distributors/{id} - Update distributor (admin only)
- DELETE /distributors/{id} - Delete distributor (admin only)
- POST /distributors/{id}/partners - Link partner to distributor
- GET /distributors/{id}/partners - List distributor's partners
"""

import logging
from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser
from app.models.partner import Partner, Distributor, DistributorPartner
from app.auth.dependencies import get_current_user, require_admin
from app.api.dependencies import PaginationParams, MultiTenantFilter, get_multi_tenant_filter
from app.schemas.partner import (
    PartnerCreate,
    PartnerUpdate,
    PartnerResponse,
    PartnerListResponse,
    DistributorCreate,
    DistributorUpdate,
    DistributorResponse,
    DistributorListResponse,
    DistributorPartnerLinkRequest,
    DistributorPartnerResponse,
)
from app.schemas.common import PaginationInfo, SuccessResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== PARTNER ENDPOINTS ====================


@router.get("/partners", response_model=PartnerListResponse, tags=["Partners"])
async def list_partners(
    pagination: PaginationParams = Depends(),
    is_active: bool = Query(None, description="Filter by active status"),
    search: str = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """
    List partners with multi-tenant filtering

    - Admins see all partners
    - Distributors see only their associated partners
    - Partners see only their own record
    """
    # Build query with multi-tenant filter
    query = db.query(Partner)
    query = mt_filter.filter_partners_query(query, current_user, Partner)

    # Apply additional filters
    if is_active is not None:
        query = query.filter(Partner.is_active == is_active)

    if search:
        query = query.filter(Partner.name.ilike(f"%{search}%"))

    # Count total
    total = query.count()

    # Apply pagination
    partners = query.offset(pagination.skip).limit(pagination.limit).all()

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

    return PartnerListResponse(
        items=[PartnerResponse.from_orm(p) for p in partners],
        pagination=pagination_info.dict(),
    )


@router.get("/partners/{partner_id}", response_model=PartnerResponse, tags=["Partners"])
async def get_partner(
    partner_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """
    Get partner details

    Access controlled by multi-tenant filter.
    """
    partner = db.query(Partner).filter(Partner.id == partner_id).first()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {partner_id} not found",
        )

    # Check access
    if not mt_filter.can_access_partner(current_user, partner_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this partner",
        )

    return PartnerResponse.from_orm(partner)


@router.post("/partners", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED, tags=["Partners"])
async def create_partner(
    partner_data: PartnerCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Create a new partner (admin only)
    """
    # Check if partner with same registration number exists
    if partner_data.registration_number:
        existing = db.query(Partner).filter(
            Partner.registration_number == partner_data.registration_number
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Partner with registration number '{partner_data.registration_number}' already exists",
            )

    # Create partner
    partner = Partner(**partner_data.dict())

    db.add(partner)
    db.commit()
    db.refresh(partner)

    logger.info(f"Created partner {partner.name} by user {current_user.id}")

    return PartnerResponse.from_orm(partner)


@router.put("/partners/{partner_id}", response_model=PartnerResponse, tags=["Partners"])
async def update_partner(
    partner_id: UUID,
    partner_data: PartnerUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Update a partner (admin only)
    """
    partner = db.query(Partner).filter(Partner.id == partner_id).first()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {partner_id} not found",
        )

    # Update fields
    update_data = partner_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(partner, field, value)

    db.commit()
    db.refresh(partner)

    logger.info(f"Updated partner {partner.name} by user {current_user.id}")

    return PartnerResponse.from_orm(partner)


@router.delete("/partners/{partner_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Partners"])
async def delete_partner(
    partner_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Delete a partner (admin only)

    Deletes partner and all associations (cascade).
    """
    partner = db.query(Partner).filter(Partner.id == partner_id).first()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {partner_id} not found",
        )

    db.delete(partner)
    db.commit()

    logger.info(f"Deleted partner {partner.name} by user {current_user.id}")

    return None


# ==================== DISTRIBUTOR ENDPOINTS ====================


@router.get("/distributors", response_model=DistributorListResponse, tags=["Distributors"])
async def list_distributors(
    pagination: PaginationParams = Depends(),
    is_active: bool = Query(None, description="Filter by active status"),
    search: str = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """
    List distributors with multi-tenant filtering

    - Admins see all distributors
    - Distributors see only their own record
    - Partners see their associated distributors
    """
    # Build query with multi-tenant filter
    query = db.query(Distributor)
    query = mt_filter.filter_distributors_query(query, current_user, Distributor)

    # Apply additional filters
    if is_active is not None:
        query = query.filter(Distributor.is_active == is_active)

    if search:
        query = query.filter(Distributor.name.ilike(f"%{search}%"))

    # Count total
    total = query.count()

    # Apply pagination
    distributors = query.offset(pagination.skip).limit(pagination.limit).all()

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

    return DistributorListResponse(
        items=[DistributorResponse.from_orm(d) for d in distributors],
        pagination=pagination_info.dict(),
    )


@router.get("/distributors/{distributor_id}", response_model=DistributorResponse, tags=["Distributors"])
async def get_distributor(
    distributor_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """
    Get distributor details

    Access controlled by multi-tenant filter.
    """
    distributor = db.query(Distributor).filter(Distributor.id == distributor_id).first()

    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distributor {distributor_id} not found",
        )

    # Check access
    if not mt_filter.can_access_distributor(current_user, distributor_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this distributor",
        )

    return DistributorResponse.from_orm(distributor)


@router.post("/distributors", response_model=DistributorResponse, status_code=status.HTTP_201_CREATED, tags=["Distributors"])
async def create_distributor(
    distributor_data: DistributorCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Create a new distributor (admin only)
    """
    # Check if distributor with same registration number exists
    if distributor_data.registration_number:
        existing = db.query(Distributor).filter(
            Distributor.registration_number == distributor_data.registration_number
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Distributor with registration number '{distributor_data.registration_number}' already exists",
            )

    # Create distributor
    distributor = Distributor(**distributor_data.dict())

    db.add(distributor)
    db.commit()
    db.refresh(distributor)

    logger.info(f"Created distributor {distributor.name} by user {current_user.id}")

    return DistributorResponse.from_orm(distributor)


@router.put("/distributors/{distributor_id}", response_model=DistributorResponse, tags=["Distributors"])
async def update_distributor(
    distributor_id: UUID,
    distributor_data: DistributorUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Update a distributor (admin only)
    """
    distributor = db.query(Distributor).filter(Distributor.id == distributor_id).first()

    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distributor {distributor_id} not found",
        )

    # Update fields
    update_data = distributor_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(distributor, field, value)

    db.commit()
    db.refresh(distributor)

    logger.info(f"Updated distributor {distributor.name} by user {current_user.id}")

    return DistributorResponse.from_orm(distributor)


@router.delete("/distributors/{distributor_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Distributors"])
async def delete_distributor(
    distributor_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Delete a distributor (admin only)

    Deletes distributor and all associations (cascade).
    """
    distributor = db.query(Distributor).filter(Distributor.id == distributor_id).first()

    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distributor {distributor_id} not found",
        )

    db.delete(distributor)
    db.commit()

    logger.info(f"Deleted distributor {distributor.name} by user {current_user.id}")

    return None


# ==================== DISTRIBUTOR-PARTNER RELATIONSHIP ENDPOINTS ====================


@router.post("/distributors/{distributor_id}/partners", response_model=DistributorPartnerResponse, status_code=status.HTTP_201_CREATED, tags=["Distributors"])
async def link_partner_to_distributor(
    distributor_id: UUID,
    link_data: DistributorPartnerLinkRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Link a partner to a distributor (admin only)

    Creates a distributor-partner association.
    """
    # Verify distributor exists
    distributor = db.query(Distributor).filter(Distributor.id == distributor_id).first()
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distributor {distributor_id} not found",
        )

    # Verify partner exists
    partner = db.query(Partner).filter(Partner.id == link_data.partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {link_data.partner_id} not found",
        )

    # Check if association already exists
    existing = db.query(DistributorPartner).filter(
        DistributorPartner.distributor_id == distributor_id,
        DistributorPartner.partner_id == link_data.partner_id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Partner {partner.name} is already linked to distributor {distributor.name}",
        )

    # Create association
    association = DistributorPartner(
        distributor_id=distributor_id,
        partner_id=link_data.partner_id,
        assigned_by=current_user.id if isinstance(current_user, AdminUser) else None,
        notes=link_data.notes,
        is_active=True,
    )

    db.add(association)
    db.commit()
    db.refresh(association)

    logger.info(
        f"Linked partner {partner.name} to distributor {distributor.name} "
        f"by user {current_user.id}"
    )

    return DistributorPartnerResponse.from_orm(association)


@router.get("/distributors/{distributor_id}/partners", response_model=List[DistributorPartnerResponse], tags=["Distributors"])
async def list_distributor_partners(
    distributor_id: UUID,
    is_active: bool = Query(True, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """
    List partners associated with a distributor

    Access controlled by multi-tenant filter.
    """
    # Check access to distributor
    if not mt_filter.can_access_distributor(current_user, distributor_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this distributor",
        )

    # Query associations
    query = db.query(DistributorPartner).filter(
        DistributorPartner.distributor_id == distributor_id
    )

    if is_active is not None:
        query = query.filter(DistributorPartner.is_active == is_active)

    associations = query.all()

    return [DistributorPartnerResponse.from_orm(assoc) for assoc in associations]
