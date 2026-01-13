"""
Pennylane API Service

Handles all interactions with the Pennylane API including:
- API client with retry logic and rate limiting
- Sync service for importing data to local database
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Any, AsyncGenerator, Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.pennylane import (
    PennylaneConnection,
    PennylaneCustomer,
    PennylaneInvoice,
    PennylaneQuote,
    PennylaneSubscription,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class PennylaneAPIError(Exception):
    """Base exception for Pennylane API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"PennylaneAPIError({self.status_code}): {self.message}"
        return f"PennylaneAPIError: {self.message}"


class PennylaneAuthError(PennylaneAPIError):
    """Raised when authentication fails (401, 403)."""

    def __str__(self) -> str:
        return f"PennylaneAuthError: {self.message}"


class PennylaneRateLimitError(PennylaneAPIError):
    """Raised when rate limit is hit (429)."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        status_code: int = 429,
        response_body: Optional[str] = None,
    ):
        super().__init__(message, status_code, response_body)
        self.retry_after = retry_after

    def __str__(self) -> str:
        if self.retry_after:
            return f"PennylaneRateLimitError: {self.message} (retry after {self.retry_after}s)"
        return f"PennylaneRateLimitError: {self.message}"


# =============================================================================
# Sync Result Dataclass
# =============================================================================


@dataclass
class SyncResult:
    """Result of a sync operation for a specific entity type."""

    entity_type: str
    total_fetched: int = 0
    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)
    success: bool = True

    def add_error(self, error: str) -> None:
        """Add an error and mark the sync as failed."""
        self.errors.append(error)
        self.success = False

    def __repr__(self) -> str:
        return (
            f"<SyncResult(entity={self.entity_type}, fetched={self.total_fetched}, "
            f"created={self.created}, updated={self.updated}, success={self.success})>"
        )


# =============================================================================
# Pennylane API Client
# =============================================================================


class PennylaneClient:
    """
    Async HTTP client for the Pennylane API.

    Handles authentication, pagination, retry logic, and error handling.
    """

    BASE_URL = "https://app.pennylane.com/api/external/v2"

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 1.0
    RETRY_BACKOFF_MULTIPLIER = 2.0
    RETRYABLE_STATUS_CODES = {429, 503}

    def __init__(self, api_token: str, timeout: float = 30.0):
        """
        Initialize the Pennylane client.

        Args:
            api_token: Bearer token for API authentication
            timeout: Request timeout in seconds (default 30s)
        """
        self.api_token = api_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def _headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "PennylaneClient":
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        Make an HTTP request to the Pennylane API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/customers")
            params: Query parameters
            retry_count: Current retry attempt number

        Returns:
            Parsed JSON response

        Raises:
            PennylaneAuthError: For authentication failures
            PennylaneRateLimitError: For rate limit errors
            PennylaneAPIError: For other API errors
        """
        client = await self._get_client()
        url = endpoint.lstrip("/")

        logger.debug(f"Pennylane API request: {method} {url} params={params}")

        try:
            response = await client.request(method, url, params=params)

            # Handle successful responses
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Pennylane API response: {response.status_code}")
                return data

            # Handle authentication errors
            if response.status_code in (401, 403):
                raise PennylaneAuthError(
                    message=f"Authentication failed: {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_after_seconds = int(retry_after) if retry_after else None

                if retry_count < self.MAX_RETRIES:
                    wait_time = retry_after_seconds or (
                        self.RETRY_DELAY_SECONDS * (self.RETRY_BACKOFF_MULTIPLIER ** retry_count)
                    )
                    logger.warning(
                        f"Rate limited, waiting {wait_time}s before retry {retry_count + 1}/{self.MAX_RETRIES}"
                    )
                    await asyncio.sleep(wait_time)
                    return await self._request(method, endpoint, params, retry_count + 1)

                raise PennylaneRateLimitError(
                    message="Rate limit exceeded after max retries",
                    retry_after=retry_after_seconds,
                    status_code=429,
                    response_body=response.text,
                )

            # Handle 503 with retry
            if response.status_code == 503:
                if retry_count < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY_SECONDS * (self.RETRY_BACKOFF_MULTIPLIER ** retry_count)
                    logger.warning(
                        f"Service unavailable (503), waiting {wait_time}s before retry {retry_count + 1}/{self.MAX_RETRIES}"
                    )
                    await asyncio.sleep(wait_time)
                    return await self._request(method, endpoint, params, retry_count + 1)

            # Handle other errors
            raise PennylaneAPIError(
                message=f"API error: {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )

        except httpx.TimeoutException as e:
            if retry_count < self.MAX_RETRIES:
                wait_time = self.RETRY_DELAY_SECONDS * (self.RETRY_BACKOFF_MULTIPLIER ** retry_count)
                logger.warning(
                    f"Request timeout, waiting {wait_time}s before retry {retry_count + 1}/{self.MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                return await self._request(method, endpoint, params, retry_count + 1)
            raise PennylaneAPIError(f"Request timeout after {self.MAX_RETRIES} retries: {e}")

        except httpx.RequestError as e:
            raise PennylaneAPIError(f"Request failed: {e}")

    # -------------------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------------------

    async def test_connection(self) -> dict[str, Any]:
        """
        Test the API connection by fetching current company info.

        Returns:
            Company information from /me endpoint

        Raises:
            PennylaneAPIError: If the connection test fails
        """
        logger.info("Testing Pennylane API connection")
        result = await self._request("GET", "/me")
        logger.info("Pennylane API connection successful")
        return result

    async def list_customers(
        self,
        page: int = 1,
        per_page: int = 100,
        **filters: Any,
    ) -> dict[str, Any]:
        """
        List customers with pagination.

        Args:
            page: Page number (1-based)
            per_page: Number of items per page (max 100)
            **filters: Additional filter parameters

        Returns:
            Paginated list of customers
        """
        params = {"page": page, "per_page": min(per_page, 100), **filters}
        logger.info(f"Fetching customers page {page}")
        return await self._request("GET", "/customers", params=params)

    async def get_customer(self, customer_id: str) -> dict[str, Any]:
        """
        Get a single customer by ID.

        Args:
            customer_id: Pennylane customer ID

        Returns:
            Customer data
        """
        logger.info(f"Fetching customer {customer_id}")
        return await self._request("GET", f"/customers/{customer_id}")

    async def list_invoices(
        self,
        page: int = 1,
        per_page: int = 100,
        **filters: Any,
    ) -> dict[str, Any]:
        """
        List invoices with pagination.

        Args:
            page: Page number (1-based)
            per_page: Number of items per page (max 100)
            **filters: Additional filter parameters

        Returns:
            Paginated list of invoices
        """
        params = {"page": page, "per_page": min(per_page, 100), **filters}
        logger.info(f"Fetching invoices page {page}")
        return await self._request("GET", "/customer_invoices", params=params)

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        """
        Get a single invoice by ID.

        Args:
            invoice_id: Pennylane invoice ID

        Returns:
            Invoice data
        """
        logger.info(f"Fetching invoice {invoice_id}")
        return await self._request("GET", f"/customer_invoices/{invoice_id}")

    async def list_quotes(
        self,
        page: int = 1,
        per_page: int = 100,
        **filters: Any,
    ) -> dict[str, Any]:
        """
        List quotes with pagination.

        Args:
            page: Page number (1-based)
            per_page: Number of items per page (max 100)
            **filters: Additional filter parameters

        Returns:
            Paginated list of quotes
        """
        params = {"page": page, "per_page": min(per_page, 100), **filters}
        logger.info(f"Fetching quotes page {page}")
        return await self._request("GET", "/quotes", params=params)

    async def get_quote(self, quote_id: str) -> dict[str, Any]:
        """
        Get a single quote by ID.

        Args:
            quote_id: Pennylane quote ID

        Returns:
            Quote data
        """
        logger.info(f"Fetching quote {quote_id}")
        return await self._request("GET", f"/quotes/{quote_id}")

    async def list_subscriptions(
        self,
        page: int = 1,
        per_page: int = 100,
        **filters: Any,
    ) -> dict[str, Any]:
        """
        List billing subscriptions with pagination.

        Args:
            page: Page number (1-based)
            per_page: Number of items per page (max 100)
            **filters: Additional filter parameters

        Returns:
            Paginated list of subscriptions
        """
        params = {"page": page, "per_page": min(per_page, 100), **filters}
        logger.info(f"Fetching subscriptions page {page}")
        return await self._request("GET", "/billing_subscriptions", params=params)

    async def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        """
        Get a single subscription by ID.

        Args:
            subscription_id: Pennylane subscription ID

        Returns:
            Subscription data
        """
        logger.info(f"Fetching subscription {subscription_id}")
        return await self._request("GET", f"/billing_subscriptions/{subscription_id}")

    async def fetch_all_pages(
        self,
        endpoint: str,
        per_page: int = 100,
        **filters: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Fetch all pages from a paginated endpoint using cursor-based pagination.

        Pennylane uses cursor-based pagination with:
        - `per_page`: Number of items per page (max 100)
        - `cursor`: Cursor for the next page (from previous response)
        - Response contains: `items`, `has_more`, `next_cursor`

        Args:
            endpoint: API endpoint (e.g., "/customers")
            per_page: Number of items per page (max 100)
            **filters: Additional filter parameters

        Yields:
            Individual items from all pages
        """
        per_page = min(per_page, 100)
        cursor: Optional[str] = None
        page_num = 0

        while True:
            page_num += 1
            params = {"per_page": per_page, **filters}
            if cursor:
                params["cursor"] = cursor

            logger.info(f"Fetching {endpoint} page {page_num}" + (f" (cursor: {cursor[:20]}...)" if cursor else ""))

            response = await self._request("GET", endpoint, params=params)

            # Extract items from response
            items = []
            if isinstance(response, list):
                items = response
            elif isinstance(response, dict):
                # Pennylane returns items in "items" key
                items = response.get("items", [])

            if not items:
                logger.info(f"No more items from {endpoint} after {page_num} pages")
                break

            for item in items:
                yield item

            # Check if there are more pages using cursor-based pagination
            if isinstance(response, dict):
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")

                if has_more and next_cursor:
                    cursor = next_cursor
                else:
                    logger.info(f"Finished fetching {endpoint}: {page_num} pages")
                    break
            else:
                # If response is a list, we can't paginate
                break


# =============================================================================
# Pennylane Sync Service
# =============================================================================


class PennylaneSyncService:
    """
    Service for syncing Pennylane data to the local database.

    Handles fetching data from the API and upserting to local models.
    """

    def __init__(self, db: Session, connection: PennylaneConnection):
        """
        Initialize the sync service.

        Args:
            db: SQLAlchemy database session
            connection: PennylaneConnection with API credentials
        """
        self.db = db
        self.connection = connection
        self.client = PennylaneClient(connection.api_token)

    async def _run_sync(self, sync_func) -> SyncResult:
        """Run a sync function with the client context manager."""
        async with self.client:
            return await sync_func()

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse a date string from the API."""
        if not date_str:
            return None
        try:
            # Handle various date formats
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    return datetime.strptime(date_str.split("T")[0], "%Y-%m-%d").date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse a datetime string from the API."""
        if not dt_str:
            return None
        try:
            # Handle ISO format with optional timezone
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"
            return datetime.fromisoformat(dt_str)
        except Exception:
            return None

    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse a decimal value from the API."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Customer Sync
    # -------------------------------------------------------------------------

    async def sync_customers(self) -> SyncResult:
        """
        Sync all customers from Pennylane.

        Returns:
            SyncResult with counts and any errors
        """
        result = SyncResult(entity_type="customers")
        logger.info(f"Starting customer sync for connection {self.connection.name}")

        try:
            async with self.client:
                async for customer_data in self.client.fetch_all_pages("/customers"):
                    result.total_fetched += 1

                    try:
                        pennylane_id = str(customer_data.get("id", customer_data.get("source_id", "")))
                        if not pennylane_id:
                            result.add_error(f"Customer missing ID: {customer_data}")
                            continue

                        # Check if customer exists
                        existing = (
                            self.db.query(PennylaneCustomer)
                            .filter(
                                PennylaneCustomer.connection_id == self.connection.id,
                                PennylaneCustomer.pennylane_id == pennylane_id,
                            )
                            .first()
                        )

                        # Extract nested address objects
                        billing_address = customer_data.get("billing_address") or {}
                        delivery_address = customer_data.get("delivery_address") or {}

                        # Extract customer fields
                        customer_values = {
                            "pennylane_id": pennylane_id,
                            "connection_id": self.connection.id,
                            "name": customer_data.get("name") or customer_data.get("company_name"),
                            "first_name": customer_data.get("first_name"),
                            "last_name": customer_data.get("last_name"),
                            "email": customer_data.get("email") or customer_data.get("emails", [None])[0] if customer_data.get("emails") else None,
                            "phone": customer_data.get("phone"),
                            # Billing address - prefer nested billing_address object, fallback to root
                            "address": billing_address.get("address") or customer_data.get("address"),
                            "city": billing_address.get("city") or customer_data.get("city"),
                            "postal_code": billing_address.get("postal_code") or customer_data.get("postal_code") or customer_data.get("zipcode"),
                            "country_code": billing_address.get("country_alpha2") or customer_data.get("country") or customer_data.get("country_alpha2"),
                            # Delivery address
                            "delivery_address": delivery_address.get("address") or None,
                            "delivery_city": delivery_address.get("city") or None,
                            "delivery_postal_code": delivery_address.get("postal_code") or None,
                            "delivery_country_code": delivery_address.get("country_alpha2") or None,
                            # Standard fields
                            "vat_number": customer_data.get("vat_number"),
                            "customer_type": customer_data.get("customer_type") or ("company" if customer_data.get("company_name") else "individual"),
                            # Additional fields
                            "reg_no": customer_data.get("reg_no"),
                            "recipient": customer_data.get("recipient"),
                            "reference": customer_data.get("reference"),
                            "external_reference": customer_data.get("external_reference"),
                            "billing_language": customer_data.get("billing_language"),
                            "payment_conditions": customer_data.get("payment_conditions"),
                            "notes": customer_data.get("notes"),
                            "billing_iban": customer_data.get("billing_iban"),
                            # Pennylane timestamps
                            "pennylane_created_at": self._parse_datetime(customer_data.get("created_at")),
                            "pennylane_updated_at": self._parse_datetime(customer_data.get("updated_at")),
                            "raw_data": customer_data,
                            "synced_at": func.now(),
                        }

                        if existing:
                            # Update existing customer
                            for key, value in customer_values.items():
                                if key != "connection_id":
                                    setattr(existing, key, value)
                            result.updated += 1
                        else:
                            # Create new customer
                            new_customer = PennylaneCustomer(**customer_values)
                            self.db.add(new_customer)
                            result.created += 1

                    except Exception as e:
                        error_msg = f"Error processing customer {customer_data.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        result.add_error(error_msg)

                self.db.commit()
                logger.info(f"Customer sync complete: {result}")

        except PennylaneAPIError as e:
            error_msg = f"API error during customer sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        except Exception as e:
            error_msg = f"Unexpected error during customer sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        return result

    def _extract_pdf_url(self, data: dict[str, Any]) -> Optional[str]:
        """
        Extract PDF URL from raw data, checking multiple possible field names.

        Args:
            data: Raw API response data

        Returns:
            PDF URL if found, None otherwise
        """
        # Check multiple possible field names for the PDF URL
        for field in ("public_file_url", "file_url", "pdf_invoice_url", "public_url", "pdf_url"):
            url = data.get(field)
            if url and isinstance(url, str) and url.startswith("http"):
                return url
        return None

    # -------------------------------------------------------------------------
    # Invoice Sync
    # -------------------------------------------------------------------------

    async def sync_invoices(self, customer_lookup: Optional[dict[str, str]] = None) -> SyncResult:
        """
        Sync all invoices from Pennylane.

        Args:
            customer_lookup: Optional dict mapping customer pennylane_id to customer name

        Returns:
            SyncResult with counts and any errors
        """
        if customer_lookup is None:
            customer_lookup = {}
        result = SyncResult(entity_type="invoices")
        logger.info(f"Starting invoice sync for connection {self.connection.name}")

        try:
            async with self.client:
                async for invoice_data in self.client.fetch_all_pages("/customer_invoices"):
                    result.total_fetched += 1

                    try:
                        pennylane_id = str(invoice_data.get("id", ""))
                        if not pennylane_id:
                            result.add_error(f"Invoice missing ID: {invoice_data}")
                            continue

                        # Check if invoice exists
                        existing = (
                            self.db.query(PennylaneInvoice)
                            .filter(
                                PennylaneInvoice.connection_id == self.connection.id,
                                PennylaneInvoice.pennylane_id == pennylane_id,
                            )
                            .first()
                        )

                        # Extract customer info - API returns customer as {'id': 123, 'url': '...'} without name
                        customer = invoice_data.get("customer", {})
                        customer_id = str(customer.get("id")) if isinstance(customer, dict) and customer.get("id") else None

                        # Extract invoice fields
                        invoice_values = {
                            "pennylane_id": pennylane_id,
                            "connection_id": self.connection.id,
                            "invoice_number": invoice_data.get("invoice_number") or invoice_data.get("label"),
                            "status": invoice_data.get("status"),
                            "customer_name": customer_lookup.get(customer_id) if customer_id else None,
                            "customer_id": customer_id,
                            "amount": self._parse_decimal(invoice_data.get("amount") or invoice_data.get("total")),
                            "currency": invoice_data.get("currency", "EUR"),
                            "issue_date": self._parse_date(invoice_data.get("date") or invoice_data.get("issue_date")),
                            "due_date": self._parse_date(invoice_data.get("deadline") or invoice_data.get("due_date")),
                            "paid_date": self._parse_date(invoice_data.get("paid_date")),
                            "pdf_url": self._extract_pdf_url(invoice_data),
                            "raw_data": invoice_data,
                            "synced_at": func.now(),
                        }

                        if existing:
                            # Update existing invoice
                            for key, value in invoice_values.items():
                                if key != "connection_id":
                                    setattr(existing, key, value)
                            result.updated += 1
                        else:
                            # Create new invoice
                            new_invoice = PennylaneInvoice(**invoice_values)
                            self.db.add(new_invoice)
                            result.created += 1

                    except Exception as e:
                        error_msg = f"Error processing invoice {invoice_data.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        result.add_error(error_msg)

                self.db.commit()
                logger.info(f"Invoice sync complete: {result}")

        except PennylaneAPIError as e:
            error_msg = f"API error during invoice sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        except Exception as e:
            error_msg = f"Unexpected error during invoice sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        return result

    # -------------------------------------------------------------------------
    # Quote Sync
    # -------------------------------------------------------------------------

    async def sync_quotes(self, customer_lookup: Optional[dict[str, str]] = None) -> SyncResult:
        """
        Sync all quotes from Pennylane.

        Args:
            customer_lookup: Optional dict mapping customer pennylane_id to customer name

        Returns:
            SyncResult with counts and any errors
        """
        if customer_lookup is None:
            customer_lookup = {}
        result = SyncResult(entity_type="quotes")
        logger.info(f"Starting quote sync for connection {self.connection.name}")

        try:
            async with self.client:
                async for quote_data in self.client.fetch_all_pages("/quotes"):
                    result.total_fetched += 1

                    try:
                        pennylane_id = str(quote_data.get("id", ""))
                        if not pennylane_id:
                            result.add_error(f"Quote missing ID: {quote_data}")
                            continue

                        # Check if quote exists
                        existing = (
                            self.db.query(PennylaneQuote)
                            .filter(
                                PennylaneQuote.connection_id == self.connection.id,
                                PennylaneQuote.pennylane_id == pennylane_id,
                            )
                            .first()
                        )

                        # Extract customer info - API returns customer as {'id': 123, 'url': '...'} without name
                        customer = quote_data.get("customer", {})
                        customer_id = str(customer.get("id")) if isinstance(customer, dict) and customer.get("id") else None

                        # Extract quote fields
                        quote_values = {
                            "pennylane_id": pennylane_id,
                            "connection_id": self.connection.id,
                            "quote_number": quote_data.get("quote_number") or quote_data.get("label"),
                            "status": quote_data.get("status"),
                            "customer_name": customer_lookup.get(customer_id) if customer_id else None,
                            "customer_id": customer_id,
                            "amount": self._parse_decimal(quote_data.get("amount") or quote_data.get("total")),
                            "currency": quote_data.get("currency", "EUR"),
                            "issue_date": self._parse_date(quote_data.get("date") or quote_data.get("issue_date")),
                            "valid_until": self._parse_date(quote_data.get("deadline") or quote_data.get("expiry_date")),
                            "accepted_at": self._parse_datetime(quote_data.get("accepted_at")),
                            "raw_data": quote_data,
                            "synced_at": func.now(),
                        }

                        if existing:
                            # Update existing quote
                            for key, value in quote_values.items():
                                if key != "connection_id":
                                    setattr(existing, key, value)
                            result.updated += 1
                        else:
                            # Create new quote
                            new_quote = PennylaneQuote(**quote_values)
                            self.db.add(new_quote)
                            result.created += 1

                    except Exception as e:
                        error_msg = f"Error processing quote {quote_data.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        result.add_error(error_msg)

                self.db.commit()
                logger.info(f"Quote sync complete: {result}")

        except PennylaneAPIError as e:
            error_msg = f"API error during quote sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        except Exception as e:
            error_msg = f"Unexpected error during quote sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        return result

    # -------------------------------------------------------------------------
    # Subscription Sync
    # -------------------------------------------------------------------------

    async def sync_subscriptions(self, customer_lookup: Optional[dict[str, str]] = None) -> SyncResult:
        """
        Sync all billing subscriptions from Pennylane.

        Args:
            customer_lookup: Optional dict mapping customer pennylane_id to customer name

        Returns:
            SyncResult with counts and any errors
        """
        if customer_lookup is None:
            customer_lookup = {}
        result = SyncResult(entity_type="subscriptions")
        logger.info(f"Starting subscription sync for connection {self.connection.name}")

        try:
            async with self.client:
                async for sub_data in self.client.fetch_all_pages("/billing_subscriptions"):
                    result.total_fetched += 1

                    try:
                        pennylane_id = str(sub_data.get("id", ""))
                        if not pennylane_id:
                            result.add_error(f"Subscription missing ID: {sub_data}")
                            continue

                        # Check if subscription exists
                        existing = (
                            self.db.query(PennylaneSubscription)
                            .filter(
                                PennylaneSubscription.connection_id == self.connection.id,
                                PennylaneSubscription.pennylane_id == pennylane_id,
                            )
                            .first()
                        )

                        # Extract customer info - API returns customer as {'id': 123, 'url': '...'} without name
                        customer = sub_data.get("customer", {})
                        customer_id = str(customer.get("id")) if isinstance(customer, dict) and customer.get("id") else None

                        # Extract subscription fields
                        # Amount and currency are in customer_invoice_data
                        invoice_data = sub_data.get("customer_invoice_data", {}) or {}
                        recurring_rule = sub_data.get("recurring_rule", {}) or {}

                        sub_values = {
                            "pennylane_id": pennylane_id,
                            "connection_id": self.connection.id,
                            "status": sub_data.get("status"),
                            "customer_name": customer_lookup.get(customer_id) if customer_id else None,
                            "customer_id": customer_id,
                            "amount": self._parse_decimal(invoice_data.get("amount") or sub_data.get("amount")),
                            "currency": invoice_data.get("currency") or sub_data.get("currency", "EUR"),
                            "interval": recurring_rule.get("rule_type") or sub_data.get("interval"),
                            "start_date": self._parse_date(sub_data.get("start") or sub_data.get("start_date")),
                            "next_billing_date": self._parse_date(sub_data.get("next_occurrence") or sub_data.get("next_billing_date")),
                            "cancelled_at": self._parse_datetime(sub_data.get("stopped_at") or sub_data.get("cancelled_at")),
                            "raw_data": sub_data,
                            "synced_at": func.now(),
                        }

                        if existing:
                            # Update existing subscription
                            for key, value in sub_values.items():
                                if key != "connection_id":
                                    setattr(existing, key, value)
                            result.updated += 1
                        else:
                            # Create new subscription
                            new_sub = PennylaneSubscription(**sub_values)
                            self.db.add(new_sub)
                            result.created += 1

                    except Exception as e:
                        error_msg = f"Error processing subscription {sub_data.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        result.add_error(error_msg)

                self.db.commit()
                logger.info(f"Subscription sync complete: {result}")

        except PennylaneAPIError as e:
            error_msg = f"API error during subscription sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        except Exception as e:
            error_msg = f"Unexpected error during subscription sync: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            self.db.rollback()

        return result

    # -------------------------------------------------------------------------
    # Full Sync
    # -------------------------------------------------------------------------

    async def sync_all(self) -> dict[str, SyncResult]:
        """
        Sync all enabled entity types for this connection.

        Updates connection.last_sync_at, last_sync_status, and last_sync_error.

        Returns:
            Dictionary mapping entity type to SyncResult
        """
        results: dict[str, SyncResult] = {}
        all_success = True
        errors: list[str] = []

        logger.info(f"Starting full sync for connection {self.connection.name}")

        try:
            # Sync customers if enabled
            if self.connection.sync_customers:
                results["customers"] = await self.sync_customers()
                if not results["customers"].success:
                    all_success = False
                    errors.extend(results["customers"].errors)

            # Build customer lookup dict for resolving customer names in invoices/quotes/subscriptions
            # The Pennylane API returns customer as {'id': 123, 'url': '...'} without the actual name,
            # so we need to look up the name from our synced customers table
            customer_lookup: dict[str, str] = {}
            customers = self.db.query(PennylaneCustomer).filter(
                PennylaneCustomer.connection_id == self.connection.id
            ).all()
            for c in customers:
                if c.pennylane_id and c.name:
                    customer_lookup[c.pennylane_id] = c.name

            # Sync invoices if enabled
            if self.connection.sync_invoices:
                results["invoices"] = await self.sync_invoices(customer_lookup)
                if not results["invoices"].success:
                    all_success = False
                    errors.extend(results["invoices"].errors)

            # Sync quotes if enabled
            if self.connection.sync_quotes:
                results["quotes"] = await self.sync_quotes(customer_lookup)
                if not results["quotes"].success:
                    all_success = False
                    errors.extend(results["quotes"].errors)

            # Sync subscriptions if enabled
            if self.connection.sync_subscriptions:
                results["subscriptions"] = await self.sync_subscriptions(customer_lookup)
                if not results["subscriptions"].success:
                    all_success = False
                    errors.extend(results["subscriptions"].errors)

            # Update connection sync status
            self.connection.last_sync_at = func.now()
            self.connection.last_sync_status = "success" if all_success else "partial" if results else "failed"
            self.connection.last_sync_error = "\n".join(errors) if errors else None
            self.db.commit()

            logger.info(
                f"Full sync complete for connection {self.connection.name}: "
                f"status={self.connection.last_sync_status}"
            )

        except Exception as e:
            error_msg = f"Unexpected error during full sync: {e}"
            logger.error(error_msg)

            self.connection.last_sync_at = func.now()
            self.connection.last_sync_status = "failed"
            self.connection.last_sync_error = error_msg
            self.db.commit()

        return results
