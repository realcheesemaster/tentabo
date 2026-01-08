#!/usr/bin/env python3
"""
Test script to verify database schema and models
Tests database connectivity, table creation, and basic CRUD operations
"""
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError

from app.database import engine, SessionLocal, check_database_connection
from app.models import (
    AdminUser, User, UserRole,
    Product, PriceTier, Duration,
    Partner, Distributor, DistributorPartner,
    Lead, LeadStatus,
    Order, OrderStatus, OrderItem,
    Contract, ContractStatus,
    ProviderConfig, ProviderType,
    Note, AuditLog, WebhookEvent,
)


def test_database_connection():
    """Test database connectivity"""
    print("1. Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✓ Connected to PostgreSQL: {version[:50]}...")
            return True
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return False


def test_tables_exist():
    """Verify all tables were created"""
    print("\n2. Verifying tables exist...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = [
        'admin_users', 'users', 'products', 'price_tiers', 'durations',
        'partners', 'distributors', 'distributor_partners',
        'leads', 'lead_activities', 'lead_notes', 'lead_status_history',
        'orders', 'order_items', 'contracts',
        'provider_configs', 'provider_sync_logs',
        'notes', 'audit_logs', 'webhook_events',
        'alembic_version'
    ]

    missing_tables = [t for t in expected_tables if t not in tables]

    if missing_tables:
        print(f"   ✗ Missing tables: {', '.join(missing_tables)}")
        return False
    else:
        print(f"   ✓ All {len(expected_tables)} tables exist")
        return True


def test_indexes_exist():
    """Verify key indexes were created"""
    print("\n3. Verifying indexes...")
    inspector = inspect(engine)

    # Check a few critical indexes
    critical_indexes = [
        ('leads', 'idx_leads_owner_status'),
        ('leads', 'idx_leads_metadata'),
        ('orders', 'idx_orders_status_created'),
        ('contracts', 'idx_contracts_status_activation'),
        ('provider_configs', 'idx_provider_configs_active'),
    ]

    missing_indexes = []
    for table, index_name in critical_indexes:
        indexes = inspector.get_indexes(table)
        if not any(idx['name'] == index_name for idx in indexes):
            missing_indexes.append(f"{table}.{index_name}")

    if missing_indexes:
        print(f"   ✗ Missing indexes: {', '.join(missing_indexes)}")
        return False
    else:
        print(f"   ✓ All critical indexes exist")
        return True


