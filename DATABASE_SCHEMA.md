# Tentabo PRM - Database Schema Documentation

## Overview

Complete PostgreSQL 13.22 database schema for Tentabo Partner Relationship Management system. This is a production-ready schema with proper constraints, indexes, and multi-tenant support.

**Database Details:**
- **Host:** marshmallow02.oxileo.net:5432
- **Database:** tentabo_oxibox
- **User:** tentabo_oxibox
- **PostgreSQL Version:** 13.22

## Architecture Principles

### 1. Provider-Agnostic Design
The schema supports pluggable external providers for:
- **Authentication:** LDAP (Oxiadmin), OAuth, SAML, Database
- **CRM:** Pipedrive, Salesforce, HubSpot, etc.
- **Billing:** Pennylane, QuickBooks, Xero, Stripe, etc.

Provider-specific data stored in JSONB fields (`provider_metadata`, `billing_metadata`, `crm_metadata`).

### 2. Multi-Tenancy
- Distributors manage multiple partners
- Row-level data isolation enforced through relationships
- Indexes optimized for tenant-based queries

### 3. Financial Precision
- All monetary values use `NUMERIC` type (never FLOAT)
- Price calculations with 4 decimal precision
- Currency fields use ISO 4217 codes

### 4. Audit Trail
- All tables have `created_at` and `updated_at` timestamps
- `AuditLog` table tracks all critical operations
- Status history tracking for leads

## Table Structure

### Authentication & Users (2 tables)

#### admin_users
Independent admin accounts with bcrypt password hashing.
- **Primary Key:** UUID
- **Unique:** username, email
- **No external dependencies** - works even if auth providers fail

```sql
Columns:
  - id (UUID, PK)
  - username (VARCHAR, unique)
  - password_hash (VARCHAR) -- bcrypt hash
  - email (VARCHAR, unique)
  - full_name (VARCHAR)
  - is_active (BOOLEAN)
  - created_at, updated_at, last_login (TIMESTAMP)
```

#### users
Provider-based user accounts. Roles managed in database, not from provider.
- **Primary Key:** UUID
- **Foreign Keys:** enabled_by (admin_users), partner_id, distributor_id
- **Must be enabled by admin** after first login

```sql
Columns:
  - id (UUID, PK)
  - provider (VARCHAR) -- 'ldap', 'google', 'saml', etc.
  - provider_id (VARCHAR) -- External user ID
  - email (VARCHAR, indexed)
  - full_name, username (VARCHAR)
  - role (ENUM: admin, restricted_admin, partner, distributor, fulfiller)
  - is_enabled (BOOLEAN, indexed)
  - enabled_by (UUID, FK -> admin_users.id)
  - partner_id, distributor_id (UUID, FKs)
  - created_at, updated_at, last_login (TIMESTAMP)
```

### Core Business (3 tables)

#### products
Products available for subscription.
- **Primary Key:** UUID
- **Unique:** name

```sql
Columns:
  - id (UUID, PK)
  - name (VARCHAR, unique)
  - type (VARCHAR, indexed) -- 'appliance', 'service', etc.
  - unit (VARCHAR) -- 'TB', 'GB', 'user', etc.
  - description (TEXT)
  - is_active (VARCHAR) -- 'true' or 'false'
  - created_at, updated_at (TIMESTAMP)

Relationships:
  - price_tiers (1:N, cascade delete)
  - order_items (1:N)
```

#### price_tiers
Progressive pricing based on quantity ranges.
- **Primary Key:** UUID
- **Foreign Key:** product_id
- **Decimal Precision:** 4 places for pricing

```sql
Columns:
  - id (UUID, PK)
  - product_id (UUID, FK -> products.id)
  - min_quantity (INTEGER, CHECK >= 0)
  - max_quantity (INTEGER, nullable) -- NULL = unlimited
  - price_per_unit (NUMERIC(10,4), CHECK > 0)
  - period (VARCHAR) -- 'month' or 'year'
  - created_at, updated_at (TIMESTAMP)

Constraints:
  - max_quantity > min_quantity OR max_quantity IS NULL
  - price_per_unit > 0
  - period IN ('month', 'year')
```

#### durations
Subscription duration options with discounts.
- **Primary Key:** UUID
- **Unique:** months

