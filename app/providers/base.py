"""
Base provider interfaces for external integrations

This module defines abstract base classes for different types of providers:
- CRMProvider: For CRM systems (Pipedrive, Salesforce, HubSpot, etc.)
- BillingProvider: For billing systems (Pennylane, QuickBooks, Xero, etc.)
- AuthProvider: For authentication systems (LDAP, Google, SAML, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class CRMProvider(ABC):
    """
    Abstract base class for CRM providers

    Provides a unified interface for interacting with different CRM systems.
    All CRM operations should go through this interface to maintain provider
    independence.
    """

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        """
        Initialize CRM provider

        Args:
            config: Provider configuration (non-sensitive)
            credentials: Provider credentials (sensitive)
        """
        self.config = config
        self.credentials = credentials
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to CRM provider

        Returns:
            True if connection is successful, False otherwise
        """
        pass

    @abstractmethod
    async def create_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new lead in the CRM

        Args:
            lead_data: Lead information

        Returns:
            Dict with provider-specific lead data including provider_id
        """
        pass

    @abstractmethod
    async def update_lead(self, provider_id: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing lead in the CRM

        Args:
            provider_id: Provider's lead ID
            lead_data: Updated lead information

        Returns:
            Dict with updated provider-specific data
        """
        pass

    @abstractmethod
    async def get_lead(self, provider_id: str) -> Dict[str, Any]:
        """
        Get lead details from CRM

        Args:
            provider_id: Provider's lead ID

        Returns:
            Dict with lead data
        """
        pass

    @abstractmethod
    async def create_activity(self, provider_lead_id: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an activity for a lead

        Args:
            provider_lead_id: Provider's lead ID
            activity_data: Activity information

        Returns:
            Dict with provider-specific activity data
        """
        pass

    @abstractmethod
    async def create_note(self, provider_lead_id: str, note_content: str) -> Dict[str, Any]:
        """
        Create a note for a lead

        Args:
            provider_lead_id: Provider's lead ID
            note_content: Note text

        Returns:
            Dict with provider-specific note data
        """
        pass

    @abstractmethod
    async def sync_leads(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Sync leads from CRM (pull)

        Args:
            since: Only sync leads updated since this datetime

        Returns:
            List of lead data dicts
        """
        pass


class BillingProvider(ABC):
    """
    Abstract base class for billing providers

    Provides a unified interface for interacting with different billing systems.
    All billing operations should go through this interface.
    """

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        """
        Initialize billing provider

        Args:
            config: Provider configuration (non-sensitive)
            credentials: Provider credentials (sensitive)
        """
        self.config = config
        self.credentials = credentials
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to billing provider

        Returns:
            True if connection is successful, False otherwise
        """
        pass

    @abstractmethod
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a customer in the billing system

        Args:
            customer_data: Customer information (partner data)

        Returns:
            Dict with provider-specific customer data including customer_id
        """
        pass

    @abstractmethod
    async def get_customer(self, provider_customer_id: str) -> Dict[str, Any]:
        """
        Get customer details from billing system

        Args:
            provider_customer_id: Provider's customer ID

        Returns:
            Dict with customer data
        """
        pass

    @abstractmethod
    async def create_quote(self, customer_id: str, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a quote/estimate for a customer

        Args:
            customer_id: Provider's customer ID
            quote_data: Quote information (from order)

        Returns:
            Dict with provider-specific quote data including quote_id, pdf_url, etc.
        """
        pass

    @abstractmethod
    async def get_quote(self, provider_quote_id: str) -> Dict[str, Any]:
        """
        Get quote details from billing system

        Args:
            provider_quote_id: Provider's quote ID

        Returns:
            Dict with quote data
        """
        pass

    @abstractmethod
    async def create_invoice(self, customer_id: str, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an invoice for a customer

        Args:
            customer_id: Provider's customer ID
            invoice_data: Invoice information (from contract)

        Returns:
            Dict with provider-specific invoice data including invoice_id, pdf_url, etc.
        """
        pass

    @abstractmethod
    async def get_invoice(self, provider_invoice_id: str) -> Dict[str, Any]:
        """
        Get invoice details from billing system

        Args:
            provider_invoice_id: Provider's invoice ID

        Returns:
            Dict with invoice data
        """
        pass

    @abstractmethod
    async def list_invoices(self, customer_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        List invoices for a customer

        Args:
            customer_id: Provider's customer ID
            since: Only return invoices created since this datetime

        Returns:
            List of invoice data dicts
        """
        pass


class AuthProvider(ABC):
    """
    Abstract base class for authentication providers

    Provides a unified interface for different authentication systems.
    Note: The LDAP provider is already implemented. This interface allows
    for adding additional providers (Google, SAML, etc.) in the future.
    """

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        """
        Initialize auth provider

        Args:
            config: Provider configuration (non-sensitive)
            credentials: Provider credentials (sensitive)
        """
        self.config = config
        self.credentials = credentials
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to auth provider

        Returns:
            True if connection is successful, False otherwise
        """
        pass

    @abstractmethod
    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user

        Args:
            username: Username
            password: Password

        Returns:
            Dict with user data if authentication successful, None otherwise
            User data should include: username, email, full_name
        """
        pass

    @abstractmethod
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user details from auth provider

        Args:
            username: Username

        Returns:
            Dict with user data if found, None otherwise
        """
        pass

    @abstractmethod
    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for users in auth provider

        Args:
            query: Search query

        Returns:
            List of user data dicts
        """
        pass
