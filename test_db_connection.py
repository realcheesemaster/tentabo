#!/usr/bin/env python3
"""
Test PostgreSQL database connection for Tentabo PRM
"""
import psycopg2
from psycopg2 import sql
import sys

# Database configuration
DB_CONFIG = {
    'host': 'marshmallow02.oxileo.net',
    'database': 'tentabo_oxibox',
    'user': 'tentabo_oxibox',
    'password': 'CN1IdxkA^waY9tVdEivk%2Q&fpQWA4y!',
    'port': 5432  # Default PostgreSQL port
}

def test_connection():
    """Test the database connection and print basic info"""
    try:
        # Connect to the database
        print(f"Connecting to PostgreSQL at {DB_CONFIG['host']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Test the connection
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        print(f"✅ Successfully connected to PostgreSQL!")
        print(f"📊 Database version: {version}")

        # Check current database
        cursor.execute('SELECT current_database();')
        current_db = cursor.fetchone()[0]
        print(f"📁 Current database: {current_db}")

        # Check current user
        cursor.execute('SELECT current_user;')
        current_user = cursor.fetchone()[0]
        print(f"👤 Connected as: {current_user}")

        # List tables (if any exist)
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"\n📋 Existing tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print(f"\n📋 No tables found (empty database)")

        # Close connection
        cursor.close()
        conn.close()
        print("\n✅ Connection test successful!")
        return True

    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)