```sql
Columns:
  - id (UUID, PK)
  - months (INTEGER, unique, CHECK > 0)
  - discount_percentage (NUMERIC(5,2), CHECK 0-100)
  - name (VARCHAR) -- Display name
  - created_at, updated_at (TIMESTAMP)
```

### Partners & Distributors (3 tables)

#### partners
End customer companies.
- **Primary Key:** UUID
- **Unique:** registration_number

```sql
Columns:
  - id (UUID, PK)
  - name (VARCHAR, indexed)
  - legal_name (VARCHAR)
  - registration_number (VARCHAR, unique) -- SIRET, VAT, etc.
  - email, phone, website (VARCHAR)
  - address_line1, address_line2, city, postal_code, country (VARCHAR)
  - is_active (BOOLEAN, indexed)
  - notes (TEXT)
  - created_at, updated_at (TIMESTAMP)

Relationships:
  - users (1:N)
  - leads (1:N)
  - orders (1:N)
  - contracts (1:N)
  - distributor_associations (N:M via distributor_partners)
```

#### distributors
Companies managing multiple partners.
- **Primary Key:** UUID
- **Unique:** registration_number

```sql
Columns: (same structure as partners)

Relationships:
  - users (1:N)
  - leads (1:N)
  - orders (1:N)
  - contracts (1:N)
  - partner_associations (N:M via distributor_partners)
```

#### distributor_partners
Junction table for distributor-partner relationships.
- **Primary Key:** UUID
- **Unique:** (distributor_id, partner_id)

```sql
Columns:
  - id (UUID, PK)
  - distributor_id (UUID, FK -> distributors.id)
  - partner_id (UUID, FK -> partners.id)
  - assigned_at (TIMESTAMP)
  - assigned_by (UUID, FK -> admin_users.id)
  - is_active (BOOLEAN)
  - notes (TEXT)
  - created_at, updated_at (TIMESTAMP)

Constraints:
  - UNIQUE(distributor_id, partner_id)
```

### CRM / Lead Management (4 tables)

#### leads
Provider-agnostic sales opportunities.
- **Primary Key:** UUID
- **Foreign Keys:** owner_id (users), partner_id, distributor_id
- **GIN Index:** provider_metadata (JSONB)

```sql
Columns:
  - id (UUID, PK)
  - provider_name (VARCHAR, indexed) -- 'pipedrive', 'salesforce', etc.
  - provider_id (VARCHAR, indexed) -- External CRM ID
  - provider_metadata (JSONB, GIN indexed) -- Provider-specific data
  - title, organization (VARCHAR)
  - contact_name, contact_email, contact_phone (VARCHAR)
  - value (NUMERIC(12,2))
  - currency (VARCHAR) -- ISO 4217
  - status (ENUM, indexed) -- new, contacted, qualified, proposal, negotiation, won, lost
  - probability (INTEGER, CHECK 0-100)
  - expected_close_date (TIMESTAMP)
  - owner_id (UUID, FK -> users.id, indexed)
  - partner_id, distributor_id (UUID, FKs, indexed)
  - last_sync_at (TIMESTAMP)
  - sync_status, sync_error (VARCHAR/TEXT)
  - created_at, updated_at (TIMESTAMP)

Indexes:
  - (owner_id, status)
  - (distributor_id, partner_id)
  - (provider_name, provider_id)
  - (status, created_at)
  - GIN(provider_metadata)

Relationships:
  - activities (1:N, cascade delete)
  - notes (1:N, cascade delete)
  - status_history (1:N, cascade delete)
  - orders (1:N)
```

#### lead_activities
Activities tracked from CRM (calls, emails, meetings).
- **Primary Key:** UUID
- **Foreign Key:** lead_id

```sql
Columns:
  - id (UUID, PK)
  - lead_id (UUID, FK -> leads.id)
  - provider_name, provider_id, provider_metadata (VARCHAR/JSONB)
  - activity_type (VARCHAR, indexed) -- 'call', 'email', 'meeting', etc.
  - subject, description (VARCHAR/TEXT)
  - due_date (TIMESTAMP, indexed)
  - done (VARCHAR) -- 'true' or 'false'
  - done_at (TIMESTAMP)
  - user_id (UUID, FK -> users.id)
  - created_at, updated_at (TIMESTAMP)

Indexes:
  - (lead_id, activity_type)
  - (due_date)
```

