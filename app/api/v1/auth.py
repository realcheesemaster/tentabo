"""
Authentication API endpoints for Tentabo PRM

Provides:
- POST /auth/login - Authenticate and get JWT token
- POST /auth/refresh - Refresh JWT token
- GET /auth/me - Get current user info
- POST /users/me/api-keys - Create API key
- GET /users/me/api-keys - List user's API keys
- DELETE /users/me/api-keys/{key_id} - Revoke API key
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser, UserRole
from app.models.api_key import APIKey
from app.auth.security import (
    verify_password,
    create_token_for_user,
    generate_api_key,
    hash_api_key,
)
from app.auth.ldap_auth import (
    authenticate_and_sync_ldap_user,
    LDAPConnectionError,
    LDAPInvalidCredentialsError,
)
from app.auth.dependencies import get_current_user
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request with username and password"""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_type: str = Field(..., description="User type: 'admin' or 'user'")


class UserInfoResponse(BaseModel):
    """Current user information"""
    id: str
    user_type: str  # 'admin' or 'user'
    username: Optional[str] = None
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = None  # Only for regular users
    is_enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key"""
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the key")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days (optional)")
    scopes: List[str] = Field(default=["read", "write"], description="Permission scopes")


class APIKeyResponse(BaseModel):
    """Response when creating an API key (includes the raw key)"""
    api_key: str = Field(..., description="The actual API key - save this securely!")
    id: str
    name: str
    prefix: str
    expires_at: Optional[datetime]
    scopes: List[str]
    message: str = "Save this key securely - it won't be shown again"


class APIKeyInfo(BaseModel):
    """Information about an API key (without the actual key)"""
    id: str
    name: str
    description: Optional[str]
    prefix: str
    last_used_at: Optional[datetime]
    last_used_ip: Optional[str]
    usage_count: int
    expires_at: Optional[datetime]
    is_active: bool
    scopes: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token

    Supports two authentication methods:
    1. Admin users: Authenticated against database with bcrypt password
    2. Regular users: Authenticated against LDAP, then synced to database

    The returned JWT token is valid for 24 hours (configurable).
    """
    username = login_data.username.strip()
    password = login_data.password

    # Log authentication attempt (but never log passwords)
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Login attempt for user '{username}' from {client_ip}")

    # Try admin authentication first
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()

    if admin:
        logger.debug(f"Found admin user: {username}")

        # Verify admin password
        if not verify_password(password, admin.password_hash):
            logger.warning(f"Admin login failed: invalid password for {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if admin is active
        if not admin.is_active:
            logger.warning(f"Admin login failed: account disabled for {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Update last login
        admin.last_login = datetime.utcnow()
        db.commit()

        # Create JWT token
        token = create_token_for_user(
            admin,
            settings.jwt_secret_key,
            timedelta(minutes=settings.jwt_access_token_expire_minutes)
        )

        logger.info(f"Admin login successful: {username}")

        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user_type="admin"
        )

    # Try LDAP authentication for regular users
    try:
        logger.debug(f"Attempting LDAP authentication for: {username}")

        user = authenticate_and_sync_ldap_user(username, password, db)

        if not user:
            logger.warning(f"LDAP authentication failed for {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is enabled
        if not user.is_enabled:
            logger.warning(f"Login failed: user not enabled: {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is not enabled. Please contact an administrator.",
            )

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        # Create JWT token
        token = create_token_for_user(
            user,
            settings.jwt_secret_key,
            timedelta(minutes=settings.jwt_access_token_expire_minutes)
        )

        logger.info(f"LDAP user login successful: {username}")

        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user_type="user"
        )

    except LDAPInvalidCredentialsError:
        logger.warning(f"LDAP login failed: invalid credentials for {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except LDAPConnectionError as e:
        logger.error(f"LDAP connection error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again later.",
        )

    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during authentication",
        )


@router.post("/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
async def refresh_token(
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Refresh JWT token

    Requires a valid JWT token. Returns a new token with extended expiration.
    """
    # Create new token
    token = create_token_for_user(
        current_user,
        settings.jwt_secret_key,
        timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )

    user_type = "admin" if isinstance(current_user, AdminUser) else "user"

    logger.info(f"Token refreshed for {user_type} {current_user.id}")

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user_type=user_type
    )


@router.get("/auth/me", response_model=UserInfoResponse, tags=["Authentication"])
async def get_current_user_info(
    current_user: Union[User, AdminUser] = Depends(get_current_user),
):
    """
    Get current user information

    Returns information about the authenticated user.
    """
    is_admin = isinstance(current_user, AdminUser)

    return UserInfoResponse(
        id=str(current_user.id),
        user_type="admin" if is_admin else "user",
        username=getattr(current_user, 'username', None),
        email=current_user.email,
        full_name=getattr(current_user, 'full_name', None),
        role=current_user.role.value if hasattr(current_user, 'role') else None,
        is_enabled=current_user.is_active if is_admin else current_user.is_enabled,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.post("/users/me/api-keys", response_model=APIKeyResponse, tags=["API Keys"])
async def create_api_key(
    key_data: CreateAPIKeyRequest,
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the current user

    API keys are long-lived bearer tokens for programmatic API access.
    The key is only shown once - save it securely!
    """
    # Generate the API key
    raw_key = generate_api_key()
    key_prefix = raw_key[:8]  # "tnt_" + 4 chars
    key_hash = hash_api_key(raw_key)

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    # Create API key record
    is_admin = isinstance(current_user, AdminUser)

    api_key = APIKey(
        user_id=None if is_admin else current_user.id,
        admin_user_id=current_user.id if is_admin else None,
        name=key_data.name,
        description=key_data.description,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=expires_at,
        scopes=key_data.scopes,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    user_type = "admin" if is_admin else "user"
    logger.info(f"API key created for {user_type} {current_user.id}: {key_data.name}")

    return APIKeyResponse(
        api_key=raw_key,
        id=str(api_key.id),
        name=api_key.name,
        prefix=api_key.key_prefix,
        expires_at=api_key.expires_at,
        scopes=api_key.scopes,
    )


@router.get("/users/me/api-keys", response_model=List[APIKeyInfo], tags=["API Keys"])
async def list_api_keys(
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user

    Returns information about all API keys (but not the actual keys).
    """
    is_admin = isinstance(current_user, AdminUser)

    # Query API keys
    if is_admin:
        keys = db.query(APIKey).filter(APIKey.admin_user_id == current_user.id).all()
    else:
        keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()

    return [
        APIKeyInfo(
            id=str(key.id),
            name=key.name,
            description=key.description,
            prefix=key.key_prefix,
            last_used_at=key.last_used_at,
            last_used_ip=key.last_used_ip,
            usage_count=key.usage_count,
            expires_at=key.expires_at,
            is_active=key.is_active,
            scopes=key.scopes,
            created_at=key.created_at,
        )
        for key in keys
    ]


@router.delete("/users/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["API Keys"])
async def revoke_api_key(
    key_id: UUID,
    reason: Optional[str] = None,
    current_user: Union[User, AdminUser] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key

    The key will be immediately deactivated and cannot be used again.
    """
    is_admin = isinstance(current_user, AdminUser)

    # Find the key
    if is_admin:
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.admin_user_id == current_user.id
        ).first()
    else:
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Revoke the key
    api_key.revoke(current_user, reason)
    db.commit()

    user_type = "admin" if is_admin else "user"
    logger.info(f"API key revoked by {user_type} {current_user.id}: {api_key.name}")

    return None
