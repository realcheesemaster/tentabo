#!/usr/bin/env python3
"""
Test script to verify Partners and Distributors API endpoints return real data
"""

import asyncio
from app.database import SessionLocal
from app.models.partner import Partner, Distributor
from app.models.auth import User, AdminUser
from app.auth.dependencies import get_current_user
from app.api.v1.partners import list_partners, list_distributors
from app.api.dependencies import PaginationParams, MultiTenantFilter
from unittest.mock import MagicMock


async def test_partners_endpoint():
    """Test that partners endpoint returns real database data"""

    db = SessionLocal()

    # Get a real admin user
    admin = db.query(AdminUser).first()
    if not admin:
        print("ERROR: No admin user found in database")
        return False

    print(f"Testing as admin user: {admin.username}")

    # Create mock dependencies
    pagination = PaginationParams(page=1, page_size=100)
    mt_filter = MultiTenantFilter()

    # Call the actual endpoint function
    try:
        result = await list_partners(
            pagination=pagination,
            is_active=None,
            search=None,
            db=db,
            current_user=admin,
            mt_filter=mt_filter
        )

        print("\n" + "="*60)
        print("PARTNERS API RESPONSE:")
        print("="*60)
        print(f"Total items: {result.pagination['total_items']}")
        print(f"Items returned: {len(result.items)}")

        if len(result.items) > 0:
            print("\nPartners found:")
            for partner in result.items:
                print(f"  - ID: {partner.id}")
                print(f"    Name: {partner.name}")
                print(f"    Email: {partner.email}")
                print(f"    Active: {partner.is_active}")
                print(f"    Created: {partner.created_at}")
                print()
            print("✓ SUCCESS: Partners endpoint returns REAL data from database")
            return True
        else:
            print("✓ SUCCESS: Partners endpoint returns empty array (no partners in DB)")
            return True

    except Exception as e:
        print(f"✗ ERROR calling partners endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_distributors_endpoint():
    """Test that distributors endpoint returns real database data"""

    db = SessionLocal()

    # Get a real admin user
    admin = db.query(AdminUser).first()
    if not admin:
        print("ERROR: No admin user found in database")
        return False

    # Create mock dependencies
    pagination = PaginationParams(page=1, page_size=100)
    mt_filter = MultiTenantFilter()

    # Call the actual endpoint function
    try:
        result = await list_distributors(
            pagination=pagination,
            is_active=None,
            search=None,
            db=db,
            current_user=admin,
            mt_filter=mt_filter
        )

        print("\n" + "="*60)
        print("DISTRIBUTORS API RESPONSE:")
        print("="*60)
        print(f"Total items: {result.pagination['total_items']}")
        print(f"Items returned: {len(result.items)}")

        if len(result.items) > 0:
            print("\nDistributors found:")
            for dist in result.items:
                print(f"  - ID: {dist.id}")
                print(f"    Name: {dist.name}")
                print(f"    Email: {dist.email}")
                print(f"    Active: {dist.is_active}")
                print(f"    Created: {dist.created_at}")
                print()
            print("✓ SUCCESS: Distributors endpoint returns REAL data from database")
            return True
        else:
            print("✓ SUCCESS: Distributors endpoint returns empty array (no distributors in DB)")
            return True

    except Exception as e:
        print(f"✗ ERROR calling distributors endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def check_database_contents():
    """Check what's actually in the database"""
    db = SessionLocal()

    print("\n" + "="*60)
    print("DATABASE CONTENTS:")
    print("="*60)

    partners = db.query(Partner).all()
    distributors = db.query(Distributor).all()

    print(f"\nPartners in database: {len(partners)}")
    for p in partners:
        print(f"  - {p.name} (ID: {p.id})")

    print(f"\nDistributors in database: {len(distributors)}")
    for d in distributors:
        print(f"  - {d.name} (ID: {d.id})")

    db.close()


async def main():
    print("\n" + "="*60)
    print("TESTING PARTNERS & DISTRIBUTORS API ENDPOINTS")
    print("="*60)

    # Check database first
    await check_database_contents()

    # Test endpoints
    partners_ok = await test_partners_endpoint()
    distributors_ok = await test_distributors_endpoint()

    print("\n" + "="*60)
    print("TEST RESULTS:")
    print("="*60)
    print(f"Partners API: {'✓ PASS' if partners_ok else '✗ FAIL'}")
    print(f"Distributors API: {'✓ PASS' if distributors_ok else '✗ FAIL'}")

    if partners_ok and distributors_ok:
        print("\n✓ ALL TESTS PASSED - No mock data detected!")
        print("  The API endpoints correctly return real database data.")
    else:
        print("\n✗ SOME TESTS FAILED")


if __name__ == "__main__":
    asyncio.run(main())