#### lead_notes
Notes attached to leads.
- **Primary Key:** UUID
- **Foreign Key:** lead_id

```sql
Columns:
  - id (UUID, PK)
  - lead_id (UUID, FK -> leads.id)
  - provider_name, provider_id (VARCHAR, nullable) -- NULL if created internally
  - content (TEXT)
  - created_by_user_id (UUID, FK -> users.id)
  - created_at, updated_at (TIMESTAMP)
```

#### lead_status_history
Audit trail of lead status changes.
- **Primary Key:** UUID
- **Foreign Key:** lead_id

```sql
Columns:
  - id (UUID, PK)
  - lead_id (UUID, FK -> leads.id)
  - old_status, new_status (ENUM LeadStatus)
  - changed_by_user_id (UUID, FK -> users.id)
  - reason (TEXT)
  - changed_at (TIMESTAMP)

Indexes:
  - (lead_id, changed_at)
```

### Orders & Contracts (3 tables)

#### orders
Customer orders with billing and CRM integration.
- **Primary Key:** UUID
- **Unique:** order_number
- **GIN Indexes:** billing_metadata, crm_metadata

```sql
Columns:
  - id (UUID, PK)
  - order_number (VARCHAR, unique, indexed)
  - status (ENUM, indexed) -- created, cancelled, sent, in_fulfillment, fulfilled
  - billing_provider (VARCHAR) -- 'pennylane', 'quickbooks', etc.
  - billing_quote_id (VARCHAR)
  - billing_metadata (JSONB, GIN indexed)
  - crm_provider, crm_deal_id, crm_metadata (VARCHAR/JSONB)
  - created_by (UUID, FK -> users.id, indexed)
  - partner_id, distributor_id, lead_id (UUID, FKs, indexed)
  - subtotal, discount_amount, tax_amount, total_amount (NUMERIC(12,2))
  - notes_internal (TEXT)
  - created_at, updated_at, sent_at, fulfilled_at, cancelled_at (TIMESTAMP)

Indexes:
  - (status, created_at)
  - (partner_id, status)
  - (distributor_id, status)
  - GIN(billing_metadata)
  - GIN(crm_metadata)

Relationships:
  - items (1:N, cascade delete)
  - contract (1:1)
  - notes (1:N)
```

#### order_items
Line items in orders (product + duration + quantity).
- **Primary Key:** UUID
- **Foreign Keys:** order_id, product_id, duration_id

```sql
Columns:
  - id (UUID, PK)
  - order_id (UUID, FK -> orders.id)
  - product_id (UUID, FK -> products.id)
  - duration_id (UUID, FK -> durations.id)
  - quantity (INTEGER, CHECK > 0)
  - unit_price (NUMERIC(10,4), CHECK >= 0)
  - discount_percentage (NUMERIC(5,2), CHECK 0-100)
  - subtotal, discount_amount, total (NUMERIC(12,2))
  - product_name, product_type, product_unit (VARCHAR) -- Snapshot
  - duration_months (INTEGER)
  - created_at, updated_at (TIMESTAMP)
```

#### contracts
Activated contracts from fulfilled orders.
- **Primary Key:** UUID
- **Unique:** contract_number, order_id

```sql
Columns:
  - id (UUID, PK)
  - contract_number (VARCHAR, unique, indexed)
  - order_id (UUID, FK -> orders.id, unique)
  - status (ENUM, indexed) -- active, lost, upgraded, downgraded, expired, cancelled
  - billing_provider (VARCHAR)
  - billing_customer_id (VARCHAR)
  - billing_invoices (JSONB) -- Array of invoice IDs
  - billing_metadata (JSONB, GIN indexed)
  - user_id (UUID, FK -> users.id, indexed)
  - partner_id, distributor_id (UUID, FKs, indexed)
  - activation_date, expiration_date (TIMESTAMP)
  - renewed_from_id (UUID, FK -> contracts.id) -- Self-referential
  - total_value (NUMERIC(12,2))
  - currency (VARCHAR)
  - notes_internal (TEXT)
  - created_at, updated_at, cancelled_at (TIMESTAMP)

Indexes:
  - (status, activation_date)
  - (partner_id, status)
  - (distributor_id, status)
  - (expiration_date)
  - GIN(billing_metadata)
```

