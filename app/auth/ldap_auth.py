"""
LDAP Authentication Module for Tentabo PRM

Provides authentication against LDAP server and user data synchronization.
Handles connection failures gracefully and logs authentication attempts.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPSocketOpenError, LDAPInvalidCredentialsResult
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.system import AuditLog

# Import LDAP configuration
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from ldap_config import (
    LDAP_SERVER,
    LDAP_PORT,
    LDAP_USE_SSL,
    LDAP_BIND_DN,
    LDAP_BIND_PASSWORD,
    LDAP_USER_SEARCH_BASE,
    LDAP_USER_OBJECT_CLASS,
    LDAP_USER_ID_ATTRIBUTE,
    LDAP_USER_EMAIL_ATTRIBUTE,
)

logger = logging.getLogger(__name__)


def parse_ldap_email(entry, email_attribute: str) -> Optional[str]:
    """
    Parse email from LDAP entry, handling both single values and lists

    Args:
        entry: LDAP entry object
        email_attribute: Name of the email attribute

    Returns:
        First email address if available, None otherwise
    """
    if not hasattr(entry, email_attribute):
        return None

    email_attr = getattr(entry, email_attribute)
    if not email_attr:
        return None

    email_value = email_attr.value
    if isinstance(email_value, list) and len(email_value) > 0:
        return str(email_value[0])  # Take first email from list
    elif email_value:
        return str(email_value)

    return None


class LDAPAuthenticationError(Exception):
    """Base exception for LDAP authentication errors"""
    pass


class LDAPConnectionError(LDAPAuthenticationError):
    """LDAP server connection failed"""
    pass


class LDAPInvalidCredentialsError(LDAPAuthenticationError):
    """Invalid username or password"""
    pass


def get_ldap_connection() -> Optional[Connection]:
    """
    Create and return an LDAP connection using service account

    Returns:
        LDAP Connection object if successful, None if connection fails

    Raises:
        LDAPConnectionError: If unable to connect to LDAP server
    """
    try:
        server_uri = f"ldaps://{LDAP_SERVER}:{LDAP_PORT}" if LDAP_USE_SSL else f"ldap://{LDAP_SERVER}:{LDAP_PORT}"
        logger.info(f"Connecting to LDAP server: {server_uri}")

        server = Server(
            LDAP_SERVER,
            port=LDAP_PORT,
            use_ssl=LDAP_USE_SSL,
            get_info=ALL
        )

        conn = Connection(
            server,
            user=LDAP_BIND_DN,
            password=LDAP_BIND_PASSWORD,
            auto_bind=True,
            raise_exceptions=True
        )

        logger.info("LDAP connection established successfully")
        return conn

    except LDAPSocketOpenError as e:
        logger.error(f"Cannot connect to LDAP server: {e}")
        raise LDAPConnectionError(f"LDAP server unavailable: {LDAP_SERVER}:{LDAP_PORT}")

    except LDAPBindError as e:
        logger.error(f"LDAP bind failed with service account: {e}")
        raise LDAPConnectionError("LDAP service account authentication failed")

    except LDAPException as e:
        logger.error(f"LDAP error: {e}")
        raise LDAPConnectionError(f"LDAP error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error connecting to LDAP: {e}")
        raise LDAPConnectionError(f"Unexpected LDAP error: {str(e)}")


def search_ldap_user(username: str) -> Optional[Dict[str, Any]]:
    """
    Search for a user in LDAP directory

    Args:
        username: Username to search for

    Returns:
        Dictionary with user data if found, None otherwise

    Raises:
        LDAPConnectionError: If unable to connect or search
    """
    conn = None
    try:
        conn = get_ldap_connection()

        # Build search filter
        search_filter = f"(&(objectClass={LDAP_USER_OBJECT_CLASS})({LDAP_USER_ID_ATTRIBUTE}={username}))"

        logger.info(f"Searching for user: {username}")
        logger.debug(f"Search filter: {search_filter}")
        logger.debug(f"Search base: {LDAP_USER_SEARCH_BASE}")

        # Execute search
        success = conn.search(
            search_base=LDAP_USER_SEARCH_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['*']
        )

        if not success or not conn.entries:
            logger.info(f"User not found in LDAP: {username}")
            return None

        # Extract user data
        entry = conn.entries[0]
        user_dn = entry.entry_dn

        # Parse user attributes
        user_data = {
            'dn': user_dn,
            'username': username,
            'email': parse_ldap_email(entry, LDAP_USER_EMAIL_ATTRIBUTE),
            'full_name': str(entry.cn.value) if hasattr(entry, 'cn') else None,
            'first_name': str(entry.givenName.value) if hasattr(entry, 'givenName') else None,
            'last_name': str(entry.sn.value) if hasattr(entry, 'sn') else None,
            'groups': list(entry.memberOf.values) if hasattr(entry, 'memberOf') else [],
            'display_name': str(entry.displayName.value) if hasattr(entry, 'displayName') else None,
        }

        logger.info(f"User found in LDAP: {username} ({user_data.get('email')})")
        return user_data

    except LDAPConnectionError:
        raise

    except Exception as e:
        logger.error(f"Error searching LDAP user: {e}")
        raise LDAPConnectionError(f"LDAP search error: {str(e)}")

    finally:
        if conn:
            try:
                conn.unbind()
            except:
                pass


def authenticate_ldap_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user against LDAP

    This function:
    1. Searches for the user in LDAP
    2. Attempts to bind with the user's credentials
    3. Returns user data if authentication succeeds

    Args:
        username: Username to authenticate
        password: Password to verify

    Returns:
        Dictionary with user data if authentication succeeds, None otherwise

    Raises:
        LDAPConnectionError: If unable to connect to LDAP
        LDAPInvalidCredentialsError: If credentials are invalid
    """
    # SECURITY: Never log passwords
    logger.info(f"Attempting LDAP authentication for user: {username}")

    # First, search for the user to get their DN
    user_data = search_ldap_user(username)

    if not user_data:
        logger.warning(f"Authentication failed: user not found in LDAP: {username}")
        raise LDAPInvalidCredentialsError("Invalid username or password")

    user_dn = user_data['dn']

    # Now try to bind as the user to verify their password
    try:
        server = Server(
            LDAP_SERVER,
            port=LDAP_PORT,
            use_ssl=LDAP_USE_SSL,
            get_info=ALL
        )

        user_conn = Connection(
            server,
            user=user_dn,
            password=password,
            auto_bind=False,
            raise_exceptions=True
        )

        if not user_conn.bind():
            logger.warning(f"Authentication failed: invalid password for user: {username}")
            raise LDAPInvalidCredentialsError("Invalid username or password")

        logger.info(f"LDAP authentication successful for user: {username}")
        user_conn.unbind()

        return user_data

    except LDAPInvalidCredentialsResult as e:
        # LDAP error code 49 - invalid credentials
        logger.warning(f"Authentication failed: invalid credentials for user: {username}")
        raise LDAPInvalidCredentialsError("Invalid username or password")

    except LDAPBindError as e:
        # Check for invalid credentials in the error message as a fallback
        if "invalidCredentials" in str(e) or "49" in str(e):
            logger.warning(f"Authentication failed: invalid credentials for user: {username}")
            raise LDAPInvalidCredentialsError("Invalid username or password")
        else:
            logger.error(f"LDAP bind error: {e}")
            raise LDAPConnectionError(f"LDAP authentication error: {str(e)}")

    except LDAPException as e:
        # Check for invalid credentials in generic LDAP exceptions as well
        error_str = str(e)
        if "invalidCredentials" in error_str or "LDAPInvalidCredentialsResult" in error_str or " 49 " in error_str:
            logger.warning(f"Authentication failed: invalid credentials for user: {username}")
            raise LDAPInvalidCredentialsError("Invalid username or password")
        logger.error(f"LDAP error during authentication: {e}")
        raise LDAPConnectionError(f"LDAP error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error during LDAP authentication: {e}")
        raise LDAPConnectionError(f"Authentication error: {str(e)}")


