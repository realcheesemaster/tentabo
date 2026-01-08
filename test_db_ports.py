#!/usr/bin/env python3
"""
Test PostgreSQL connection on different ports
"""
import socket
import sys

HOST = "marshmallow02.oxileo.net"
COMMON_PORTS = [5432, 5433, 5434, 15432, 25432, 35432]

def test_port(host, port, timeout=3):
    """Test if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.gaierror:
        return False
    except Exception as e:
        print(f"Error testing port {port}: {e}")
        return False

print(f"🔍 Testing PostgreSQL ports on {HOST}")
print("=" * 50)

# Resolve hostname to IP
try:
    ip = socket.gethostbyname(HOST)
    print(f"✅ Resolved {HOST} to {ip}")
except socket.gaierror as e:
    print(f"❌ Cannot resolve hostname: {e}")
    sys.exit(1)

print(f"\n📊 Testing common PostgreSQL ports:")
open_ports = []

for port in COMMON_PORTS:
    if test_port(HOST, port):
        print(f"  ✅ Port {port}: OPEN")
        open_ports.append(port)
    else:
        print(f"  ❌ Port {port}: CLOSED/FILTERED")

if open_ports:
    print(f"\n✅ Found {len(open_ports)} open port(s): {open_ports}")
    print("Try connecting with these ports instead.")
else:
    print("\n❌ No PostgreSQL ports appear to be open.")
    print("\nPossible issues:")
    print("1. PostgreSQL is not configured for remote connections")
    print("2. Firewall is blocking the connection")
    print("3. The server only accepts connections from specific IPs")
    print("4. PostgreSQL is running on a non-standard port")
    print("\nPlease check with your system administrator.")