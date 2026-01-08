"""
LDAP Configuration for Tentabo PRM (Oxiadmin)
"""
import os
from ldap3 import Server, Connection, ALL, SUBTREE

# LDAP Configuration
LDAP_SERVER = os.getenv('LDAP_SERVER', 'auth.fr.oxileo.net')
LDAP_PORT = int(os.getenv('LDAP_PORT', '6366'))
LDAP_USE_SSL = os.getenv('LDAP_USE_SSL', 'true').lower() == 'true'

# Bind credentials for service account
LDAP_BIND_DN = os.getenv('LDAP_BIND_DN', 'cn=view,dc=oxileo,dc=net')
LDAP_BIND_PASSWORD = os.getenv('LDAP_BIND_PASSWORD', 'QsL7OWWfWHcuMqfjcOLYwgBjX0V6gE')

# Base DN for searches
LDAP_BASE_DN = os.getenv('LDAP_BASE_DN', 'dc=oxileo,dc=net')

# User search configuration
LDAP_USER_SEARCH_BASE = os.getenv('LDAP_USER_SEARCH_BASE', 'dc=oxileo,dc=net')
LDAP_USER_OBJECT_CLASS = os.getenv('LDAP_USER_OBJECT_CLASS', 'inetOrgPerson')
LDAP_USER_ID_ATTRIBUTE = os.getenv('LDAP_USER_ID_ATTRIBUTE', 'uid')
LDAP_USER_EMAIL_ATTRIBUTE = os.getenv('LDAP_USER_EMAIL_ATTRIBUTE', 'mail')

# Group configuration for roles
LDAP_GROUP_SEARCH_BASE = os.getenv('LDAP_GROUP_SEARCH_BASE', 'dc=oxileo,dc=net')
LDAP_GROUP_OBJECT_CLASS = os.getenv('LDAP_GROUP_OBJECT_CLASS', 'groupOfNames')

# Role mapping from LDAP groups to Tentabo roles
LDAP_ROLE_MAPPING = {
    'cn=tentabo-admin,ou=groups,dc=oxileo,dc=net': 'admin',
    'cn=tentabo-restricted-admin,ou=groups,dc=oxileo,dc=net': 'restricted_admin',
    'cn=tentabo-partner,ou=groups,dc=oxileo,dc=net': 'partner',
    'cn=tentabo-distributor,ou=groups,dc=oxileo,dc=net': 'distributor',
    'cn=tentabo-fulfiller,ou=groups,dc=oxileo,dc=net': 'fulfiller',
}

def get_ldap_connection():
    """
    Create and return an LDAP connection
    """
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

    return conn

def authenticate_user(username: str, password: str):
    """
    Authenticate a user against LDAP
    """
    try:
        conn = get_ldap_connection()

        # Search for user
        search_filter = f"(&(objectClass={LDAP_USER_OBJECT_CLASS})({LDAP_USER_ID_ATTRIBUTE}={username}))"
        conn.search(
            search_base=LDAP_USER_SEARCH_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['*']
        )

        if not conn.entries:
            return None

        user_dn = conn.entries[0].entry_dn
        user_data = conn.entries[0]

        # Try to bind as the user to verify password
        user_conn = Connection(
            conn.server,
            user=user_dn,
            password=password,
            auto_bind=True,
            raise_exceptions=False
        )

        if not user_conn.bind():
            return None

        user_conn.unbind()
        conn.unbind()

        # Return user data
        return {
            'dn': user_dn,
            'username': username,
            'email': str(user_data.mail) if hasattr(user_data, 'mail') else None,
            'cn': str(user_data.cn) if hasattr(user_data, 'cn') else None,
            'groups': user_data.memberOf if hasattr(user_data, 'memberOf') else []
        }

    except Exception as e:
        print(f"LDAP authentication error: {e}")
        return None

def get_user_role(user_groups):
    """
    Map LDAP groups to Tentabo role
    """
    for group_dn, role in LDAP_ROLE_MAPPING.items():
        if group_dn in user_groups:
            return role
    return 'guest'  # Default role if no mapping found