def sync_ldap_user_to_db(
    ldap_data: Dict[str, Any],
    db: Session,
    default_role: UserRole = UserRole.PARTNER
) -> User:
    """
    Sync LDAP user data to database

    Creates a new user if they don't exist, or updates existing user data.
    Users are disabled by default and must be enabled by an admin.

    IMPORTANT: Does NOT store email or full_name in database - these are
    fetched from LDAP on-demand to avoid sync issues with multi-valued fields.

    Args:
        ldap_data: User data from LDAP
        db: Database session
        default_role: Default role for new users

    Returns:
        User object (from database)
    """
    username = ldap_data['username']

    # Look for existing user
    user = db.query(User).filter(
        User.provider == 'ldap',
        User.provider_id == username
    ).first()

    if user:
        # Update last login only - display data fetched from LDAP on-demand
        logger.info(f"Updating existing user: {username}")
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    # Create new user (disabled by default)
    logger.info(f"Creating new user from LDAP: {username}")

    # NOTE: email and full_name are NOT synced from LDAP to avoid issues with
    # multi-valued fields. They are fetched on-demand from LDAP.
    # We set placeholder values to satisfy NOT NULL constraints.
    new_user = User(
        provider='ldap',
        provider_id=username,
        username=username,
        email=f"{username}@ldap.placeholder",  # Placeholder - real email from LDAP
        full_name=None,  # Will be fetched from LDAP on-demand
        role=default_role,
        is_enabled=False,  # Must be enabled by admin
        last_login=datetime.utcnow(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Created new user: {username} (id: {new_user.id}, enabled: {new_user.is_enabled})")
    return new_user


def authenticate_and_sync_ldap_user(
    username: str,
    password: str,
    db: Session
) -> Optional[User]:
    """
    Authenticate user via LDAP and sync to database

    This is the main entry point for LDAP authentication.
    It combines authentication and database sync in one operation.

    Args:
        username: Username to authenticate
        password: Password to verify
        db: Database session

    Returns:
        User object if authentication succeeds and user is enabled, None otherwise

    Raises:
        LDAPConnectionError: If unable to connect to LDAP
        LDAPInvalidCredentialsError: If credentials are invalid
    """
    # Authenticate against LDAP
    ldap_data = authenticate_ldap_user(username, password)

    if not ldap_data:
        return None

    # Sync to database
    user = sync_ldap_user_to_db(ldap_data, db)

    # Check if user is enabled
    if not user.is_enabled:
        logger.warning(f"User authenticated but not enabled: {username}")
        return None

    logger.info(f"User authenticated and authorized: {username}")
    return user


def get_ldap_user_display_data(username: str) -> Optional[Dict[str, Any]]:
    """
    Fetch display data (email, full_name) for a single LDAP user on-demand

    Args:
        username: Username to fetch data for

    Returns:
        Dictionary with email and full_name if found, None otherwise
    """
    try:
        user_data = search_ldap_user(username)
        if not user_data:
            return None

        return {
            'email': user_data.get('email'),
            'full_name': user_data.get('full_name'),
        }
    except Exception as e:
        logger.error(f"Error fetching LDAP display data for {username}: {e}")
        return None


def get_ldap_users_display_data_batch(usernames: list[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch display data for multiple LDAP users efficiently in batch

    Args:
        usernames: List of usernames to fetch data for

    Returns:
        Dictionary mapping username to display data (email, full_name)
    """
    result = {}
    conn = None

    try:
        conn = get_ldap_connection()
        if not conn:
            logger.warning("Cannot connect to LDAP for batch fetch")
            return result

        # Build filter for multiple users
        if not usernames:
            return result

        # Create OR filter for all usernames
        if len(usernames) == 1:
            search_filter = f"(&(objectClass={LDAP_USER_OBJECT_CLASS})({LDAP_USER_ID_ATTRIBUTE}={usernames[0]}))"
        else:
            user_filters = ''.join([f"({LDAP_USER_ID_ATTRIBUTE}={u})" for u in usernames])
            search_filter = f"(&(objectClass={LDAP_USER_OBJECT_CLASS})(|{user_filters}))"

        logger.debug(f"Batch fetching LDAP data for {len(usernames)} users")

        # Execute batch search
        success = conn.search(
            search_base=LDAP_USER_SEARCH_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['*']
        )

        if success and conn.entries:
            for entry in conn.entries:
                username = str(getattr(entry, LDAP_USER_ID_ATTRIBUTE).value) if hasattr(entry, LDAP_USER_ID_ATTRIBUTE) else None
                if username:
                    result[username] = {
                        'email': parse_ldap_email(entry, LDAP_USER_EMAIL_ATTRIBUTE),
                        'full_name': str(entry.cn.value) if hasattr(entry, 'cn') else None,
                    }

        logger.debug(f"Successfully fetched LDAP data for {len(result)} users")

    except Exception as e:
        logger.error(f"Error in batch LDAP fetch: {e}")

    finally:
        if conn:
            try:
                conn.unbind()
            except:
                pass

    return result


def check_ldap_connection() -> bool:
    """
    Health check for LDAP connectivity

    Returns:
        True if LDAP server is accessible, False otherwise
    """
    try:
        conn = get_ldap_connection()
        if conn:
            conn.unbind()
            return True
        return False
    except Exception as e:
        logger.error(f"LDAP health check failed: {e}")
        return False
