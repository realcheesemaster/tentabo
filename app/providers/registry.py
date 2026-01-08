"""
Provider registry for managing active providers

This module provides a centralized registry for managing different types of providers.
It allows switching between providers at runtime and retrieving the active provider
for each type (CRM, Billing, Auth).
"""

import logging
from typing import Dict, Type, Optional, Any
from enum import Enum

from app.providers.base import CRMProvider, BillingProvider, AuthProvider

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Provider types"""
    CRM = "crm"
    BILLING = "billing"
    AUTH = "auth"


class ProviderRegistry:
    """
    Registry for managing providers

    Supports:
    - Registering provider classes
    - Setting active provider for each type
    - Retrieving active provider instances
    - Switching providers at runtime
    """

    def __init__(self):
        """Initialize empty registry"""
        self._providers: Dict[ProviderType, Dict[str, Type]] = {
            ProviderType.CRM: {},
            ProviderType.BILLING: {},
            ProviderType.AUTH: {},
        }
        self._active: Dict[ProviderType, Optional[str]] = {
            ProviderType.CRM: None,
            ProviderType.BILLING: None,
            ProviderType.AUTH: None,
        }
        self._instances: Dict[str, Any] = {}

    def register(
        self,
        provider_type: ProviderType,
        name: str,
        provider_class: Type,
        set_active: bool = False
    ):
        """
        Register a provider class

        Args:
            provider_type: Type of provider (CRM, BILLING, AUTH)
            name: Provider name (e.g., 'pipedrive', 'pennylane')
            provider_class: Provider class (must inherit from appropriate base)
            set_active: Whether to set this as the active provider
        """
        # Validate provider class
        base_classes = {
            ProviderType.CRM: CRMProvider,
            ProviderType.BILLING: BillingProvider,
            ProviderType.AUTH: AuthProvider,
        }

        expected_base = base_classes[provider_type]
        if not issubclass(provider_class, expected_base):
            raise ValueError(
                f"Provider class must inherit from {expected_base.__name__}"
            )

        # Register provider
        self._providers[provider_type][name] = provider_class
        logger.info(f"Registered {provider_type.value} provider: {name}")

        # Set as active if requested
        if set_active:
            self.set_active(provider_type, name)

    def set_active(self, provider_type: ProviderType, name: str):
        """
        Set the active provider for a type

        Args:
            provider_type: Type of provider
            name: Provider name

        Raises:
            ValueError: If provider is not registered
        """
        if name not in self._providers[provider_type]:
            raise ValueError(
                f"Provider '{name}' not registered for type {provider_type.value}"
            )

        old_active = self._active[provider_type]
        self._active[provider_type] = name

        logger.info(
            f"Switched active {provider_type.value} provider: "
            f"{old_active} -> {name}"
        )

    def get_active_name(self, provider_type: ProviderType) -> Optional[str]:
        """
        Get the name of the active provider for a type

        Args:
            provider_type: Type of provider

        Returns:
            Provider name or None if no active provider
        """
        return self._active[provider_type]

    def get_instance(
        self,
        provider_type: ProviderType,
        config: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> Any:
        """
        Get an instance of the active provider

        Args:
            provider_type: Type of provider
            config: Provider configuration
            credentials: Provider credentials

        Returns:
            Provider instance

        Raises:
            RuntimeError: If no active provider is set
        """
        active_name = self._active[provider_type]

        if not active_name:
            raise RuntimeError(
                f"No active provider set for type {provider_type.value}"
            )

        provider_class = self._providers[provider_type][active_name]

        # Create new instance each time to ensure fresh config/credentials
        instance = provider_class(config, credentials)

        logger.debug(
            f"Created instance of {provider_type.value} provider: {active_name}"
        )

        return instance

    def list_providers(self, provider_type: ProviderType) -> list[str]:
        """
        List all registered providers for a type

        Args:
            provider_type: Type of provider

        Returns:
            List of provider names
        """
        return list(self._providers[provider_type].keys())

    def is_registered(self, provider_type: ProviderType, name: str) -> bool:
        """
        Check if a provider is registered

        Args:
            provider_type: Type of provider
            name: Provider name

        Returns:
            True if registered, False otherwise
        """
        return name in self._providers[provider_type]


# Global registry instance
_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get the global provider registry"""
    return _registry


def get_active_crm(config: Dict[str, Any], credentials: Dict[str, Any]) -> CRMProvider:
    """
    Get the active CRM provider instance

    Args:
        config: CRM provider configuration
        credentials: CRM provider credentials

    Returns:
        CRMProvider instance

    Raises:
        RuntimeError: If no active CRM provider is set
    """
    return _registry.get_instance(ProviderType.CRM, config, credentials)


def get_active_billing(config: Dict[str, Any], credentials: Dict[str, Any]) -> BillingProvider:
    """
    Get the active billing provider instance

    Args:
        config: Billing provider configuration
        credentials: Billing provider credentials

    Returns:
        BillingProvider instance

    Raises:
        RuntimeError: If no active billing provider is set
    """
    return _registry.get_instance(ProviderType.BILLING, config, credentials)


def get_active_auth(config: Dict[str, Any], credentials: Dict[str, Any]) -> AuthProvider:
    """
    Get the active auth provider instance

    Args:
        config: Auth provider configuration
        credentials: Auth provider credentials

    Returns:
        AuthProvider instance

    Raises:
        RuntimeError: If no active auth provider is set
    """
    return _registry.get_instance(ProviderType.AUTH, config, credentials)