### System & Configuration (5 tables)

#### provider_configs
External provider configurations.
- **Primary Key:** UUID
- **Unique:** (provider_type, provider_name)
- **Partial Unique Index:** Only one active provider per type

```sql
Columns:
  - id (UUID, PK)
  - provider_type (ENUM: auth, crm, billing)
  - provider_name (VARCHAR) -- 'oxiadmin_ldap', 'pipedrive', 'pennylane', etc.
  - is_active (BOOLEAN, indexed)
  - configuration (JSONB, GIN indexed) -- Non-sensitive settings
  - credentials (JSONB) -- Encrypted sensitive data
  - health_status (VARCHAR) -- 'healthy', 'degraded', 'offline', 'unknown'
  - last_health_check (TIMESTAMP)
  - health_check_error (TEXT)
  - created_at, updated_at (TIMESTAMP)

Constraints:
  - UNIQUE(provider_type, provider_name)
  - UNIQUE(provider_type, is_active) WHERE is_active = true
```

#### provider_sync_logs
Audit log for provider synchronization.
- **Primary Key:** UUID
- **Foreign Key:** provider_id

```sql
Columns:
  - id (UUID, PK)
  - provider_id (UUID, FK -> provider_configs.id)
  - sync_type (VARCHAR) -- 'full', 'incremental', 'webhook', 'manual'
  - entity_type (VARCHAR, indexed) -- 'lead', 'user', 'invoice', etc.
  - direction (VARCHAR) -- 'pull', 'push', 'bidirectional'
  - records_synced, records_failed (INTEGER)
  - error_details (JSONB)
  - status (VARCHAR, indexed) -- 'success', 'partial', 'failed'
  - started_at, completed_at (TIMESTAMP)

Indexes:
  - (provider_id, entity_type)
  - (status, started_at)
```

#### notes
Polymorphic notes for orders and contracts.
- **Primary Key:** UUID
- **Foreign Keys:** order_id OR contract_id (at least one required)

```sql
Columns:
  - id (UUID, PK)
  - order_id (UUID, FK -> orders.id, nullable)
  - contract_id (UUID, FK -> contracts.id, nullable)
  - content (TEXT)
  - is_internal (BOOLEAN) -- Not visible to customers
  - is_pinned (BOOLEAN)
  - created_by (UUID, FK -> users.id)
  - created_at, updated_at (TIMESTAMP)

Constraints:
  - CHECK(order_id IS NOT NULL OR contract_id IS NOT NULL)

Indexes:
  - (order_id, created_at)
  - (contract_id, created_at)
```

#### audit_logs
System-wide audit trail.
- **Primary Key:** UUID
- **Foreign Keys:** user_id OR admin_user_id

```sql
Columns:
  - id (UUID, PK)
  - user_id (UUID, FK -> users.id, nullable)
  - admin_user_id (UUID, FK -> admin_users.id, nullable)
  - action (VARCHAR, indexed) -- 'create', 'update', 'delete', 'activate', etc.
  - entity_type (VARCHAR, indexed) -- 'order', 'contract', 'user', etc.
  - entity_id (UUID, indexed)
  - changes (JSONB, GIN indexed) -- Before/after values
  - ip_address (VARCHAR) -- IPv6 compatible
  - user_agent (VARCHAR)
  - created_at (TIMESTAMP, indexed)

Indexes:
  - (entity_type, entity_id)
  - (action, created_at)
  - (user_id, created_at)
  - GIN(changes)
```

#### webhook_events
Incoming webhooks from external systems.
- **Primary Key:** UUID
- **GIN Index:** payload

```sql
Columns:
  - id (UUID, PK)
  - provider_name (VARCHAR, indexed)
  - provider_type (ENUM: auth, crm, billing)
  - event_type (VARCHAR, indexed) -- Provider-specific
  - event_id (VARCHAR, indexed) -- For deduplication
  - payload (JSONB, GIN indexed)
  - status (VARCHAR, indexed) -- 'pending', 'processing', 'processed', 'failed'
  - processed_at (TIMESTAMP)
  - error_message (TEXT)
  - ip_address (VARCHAR)
  - headers (JSONB)
  - received_at, created_at (TIMESTAMP)

Indexes:
  - (provider_name, event_type)
  - (status, received_at)
  - (provider_name, event_id) -- Deduplication
  - GIN(payload)
```

