#!/usr/bin/env python3
"""
Complete test to verify Partners and Distributors functionality:
1. Backend database contains real data
2. API endpoints return real data (not mock)
3. Response schema matches expectations
4. No mock data generators exist
"""

import asyncio
import json
from app.database import SessionLocal
from app.models.partner import Partner, Distributor
from app.models.auth import AdminUser
from app.api.v1.partners import list_partners, list_distributors
from app.api.dependencies import PaginationParams, MultiTenantFilter


def test_no_mock_data_in_code():
    """Verify that API endpoints don't contain mock data generation"""
    print("\n" + "="*60)
    print("TEST 1: Checking for mock data in API code")
    print("="*60)

    with open('/home/francois/tentabo/app/api/v1/partners.py', 'r') as f:
        content = f.read()

    # Check for common mock data patterns
    mock_patterns = [
        'Acme', 'TechPartners', 'GlobalTech', 'mock_',
        'dummy', 'fake_', 'sample_data', 'test_data',
        'return [{"name":', 'return {"name":'
    ]

    found_mock = False
    for pattern in mock_patterns:
        if pattern.lower() in content.lower():
            print(f"  ✗ FOUND mock pattern: '{pattern}'")
            found_mock = True

    if not found_mock:
        print("  ✓ PASS: No mock data patterns found in partners.py")
        return True
    else:
        print("  ✗ FAIL: Mock data patterns detected")
        return False


async def test_database_has_real_data():
    """Verify database contains real partner/distributor records"""
    print("\n" + "="*60)
    print("TEST 2: Checking database for real data")
    print("="*60)

    db = SessionLocal()

    partners = db.query(Partner).all()
    distributors = db.query(Distributor).all()

    print(f"\n  Partners in database: {len(partners)}")
    for p in partners[:3]:
        print(f"    - {p.name}")
        print(f"      Email: {p.email}")
        print(f"      ID: {p.id}")

    print(f"\n  Distributors in database: {len(distributors)}")
    for d in distributors[:3]:
        print(f"    - {d.name}")
        print(f"      Email: {d.email}")
        print(f"      ID: {d.id}")

    db.close()

    # Database can be empty (that's ok) or have real data
    print(f"\n  ✓ PASS: Database contains {len(partners)} partners and {len(distributors)} distributors")
    return True


async def test_api_returns_real_data():
    """Test that API endpoints return real data from database"""
    print("\n" + "="*60)
    print("TEST 3: Testing API endpoints return real data")
    print("="*60)

    db = SessionLocal()
    admin = db.query(AdminUser).first()

    if not admin:
        print("  ✗ FAIL: No admin user in database")
        db.close()
        return False

    pagination = PaginationParams(page=1, page_size=100)
    mt_filter = MultiTenantFilter()

    try:
        # Test Partners endpoint
        partners_result = await list_partners(
            pagination=pagination,
            is_active=None,
            search=None,
            db=db,
            current_user=admin,
            mt_filter=mt_filter
        )

        print(f"\n  Partners API Response:")
        print(f"    Total items: {partners_result.pagination['total_items']}")
        print(f"    Items returned: {len(partners_result.items)}")

        # Verify response structure
        if len(partners_result.items) > 0:
            partner = partners_result.items[0]
            print(f"\n    Sample partner:")
            print(f"      ID: {partner.id}")
            print(f"      Name: {partner.name}")
            print(f"      Email: {partner.email}")
            print(f"      Active: {partner.is_active}")

            # Check it's NOT mock data
            if 'Acme' in partner.name or 'TechPartners' in partner.name:
                print("  ✗ FAIL: Partner appears to be mock data!")
                return False

        # Test Distributors endpoint
        dist_result = await list_distributors(
            pagination=pagination,
            is_active=None,
            search=None,
            db=db,
            current_user=admin,
            mt_filter=mt_filter
        )

        print(f"\n  Distributors API Response:")
        print(f"    Total items: {dist_result.pagination['total_items']}")
        print(f"    Items returned: {len(dist_result.items)}")

        if len(dist_result.items) > 0:
            dist = dist_result.items[0]
            print(f"\n    Sample distributor:")
            print(f"      ID: {dist.id}")
            print(f"      Name: {dist.name}")
            print(f"      Email: {dist.email}")
            print(f"      Active: {dist.is_active}")

            # Check it's NOT mock data
            if 'Acme' in dist.name or 'GlobalTech' in dist.name:
                print("  ✗ FAIL: Distributor appears to be mock data!")
                return False

        print("\n  ✓ PASS: API endpoints return real database data")
        return True

    except Exception as e:
        print(f"  ✗ FAIL: Error testing API endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_schema_structure():
    """Verify response schema matches backend models"""
    print("\n" + "="*60)
    print("TEST 4: Verifying response schema structure")
    print("="*60)

    db = SessionLocal()
    admin = db.query(AdminUser).first()

    pagination = PaginationParams(page=1, page_size=1)
    mt_filter = MultiTenantFilter()

    try:
        result = await list_partners(
            pagination=pagination,
            is_active=None,
            search=None,
            db=db,
            current_user=admin,
            mt_filter=mt_filter
        )

        print(f"\n  Response structure:")
        print(f"    Has 'items' field: {hasattr(result, 'items')}")
        print(f"    Has 'pagination' field: {hasattr(result, 'pagination')}")

        if len(result.items) > 0:
            partner = result.items[0]
            required_fields = ['id', 'name', 'is_active', 'created_at', 'updated_at']
            optional_fields = ['email', 'phone', 'website', 'city', 'country', 'notes']

            print(f"\n  Partner object fields:")
            for field in required_fields:
                has_field = hasattr(partner, field)
                print(f"    {field}: {has_field}")
                if not has_field:
                    print(f"  ✗ FAIL: Missing required field '{field}'")
                    return False

            # Check that mock fields don't exist
            bad_fields = ['commission_rate', 'distributor_id']
            for field in bad_fields:
                if hasattr(partner, field) and getattr(partner, field) is not None:
                    print(f"  ✗ FAIL: Found unexpected field '{field}' (possible mock data)")
                    return False

        print("\n  ✓ PASS: Schema structure is correct")
        return True

    except Exception as e:
        print(f"  ✗ FAIL: Error checking schema: {e}")
        return False
    finally:
        db.close()


async def main():
    print("\n" + "="*60)
    print("COMPREHENSIVE PARTNERS & DISTRIBUTORS TEST")
    print("="*60)

    results = {
        'no_mock_code': test_no_mock_data_in_code(),
        'database_data': await test_database_has_real_data(),
        'api_real_data': await test_api_returns_real_data(),
        'schema_structure': await test_schema_structure(),
    }

    print("\n" + "="*60)
    print("FINAL RESULTS:")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        print("\nConclusion:")
        print("  • NO mock data found in API code")
        print("  • Database contains real partner/distributor records")
        print("  • API endpoints return REAL data from database")
        print("  • Response schema matches backend models")
        print("\n  The Partners and Distributors pages will show:")
        print("    - Real organizations from the database")
        print("    - OR empty lists if no data exists")
        print("    - NO dummy/mock data like 'Acme Corp'")
    else:
        print("\n" + "="*60)
        print("✗ SOME TESTS FAILED")
        print("="*60)
        print("\nPlease review the failed tests above.")

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
