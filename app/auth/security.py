"""
Core security functions for Tentabo PRM authentication system

This module provides:
- Password hashing and verification with bcrypt
- JWT token creation and validation
- API key generation and validation
- Constant-time token comparison for timing attack prevention
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import hmac

from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.models.auth import User, AdminUser
from app.models.api_key import APIKey

# Configure logging - NEVER log passwords or tokens
logger = logging.getLogger(__name__)

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash of the password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash using constant-time comparison

    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash to check against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


def create_access_token(
    data: Dict[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
    algorithm: str = "HS256"
) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in the token (user_id, username, etc.)
        secret_key: Secret key for signing the token
        expires_delta: Time until token expires (default: 24 hours)
        algorithm: JWT algorithm (default: HS256)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta is None:
        expires_delta = timedelta(hours=24)

    expire = datetime.utcnow() + expires_delta
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256"
) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token to decode
        secret_key: Secret key used to sign the token
        algorithm: JWT algorithm (default: HS256)

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])

        # Verify token type
        if payload.get("type") != "access":
            logger.warning("Invalid token type")
            return None

        return payload

    except JWTError as e:
        logger.warning(f"Token validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key

    Format: tnt_<43 random URL-safe characters>
    Total length: ~47 characters

    Returns:
        API key string with tnt_ prefix
    """
    # Generate 32 bytes (256 bits) of random data
    # This gives us ~43 characters in base64url encoding
    random_part = secrets.token_urlsafe(32)
    return f"tnt_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage

    Args:
        api_key: Plain API key to hash

    Returns:
        Bcrypt hash of the API key
    """
    return pwd_context.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash using constant-time comparison

    Args:
        plain_key: Plain API key to verify
        hashed_key: Bcrypt hash to check against

    Returns:
        True if key matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_key, hashed_key)
    except Exception as e:
        logger.warning(f"API key verification failed: {e}")
        return False


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal, False otherwise
    """
    return hmac.compare_digest(a.encode(), b.encode())


def validate_api_key_from_db(
    token: str,
    db: Session,
    update_usage: bool = True,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[Union[User, AdminUser]]:
    """
    Validate an API key against the database

    This function:
    1. Extracts the key prefix for quick lookup
    2. Queries potential matching keys from database
    3. Uses constant-time comparison to check hashes
    4. Validates expiration and active status
    5. Updates usage tracking if requested

    Args:
        token: The API key to validate (full key, not just prefix)
        db: Database session
        update_usage: Whether to update last_used fields
        ip_address: Client IP address for tracking
        user_agent: Client user agent for tracking

    Returns:
        User or AdminUser object if valid, None otherwise
    """
    # Extract prefix for database lookup (e.g., "tnt_xxxx")
    if not token.startswith("tnt_"):
        logger.warning("Invalid API key format")
        return None

    # Get prefix (first 8 characters: "tnt_" + 4 random chars)
    prefix = token[:8] if len(token) >= 8 else token

    # Query database for potential matches
    try:
        potential_keys = db.query(APIKey).filter(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True
        ).all()

        if not potential_keys:
            logger.info("No active API keys found with matching prefix")
            return None

        # Check each potential key using constant-time comparison
        for api_key in potential_keys:
            if verify_api_key(token, api_key.key_hash):
                # Check expiration
                if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                    logger.info(f"API key {api_key.id} has expired")
                    return None

                # Update usage tracking
                if update_usage:
                    api_key.record_usage(ip_address, user_agent)
                    db.commit()

                # Return the owner (User or AdminUser)
                owner = api_key.user or api_key.admin_user

                if not owner:
                    logger.error(f"API key {api_key.id} has no owner")
                    return None

                # For users, check if they're enabled
                if isinstance(owner, User) and not owner.is_enabled:
                    logger.warning(f"User {owner.id} is disabled")
                    return None

                # For admin users, check if they're active
                if isinstance(owner, AdminUser) and not owner.is_active:
                    logger.warning(f"Admin {owner.id} is inactive")
                    return None

                logger.info(f"API key validated for {owner.__tablename__} {owner.id}")
                return owner

        logger.info("No matching API key hash found")
        return None

    except Exception as e:
        logger.error(f"Database error validating API key: {e}")
        return None


def create_token_for_user(
    user: Union[User, AdminUser],
    secret_key: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT token for a user or admin

    Args:
        user: User or AdminUser instance
        secret_key: JWT secret key
        expires_delta: Token expiration time

    Returns:
        JWT token string
    """
    # Determine user type
    is_admin = isinstance(user, AdminUser)

    token_data = {
        "sub": str(user.id),
        "user_type": "admin" if is_admin else "user",
        "username": user.username if hasattr(user, 'username') else user.email,
    }

    # Add role for regular users
    if not is_admin and hasattr(user, 'role'):
        token_data["role"] = user.role.value

    return create_access_token(token_data, secret_key, expires_delta)


def get_user_from_token(
    token: str,
    secret_key: str,
    db: Session
) -> Optional[Union[User, AdminUser]]:
    """
    Extract and validate user from JWT token

    Args:
        token: JWT token
        secret_key: JWT secret key
        db: Database session

    Returns:
        User or AdminUser if valid, None otherwise
    """
    payload = decode_access_token(token, secret_key)

    if not payload:
        return None

    user_id = payload.get("sub")
    user_type = payload.get("user_type")

    if not user_id or not user_type:
        logger.warning("Token missing required fields")
        return None

    try:
        if user_type == "admin":
            user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
            if user and not user.is_active:
                logger.warning(f"Admin user {user_id} is inactive")
                return None
        else:
            user = db.query(User).filter(User.id == user_id).first()
            if user and not user.is_enabled:
                logger.warning(f"User {user_id} is disabled")
                return None

        return user

    except Exception as e:
        logger.error(f"Database error retrieving user: {e}")
        return None