## Key Indexes Summary

### Performance-Critical Indexes
```sql
-- Lead queries (most common)
idx_leads_owner_status (owner_id, status)
idx_leads_distributor_partner (distributor_id, partner_id)
idx_leads_metadata (GIN on provider_metadata)

-- Order queries
idx_orders_status_created (status, created_at)
idx_orders_partner_status (partner_id, status)
idx_orders_billing_metadata (GIN on billing_metadata)

-- Contract queries
idx_contracts_status_activation (status, activation_date)
idx_contracts_expiration (expiration_date)
idx_contracts_partner_status (partner_id, status)

-- Provider management
idx_provider_configs_active (provider_type, is_active) -- Partial unique index
```

## Migration Management

### Using Alembic

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### Initial Setup Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run initial migration
python3 -m alembic upgrade head

# Verify schema
python3 test_schema.py
```

## Security Considerations

### Password Storage
- Admin passwords: bcrypt hashed (72 byte limit)
- Never store plain text passwords
- Use environment variables for database credentials

### Sensitive Data
- Provider credentials in `provider_configs.credentials` should be encrypted at application level
- Use row-level security for multi-tenant data isolation
- Audit all access to sensitive tables via `audit_logs`

### Multi-Tenancy
- Distributors can only access their assigned partners
- Enforce filtering at application layer:
  ```python
  # Example SQLAlchemy filter
  query = query.join(DistributorPartner).filter(
      DistributorPartner.distributor_id == current_distributor_id,
      DistributorPartner.is_active == True
  )
  ```

## Testing

### Running Tests
```bash
# Full schema verification
python3 test_schema.py

# Verify specific table
python3 -c "from app.models import Lead; print(Lead.__table__)"

# Check database connection
python3 -c "from app.database import check_database_connection; import asyncio; print(asyncio.run(check_database_connection()))"
```

### Sample Data Created by test_schema.py
- 1 admin user (username: admin, password: admin123)
- 1 product with 3 price tiers
- 3 duration options
- 1 partner
- 1 distributor
- 1 provider config (Pipedrive CRM)

## Backup and Maintenance

### Backup
```bash
# Full backup
pg_dump -h marshmallow02.oxileo.net -U tentabo_oxibox -d tentabo_oxibox > backup.sql

# Schema only
pg_dump -h marshmallow02.oxileo.net -U tentabo_oxibox -d tentabo_oxibox --schema-only > schema.sql
```

### Restore
```bash
psql -h marshmallow02.oxileo.net -U tentabo_oxibox -d tentabo_oxibox < backup.sql
```

### Maintenance
```sql
-- Vacuum and analyze
VACUUM ANALYZE;

-- Reindex
REINDEX DATABASE tentabo_oxibox;

-- Check table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Troubleshooting

### Connection Issues
```python
# Test connection
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.fetchone())
```

### Migration Issues
```bash
# Reset migrations (DANGER: drops all data)
alembic downgrade base
alembic upgrade head

# Check migration status
alembic current -v
```

### Index Issues
```sql
-- Find missing indexes
SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename;

-- Rebuild specific index
REINDEX INDEX idx_leads_owner_status;
```

## Future Enhancements

### Planned Features
1. Partitioning for `audit_logs` by date
2. Read replicas for reporting queries
3. Full-text search indexes on notes/descriptions
4. Time-series data for analytics
5. Automated archival of old records

### Schema Evolution
- All migrations tracked in `alembic_version` table
- Zero-downtime migrations using Blue-Green deployment
- Always test migrations on staging first

## Support

For issues or questions:
- Check migration logs: `alembic history`
- Review test output: `python3 test_schema.py`
- Database logs: Check PostgreSQL server logs
- Application logs: Review SQLAlchemy query logs

---

**Last Updated:** 2025-11-12
**Schema Version:** 1.0.0 (Initial Release)
**Migration:** a8e2b505fe67_initial_schema_with_all_models
