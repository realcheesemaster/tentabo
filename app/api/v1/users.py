"""
User management API endpoints

Provides user administration (admin only)
"""

import logging
from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser, UserRole
from app.auth.dependencies import get_current_user, require_admin
from app.api.dependencies import PaginationParams
from app.schemas.user import (
    UserResponse, UserListResponse,
    UserEnableRequest, UserRoleUpdateRequest,
)
from app.schemas.common import PaginationInfo
from app.auth.ldap_auth import (
    get_ldap_connection,
    sync_ldap_user_to_db,
    get_ldap_users_display_data_batch,
    parse_ldap_email,
    LDAPConnectionError
)
from ldap3 import SUBTREE
from ldap_config import (
    LDAP_USER_SEARCH_BASE,
    LDAP_USER_OBJECT_CLASS,
    LDAP_USER_ID_ATTRIBUTE,
    LDAP_USER_EMAIL_ATTRIBUTE,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users", response_model=UserListResponse, tags=["Users"])
async def list_users(
    pagination: PaginationParams = Depends(),
    role: str = Query(None, description="Filter by role"),
    is_enabled: bool = Query(None, description="Filter by enabled status"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    List users (admin only)

    Returns all users with pagination and filtering.
    """
    query = db.query(User)

    # Apply filters
    if role:
        try:
            role_enum = UserRole(role)
            query = query.filter(User.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}"
            )

    if is_enabled is not None:
        query = query.filter(User.is_enabled == is_enabled)

    # Count total
    total = query.count()

    # Apply pagination
    users = query.order_by(User.created_at.desc()).offset(pagination.skip).limit(pagination.limit).all()

    # Fetch LDAP display data on-demand for LDAP users
    ldap_users = [u for u in users if u.provider == 'ldap']
    if ldap_users:
        try:
            ldap_usernames = [u.provider_id for u in ldap_users]
            ldap_display_data = get_ldap_users_display_data_batch(ldap_usernames)

            # Update users with LDAP data
            for user in ldap_users:
                if user.provider_id in ldap_display_data:
                    display_data = ldap_display_data[user.provider_id]
                    # Temporarily set email and full_name for response
                    # Note: These are not saved to DB, only returned in API response
                    # Ensure we only set string values, never lists or other types
                    email_value = display_data.get('email')
                    if email_value and isinstance(email_value, str):
                        user.email = email_value

                    full_name_value = display_data.get('full_name')
                    if full_name_value and isinstance(full_name_value, str):
                        user.full_name = full_name_value
        except Exception as e:
            # Log error but don't fail the entire request
            logger.error(f"Error fetching LDAP display data: {e}")
            # Continue with placeholder email values from database

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

    return UserListResponse(
        items=[UserResponse.from_orm(u) for u in users],
        pagination=pagination_info.dict(),
    )


@router.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Get user details (admin only)

    Returns detailed user information.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return UserResponse.from_orm(user)


@router.put("/users/{user_id}/enable", response_model=UserResponse, tags=["Users"])
async def enable_disable_user(
    user_id: UUID,
    enable_data: UserEnableRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Enable or disable a user (admin only)

    Sets the is_enabled flag and tracks who made the change.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Update enabled status
    from datetime import datetime

    old_status = user.is_enabled
    user.is_enabled = enable_data.enabled

    if enable_data.enabled and not old_status:
        # User is being enabled
        user.enabled_by = current_user.id if isinstance(current_user, AdminUser) else None
        user.enabled_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    action = "enabled" if enable_data.enabled else "disabled"
    logger.info(
        f"User {user.email} {action} by {current_user.id}. "
        f"Reason: {enable_data.reason or 'No reason provided'}"
    )

    return UserResponse.from_orm(user)


@router.put("/users/{user_id}/role", response_model=UserResponse, tags=["Users"])
async def update_user_role(
    user_id: UUID,
    role_data: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Update user role (admin only)

    Changes the user's role (admin, partner, distributor, etc.)
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Validate role
    try:
        new_role = UserRole(role_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role_data.role}"
        )

    old_role = user.role
    user.role = new_role

    db.commit()
    db.refresh(user)

    logger.info(
        f"User {user.email} role changed from {old_role.value} to {new_role.value} "
        f"by {current_user.id}. Reason: {role_data.reason or 'No reason provided'}"
    )

    return UserResponse.from_orm(user)

@router.get("/users/ldap/discover", tags=["Users"])
async def discover_ldap_users(
    search: str = Query(None, description="Search filter for username/email"),
    limit: int = Query(50, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Discover users from LDAP directory (admin only)

    Returns a list of LDAP users with their current authorization status.
    """
    conn = None
    try:
        # Connect to LDAP
        conn = get_ldap_connection()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to LDAP server"
            )

        # Build search filter
        if search:
            search_filter = f"(&(objectClass={LDAP_USER_OBJECT_CLASS})(|({LDAP_USER_ID_ATTRIBUTE}=*{search}*)({LDAP_USER_EMAIL_ATTRIBUTE}=*{search}*)))"
        else:
            search_filter = f"(objectClass={LDAP_USER_OBJECT_CLASS})"

        # Search LDAP
        success = conn.search(
            search_base=LDAP_USER_SEARCH_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['*'],
            size_limit=limit
        )

        if not success:
            return {"ldap_users": [], "message": "No users found in LDAP"}

        # Process LDAP entries
        ldap_users = []
        for entry in conn.entries:
            username = str(getattr(entry, LDAP_USER_ID_ATTRIBUTE).value) if hasattr(entry, LDAP_USER_ID_ATTRIBUTE) else None
            if not username:
                continue

            # Check if user exists in database
            db_user = db.query(User).filter(
                User.provider == 'ldap',
                User.provider_id == username
            ).first()

            ldap_user = {
                'username': username,
                'email': parse_ldap_email(entry, LDAP_USER_EMAIL_ATTRIBUTE),
                'full_name': str(entry.cn.value) if hasattr(entry, 'cn') else None,
                'display_name': str(entry.displayName.value) if hasattr(entry, 'displayName') else None,
                'department': str(entry.department.value) if hasattr(entry, 'department') else None,
                'exists_in_db': db_user is not None,
                'is_enabled': db_user.is_enabled if db_user else False,
                'role': db_user.role.value if db_user else None,
                'user_id': str(db_user.id) if db_user else None
            }
            ldap_users.append(ldap_user)

        return {
            "ldap_users": ldap_users,
            "total": len(ldap_users),
            "message": f"Found {len(ldap_users)} users in LDAP"
        }

    except LDAPConnectionError as e:
        logger.error(f"LDAP connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error discovering LDAP users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching LDAP: {str(e)}"
        )
    finally:
        if conn:
            try:
                conn.unbind()
            except:
                pass


@router.post("/users/ldap/enable", response_model=UserResponse, tags=["Users"])
async def enable_ldap_user(
    username: str = Query(..., description="LDAP username to enable"),
    role: str = Query("partner", description="Role to assign to the user"),
    enabled: bool = Query(True, description="Whether to enable the user immediately"),
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Enable a user from LDAP (admin only)

    Creates or updates a user record from LDAP and sets their role and enabled status.
    """
    conn = None
    try:
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}. Valid roles: {[r.value for r in UserRole]}"
            )

        # Connect to LDAP
        conn = get_ldap_connection()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to LDAP server"
            )

        # Search for the specific user
        search_filter = f"(&(objectClass={LDAP_USER_OBJECT_CLASS})({LDAP_USER_ID_ATTRIBUTE}={username}))"

        success = conn.search(
            search_base=LDAP_USER_SEARCH_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['*']
        )

        if not success or not conn.entries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found in LDAP"
            )

        # Extract user data
        entry = conn.entries[0]
        ldap_data = {
            'username': username,
            'email': parse_ldap_email(entry, LDAP_USER_EMAIL_ATTRIBUTE),
            'full_name': str(entry.cn.value) if hasattr(entry, 'cn') else None,
            'first_name': str(entry.givenName.value) if hasattr(entry, 'givenName') else None,
            'last_name': str(entry.sn.value) if hasattr(entry, 'sn') else None,
            'display_name': str(entry.displayName.value) if hasattr(entry, 'displayName') else None,
        }

        # Sync to database
        user = sync_ldap_user_to_db(ldap_data, db, default_role=user_role)

        # Update enabled status if different from default
        if user.is_enabled != enabled:
            user.is_enabled = enabled
            if enabled:
                from datetime import datetime
                user.enabled_by = current_user.id if isinstance(current_user, AdminUser) else None
                user.enabled_at = datetime.utcnow()

        # Update role if different
        if user.role != user_role:
            user.role = user_role

        db.commit()
        db.refresh(user)

        logger.info(f"Enabled LDAP user '{username}' with role '{role}' and enabled={enabled} by admin {current_user.id}")

        return UserResponse.from_orm(user)

    except HTTPException:
        raise
    except LDAPConnectionError as e:
        logger.error(f"LDAP connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error enabling LDAP user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enabling user: {str(e)}"
        )
    finally:
        if conn:
            try:
                conn.unbind()
            except:
                pass


@router.put("/users/{user_id}/company", response_model=UserResponse, tags=["Users"])
async def update_user_company(
    user_id: UUID,
    partner_id: UUID = None,
    distributor_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: Union[User, AdminUser] = Depends(require_admin),
):
    """
    Update user company assignment (admin only)

    Assigns a user to either a partner or distributor company.
    Only one of partner_id or distributor_id should be provided.
    Both being None will clear the company assignment.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Validate that only one of partner_id or distributor_id is set
    if partner_id and distributor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign user to both partner and distributor. Provide only one.",
        )

    # If partner_id: verify partner exists, set user.partner_id
    if partner_id:
        from app.models.partner import Partner
        partner = db.query(Partner).filter(Partner.id == partner_id).first()
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Partner {partner_id} not found",
            )

        user.partner_id = partner_id
        user.distributor_id = None
        logger.info(f"Assigned user {user.email} to partner {partner.name} by admin {current_user.id}")

    # If distributor_id: verify distributor exists, set user.distributor_id
    elif distributor_id:
        from app.models.partner import Distributor
        distributor = db.query(Distributor).filter(Distributor.id == distributor_id).first()
        if not distributor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Distributor {distributor_id} not found",
            )

        user.distributor_id = distributor_id
        user.partner_id = None
        logger.info(f"Assigned user {user.email} to distributor {distributor.name} by admin {current_user.id}")

    # Both None: clear assignment
    else:
        user.partner_id = None
        user.distributor_id = None
        logger.info(f"Cleared company assignment for user {user.email} by admin {current_user.id}")

    # Commit and return updated user
    db.commit()
    db.refresh(user)

    return UserResponse.from_orm(user)