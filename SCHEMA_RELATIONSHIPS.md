# Tentabo PRM - Database Relationships

## Entity Relationship Overview

This document visualizes the relationships between all tables in the Tentabo PRM database schema.

## Core Entity Relationships

```
┌─────────────────┐
│  AdminUser      │
└────────┬────────┘
         │ enables
         ├──────────────┐
         │              │
         ▼              ▼
    ┌────────┐     ┌──────────────────┐
    │  User  │◄────│ DistributorPartner│
    └───┬────┘     └──────────────────┘
        │               │         │
        │ owns          │         │
        │               │         │
        ▼               ▼         ▼
    ┌────────┐     ┌────────┐ ┌────────┐
    │  Lead  │     │Distributor│ Partner│
    └───┬────┘     └────┬───┘ └───┬────┘
        │               │         │
        │               └─────────┤
        │                         │
        ▼                         ▼
    ┌────────┐              ┌────────┐
    │ Order  │──────────────│Contract│
    └───┬────┘              └────────┘
        │
        ▼
    ┌────────────┐
    │ OrderItem  │
    └────────────┘
```

## Detailed Relationship Diagrams

### Authentication Flow
```
AdminUser (1) ──enables──► (N) User
    │
    └──assigned_by──► (N) DistributorPartner

User (N) ──belongs_to──► (1) Partner
User (N) ──belongs_to──► (1) Distributor
User (1) ──owns──► (N) Lead
User (1) ──creates──► (N) Order
User (1) ──manages──► (N) Contract
```

### Multi-Tenancy Structure
```
Distributor (N) ◄──── DistributorPartner ────► (N) Partner
                           │
                           └── assigned_by ──► AdminUser

Distributor (1) ────► (N) User
Distributor (1) ────► (N) Lead
Distributor (1) ────► (N) Order
Distributor (1) ────► (N) Contract

Partner (1) ────► (N) User
Partner (1) ────► (N) Lead
Partner (1) ────► (N) Order
Partner (1) ────► (N) Contract
```

### Product & Pricing
```
Product (1) ────has_many───► (N) PriceTier
Product (1) ────used_in────► (N) OrderItem

Duration (1) ────applied_to──► (N) OrderItem

OrderItem (N) ──belongs_to──► (1) Order
```

### Lead Management
```
Lead (1) ────has_many────► (N) LeadActivity
Lead (1) ────has_many────► (N) LeadNote
Lead (1) ────has_many────► (N) LeadStatusHistory
Lead (1) ────converts_to──► (N) Order

Lead (N) ──owned_by──► (1) User
Lead (N) ──belongs_to──► (1) Partner
Lead (N) ──belongs_to──► (1) Distributor
```

### Order Processing
```
Order (1) ────contains────► (N) OrderItem
Order (1) ────becomes─────► (1) Contract
Order (1) ────has_notes───► (N) Note
Order (N) ────from_lead───► (1) Lead

Order (N) ──created_by──► (1) User
Order (N) ──belongs_to──► (1) Partner
Order (N) ──belongs_to──► (1) Distributor
```

### Contract Management
```
Contract (1) ──from_order──► (1) Order
Contract (1) ──has_notes───► (N) Note
Contract (1) ──renewed_from──► (1) Contract  [self-referential]

Contract (N) ──managed_by──► (1) User
Contract (N) ──belongs_to──► (1) Partner
Contract (N) ──belongs_to──► (1) Distributor
```

### Provider System
```
ProviderConfig (1) ────logs────► (N) ProviderSyncLog

WebhookEvent (N) ──from──► Provider (external)
```

### Audit System
```
AuditLog (N) ──performed_by──► (1) User
AuditLog (N) ──performed_by──► (1) AdminUser

Note (N) ──attached_to──► (1) Order
Note (N) ──attached_to──► (1) Contract
Note (N) ──created_by───► (1) User
```

## Cardinality Reference

### One-to-Many (1:N)
- **AdminUser → User** (enables)
- **User → Lead** (owns)
- **User → Order** (creates)
- **User → Contract** (manages)
- **Partner → User** (employs)
- **Partner → Lead** (has)
- **Partner → Order** (places)
- **Partner → Contract** (holds)
- **Distributor → User** (employs)
- **Distributor → Lead** (manages)
- **Distributor → Order** (handles)
- **Distributor → Contract** (oversees)
- **Product → PriceTier** (has pricing)
- **Product → OrderItem** (ordered)
- **Duration → OrderItem** (applied to)
- **Lead → LeadActivity** (has activities)
- **Lead → LeadNote** (has notes)
- **Lead → LeadStatusHistory** (has history)
- **Lead → Order** (converts to)
- **Order → OrderItem** (contains)
- **Order → Note** (has notes)
- **Contract → Note** (has notes)
- **ProviderConfig → ProviderSyncLog** (logs syncs)

### One-to-One (1:1)
- **Order → Contract** (becomes)

### Many-to-Many (N:M)
- **Distributor ◄─► Partner** (via DistributorPartner junction table)

### Self-Referential
- **Contract → Contract** (renewed_from)

## Foreign Key Cascade Rules