def test_admin_user_creation():
    """Test creating an admin user"""
    print("\n4. Testing AdminUser model...")
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(AdminUser).filter_by(username='admin').first()
        if admin:
            print("   ℹ Admin user already exists, skipping creation")
            return True

        # Create admin user (password should be hashed with bcrypt in production)
        import bcrypt as bcrypt_lib
        password = 'admin123'
        # Hash password (bcrypt has 72 byte limit)
        password_hash = bcrypt_lib.hashpw(password.encode('utf-8'), bcrypt_lib.gensalt()).decode('utf-8')

        admin = AdminUser(
            username='admin',
            email='admin@tentabo.local',
            full_name='System Administrator',
            password_hash=password_hash,  # CHANGE IN PRODUCTION!
            is_active=True
        )
        db.add(admin)
        db.commit()

        # Verify it was created
        admin = db.query(AdminUser).filter_by(username='admin').first()
        if admin:
            print(f"   ✓ Created admin user: {admin.email}")
            return True
        else:
            print("   ✗ Failed to create admin user")
            return False
    except Exception as e:
        print(f"   ✗ Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_product_and_pricing():
    """Test product and price tier creation"""
    print("\n5. Testing Product and PriceTier models...")
    db = SessionLocal()
    try:
        # Check if product exists
        product = db.query(Product).filter_by(name='OxiBox Storage').first()
        if product:
            print("   ℹ Product already exists, skipping creation")
            return True

        # Create a product with price tiers
        product = Product(
            name='OxiBox Storage',
            type='appliance',
            unit='TB',
            description='Secure cloud storage appliance',
            is_active='true'
        )
        db.add(product)
        db.flush()  # Get the product ID

        # Add progressive pricing tiers
        tiers = [
            PriceTier(product_id=product.id, min_quantity=0, max_quantity=10, price_per_unit=Decimal('100.00'), period='month'),
            PriceTier(product_id=product.id, min_quantity=11, max_quantity=50, price_per_unit=Decimal('90.00'), period='month'),
            PriceTier(product_id=product.id, min_quantity=51, max_quantity=None, price_per_unit=Decimal('80.00'), period='month'),
        ]
        for tier in tiers:
            db.add(tier)

        db.commit()

        # Verify
        product = db.query(Product).filter_by(name='OxiBox Storage').first()
        if product and len(product.price_tiers) == 3:
            print(f"   ✓ Created product with {len(product.price_tiers)} price tiers")
            return True
        else:
            print("   ✗ Failed to create product or price tiers")
            return False
    except Exception as e:
        print(f"   ✗ Error creating product: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_duration_creation():
    """Test duration options"""
    print("\n6. Testing Duration model...")
    db = SessionLocal()
    try:
        # Check if durations exist
        existing_durations = db.query(Duration).count()
        if existing_durations > 0:
            print(f"   ℹ {existing_durations} durations already exist, skipping creation")
            return True

        # Create duration options
        durations = [
            Duration(months=12, discount_percentage=Decimal('0.00'), name='12 months'),
            Duration(months=24, discount_percentage=Decimal('5.00'), name='24 months - 5% off'),
            Duration(months=36, discount_percentage=Decimal('10.00'), name='36 months - 10% off'),
        ]
        for duration in durations:
            db.add(duration)

        db.commit()

        count = db.query(Duration).count()
        if count == 3:
            print(f"   ✓ Created {count} duration options")
            return True
        else:
            print(f"   ✗ Expected 3 durations, got {count}")
            return False
    except Exception as e:
        print(f"   ✗ Error creating durations: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_partner_distributor():
    """Test partner and distributor models"""
    print("\n7. Testing Partner and Distributor models...")
    db = SessionLocal()
    try:
        # Check if they exist
        partner = db.query(Partner).filter_by(name='Test Partner').first()
        distributor = db.query(Distributor).filter_by(name='Test Distributor').first()

        if partner and distributor:
            print("   ℹ Partner and Distributor already exist, skipping creation")
            return True

        # Create partner
        if not partner:
            partner = Partner(
                name='Test Partner',
                legal_name='Test Partner SAS',
                registration_number='12345678901234',
                email='contact@testpartner.com',
                city='Paris',
                country='France',
                is_active=True
            )
            db.add(partner)

        # Create distributor
        if not distributor:
            distributor = Distributor(
                name='Test Distributor',
                legal_name='Test Distributor SA',
                registration_number='98765432109876',
                email='contact@testdist.com',
                city='Lyon',
                country='France',
                is_active=True
            )
            db.add(distributor)

        db.commit()

        print("   ✓ Created Partner and Distributor")
        return True
    except Exception as e:
        print(f"   ✗ Error creating Partner/Distributor: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_provider_config():
    """Test provider configuration"""
    print("\n8. Testing ProviderConfig model...")
    db = SessionLocal()
    try:
        # Check if config exists
        config = db.query(ProviderConfig).filter_by(
            provider_type=ProviderType.CRM,
            provider_name='pipedrive'
        ).first()

        if config:
            print("   ℹ Provider config already exists, skipping creation")
            return True

        # Create a provider config
        config = ProviderConfig(
            provider_type=ProviderType.CRM,
            provider_name='pipedrive',
            is_active=True,
            configuration={
                'api_url': 'https://api.pipedrive.com/v1',
                'sync_interval': 300
            },
            credentials={
                'api_token': 'test_token_placeholder'  # Should be encrypted in production
            },
            health_status='healthy'
        )
        db.add(config)
        db.commit()

        print("   ✓ Created ProviderConfig")
        return True
    except Exception as e:
        print(f"   ✗ Error creating ProviderConfig: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def print_database_summary():
    """Print summary of database contents"""
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)

    db = SessionLocal()
    try:
        counts = {
            'Admin Users': db.query(AdminUser).count(),
            'Users': db.query(User).count(),
            'Products': db.query(Product).count(),
            'Price Tiers': db.query(PriceTier).count(),
            'Durations': db.query(Duration).count(),
            'Partners': db.query(Partner).count(),
            'Distributors': db.query(Distributor).count(),
            'Leads': db.query(Lead).count(),
            'Orders': db.query(Order).count(),
            'Contracts': db.query(Contract).count(),
            'Provider Configs': db.query(ProviderConfig).count(),
        }

        for entity, count in counts.items():
            print(f"{entity:20} : {count:5} records")

    finally:
        db.close()


def main():
    """Run all tests"""
    print("="*60)
    print("TENTABO PRM - DATABASE SCHEMA VERIFICATION")
    print("="*60)

    tests = [
        test_database_connection,
        test_tables_exist,
        test_indexes_exist,
        test_admin_user_creation,
        test_product_and_pricing,
        test_duration_creation,
        test_partner_distributor,
        test_provider_config,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ✗ Test failed with exception: {e}")
            results.append(False)

    # Print summary
    print_database_summary()

    # Final results
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✓ ALL TESTS PASSED ({passed}/{total})")
        print("="*60)
        print("\nDatabase schema is ready for use!")
        print("\nDefault admin credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("  ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")
        return 0
    else:
        print(f"✗ SOME TESTS FAILED ({passed}/{total} passed)")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
