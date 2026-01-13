#!/usr/bin/env python3
"""
Initialize the Tentabo PRM database tables.

This script creates all database tables defined in the SQLAlchemy models.
Run this script once after setting up a new database.

Usage:
    python init_db.py

Prerequisites:
    - PostgreSQL database "tentabo" must exist
    - Database credentials must be configured via environment variables or .env file
"""

import sys


def main():
    """Create all database tables."""
    print("Initializing Tentabo PRM database...")
    print()

    # Check database connection first
    from app.database import check_database_connection, DATABASE_URL

    # Mask password in URL for display
    display_url = DATABASE_URL
    if "@" in display_url:
        # Mask the password part
        prefix, rest = display_url.split("://", 1)
        if "@" in rest:
            user_pass, host_rest = rest.split("@", 1)
            if ":" in user_pass:
                user, _ = user_pass.split(":", 1)
                display_url = f"{prefix}://{user}:****@{host_rest}"

    print(f"Database URL: {display_url}")
    print()

    # Test connection
    print("Testing database connection...")
    import asyncio
    connected = asyncio.run(check_database_connection())

    if not connected:
        print("ERROR: Could not connect to database.")
        print("Please check your database configuration and ensure PostgreSQL is running.")
        sys.exit(1)

    print("Database connection successful.")
    print()

    # Create tables
    print("Creating database tables...")
    from app.database import create_all_tables

    try:
        create_all_tables()
        print()
        print("SUCCESS: All tables created successfully!")
        print()
        print("Tables created:")
        print("  - admin_users")
        print("  - users")
        print("  - api_keys")
        print("  - product_types")
        print("  - products")
        print("  - price_tiers")
        print("  - durations")
        print("  - partners")
        print("  - distributors")
        print("  - distributor_partners")
        print("  - leads")
        print("  - lead_activities")
        print("  - lead_notes")
        print("  - lead_status_history")
        print("  - orders")
        print("  - order_items")
        print("  - contracts")
        print("  - notes")
        print("  - provider_configs")
        print("  - provider_sync_logs")
        print("  - audit_logs")
        print("  - webhook_events")
        print()
        print("You can now run setup_admin.py to create your first admin user.")
    except Exception as e:
        print(f"ERROR: Failed to create tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
