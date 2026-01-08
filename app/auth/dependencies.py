"""
FastAPI dependencies for authentication and authorization

Provides:
- get_current_user: Extract user from Bearer token (JWT or API key)
- require_admin: Ensure user has admin privileges
- require_role: Ensure user has specific role(s)
- get_optional_user: Optional authentication
"""

import logging
from typing import Optional, Union, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, AdminUser, UserRole
from app.auth.security import get_user_from_token, validate_api_key_from_db

logger = logging.getLogger(__name__)

# OAuth2 scheme for Bearer tokens
security = HTTPBearer(auto_error=True)


class AuthenticationError(HTTPException):
    """Authentication failed"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """User not authorized for this action"""
    def __init__(self, detail: str = "Not authorized to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Union[User, AdminUser]:
    """
    Extract and validate current user from Bearer token

    Supports both JWT tokens and API keys.
    - JWT tokens: Issued by /auth/login endpoint
    - API keys: Long-lived tokens with tnt_ prefix

    Args:
        request: FastAPI request object (for IP tracking)
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User or AdminUser object

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    token = credentials.credentials

    if not token:
        logger.warning("No token provided")
        raise AuthenticationError("No authentication token provided")

    # Check if it's an API key (starts with tnt_)
    if token.startswith("tnt_"):
        logger.debug("Authenticating with API key")

        # Extract client info for tracking
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        user = validate_api_key_from_db(
            token,
            db,
            update_usage=True,
            ip_address=client_ip,
            user_agent=user_agent
        )

        if not user:
            logger.warning("Invalid API key")
            raise AuthenticationError("Invalid or expired API key")

        logger.info(f"Authenticated via API key: {user.__tablename__} {user.id}")
        return user

    # Otherwise, treat as JWT token
    logger.debug("Authenticating with JWT token")

    # Import config here to avoid circular imports
    from app.core.config import get_settings
    settings = get_settings()

    user = get_user_from_token(token, settings.jwt_secret_key, db)

    if not user:
        logger.warning("Invalid JWT token")
        raise AuthenticationError("Invalid or expired token")

    logger.info(f"Authenticated via JWT: {user.__tablename__} {user.id}")
    return user


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[Union[User, AdminUser]]:
    """
    Extract user from token if present, but don't require authentication

    Useful for endpoints that behave differently based on auth status.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User/AdminUser if authenticated, None otherwise
    """
    auth_header = request.headers.get("authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")

    try:
        if token.startswith("tnt_"):
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            return validate_api_key_from_db(token, db, True, client_ip, user_agent)
        else:
            from app.core.config import get_settings
            settings = get_settings()
            return get_user_from_token(token, settings.jwt_secret_key, db)
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None


async def require_admin(
    current_user: Union[User, AdminUser] = Depends(get_current_user)
) -> Union[User, AdminUser]:
    """
    Require that the current user is an admin

    Can be either:
    - AdminUser (independent admin account)
    - User with ADMIN or RESTRICTED_ADMIN role

    Args:
        current_user: Current authenticated user

    Returns:
        User or AdminUser object

    Raises:
        AuthorizationError: If user is not an admin
    """
    # Check if it's an AdminUser
    if isinstance(current_user, AdminUser):
        return current_user

    # Check if it's a User with admin role
    if isinstance(current_user, User):
        if current_user.role in [UserRole.ADMIN, UserRole.RESTRICTED_ADMIN]:
            return current_user

    logger.warning(f"Authorization failed: user {current_user.id} is not an admin")
    raise AuthorizationError("Admin privileges required")


async def require_full_admin(
    current_user: Union[User, AdminUser] = Depends(get_current_user)
) -> Union[User, AdminUser]:
    """
    Require full admin privileges (not restricted admin)

    Can be either:
    - AdminUser
    - User with ADMIN role (not RESTRICTED_ADMIN)

    Args:
        current_user: Current authenticated user

    Returns:
        User or AdminUser object

    Raises:
        AuthorizationError: If user is not a full admin
    """
    if isinstance(current_user, AdminUser):
        return current_user

    if isinstance(current_user, User) and current_user.role == UserRole.ADMIN:
        return current_user

    logger.warning(f"Authorization failed: user {current_user.id} is not a full admin")
    raise AuthorizationError("Full admin privileges required")


def require_role(allowed_roles: List[UserRole]):
    """
    Create a dependency that requires specific role(s)

    Usage:
        @app.get("/contracts")
        async def get_contracts(
            user: User = Depends(require_role([UserRole.ADMIN, UserRole.FULFILLER]))
        ):
            ...

    Args:
        allowed_roles: List of roles that are allowed

    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: Union[User, AdminUser] = Depends(get_current_user)
    ) -> Union[User, AdminUser]:
        # AdminUsers bypass role checks
        if isinstance(current_user, AdminUser):
            return current_user

        # Check user role
        if isinstance(current_user, User):
            if current_user.role in allowed_roles:
                return current_user

        logger.warning(
            f"Authorization failed: user {current_user.id} role "
            f"{getattr(current_user, 'role', 'N/A')} not in {allowed_roles}"
        )
        raise AuthorizationError(
            f"This action requires one of the following roles: "
            f"{', '.join(role.value for role in allowed_roles)}"
        )

    return role_checker


async def require_enabled_user(
    current_user: Union[User, AdminUser] = Depends(get_current_user)
) -> Union[User, AdminUser]:
    """
    Ensure user is enabled/active

    This is already checked in get_current_user, but provided as
    explicit dependency for clarity.

    Args:
        current_user: Current authenticated user

    Returns:
        User or AdminUser object

    Raises:
        AuthorizationError: If user is disabled
    """
    if isinstance(current_user, AdminUser):
        if not current_user.is_active:
            raise AuthorizationError("Admin account is disabled")
    elif isinstance(current_user, User):
        if not current_user.is_enabled:
            raise AuthorizationError("User account is disabled")

    return current_user


async def require_self_or_admin(
    user_id: str,
    current_user: Union[User, AdminUser] = Depends(get_current_user)
) -> Union[User, AdminUser]:
    """
    Require that user is accessing their own data or is an admin

    Useful for endpoints like GET /users/{user_id} that should allow
    users to access their own data but require admin for others.

    Args:
        user_id: ID of user being accessed
        current_user: Current authenticated user

    Returns:
        User or AdminUser object

    Raises:
        AuthorizationError: If user is not accessing their own data and is not admin
    """
    # Admin can access anyone's data
    if isinstance(current_user, AdminUser):
        return current_user

    if isinstance(current_user, User):
        if current_user.is_admin or str(current_user.id) == user_id:
            return current_user

    logger.warning(
        f"Authorization failed: user {current_user.id} "
        f"attempted to access user {user_id}'s data"
    )
    raise AuthorizationError("You can only access your own data")
