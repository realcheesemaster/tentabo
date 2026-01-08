"""
Mock providers for testing without external dependencies

These providers simulate external CRM and billing systems for development
and testing. They return realistic mock data without making actual API calls.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import uuid4

from app.providers.base import CRMProvider, BillingProvider

logger = logging.getLogger(__name__)


class MockCRMProvider(CRMProvider):
    """
    Mock CRM provider for testing

    Simulates a CRM system like Pipedrive without making actual API calls.
    Stores data in memory (will be lost on restart).
    """

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        super().__init__(config, credentials)
        self._leads: Dict[str, Dict[str, Any]] = {}
        self._activities: Dict[str, List[Dict[str, Any]]] = {}
        self._notes: Dict[str, List[Dict[str, Any]]] = {}

    async def test_connection(self) -> bool:
        """Mock connection test - always succeeds"""
        logger.info("MockCRMProvider: Connection test succeeded")
        return True

    async def create_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock lead"""
        provider_id = f"mock_lead_{uuid4().hex[:8]}"

        lead = {
            "provider_id": provider_id,
            "title": lead_data.get("title"),
            "organization": lead_data.get("organization"),
            "contact_name": lead_data.get("contact_name"),
            "contact_email": lead_data.get("contact_email"),
            "contact_phone": lead_data.get("contact_phone"),
            "value": lead_data.get("value"),
            "currency": lead_data.get("currency", "EUR"),
            "status": lead_data.get("status", "new"),
            "probability": lead_data.get("probability"),
            "expected_close_date": lead_data.get("expected_close_date"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self._leads[provider_id] = lead
        self._activities[provider_id] = []
        self._notes[provider_id] = []

        logger.info(f"MockCRMProvider: Created lead {provider_id}")
        return lead

    async def update_lead(self, provider_id: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a mock lead"""
        if provider_id not in self._leads:
            raise ValueError(f"Lead {provider_id} not found")

        lead = self._leads[provider_id]
        lead.update(lead_data)
        lead["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"MockCRMProvider: Updated lead {provider_id}")
        return lead

    async def get_lead(self, provider_id: str) -> Dict[str, Any]:
        """Get a mock lead"""
        if provider_id not in self._leads:
            raise ValueError(f"Lead {provider_id} not found")

        logger.info(f"MockCRMProvider: Retrieved lead {provider_id}")
        return self._leads[provider_id]

    async def create_activity(self, provider_lead_id: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock activity"""
        if provider_lead_id not in self._leads:
            raise ValueError(f"Lead {provider_lead_id} not found")

        activity_id = f"mock_activity_{uuid4().hex[:8]}"

        activity = {
            "provider_id": activity_id,
            "lead_id": provider_lead_id,
            "type": activity_data.get("activity_type", "note"),
            "subject": activity_data.get("subject"),
            "description": activity_data.get("description"),
            "due_date": activity_data.get("due_date"),
            "done": activity_data.get("done", False),
            "created_at": datetime.utcnow().isoformat(),
        }

        self._activities[provider_lead_id].append(activity)

        logger.info(f"MockCRMProvider: Created activity {activity_id} for lead {provider_lead_id}")
        return activity

    async def create_note(self, provider_lead_id: str, note_content: str) -> Dict[str, Any]:
        """Create a mock note"""
        if provider_lead_id not in self._leads:
            raise ValueError(f"Lead {provider_lead_id} not found")

        note_id = f"mock_note_{uuid4().hex[:8]}"

        note = {
            "provider_id": note_id,
            "lead_id": provider_lead_id,
            "content": note_content,
            "created_at": datetime.utcnow().isoformat(),
        }

        self._notes[provider_lead_id].append(note)

        logger.info(f"MockCRMProvider: Created note {note_id} for lead {provider_lead_id}")
        return note

    async def sync_leads(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Sync mock leads"""
        leads = list(self._leads.values())

        if since:
            # Filter by updated_at
            leads = [
                lead for lead in leads
                if datetime.fromisoformat(lead["updated_at"]) > since
            ]

        logger.info(f"MockCRMProvider: Synced {len(leads)} leads")
        return leads


class MockBillingProvider(BillingProvider):
    """
    Mock billing provider for testing

    Simulates a billing system like Pennylane without making actual API calls.
    Stores data in memory (will be lost on restart).
    """

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any]):
        super().__init__(config, credentials)
        self._customers: Dict[str, Dict[str, Any]] = {}
        self._quotes: Dict[str, Dict[str, Any]] = {}
        self._invoices: Dict[str, Dict[str, Any]] = {}

    async def test_connection(self) -> bool:
        """Mock connection test - always succeeds"""
        logger.info("MockBillingProvider: Connection test succeeded")
        return True

    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock customer"""
        customer_id = f"mock_customer_{uuid4().hex[:8]}"

        customer = {
            "customer_id": customer_id,
            "name": customer_data.get("name"),
            "legal_name": customer_data.get("legal_name"),
            "email": customer_data.get("email"),
            "phone": customer_data.get("phone"),
            "address": customer_data.get("address", {}),
            "created_at": datetime.utcnow().isoformat(),
        }

        self._customers[customer_id] = customer

        logger.info(f"MockBillingProvider: Created customer {customer_id}")
        return customer

    async def get_customer(self, provider_customer_id: str) -> Dict[str, Any]:
        """Get a mock customer"""
        if provider_customer_id not in self._customers:
            raise ValueError(f"Customer {provider_customer_id} not found")

        logger.info(f"MockBillingProvider: Retrieved customer {provider_customer_id}")
        return self._customers[provider_customer_id]

    async def create_quote(self, customer_id: str, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock quote"""
        if customer_id not in self._customers:
            raise ValueError(f"Customer {customer_id} not found")

        quote_id = f"mock_quote_{uuid4().hex[:8]}"

        quote = {
            "quote_id": quote_id,
            "customer_id": customer_id,
            "quote_number": f"Q-{uuid4().hex[:8].upper()}",
            "items": quote_data.get("items", []),
            "subtotal": quote_data.get("subtotal"),
            "tax_amount": quote_data.get("tax_amount"),
            "total": quote_data.get("total"),
            "currency": quote_data.get("currency", "EUR"),
            "status": "draft",
            "pdf_url": f"https://mock-billing.example.com/quotes/{quote_id}.pdf",
            "created_at": datetime.utcnow().isoformat(),
        }

        self._quotes[quote_id] = quote

        logger.info(f"MockBillingProvider: Created quote {quote_id} for customer {customer_id}")
        return quote

    async def get_quote(self, provider_quote_id: str) -> Dict[str, Any]:
        """Get a mock quote"""
        if provider_quote_id not in self._quotes:
            raise ValueError(f"Quote {provider_quote_id} not found")

        logger.info(f"MockBillingProvider: Retrieved quote {provider_quote_id}")
        return self._quotes[provider_quote_id]

    async def create_invoice(self, customer_id: str, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock invoice"""
        if customer_id not in self._customers:
            raise ValueError(f"Customer {customer_id} not found")

        invoice_id = f"mock_invoice_{uuid4().hex[:8]}"

        invoice = {
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "invoice_number": f"INV-{uuid4().hex[:8].upper()}",
            "items": invoice_data.get("items", []),
            "subtotal": invoice_data.get("subtotal"),
            "tax_amount": invoice_data.get("tax_amount"),
            "total": invoice_data.get("total"),
            "currency": invoice_data.get("currency", "EUR"),
            "status": "draft",
            "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "pdf_url": f"https://mock-billing.example.com/invoices/{invoice_id}.pdf",
            "created_at": datetime.utcnow().isoformat(),
        }

        self._invoices[invoice_id] = invoice

        logger.info(f"MockBillingProvider: Created invoice {invoice_id} for customer {customer_id}")
        return invoice

    async def get_invoice(self, provider_invoice_id: str) -> Dict[str, Any]:
        """Get a mock invoice"""
        if provider_invoice_id not in self._invoices:
            raise ValueError(f"Invoice {provider_invoice_id} not found")

        logger.info(f"MockBillingProvider: Retrieved invoice {provider_invoice_id}")
        return self._invoices[provider_invoice_id]

    async def list_invoices(self, customer_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """List mock invoices for a customer"""
        invoices = [
            inv for inv in self._invoices.values()
            if inv["customer_id"] == customer_id
        ]

        if since:
            # Filter by created_at
            invoices = [
                inv for inv in invoices
                if datetime.fromisoformat(inv["created_at"]) > since
            ]

        logger.info(f"MockBillingProvider: Listed {len(invoices)} invoices for customer {customer_id}")
        return invoices
