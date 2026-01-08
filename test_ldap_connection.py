#!/usr/bin/env python3
"""
Test LDAP connection to Oxiadmin
"""
from ldap3 import Server, Connection, ALL, SUBTREE
import sys
import ssl

# LDAP Configuration
LDAP_SERVER = "auth.fr.oxileo.net"
LDAP_PORT = 6366
LDAP_USE_SSL = True
BIND_DN = "cn=view,dc=oxileo,dc=net"
BIND_PASSWORD = "QsL7OWWfWHcuMqfjcOLYwgBjX0V6gE"
BASE_DN = "dc=oxileo,dc=net"

def test_ldap_connection():
    """Test LDAP connection and explore schema"""
    try:
        print(f"🔐 Connecting to LDAP server...")
        print(f"   Server: ldaps://{LDAP_SERVER}:{LDAP_PORT}")
        print(f"   Bind DN: {BIND_DN}")
        print("=" * 60)

        # Create server object with SSL
        server = Server(
            LDAP_SERVER,
            port=LDAP_PORT,
            use_ssl=True,
            get_info=ALL,
            connect_timeout=10
        )

        # Create connection
        conn = Connection(
            server,
            user=BIND_DN,
            password=BIND_PASSWORD,
            auto_bind=True,
            raise_exceptions=True
        )

        print(f"✅ Successfully connected to LDAP!")
        print(f"   Connection: {conn}")
        print(f"   Bound as: {conn.extend.standard.who_am_i()}")

        # Get server info
        print(f"\n📊 LDAP Server Info:")
        print(f"   Server: {server.host}")
        print(f"   SSL: {LDAP_USE_SSL}")

        # Search for base structure
        print(f"\n🔍 Exploring LDAP structure...")

        # Search for organizational units
        print("\n📁 Organizational Units:")
        conn.search(
            search_base=BASE_DN,
            search_filter='(objectClass=organizationalUnit)',
            search_scope=SUBTREE,
            attributes=['ou', 'description'],
            size_limit=10
        )

        for entry in conn.entries[:5]:  # Show first 5
            print(f"   - {entry.entry_dn}")

        # Search for user objects
        print("\n👥 Sample Users:")
        conn.search(
            search_base=BASE_DN,
            search_filter='(objectClass=inetOrgPerson)',
            search_scope=SUBTREE,
            attributes=['cn', 'uid', 'mail', 'sn', 'givenName'],
            size_limit=5
        )

        for entry in conn.entries:
            print(f"   - DN: {entry.entry_dn}")
            if hasattr(entry, 'uid'):
                print(f"     UID: {entry.uid}")
            if hasattr(entry, 'mail'):
                print(f"     Mail: {entry.mail}")
            if hasattr(entry, 'cn'):
                print(f"     CN: {entry.cn}")
            if hasattr(entry, 'sn'):
                print(f"     Surname: {entry.sn}")

        # Search for groups
        print("\n👥 Sample Groups:")
        conn.search(
            search_base=BASE_DN,
            search_filter='(|(objectClass=groupOfNames)(objectClass=posixGroup))',
            search_scope=SUBTREE,
            attributes=['cn', 'description', 'member', 'gidNumber'],
            size_limit=10
        )

        for entry in conn.entries:
            print(f"   - {entry.entry_dn}")
            if hasattr(entry, 'description'):
                print(f"     Description: {entry.description}")

        # Get schema information
        print("\n📋 User Schema Attributes:")
        conn.search(
            search_base=BASE_DN,
            search_filter='(objectClass=inetOrgPerson)',
            search_scope=SUBTREE,
            attributes=['*'],
            size_limit=1
        )

        if conn.entries:
            user = conn.entries[0]
            print(f"   Available attributes for users:")
            for attr in user.entry_attributes:
                print(f"     - {attr}")

        # Test user authentication simulation
        print("\n🔐 Authentication Test:")
        print("   Note: Using 'view' account - read-only access")
        print("   For actual auth, would bind as specific user")

        conn.unbind()
        print("\n✅ LDAP connection test successful!")
        print("\n📝 Next steps:")
        print("   1. Map LDAP attributes to Tentabo user model")
        print("   2. Identify groups for role mapping")
        print("   3. Set up user authentication flow")

        return True

    except Exception as e:
        print(f"❌ LDAP connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ldap_connection()
    sys.exit(0 if success else 1)