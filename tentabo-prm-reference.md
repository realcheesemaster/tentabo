# Tentabo PRM - Project Reference Document

## Project Overview

**Name:** Tentabo PRM (Partner Relationship Management)
**Type:** Web Application with REST API
**Stack:** Python/FastAPI backend, React frontend with shadcn UI, responsive design
**Localization:** Bilingual (French and English)
**CRM Integration:** Pipedrive for lead management

## Key Architecture Decisions

### Why Python/FastAPI Backend?
1. **Financial Accuracy:** Native Decimal type for pricing calculations
2. **LDAP Excellence:** Superior python-ldap3 library for Oxiadmin integration
3. **Enterprise Integration:** Better support for French business software
4. **FastAPI Benefits:** Automatic OpenAPI docs, Pydantic validation, async support
5. **Complex Queries:** SQLAlchemy 2.0 handles multi-tenant filtering elegantly

### Core Features Summary
- **Lead Management:** CRM integration for sales pipeline (Pipedrive initially, pluggable)
- **Order Processing:** State machine workflow from lead to contract
- **Progressive Pricing:** Tier-based pricing with duration discounts
- **Multi-tenancy:** Distributors manage partners, strict data isolation
- **Pluggable Integrations:** Abstracted providers for Auth, CRM, and Billing
  - **Auth Providers:** LDAP (Oxiadmin), SSO, Database, OAuth providers
  - **CRM Providers:** Pipedrive, Salesforce, HubSpot, etc.
  - **Billing Providers:** Pennylane, QuickBooks, Xero, Stripe, etc.

### Development Approach
- **Direct Integration:** Full access to all production APIs and servers from day one
- **No Mocking Required:** Live development against actual services
- **Early Validation:** Test integrations immediately in development
- **Faster Iteration:** No mock-to-real transition overhead

### Production Access Benefits
**Advantages:**
- **Real-world Testing:** Discover edge cases and API quirks immediately
- **Accurate Performance Metrics:** Understand actual response times and limits
- **Schema Validation:** Work with real data structures from the start
- **Early Integration Issues Detection:** Find compatibility problems in week 1, not week 12
- **No Mock Maintenance:** Save time by not building/maintaining mock services

**Development Safeguards:**
- **Separate Development Tenant:** Use dedicated test accounts in Pipedrive/Pennylane
- **Rate Limit Awareness:** Implement throttling from day one
- **Audit Logging:** Track all API calls during development
- **Rollback Capability:** Ensure all operations are reversible
- **Credential Security:** Use environment variables, never commit secrets

## Pluggable Architecture Design

### Provider Abstraction Strategy

The system is designed with a **provider-based architecture** where core business logic is decoupled from external integrations. This allows swapping providers without changing business logic.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class ProviderType(Enum):
    AUTH = "auth"
    CRM = "crm"
    BILLING = "billing"

