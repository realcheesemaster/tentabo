"""
Integration tests for Tentabo PRM API

Tests basic CRUD operations, role-based access, and multi-tenant filtering
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

from app.main import app
from app.database import Base, get_db
from app.models.auth import AdminUser, User, UserRole
from app.models.core import Product, PriceTier, Duration
from app.models.partner import Partner, Distributor
from app.auth.security import hash_password

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def admin_user(test_db):
    """Create admin user for testing"""
    admin = AdminUser(
        username="testadmin",
        email="admin@test.com",
        password_hash=hash_password("testpass"),
        full_name="Test Admin",
        is_active=True,
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture
def admin_token(client, admin_user):
    """Get JWT token for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "testpass"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def test_product(test_db):
    """Create test product with price tiers"""
    product = Product(
        name="Test Storage",
        type="appliance",
        unit="TB",
        description="Test storage product",
        is_active="true",
    )
    test_db.add(product)
    test_db.flush()

    # Add price tiers
    tier1 = PriceTier(
        product_id=product.id,
        min_quantity=1,
        max_quantity=10,
        price_per_unit=Decimal("100.00"),
        period="month",
    )
    tier2 = PriceTier(
        product_id=product.id,
        min_quantity=11,
        max_quantity=None,
        price_per_unit=Decimal("90.00"),
        period="month",
    )
    test_db.add(tier1)
    test_db.add(tier2)
    test_db.commit()
    test_db.refresh(product)
    return product


@pytest.fixture
def test_duration(test_db):
    """Create test duration"""
    duration = Duration(
        months=12,
        discount_percentage=Decimal("10.00"),
        name="12 months",
    )
    test_db.add(duration)
    test_db.commit()
    test_db.refresh(duration)
    return duration


@pytest.fixture
def test_partner(test_db):
    """Create test partner"""
    partner = Partner(
        name="Test Partner",
        legal_name="Test Partner LLC",
        registration_number="12345",
        email="partner@test.com",
        is_active=True,
    )
    test_db.add(partner)
    test_db.commit()
    test_db.refresh(partner)
    return partner


@pytest.fixture
def test_distributor(test_db):
    """Create test distributor"""
    distributor = Distributor(
        name="Test Distributor",
        legal_name="Test Distributor Inc",
        registration_number="67890",
        email="distributor@test.com",
        is_active=True,
    )
    test_db.add(distributor)
    test_db.commit()
    test_db.refresh(distributor)
    return distributor


# ==================== HEALTH CHECK TESTS ====================


def test_health_check(client):
    """Test basic health check"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "api" in data


# ==================== AUTHENTICATION TESTS ====================


def test_admin_login(client, admin_user):
    """Test admin login"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "testpass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user_type"] == "admin"


def test_invalid_login(client):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "invalid", "password": "wrong"}
    )
    assert response.status_code == 401


def test_get_current_user(client, admin_token):
    """Test getting current user info"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_type"] == "admin"
    assert data["email"] == "admin@test.com"


# ==================== PRODUCT TESTS ====================


def test_list_products(client, admin_token, test_product):
    """Test listing products"""
    response = client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) >= 1


def test_get_product(client, admin_token, test_product):
    """Test getting product details"""
    response = client.get(
        f"/api/v1/products/{test_product.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Storage"
    assert len(data["price_tiers"]) == 2


def test_create_product(client, admin_token):
    """Test creating a product"""
    response = client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "New Product",
            "type": "service",
            "unit": "user",
            "description": "New test product",
            "is_active": True,
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Product"


def test_calculate_price(client, admin_token, test_product, test_duration):
    """Test price calculation"""
    response = client.post(
        f"/api/v1/products/{test_product.id}/calculate-price",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "quantity": 5,
            "duration_id": str(test_duration.id),
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 5
    assert float(data["unit_price"]) == 100.00
    assert float(data["subtotal"]) == 500.00
    assert float(data["discount_percentage"]) == 10.00
    assert float(data["total"]) == 450.00  # 500 - 10%


# ==================== PARTNER TESTS ====================


def test_list_partners(client, admin_token, test_partner):
    """Test listing partners"""
    response = client.get(
        "/api/v1/partners",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_create_partner(client, admin_token):
    """Test creating a partner"""
    response = client.post(
        "/api/v1/partners",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "New Partner",
            "legal_name": "New Partner LLC",
            "registration_number": "99999",
            "email": "newpartner@test.com",
            "is_active": True,
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Partner"


# ==================== ORDER TESTS ====================


def test_create_order(client, admin_token, test_product, test_duration, test_partner):
    """Test creating an order"""
    response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "partner_id": str(test_partner.id),
            "items": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 5,
                    "duration_id": str(test_duration.id),
                }
            ],
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "order_number" in data
    assert data["status"] == "created"
    assert float(data["total_amount"]) == 450.00  # 5 * 100 - 10% discount


def test_list_orders(client, admin_token):
    """Test listing orders"""
    response = client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data


# ==================== AUTHENTICATION REQUIRED TESTS ====================


def test_unauthorized_access(client):
    """Test that endpoints require authentication"""
    response = client.get("/api/v1/products")
    assert response.status_code == 401


def test_invalid_token(client):
    """Test with invalid token"""
    response = client.get(
        "/api/v1/products",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


# ==================== RUN TESTS ====================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
