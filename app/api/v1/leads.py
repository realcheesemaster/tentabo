"""
Lead API endpoints

Provides CRM-agnostic lead management with multi-tenant filtering
"""

import logging
from typing import Union
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser
from app.models.crm import Lead, LeadStatus, LeadActivity, LeadNote, LeadStatusHistory
from app.auth.dependencies import get_current_user
from app.api.dependencies import PaginationParams, MultiTenantFilter, get_multi_tenant_filter
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse, LeadDetailResponse, LeadListResponse,
    LeadActivityCreate, LeadActivityResponse,
    LeadNoteCreate, LeadNoteResponse,
    LeadStatusChangeRequest,
)
from app.schemas.common import PaginationInfo

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/leads", response_model=LeadListResponse, tags=["Leads"])
async def list_leads(
    pagination: PaginationParams = Depends(),
    status_filter: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    mt_filter: MultiTenantFilter = Depends(get_multi_tenant_filter),
):
    """List leads with multi-tenant filtering"""
    query = db.query(Lead)
    query = mt_filter.filter_leads_query(query, current_user, Lead)

    if status_filter:
        query = query.filter(Lead.status == status_filter)

    total = query.count()
    leads = query.offset(pagination.skip).limit(pagination.limit).all()

    import math
    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1
    pagination_info = PaginationInfo(
        page=pagination.page, page_size=pagination.page_size,
        total_items=total, total_pages=total_pages,
        has_next=pagination.page < total_pages, has_prev=pagination.page > 1
    )

    return LeadListResponse(
        items=[LeadResponse.from_orm(l) for l in leads],
        pagination=pagination_info.dict()
    )


@router.get("/leads/{lead_id}", response_model=LeadDetailResponse, tags=["Leads"])
async def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Get lead details with activities and notes"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    return LeadDetailResponse.from_orm(lead)


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED, tags=["Leads"])
async def create_lead(
    lead_data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Create a new lead"""
    lead = Lead(
        provider_name=lead_data.provider_name,
        provider_id=lead_data.provider_id,
        title=lead_data.title,
        organization=lead_data.organization,
        contact_name=lead_data.contact_name,
        contact_email=lead_data.contact_email,
        contact_phone=lead_data.contact_phone,
        value=lead_data.value,
        currency=lead_data.currency,
        status=LeadStatus(lead_data.status),
        probability=lead_data.probability,
        expected_close_date=lead_data.expected_close_date,
        owner_id=current_user.id,
        partner_id=lead_data.partner_id,
        distributor_id=lead_data.distributor_id,
        sync_status='synced',
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    logger.info(f"Created lead {lead.title} by user {current_user.id}")
    return LeadResponse.from_orm(lead)


@router.put("/leads/{lead_id}", response_model=LeadResponse, tags=["Leads"])
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Update a lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    update_data = lead_data.dict(exclude_unset=True)
    if 'status' in update_data:
        update_data['status'] = LeadStatus(update_data['status'])

    for field, value in update_data.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    logger.info(f"Updated lead {lead.title} by user {current_user.id}")
    return LeadResponse.from_orm(lead)


@router.get("/leads/{lead_id}/activities", response_model=list[LeadActivityResponse], tags=["Leads"])
async def list_lead_activities(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """List activities for a lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    activities = db.query(LeadActivity).filter(LeadActivity.lead_id == lead_id).all()
    return [LeadActivityResponse.from_orm(a) for a in activities]


@router.post("/leads/{lead_id}/activities", response_model=LeadActivityResponse, status_code=status.HTTP_201_CREATED, tags=["Leads"])
async def create_lead_activity(
    lead_id: UUID,
    activity_data: LeadActivityCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Create an activity for a lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    activity = LeadActivity(
        lead_id=lead_id,
        provider_name=lead.provider_name,
        activity_type=activity_data.activity_type,
        subject=activity_data.subject,
        description=activity_data.description,
        due_date=activity_data.due_date,
        done='true' if activity_data.done else 'false',
        user_id=current_user.id,
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    logger.info(f"Created activity for lead {lead.title} by user {current_user.id}")
    return LeadActivityResponse.from_orm(activity)


@router.post("/leads/{lead_id}/notes", response_model=LeadNoteResponse, status_code=status.HTTP_201_CREATED, tags=["Leads"])
async def create_lead_note(
    lead_id: UUID,
    note_data: LeadNoteCreate,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Create a note for a lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    note = LeadNote(
        lead_id=lead_id,
        content=note_data.content,
        created_by_user_id=current_user.id,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info(f"Created note for lead {lead.title} by user {current_user.id}")
    return LeadNoteResponse.from_orm(note)


@router.put("/leads/{lead_id}/status", response_model=LeadResponse, tags=["Leads"])
async def change_lead_status(
    lead_id: UUID,
    status_data: LeadStatusChangeRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """Change lead status with history tracking"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    old_status = lead.status
    new_status = LeadStatus(status_data.status)

    # Record status change in history
    history = LeadStatusHistory(
        lead_id=lead_id,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=current_user.id,
        reason=status_data.reason,
    )
    db.add(history)

    lead.status = new_status
    db.commit()
    db.refresh(lead)

    logger.info(f"Changed lead {lead.title} status: {old_status.value} -> {new_status.value}")
    return LeadResponse.from_orm(lead)