### CASCADE DELETE
These relationships will cascade delete child records:
```
Lead → LeadActivity        (cascade delete)
Lead → LeadNote           (cascade delete)
Lead → LeadStatusHistory  (cascade delete)
Order → OrderItem         (cascade delete)
Product → PriceTier       (cascade delete)
ProviderConfig → ProviderSyncLog (cascade delete)
DistributorPartner        (cascade delete from both sides)
Note → Order/Contract     (cascade delete)
```

### NO CASCADE (Manual cleanup required)
```
User → Lead               (orphaned leads must be reassigned)
User → Order              (orders keep creator reference)
Partner → Order           (orders keep partner reference)
Distributor → Order       (orders keep distributor reference)
```

## Index Coverage for Relationships

### Most Frequently Queried Relationships
```sql
-- Lead ownership queries
idx_leads_owner_status (owner_id, status)

-- Multi-tenant queries
idx_leads_distributor_partner (distributor_id, partner_id)
idx_orders_partner_status (partner_id, status)
idx_contracts_distributor_status (distributor_id, status)

-- Order processing
idx_orders_status_created (status, created_at)
idx_order_items_order_id (order_id)

-- Contract management
idx_contracts_status_activation (status, activation_date)
idx_contracts_order_id (order_id) [unique]

-- Notes
idx_notes_order_created (order_id, created_at)
idx_notes_contract_created (contract_id, created_at)
```

## Common Query Patterns

### 1. Get all leads for a distributor
```python
leads = db.query(Lead).filter(
    Lead.distributor_id == distributor_id,
    Lead.status == LeadStatus.QUALIFIED
).order_by(Lead.created_at.desc()).all()
```
**Uses Index:** `idx_leads_distributor_partner`, `idx_leads_status_created`

### 2. Get partner's orders with items
```python
orders = db.query(Order).options(
    joinedload(Order.items)
).filter(
    Order.partner_id == partner_id,
    Order.status == OrderStatus.SENT
).all()
```
**Uses Index:** `idx_orders_partner_status`

### 3. Get active contracts for a partner
```python
contracts = db.query(Contract).filter(
    Contract.partner_id == partner_id,
    Contract.status == ContractStatus.ACTIVE
).all()
```
**Uses Index:** `idx_contracts_partner_status`

### 4. Get distributor's partners
```python
partners = db.query(Partner).join(DistributorPartner).filter(
    DistributorPartner.distributor_id == distributor_id,
    DistributorPartner.is_active == True
).all()
```
**Uses Index:** `ix_distributor_partners_distributor_id`

### 5. Get lead with all related data
```python
lead = db.query(Lead).options(
    joinedload(Lead.owner),
    joinedload(Lead.partner),
    joinedload(Lead.activities),
    joinedload(Lead.notes),
    joinedload(Lead.status_history)
).filter(Lead.id == lead_id).first()
```
**Uses Index:** Primary key + relationship foreign keys

## Referential Integrity

### Enforced by Database
- All foreign key constraints are enforced
- Cascade deletes where appropriate
- Check constraints on numeric ranges
- Unique constraints on business keys

### Enforced by Application
- Multi-tenant data isolation
- Provider-specific metadata validation
- Financial calculation accuracy
- Status transition rules

## Orphan Prevention

### Tables that can become orphaned:
1. **User** - if enabled_by admin is deleted (FK nullable)
2. **Lead** - if owner user is deleted (FK not nullable, requires reassignment)
3. **Order** - if creator user is deleted (FK not nullable, requires handling)

### Prevention strategies:
```python
# Before deleting a user
- Reassign all owned leads to another user
- Keep orders (historical data) but mark user as deleted
- Update audit logs to preserve history
```

## Performance Considerations

### Index Coverage
- All foreign keys are indexed
- Compound indexes for common filter combinations
- GIN indexes for JSONB queries
- Partial indexes where applicable

### Query Optimization
- Use `joinedload()` for 1:N relationships
- Use `subqueryload()` for N:M relationships
- Avoid N+1 queries with proper eager loading
- Use `select_in_loading()` for collections

### Table Sizes (Estimated Growth)
```
Small tables (< 1000 rows):
  - admin_users, products, price_tiers, durations
  - provider_configs

Medium tables (1000-100,000 rows):
  - users, partners, distributors, distributor_partners

Large tables (100,000+ rows):
  - leads, lead_activities, lead_notes, lead_status_history
  - orders, order_items, contracts
  - notes, audit_logs, webhook_events, provider_sync_logs
```

## Maintenance Recommendations

### Regular Tasks
```sql
-- Analyze table statistics (weekly)
ANALYZE leads, orders, contracts;

-- Reindex frequently updated tables (monthly)
REINDEX TABLE leads;
REINDEX TABLE orders;

-- Vacuum bloated tables (as needed)
VACUUM ANALYZE audit_logs;
VACUUM ANALYZE webhook_events;
```

### Monitoring Queries
```sql
-- Check foreign key violations
SELECT * FROM pg_constraint
WHERE contype = 'f' AND convalidated = false;

-- Find missing indexes on foreign keys
SELECT c.conname, c.confrelid::regclass, a.attname
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid
WHERE c.contype = 'f';

-- Check table bloat
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

**Generated:** 2025-11-12
**Schema Version:** 1.0.0
**Total Tables:** 21
**Total Relationships:** 50+
