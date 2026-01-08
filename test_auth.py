#!/usr/bin/env python3
"""
Authentication System Test Suite for Tentabo PRM

This script tests all authentication flows:
1. Admin login with database password
2. LDAP user login
3. JWT token validation
4. API key creation and usage
5. Token refresh
6. User info retrieval

Usage:
    python test_auth.py
"""

import sys
import requests
import json
from datetime import datetime
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Test credentials (to be set up first)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Change this after first run

# LDAP test user (should exist in your LDAP)
LDAP_USERNAME = "testuser"  # Replace with actual LDAP user
LDAP_PASSWORD = "password"  # Replace with actual LDAP password

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_success(message: str):
    """Print success message in green"""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message: str):
    """Print error message in red"""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message: str):
    """Print info message in blue"""
    print(f"{BLUE}ℹ {message}{RESET}")


def print_warning(message: str):
    """Print warning message in yellow"""
    print(f"{YELLOW}⚠ {message}{RESET}")


def print_section(title: str):
    """Print section header"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


class TestResults:
    """Track test results"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def add_pass(self):
        self.total += 1
        self.passed += 1

    def add_fail(self):
        self.total += 1
        self.failed += 1

    def add_skip(self):
        self.total += 1
        self.skipped += 1

    def summary(self):
        print_section("Test Summary")
        print(f"Total tests: {self.total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")
        print(f"{YELLOW}Skipped: {self.skipped}{RESET}")
        print()

        if self.failed == 0:
            print_success("All tests passed!")
            return 0
        else:
            print_error(f"{self.failed} test(s) failed")
            return 1


results = TestResults()


def test_health_checks():
    """Test health check endpoints"""
    print_section("Health Checks")

    # Basic health
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Basic health check passed")
            results.add_pass()
        else:
            print_error(f"Health check failed: {response.status_code}")
            results.add_fail()
    except Exception as e:
        print_error(f"Health check error: {e}")
        results.add_fail()

    # Database health
    try:
        response = requests.get(f"{BASE_URL}/health/db", timeout=5)
        if response.status_code == 200:
            print_success("Database health check passed")
            results.add_pass()
        else:
            print_error(f"Database health check failed: {response.status_code}")
            results.add_fail()
    except Exception as e:
        print_error(f"Database health check error: {e}")
        results.add_fail()

    # LDAP health
    try:
        response = requests.get(f"{BASE_URL}/health/ldap", timeout=5)
        if response.status_code == 200:
            print_success("LDAP health check passed")
            results.add_pass()
        elif response.status_code == 503:
            print_warning("LDAP is not available (will skip LDAP tests)")
            results.add_pass()
        else:
            print_error(f"LDAP health check failed: {response.status_code}")
            results.add_fail()
    except Exception as e:
        print_error(f"LDAP health check error: {e}")
        results.add_fail()


