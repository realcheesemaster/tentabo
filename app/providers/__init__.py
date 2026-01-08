"""
Provider abstraction layer for external integrations
"""

from app.providers.base import CRMProvider, BillingProvider, AuthProvider
from app.providers.registry import ProviderRegistry, get_active_crm, get_active_billing, get_active_auth
from app.providers.mock_providers import MockCRMProvider, MockBillingProvider

__all__ = [
    'CRMProvider',
    'BillingProvider',
    'AuthProvider',
    'ProviderRegistry',
    'get_active_crm',
    'get_active_billing',
    'get_active_auth',
    'MockCRMProvider',
    'MockBillingProvider',
]