# Authentication Provider Interface
class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user and return user object"""
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        """Retrieve user information"""
        pass

    @abstractmethod
    async def sync_users(self) -> List[User]:
        """Sync users from external system"""
        pass

# CRM Provider Interface
class CRMProvider(ABC):
    @abstractmethod
    async def create_lead(self, lead_data: Lead) -> Dict[str, Any]:
        """Create lead in CRM system"""
        pass

    @abstractmethod
    async def update_lead(self, lead_id: str, data: Dict) -> bool:
        """Update lead status/data"""
        pass

    @abstractmethod
    async def sync_leads(self) -> List[Lead]:
        """Sync leads from CRM"""
        pass

# Billing Provider Interface
class BillingProvider(ABC):
    @abstractmethod
    async def create_quote(self, order: Order) -> str:
        """Generate quote from order"""
        pass

    @abstractmethod
    async def create_invoice(self, contract: Contract) -> str:
        """Create invoice from contract"""
        pass

    @abstractmethod
    async def sync_invoices(self) -> List[Invoice]:
        """Sync invoices from billing system"""
        pass

# Provider Registry
class ProviderRegistry:
    def __init__(self):
        self._providers = {}
        self._active_providers = {}

    def register(self, provider_type: ProviderType, name: str, provider_class):
        """Register a provider implementation"""
        if provider_type not in self._providers:
            self._providers[provider_type] = {}
        self._providers[provider_type][name] = provider_class

    def get_active(self, provider_type: ProviderType) -> Any:
        """Get the currently active provider for a type"""
        return self._active_providers.get(provider_type)
```

### Provider Implementations

```python
# Concrete implementations for initial providers
class OxiadminLDAPProvider(AuthProvider):
    """Oxiadmin LDAP authentication provider"""
    async def authenticate(self, username: str, password: str):
        # LDAP authentication logic
        pass

class DatabaseAuthProvider(AuthProvider):
    """Database-based authentication provider"""
    async def authenticate(self, username: str, password: str):
        # Database authentication logic
        pass

class PipedriveProvider(CRMProvider):
    """Pipedrive CRM provider"""
    async def create_lead(self, lead_data: Lead):
        # Pipedrive API call
        pass

class PennylaneProvider(BillingProvider):
    """Pennylane billing provider"""
    async def create_quote(self, order: Order):
        # Pennylane API call
        pass
```

### Provider Configuration Management

```python
class ProviderConfig(BaseModel):
    """Provider configuration stored in database"""
    id: UUID
    provider_type: ProviderType
    provider_name: str  # 'oxiadmin_ldap', 'pipedrive', etc.
    is_active: bool
    configuration: Dict[str, Any]  # JSONB field for provider-specific config
    credentials: Dict[str, Any]  # Encrypted JSONB for sensitive data
    created_at: datetime
    updated_at: datetime

# Database table for provider configurations
class ProviderConfigDB(Base):
    __tablename__ = 'provider_configs'

    id = Column(UUID, primary_key=True)
    provider_type = Column(Enum(ProviderType))
    provider_name = Column(String)
    is_active = Column(Boolean, default=False)
    configuration = Column(JSONB)  # Non-sensitive config
    credentials = Column(JSONB)  # Encrypted sensitive data
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

### Admin Interface for Provider Management

The admin interface allows managing provider configurations:

1. **Provider Configuration UI**
   - List all available providers by type
   - Configure provider settings (API keys, endpoints, etc.)
   - Test provider connections
   - Switch active providers
   - View provider health/status

2. **Provider Switching Logic**
   ```python
   async def switch_provider(provider_type: ProviderType, new_provider_name: str):
       # Deactivate current provider
       # Activate new provider
       # Run validation tests
       # Update active provider in registry
   ```

## Analysis and Comments

### 1. Architecture Considerations

#### Frontend
- **shadcn/ui** is an excellent choice for a modern, accessible component library
- Built on Radix UI primitives with Tailwind CSS
- Ensures consistent, professional UI with built-in accessibility
- Recommendation: Use Next.js or Vite+React for the frontend framework

#### Backend (Python/FastAPI)
- **FastAPI** provides automatic OpenAPI documentation and validation
- **Python** offers superior financial calculation precision with Decimal type
- Key implementation points:
  - JWT-based authentication with refresh tokens
  - Built-in rate limiting with slowapi
  - API versioning from the start (e.g., /api/v1/)
  - Automatic OpenAPI/Swagger documentation via FastAPI
  - Pydantic models for request/response validation
  - SQLAlchemy 2.0 for ORM with complex query support

### 2. User Roles & Authorization Matrix

#### Core Operations Permissions
| Role | Create Order | View Own Contracts | View Partner Contracts | View Distributor Contracts | Activate Contracts | Manage Contracts | Delete Orders | Reassign |
|------|-------------|-------------------|----------------------|---------------------------|-------------------|------------------|---------------|----------|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Restricted Admin** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Partner** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Distributor** | ❌ | ✅ | ✅ (attached only) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Fulfiller** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |

#### Lead Management Permissions (Pipedrive)
| Role | Create Leads | View Own Leads | View Partner Leads | Update Lead Status | Delete Leads | View Lead Analytics |
|------|-------------|----------------|-------------------|-------------------|--------------|-------------------|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Restricted Admin** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Partner** | ✅ | ✅ | ❌ | ✅ (own only) | ❌ | ✅ (own only) |
| **Distributor** | ✅ | ✅ | ✅ (attached only) | ✅ (own + attached) | ❌ | ✅ (own + attached) |
| **Fulfiller** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Key Observations:**
- Role hierarchy is well-defined with lead management added
- Partners and distributors can manage their own sales pipeline
- Consider implementing Role-Based Access Control (RBAC) with policy-based permissions
- Fulfiller role has no access to CRM functions

### 3. Data Model Analysis

#### Core Entities

##### Product
```python
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID

class PeriodEnum(str, Enum):
    YEAR = "year"
    MONTH = "month"

class PriceTier(BaseModel):
    min_quantity: int = Field(ge=0)
    max_quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(decimal_places=2)
    period: PeriodEnum

class Product(BaseModel):
    id: UUID
    type: str  # 'appliance', etc.
    unit: str  # 'TB', 'GB', etc.
    name: str
    progressive_price_list: List[PriceTier]
```

**Comments:**
- Progressive pricing with Decimal precision for financial accuracy
- Price tier transitions validated with Pydantic
- Consider storing price history for audit purposes

##### Duration & Subscription
```python
class Duration(BaseModel):
    months: int = Field(gt=0)
    discount_percentage: Decimal = Field(ge=0, le=100)

class Subscription(BaseModel):
    product: Product
    duration: Duration
    quantity: int = Field(gt=0)
```

##### Lead (Provider-Agnostic)
```python
class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"

class Lead(BaseModel):
    """Provider-agnostic lead model"""
    id: UUID
    # Provider tracking
    provider_name: str  # 'pipedrive', 'salesforce', 'hubspot', etc.
    provider_id: Optional[str]  # External ID from the CRM provider
    provider_metadata: Dict[str, Any]  # JSONB field for provider-specific data

    # Core fields (common across all CRM providers)
    title: str
    organization: str
    contact_name: str
    contact_email: str
    contact_phone: Optional[str]
    value: Optional[Decimal]
    currency: str = "EUR"
    status: LeadStatus
    probability: Optional[int] = Field(ge=0, le=100)
    expected_close_date: Optional[datetime]

    # Relationships
    owner: User  # Partner or Distributor who owns the lead
    distributor: Optional[Distributor]
    partner: Optional[Partner]

    # Internal data
    notes: List[Note]
    activities: List[Activity]  # Synced from CRM provider
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime]
```

##### Order
```python
class OrderStatus(str, Enum):
    CREATED = "created"
    CANCELLED = "cancelled"
    SENT = "sent"
    IN_FULFILLMENT = "in_fulfillment"
    FULFILLED = "fulfilled"

class Order(BaseModel):
    """Provider-agnostic order model"""
    id: UUID
    subscriptions: List[Subscription]
    products: List[ProductOrder]
    status: OrderStatus
    notes: List[Note]

    # Provider tracking for billing system
    billing_provider: Optional[str]  # 'pennylane', 'quickbooks', 'xero', etc.
    billing_quote_id: Optional[str]  # External quote ID from billing provider
    billing_metadata: Dict[str, Any]  # JSONB for provider-specific data

    # CRM tracking
    crm_provider: Optional[str]  # 'pipedrive', 'salesforce', etc.
    crm_deal_id: Optional[str]  # External deal/opportunity ID
    crm_metadata: Dict[str, Any]  # JSONB for CRM-specific data

    created_by: User
    partner: Optional[Partner]
    distributor: Optional[Distributor]
    lead_id: Optional[UUID]  # Reference to originating lead
```

**Critical Points:**
- Status workflow needs strict state transitions
- Notes system with visibility controls adds complexity
- Integration with both Pennylane and Pipedrive
- Orders can be traced back to originating leads

##### Contract
```python
class ContractStatus(str, Enum):
    ACTIVE = "active"
    LOST = "lost"
    UPGRADED = "upgraded"
    DOWNGRADED = "downgraded"

class Contract(BaseModel):
    """Provider-agnostic contract model"""
    id: UUID
    order: Order
    distributor: Optional[Distributor]
    partner: Optional[Partner]
    user: User  # from auth provider

    # Billing provider tracking
    billing_provider: str  # 'pennylane', 'quickbooks', etc.
    billing_invoices: List[str]  # External invoice IDs
    billing_metadata: Dict[str, Any]  # JSONB for provider-specific data

    status: ContractStatus
    activation_date: datetime
    expiration_date: Optional[datetime]
```

### 4. Integration Points (Provider-Based)

#### Provider Categories

##### Authentication Providers
**Initial Provider: Oxiadmin LDAP**
- User authentication and authorization
- Partner and user account lookup
- Role synchronization from LDAP groups

**Future Providers:**
- Generic LDAP (different schema)
- OAuth 2.0 providers (Google, Microsoft)
- SAML SSO providers
- Database authentication
- Keycloak integration

##### CRM Providers
**Initial Provider: Pipedrive**
- Lead/Deal management and synchronization
- Activity tracking and follow-ups
- Sales pipeline visualization
- Two-way sync for leads and deals
- Webhook support for real-time updates

**Future Providers:**
- Salesforce
- HubSpot
- Microsoft Dynamics 365
- Zoho CRM
- Custom CRM via API

##### Billing/Accounting Providers
**Initial Provider: Pennylane**
- Quote generation from orders
- Invoice creation and tracking
- Customer synchronization
- Payment status tracking

**Future Providers:**
- QuickBooks
- Xero
- Stripe Billing
- Chargebee
- Custom billing systems

#### Provider Implementation Pattern

```python
# Each provider implements the abstract interface
class OxiadminLDAPProvider(AuthProvider):
    def __init__(self, config: Dict[str, Any]):
        self.server = config['server']
        self.base_dn = config['base_dn']
        self.bind_dn = config['bind_dn']
        # Initialize LDAP connection

class SalesforceProvider(CRMProvider):
    def __init__(self, config: Dict[str, Any]):
        self.instance_url = config['instance_url']
        self.access_token = config['access_token']
        # Initialize Salesforce client

class QuickBooksProvider(BillingProvider):
    def __init__(self, config: Dict[str, Any]):
        self.company_id = config['company_id']
        self.access_token = config['access_token']
        # Initialize QuickBooks client

# Provider factory
class ProviderFactory:
    @staticmethod
    def create_provider(provider_type: ProviderType, provider_name: str, config: Dict):
        providers = {
            (ProviderType.AUTH, 'oxiadmin_ldap'): OxiadminLDAPProvider,
            (ProviderType.AUTH, 'database'): DatabaseAuthProvider,
            (ProviderType.CRM, 'pipedrive'): PipedriveProvider,
            (ProviderType.CRM, 'salesforce'): SalesforceProvider,
            (ProviderType.BILLING, 'pennylane'): PennylaneProvider,
            (ProviderType.BILLING, 'quickbooks'): QuickBooksProvider,
        }
        provider_class = providers.get((provider_type, provider_name))
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_class(config)
```

**Recommendations:**
- Implement integration abstraction layer for clean architecture
- Use Celery + Redis for async operations and queuing
- Implement retry mechanisms with exponential backoff
- Store external IDs for reconciliation
- Log all integration events for audit trail
- Use circuit breaker pattern for external services
- **Week 1 Priority:** Establish all API connections and verify access
- **Development Data:** Create dedicated test data in production systems
- **Monitor Usage:** Track API calls to stay within rate limits during development

### 5. Technical Challenges & Solutions

#### Challenge 1: Complex Pricing Calculations
- **Issue:** Progressive pricing with duration discounts
- **Solution:** Implement dedicated pricing engine service using Decimal precision
- **Implementation:** Python's decimal module for financial accuracy
- **Consideration:** Cache calculations for performance

#### Challenge 2: Multi-tenant Data Access
- **Issue:** Distributors see attached partners only
- **Solution:** Row-level security with SQLAlchemy filters
- **Consideration:** Optimize queries with proper indexing

#### Challenge 3: Order-to-Contract Workflow
- **Issue:** Multi-step process with external dependencies
- **Solution:** Implement state machine pattern with transitions library
- **Consideration:** Handle partial failures gracefully

#### Challenge 4: Multi-System Synchronization
- **Issue:** Keep Pipedrive, Pennylane, and local data in sync
- **Solution:** Event-driven architecture with Celery tasks
- **Implementation:**
  ```python
  @celery_task
  def sync_lead_to_pipedrive(lead_id: UUID):
      # Async sync with retry logic
      pass
  ```
- **Consideration:** Implement conflict resolution strategy

### 6. Security Considerations

1. **Authentication & Authorization**
   - LDAP integration for SSO
   - JWT tokens with proper expiration
   - Role-based permissions at API level

2. **Data Protection**
   - Encrypt sensitive data at rest
   - Use HTTPS for all communications
   - Implement audit logging

3. **Multi-tenancy**
   - Strict data isolation between distributors/partners
   - Validate all access requests against ownership

### 7. Database Design Recommendations

**Technology Choice:** PostgreSQL
- Robust support for complex relationships
- JSONB for flexible product configurations and integration metadata
- Row-level security capabilities
- Excellent performance with proper indexing
- Native UUID support

**Key Tables:**
```sql
-- Core business entities
- users (synced with auth provider)
- products
- price_tiers
- durations
- orders
- order_items
- contracts

-- CRM entities (provider-agnostic)
- leads (with provider_name, provider_id, provider_metadata JSONB)
- lead_activities
- lead_notes
- lead_status_history

-- Relationship management
- partners
- distributors
- distributor_partners (junction table)

-- Provider configuration
- provider_configs (provider settings and credentials)
- provider_types (auth, crm, billing)
- provider_sync_logs (track all provider syncs)
- provider_webhooks (webhook configurations per provider)

-- Integration tracking
- integration_mappings (external_id, internal_id, entity_type, provider_name)
- sync_queue (pending sync operations)
- sync_conflicts (handle data conflicts between providers)

-- System
- notes (polymorphic: order, contract, lead)
- audit_logs
- webhook_events
```

**Provider Configuration Schema:**
```sql
CREATE TABLE provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_type VARCHAR(20) NOT NULL, -- 'auth', 'crm', 'billing'
    provider_name VARCHAR(50) NOT NULL,  -- 'oxiadmin_ldap', 'pipedrive', etc.
    is_active BOOLEAN DEFAULT FALSE,
    configuration JSONB NOT NULL,        -- Non-sensitive settings
    credentials JSONB,                   -- Encrypted sensitive data
    health_status VARCHAR(20),           -- 'healthy', 'degraded', 'offline'
    last_health_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider_type, provider_name),
    -- Only one active provider per type
    UNIQUE(provider_type, is_active) WHERE is_active = true
);

CREATE TABLE provider_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(50) NOT NULL,
    sync_type VARCHAR(50),               -- 'full', 'incremental', 'webhook'
    entity_type VARCHAR(50),             -- 'lead', 'user', 'invoice'
    records_synced INTEGER,
    records_failed INTEGER,
    error_details JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20)                   -- 'success', 'partial', 'failed'
);
```

**Key Indexes:**
```sql
-- Performance-critical indexes
CREATE INDEX idx_leads_owner_status ON leads(owner_id, status);
CREATE INDEX idx_leads_distributor_partner ON leads(distributor_id, partner_id);
CREATE INDEX idx_leads_provider ON leads(provider_name, provider_id);
CREATE INDEX idx_orders_status_created ON orders(status, created_at DESC);

-- Provider-related indexes
CREATE INDEX idx_provider_configs_active ON provider_configs(provider_type, is_active);
CREATE INDEX idx_integration_mappings ON integration_mappings(provider_name, entity_type, external_id);
CREATE INDEX idx_provider_sync_logs ON provider_sync_logs(provider_name, created_at DESC);

-- JSONB indexes for provider metadata queries
CREATE INDEX idx_leads_metadata ON leads USING gin(provider_metadata);
CREATE INDEX idx_orders_billing_metadata ON orders USING gin(billing_metadata);
```

---

## Development Action Plan

### Phase 1: Foundation & Provider Architecture (Week 1-2)
- [ ] **Project Setup**
  - Initialize project structure (backend/frontend/docs)
  - Set up Python 3.11+ virtual environment
  - Configure Poetry for dependency management
  - Set up Git repository with branching strategy
  - Create Docker Compose for local development

- [ ] **Core Python Infrastructure**
  - FastAPI application structure
  - Pydantic models and validation schemas
  - SQLAlchemy 2.0 setup with Alembic migrations
  - Configure pytest for testing
  - Set up Redis for caching/Celery

- [ ] **Provider Abstraction Layer**
  - Implement base provider interfaces (AuthProvider, CRMProvider, BillingProvider)
  - Create provider registry and factory
  - Set up provider configuration database schema
  - Implement provider health check system
  - Create provider switching mechanism

- [ ] **Initial Provider Implementations**
  - Implement OxiadminLDAPProvider with production connection
  - Implement PipedriveProvider with OAuth 2.0
  - Implement PennylaneProvider with API key auth
  - Test all provider connections
  - Set up encrypted credential storage

### Phase 2: Core Backend & Database (Week 3-4)
- [ ] **Database Schema**
  - Create all entity tables with SQLAlchemy models
  - Set up relationships and constraints
  - Implement audit logging with SQLAlchemy events
  - Create performance indexes
  - Add database seeders for development

- [ ] **FastAPI Structure**
  - API routers organization by domain
  - Automatic OpenAPI documentation
  - Exception handlers and middleware
  - Pydantic request/response models
  - Dependency injection for database sessions

- [ ] **Core Domain Models**
  - Product management CRUD endpoints
  - Pricing tiers with Decimal precision
  - Lead management endpoints
  - Basic order creation flow

### Phase 3: Business Logic & Integrations (Week 5-6)
- [ ] **Pricing Engine Service**
  - Progressive pricing calculator with Decimal
  - Duration discount application
  - Quote generation with caching
  - Price validation and constraints

- [ ] **Order Management**
  - State machine with python-transitions
  - Order workflow automation
  - Note system with role-based visibility
  - Order-to-lead linkage

- [ ] **Lead Management**
  - Lead CRUD operations
  - Lead status workflow
  - Lead assignment rules
  - Lead-to-order conversion

- [ ] **Contract Generation**
  - Order to contract conversion
  - Contract lifecycle management
  - Status management (lost/upgraded/downgraded)
  - Contract renewal automation

### Phase 4: Authorization & Celery Tasks (Week 7)
- [ ] **RBAC Implementation**
  - Complete role definitions with Casbin
  - FastAPI dependency injection for permissions
  - Resource-based access control
  - Multi-tenancy data filtering with SQLAlchemy

- [ ] **Async Task Infrastructure**
  - Celery configuration with Redis broker
  - Task scheduling with Celery Beat
  - Background sync tasks
  - Email notification tasks

- [ ] **Relationship Management**
  - Distributor-Partner associations
  - Partner-Contract relationships
  - Lead ownership rules
  - Access control validation

### Phase 5: Frontend Foundation (Week 8-9)
- [ ] **Frontend Setup**
  - Next.js/Vite project initialization
  - shadcn/ui component setup
  - Tailwind configuration
  - i18n setup for French/English

- [ ] **Core UI Components**
  - Authentication flow
  - Layout and navigation
  - Dashboard templates
  - Data tables with filtering/sorting

### Phase 6: Frontend Features (Week 10-11)
- [ ] **Lead Management UI**
  - Lead creation form with validation
  - Lead pipeline kanban view
  - Lead detail views with activities
  - Lead analytics dashboard
  - Lead-to-order conversion flow

- [ ] **Order Management UI**
  - Order creation wizard
  - Order listing with filters
  - Order detail views
  - Note management interface
  - Order status tracking

- [ ] **Contract Management UI**
  - Contract listing
  - Contract details
  - Status management
  - Invoice linking display
  - Contract renewal notifications

- [ ] **Role-based UI**
  - Dynamic navigation based on role
  - Conditional component rendering
  - Permission-based actions
  - Multi-tenant data filtering

- [ ] **Provider Management UI (Admin Only)**
  - Provider configuration dashboard
  - Add/edit provider credentials forms
  - Provider health status monitoring
  - Provider switching interface
  - Test connection functionality
  - Sync logs and error viewing
  - Provider-specific field mapping configuration

### Phase 7: Production Integrations (Week 12-13)
- [ ] **Pipedrive Integration (Live)**
  - Python client with httpx using production OAuth tokens
  - Lead/Deal bidirectional sync with production data
  - Activity synchronization
  - Production webhook endpoint setup and verification
  - Test with real Pipedrive users and pipelines
  - Conflict resolution strategy with production edge cases

- [ ] **Pennylane Integration (Live)**
  - API client with production API keys
  - Quote generation tested with real Pennylane account
  - Invoice synchronization with production invoices
  - Customer data sync validation
  - Production webhook handling and verification

- [ ] **Oxiadmin LDAP (Production)**
  - Live connection to production LDAP server
  - Verify all user attributes and schema
  - Test authentication with actual user accounts
  - Validate role mapping from LDAP groups
  - Performance testing with production user load

### Phase 8: Testing & Refinement (Week 14-15)
- [ ] **Testing**
  - Unit tests with pytest and pytest-cov
  - Integration tests for FastAPI endpoints
  - Live integration tests with Pipedrive and Pennylane
  - LDAP authentication tests with production server
  - E2E tests with Playwright against live services
  - Load testing with Locust (respecting API rate limits)

- [ ] **Documentation**
  - API documentation via FastAPI/OpenAPI
  - User guides per role
  - Integration setup guides
  - Deployment documentation with Docker
  - Administrator guide

### Phase 9: Deployment Preparation (Week 16)
- [ ] **DevOps**
  - GitHub Actions CI/CD pipeline
  - Multi-stage Docker containerization
  - docker-compose for staging
  - Kubernetes manifests for production
  - Prometheus + Grafana monitoring

- [ ] **Security Hardening**
  - OWASP security audit
  - SQL injection prevention verification
  - Rate limiting with slowapi
  - Secrets management with Vault
  - SSL/TLS configuration

### Phase 10: Launch & Monitoring (Week 17)
- [ ] **Deployment**
  - Database migrations with Alembic
  - Staging environment validation
  - Production deployment
  - LDAP connection verification
  - External integrations health check

- [ ] **Post-Launch**
  - Performance monitoring setup
  - Error tracking with Sentry
  - Log aggregation setup
  - User training sessions
  - Go-live support

---

## Key Success Factors

1. **Clear API Contracts:** Define all API endpoints early with OpenAPI
2. **Type Safety:** Use TypeScript throughout with shared types
3. **Test Coverage:** Aim for >80% coverage on business logic
4. **Progressive Development:** Build MVP first, then iterate
5. **User Feedback:** Regular demos to stakeholders
6. **Documentation:** Keep it updated as you build

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|-------------------|
| LDAP Integration Complexity | Test directly with production Oxiadmin server, document schema |
| Pennylane API Changes | Abstract with adapter pattern, version lock, monitor changelog |
| Pipedrive API Rate Limits | Implement caching, batch operations, exponential backoff |
| Complex Pricing Logic | Use Decimal type, extensive unit testing with pytest |
| Multi-System Sync Conflicts | Event sourcing, conflict resolution strategy, idempotent operations |
| Performance Issues | SQLAlchemy query optimization, Redis caching, monitor API response times |
| Multi-language Support | i18n from day one with proper key management |
| Data Migration | Incremental migration with rollback capability |
| Production API Stability | Implement circuit breakers, graceful degradation |
| Credential Security | Use environment variables, never commit credentials |

## Technology Stack Recommendation

### Backend (Python)
- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL 15+
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **Cache:** Redis
- **Task Queue:** Celery + Redis
- **Validation:** Pydantic v2
- **Authentication:** python-jose (JWT), python-ldap3
- **Testing:** pytest, pytest-cov, pytest-asyncio
- **HTTP Client:** httpx (async)
- **Financial:** Python decimal module

### Frontend
- **Framework:** Next.js 14+ (App Router) or Vite + React
- **UI Library:** shadcn/ui
- **State Management:** Zustand or TanStack Query
- **Forms:** React Hook Form + Zod
- **i18n:** next-i18next or react-i18next
- **API Client:** Generated from OpenAPI spec
- **Charts:** Recharts for analytics

### External Integrations
- **Pipedrive:** REST API v1 with OAuth 2.0
- **Pennylane:** REST API (requires API key)
- **Oxiadmin:** LDAP v3 protocol

### DevOps
- **Containerization:** Docker with multi-stage builds
- **Orchestration:** Kubernetes or Docker Compose
- **CI/CD:** GitHub Actions or GitLab CI
- **Monitoring:** Prometheus + Grafana
- **APM:** Sentry for error tracking
- **Logging:** ELK Stack or Loki
- **Secrets:** HashiCorp Vault or AWS Secrets Manager

---

## Next Steps

1. **Review and refine** this document with stakeholders
2. **Prioritize features** for MVP vs. future releases
3. **Set up development environment**
4. **Begin with Phase 1** of the action plan
5. **Establish regular sprint cycles** (2-week sprints recommended)

## Adding New Providers

### How to Add a New Provider (Example: Salesforce CRM)

1. **Create Provider Implementation**
```python
# app/providers/crm/salesforce.py
class SalesforceProvider(CRMProvider):
    def __init__(self, config: Dict[str, Any]):
        self.client = Salesforce(
            username=config['username'],
            password=config['password'],
            security_token=config['security_token']
        )

    async def create_lead(self, lead_data: Lead) -> Dict[str, Any]:
        # Map internal Lead model to Salesforce Lead
        sf_lead = {
            'LastName': lead_data.contact_name.split()[-1],
            'Company': lead_data.organization,
            'Email': lead_data.contact_email,
            'Status': self._map_status(lead_data.status)
        }
        result = await self.client.Lead.create(sf_lead)
        return {'id': result['id'], 'success': result['success']}

    async def sync_leads(self) -> List[Lead]:
        # Fetch and map Salesforce leads to internal model
        sf_leads = await self.client.query("SELECT Id, Name, Company FROM Lead")
        return [self._map_to_internal(lead) for lead in sf_leads['records']]
```

2. **Register Provider**
```python
# app/providers/__init__.py
from .crm.salesforce import SalesforceProvider

registry.register(ProviderType.CRM, 'salesforce', SalesforceProvider)
```

3. **Add Configuration UI**
   - Create admin form for Salesforce credentials
   - Add field mapping configuration
   - Implement connection testing

4. **Database Migration**
   - No schema changes needed (uses existing provider_configs table)
   - Add Salesforce-specific metadata mappings if needed

5. **Testing**
   - Unit tests for provider implementation
   - Integration tests with Salesforce sandbox
   - Migration tests for switching from another CRM

## Questions to Address

### Integration Questions (Ready for Development)
1. **Pipedrive API:** Provide OAuth credentials and confirm rate limits
2. **Pennylane API:** Provide API keys and endpoint documentation
3. **LDAP Server:** Provide connection details (host, port, base DN, bind credentials)
4. **Webhook URLs:** Confirm development and production webhook endpoints
5. **Test Accounts:** Create development accounts in Pipedrive/Pennylane for testing

### Data & Migration
6. **Historical Data:** Is there existing data to migrate from current systems?
7. **Pipedrive Sync:** Should we sync all existing Pipedrive data or start fresh?
8. **Data Retention:** What are the requirements for data archival?

### Business Rules
9. **Lead Assignment:** Automatic assignment rules for new leads?
10. **Pricing Updates:** How often do product prices change?
11. **Contract Renewals:** Automatic renewal process or manual?

### Technical & Deployment
12. **Scale:** Expected number of users/orders/contracts/leads?
13. **Deployment:** Cloud provider preference? (AWS/GCP/Azure/On-premise)
14. **Performance:** Response time requirements? Concurrent user expectations?
15. **Backup:** RTO/RPO requirements for disaster recovery?

### Compliance & Security
16. **GDPR:** Data privacy requirements for EU customers?
17. **Audit Trail:** What actions need to be logged?
18. **Budget:** Any constraints on third-party services or infrastructure?

---

*This document should be treated as a living document and updated as the project evolves.*