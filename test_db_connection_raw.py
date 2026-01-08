#!/usr/bin/env python3
"""
Test PostgreSQL database connection with different password handling
"""
import psycopg2
import sys

# Try raw password string
password = r'CN1IdxkA^waY9tVdEivk%2Q&fpQWA4y!'

def test_connection(password_to_try, description):
    """Test the database connection with a specific password format"""
    try:
        print(f"\n🔍 Testing with {description}...")
        conn = psycopg2.connect(
            host='marshmallow02.oxileo.net',
            database='tentabo_oxibox',
            user='tentabo_oxibox',
            password=password_to_try,
            port=5432
        )
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        print(f"✅ Success! Connected with {description}")
        print(f"📊 Database version: {version}")
        cursor.close()
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        print(f"❌ Failed with {description}")
        print(f"   Error: {str(e).split('FATAL:')[1] if 'FATAL:' in str(e) else str(e)}")
        return False

print("Testing PostgreSQL connection with different password formats...")
print("=" * 60)

# Test different password formats
passwords_to_try = [
    (r'CN1IdxkA^waY9tVdEivk%2Q&fpQWA4y!', "raw string (r-string)"),
    ('CN1IdxkA^waY9tVdEivk%2Q&fpQWA4y!', "normal string"),
    ('CN1IdxkA^waY9tVdEivk%%2Q&fpQWA4y!', "double percent"),
    ('CN1IdxkA\^waY9tVdEivk%2Q\&fpQWA4y\!', "escaped special chars"),
]

success = False
for pwd, desc in passwords_to_try:
    if test_connection(pwd, desc):
        success = True
        break

if not success:
    print("\n❌ All password formats failed.")
    print("\nPossible issues:")
    print("1. The password might be incorrect")
    print("2. The password might have been changed on the server")
    print("3. The user might not exist or be locked")
    print("\nPlease verify the credentials with your database administrator.")

sys.exit(0 if success else 1)