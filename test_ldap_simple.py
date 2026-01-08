#!/usr/bin/env python3
"""
Simple LDAP connection test with different configurations
"""
from ldap3 import Server, Connection, ALL, SIMPLE
import ssl

configs = [
    {
        "name": "With SSL/TLS (ldaps)",
        "server": "auth.fr.oxileo.net",
        "port": 6366,
        "use_ssl": True,
        "bind_dn": "cn=view,dc=oxileo,dc=net",
    },
    {
        "name": "Try with full DN path",
        "server": "auth.fr.oxileo.net",
        "port": 6366,
        "use_ssl": True,
        "bind_dn": "uid=view,cn=users,dc=oxileo,dc=net",
    },
    {
        "name": "Without SSL (if port allows)",
        "server": "auth.fr.oxileo.net",
        "port": 6366,
        "use_ssl": False,
        "bind_dn": "cn=view,dc=oxileo,dc=net",
    }
]

password = "REF8Jz5b5QaYbfFtc2W6qky8"

for config in configs:
    print(f"\n🔍 Testing: {config['name']}")
    print(f"   Server: {config['server']}:{config['port']}")
    print(f"   Bind DN: {config['bind_dn']}")
    print(f"   SSL: {config['use_ssl']}")

    try:
        server = Server(
            config['server'],
            port=config['port'],
            use_ssl=config['use_ssl'],
            get_info=ALL
        )

        conn = Connection(
            server,
            user=config['bind_dn'],
            password=password,
            authentication=SIMPLE,
            raise_exceptions=False
        )

        if conn.bind():
            print(f"   ✅ SUCCESS! Connected with this configuration")
            print(f"   Result: {conn.result}")

            # Try a simple search
            conn.search('dc=oxileo,dc=net', '(objectClass=*)', size_limit=1)
            print(f"   Search test: {'✅ OK' if conn.result['result'] == 0 else '❌ Failed'}")

            conn.unbind()
            print(f"\n🎯 Working configuration found!")
            break
        else:
            print(f"   ❌ Failed: {conn.result}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("If all failed, possible issues:")
print("1. The bind DN format might be different")
print("2. The password might need to be changed")
print("3. The 'view' account might not exist or be disabled")
print("4. Try standard LDAP port 636 for LDAPS or 389 for LDAP")