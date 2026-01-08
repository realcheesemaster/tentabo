"""
SQLAlchemy Models for Tentabo PRM
All database models using SQLAlchemy 2.0 syntax
"""

from app.models.auth import AdminUser, User, UserRole
from app.models.api_key import APIKey
from app.models.core import Product, PriceTier, Duration
from app.models.product_type import ProductType
from app.models.crm import (
    Lead,
    LeadStatus,
    LeadActivity,
    LeadNote,
    LeadStatusHistory,
)
from app.models.billing import Order, OrderItem, OrderStatus, Contract, ContractStatus
from app.models.partner import Partner, Distributor, DistributorPartner
from app.models.system import (
    ProviderConfig,
    ProviderType,
    ProviderSyncLog,
    Note,
    AuditLog,
    WebhookEvent,
)

__all__ = [
    # Auth
    "AdminUser",
    "User",
    "UserRole",
    "APIKey",
    # Core
    "Product",
    "PriceTier",
    "Duration",
    "ProductType",
    # CRM
    "Lead",
    "LeadStatus",
    "LeadActivity",
    "LeadNote",
    "LeadStatusHistory",
    # Billing
    "Order",
    "OrderItem",
    "OrderStatus",
    "Contract",
    "ContractStatus",
    # Partner
    "Partner",
    "Distributor",
    "DistributorPartner",
    # System
    "ProviderConfig",
    "ProviderType",
    "ProviderSyncLog",
    "Note",
    "AuditLog",
    "WebhookEvent",
]