def test_admin_login() -> Optional[str]:
    """Test admin login and return JWT token"""
    print_section("Admin Authentication")

    try:
        response = requests.post(
            f"{API_V1}/auth/login",
            json={
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            token_type = data.get("token_type")
            user_type = data.get("user_type")

            if token and token_type == "Bearer" and user_type == "admin":
                print_success(f"Admin login successful")
                print_info(f"Token type: {token_type}")
                print_info(f"User type: {user_type}")
                print_info(f"Token length: {len(token)} characters")
                results.add_pass()
                return token
            else:
                print_error("Admin login returned invalid data")
                results.add_fail()
                return None
        elif response.status_code == 401:
            print_error("Admin login failed: Invalid credentials")
            print_warning(f"Make sure admin user exists with username '{ADMIN_USERNAME}'")
            print_warning(f"Run: python setup_admin.py")
            results.add_fail()
            return None
        else:
            print_error(f"Admin login failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            results.add_fail()
            return None

    except Exception as e:
        print_error(f"Admin login error: {e}")
        results.add_fail()
        return None


def test_user_info(token: str, expected_user_type: str = "admin"):
    """Test getting user info with token"""
    print_section(f"Get User Info ({expected_user_type})")

    try:
        response = requests.get(
            f"{API_V1}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success("User info retrieved successfully")
            print_info(f"User ID: {data.get('id')}")
            print_info(f"User type: {data.get('user_type')}")
            print_info(f"Email: {data.get('email')}")
            print_info(f"Username: {data.get('username')}")
            results.add_pass()
            return data
        else:
            print_error(f"Get user info failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            results.add_fail()
            return None

    except Exception as e:
        print_error(f"Get user info error: {e}")
        results.add_fail()
        return None


def test_token_refresh(token: str) -> Optional[str]:
    """Test token refresh"""
    print_section("Token Refresh")

    try:
        response = requests.post(
            f"{API_V1}/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            new_token = data.get("access_token")
            print_success("Token refresh successful")
            print_info(f"New token length: {len(new_token)} characters")
            results.add_pass()
            return new_token
        else:
            print_error(f"Token refresh failed: {response.status_code}")
            results.add_fail()
            return None

    except Exception as e:
        print_error(f"Token refresh error: {e}")
        results.add_fail()
        return None


def test_create_api_key(jwt_token: str) -> Optional[str]:
    """Test API key creation"""
    print_section("API Key Creation")

    try:
        response = requests.post(
            f"{API_V1}/users/me/api-keys",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "name": "Test API Key",
                "description": "Created by test script",
                "scopes": ["read", "write"]
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            key_id = data.get("id")

            if api_key and api_key.startswith("tnt_"):
                print_success("API key created successfully")
                print_info(f"Key ID: {key_id}")
                print_info(f"Key prefix: {data.get('prefix')}")
                print_info(f"Key length: {len(api_key)} characters")
                print_warning("API Key (save this): " + api_key)
                results.add_pass()
                return api_key
            else:
                print_error("API key creation returned invalid data")
                results.add_fail()
                return None
        else:
            print_error(f"API key creation failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            results.add_fail()
            return None

    except Exception as e:
        print_error(f"API key creation error: {e}")
        results.add_fail()
        return None


def test_list_api_keys(jwt_token: str):
    """Test listing API keys"""
    print_section("List API Keys")

    try:
        response = requests.get(
            f"{API_V1}/users/me/api-keys",
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=10
        )

        if response.status_code == 200:
            keys = response.json()
            print_success(f"API keys listed successfully: {len(keys)} key(s)")
            for key in keys:
                print_info(f"  - {key['name']} ({key['prefix']})")
            results.add_pass()
        else:
            print_error(f"List API keys failed: {response.status_code}")
            results.add_fail()

    except Exception as e:
        print_error(f"List API keys error: {e}")
        results.add_fail()


def test_api_key_authentication(api_key: str):
    """Test authentication with API key"""
    print_section("API Key Authentication")

    try:
        response = requests.get(
            f"{API_V1}/auth/me",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success("API key authentication successful")
            print_info(f"User ID: {data.get('id')}")
            print_info(f"User type: {data.get('user_type')}")
            results.add_pass()
        else:
            print_error(f"API key authentication failed: {response.status_code}")
            results.add_fail()

    except Exception as e:
        print_error(f"API key authentication error: {e}")
        results.add_fail()


def test_invalid_token():
    """Test authentication with invalid token"""
    print_section("Invalid Token Handling")

    try:
        response = requests.get(
            f"{API_V1}/auth/me",
            headers={"Authorization": "Bearer invalid_token_12345"},
            timeout=10
        )

        if response.status_code == 401:
            print_success("Invalid token correctly rejected")
            results.add_pass()
        else:
            print_error(f"Invalid token should return 401, got {response.status_code}")
            results.add_fail()

    except Exception as e:
        print_error(f"Invalid token test error: {e}")
        results.add_fail()


def test_ldap_login() -> Optional[str]:
    """Test LDAP user login"""
    print_section("LDAP User Authentication")

    print_warning(f"Testing LDAP login with user: {LDAP_USERNAME}")
    print_warning("Update LDAP_USERNAME and LDAP_PASSWORD in script for your environment")

    try:
        response = requests.post(
            f"{API_V1}/auth/login",
            json={
                "username": LDAP_USERNAME,
                "password": LDAP_PASSWORD
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            user_type = data.get("user_type")

            if token and user_type == "user":
                print_success("LDAP login successful")
                results.add_pass()
                return token
            else:
                print_error("LDAP login returned invalid data")
                results.add_fail()
                return None
        elif response.status_code == 401:
            print_warning("LDAP login failed: Invalid credentials or user not found")
            print_info("This is expected if LDAP user doesn't exist")
            results.add_skip()
            return None
        elif response.status_code == 403:
            print_warning("LDAP user not enabled in database")
            print_info("User must be enabled by admin after first login")
            results.add_skip()
            return None
        elif response.status_code == 503:
            print_warning("LDAP service unavailable")
            results.add_skip()
            return None
        else:
            print_error(f"LDAP login failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            results.add_fail()
            return None

    except Exception as e:
        print_error(f"LDAP login error: {e}")
        results.add_fail()
        return None


def main():
    """Run all tests"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Tentabo PRM Authentication System Tests{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if server is running
    try:
        requests.get(BASE_URL, timeout=5)
    except Exception as e:
        print_error(f"\nCannot connect to server at {BASE_URL}")
        print_error(f"Error: {e}")
        print_warning("\nMake sure the server is running:")
        print_warning("  python -m uvicorn app.main:app --reload")
        return 1

    # Run tests
    test_health_checks()

    # Test admin authentication flow
    admin_token = test_admin_login()
    if admin_token:
        test_user_info(admin_token, "admin")
        test_token_refresh(admin_token)

        # Test API key flow
        api_key = test_create_api_key(admin_token)
        test_list_api_keys(admin_token)

        if api_key:
            test_api_key_authentication(api_key)

    # Test invalid token
    test_invalid_token()

    # Test LDAP authentication (if configured)
    ldap_token = test_ldap_login()
    if ldap_token:
        test_user_info(ldap_token, "user")

    # Print summary
    return results.summary()


if __name__ == "__main__":
    sys.exit(main())
