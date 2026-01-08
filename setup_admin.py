#!/usr/bin/env python3
"""
Admin Account Setup Script for Tentabo PRM

This script creates or updates the admin account in the database.
The admin account provides independent authentication that works even
if LDAP is unavailable.

Usage:
    python setup_admin.py                    # Interactive mode
    python setup_admin.py --username admin --email admin@example.com --password secret
"""

import sys
import getpass
import argparse
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.auth import AdminUser
from app.auth.security import hash_password
from app.core.config import get_settings


def get_admin_by_username(db: Session, username: str) -> AdminUser:
    """Find admin user by username"""
    return db.query(AdminUser).filter(AdminUser.username == username).first()


def get_admin_by_email(db: Session, email: str) -> AdminUser:
    """Find admin user by email"""
    return db.query(AdminUser).filter(AdminUser.email == email).first()


def create_admin_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    full_name: str = None
) -> AdminUser:
    """
    Create a new admin user

    Args:
        db: Database session
        username: Username for admin
        email: Email address
        password: Plain text password (will be hashed)
        full_name: Optional full name

    Returns:
        Created AdminUser instance
    """
    # Check if username exists
    existing = get_admin_by_username(db, username)
    if existing:
        raise ValueError(f"Admin user with username '{username}' already exists")

    # Check if email exists
    existing = get_admin_by_email(db, email)
    if existing:
        raise ValueError(f"Admin user with email '{email}' already exists")

    # Hash password
    password_hash = hash_password(password)

    # Create admin user
    admin = AdminUser(
        username=username,
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


def update_admin_password(db: Session, username: str, new_password: str):
    """
    Update admin user password

    Args:
        db: Database session
        username: Username of admin to update
        new_password: New plain text password (will be hashed)
    """
    admin = get_admin_by_username(db, username)

    if not admin:
        raise ValueError(f"Admin user '{username}' not found")

    # Hash new password
    admin.password_hash = hash_password(new_password)
    admin.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(admin)

    return admin


def interactive_setup():
    """
    Interactive admin setup
    """
    print("=" * 60)
    print("Tentabo PRM - Admin Account Setup")
    print("=" * 60)
    print()

    settings = get_settings()

    # Get username
    default_username = settings.default_admin_username
    username = input(f"Admin username [{default_username}]: ").strip()
    if not username:
        username = default_username

    # Check if admin exists
    db = SessionLocal()
    existing_admin = get_admin_by_username(db, username)

    if existing_admin:
        print(f"\nAdmin user '{username}' already exists.")
        update = input("Do you want to update the password? (yes/no): ").strip().lower()

        if update in ['yes', 'y']:
            password = getpass.getpass("New password: ")
            password_confirm = getpass.getpass("Confirm password: ")

            if password != password_confirm:
                print("ERROR: Passwords do not match")
                db.close()
                sys.exit(1)

            if len(password) < 8:
                print("ERROR: Password must be at least 8 characters")
                db.close()
                sys.exit(1)

            try:
                update_admin_password(db, username, password)
                print(f"\nSUCCESS: Password updated for admin '{username}'")
                db.close()
                sys.exit(0)
            except Exception as e:
                print(f"ERROR: {e}")
                db.close()
                sys.exit(1)
        else:
            print("Cancelled.")
            db.close()
            sys.exit(0)

    # Create new admin
    print(f"\nCreating new admin user: {username}")

    # Get email
    default_email = settings.default_admin_email
    email = input(f"Email address [{default_email}]: ").strip()
    if not email:
        email = default_email

    # Validate email
    if "@" not in email:
        print("ERROR: Invalid email address")
        db.close()
        sys.exit(1)

    # Get full name (optional)
    full_name = input("Full name (optional): ").strip() or None

    # Get password
    password = getpass.getpass("Password (min 8 characters): ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        print("ERROR: Passwords do not match")
        db.close()
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters")
        db.close()
        sys.exit(1)

    # Create admin
    try:
        admin = create_admin_user(db, username, email, password, full_name)
        print(f"\nSUCCESS: Admin user created!")
        print(f"  ID: {admin.id}")
        print(f"  Username: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  Full name: {admin.full_name or 'N/A'}")
        print()
        print("You can now log in with these credentials.")

    except Exception as e:
        print(f"ERROR: {e}")
        db.close()
        sys.exit(1)

    db.close()


def non_interactive_setup(args):
    """
    Non-interactive admin setup from command-line arguments
    """
    # For updates, only username and password are required
    if args.update:
        if not args.username or not args.password:
            print("ERROR: --username and --password are required for update")
            sys.exit(1)
    else:
        if not args.username or not args.email or not args.password:
            print("ERROR: --username, --email, and --password are required in non-interactive mode")
            sys.exit(1)

    if len(args.password) < 8:
        print("ERROR: Password must be at least 8 characters")
        sys.exit(1)

    db = SessionLocal()

    try:
        # Check if admin exists
        existing_admin = get_admin_by_username(db, args.username)

        if existing_admin:
            if args.update:
                update_admin_password(db, args.username, args.password)
                print(f"SUCCESS: Password updated for admin '{args.username}'")
            else:
                print(f"ERROR: Admin user '{args.username}' already exists. Use --update to update password.")
                sys.exit(1)
        else:
            # Create new admin
            admin = create_admin_user(
                db,
                args.username,
                args.email,
                args.password,
                args.full_name
            )
            print(f"SUCCESS: Admin user '{admin.username}' created (ID: {admin.id})")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Create or update Tentabo PRM admin account"
    )
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--password", help="Admin password (min 8 characters)")
    parser.add_argument("--full-name", help="Admin full name (optional)")
    parser.add_argument("--update", action="store_true", help="Update existing admin password")

    args = parser.parse_args()

    # Check if any arguments provided
    if args.username or args.email or args.password:
        # Non-interactive mode
        non_interactive_setup(args)
    else:
        # Interactive mode
        interactive_setup()


if __name__ == "__main__":
    main()
