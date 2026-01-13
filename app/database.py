"""
Database configuration for Tentabo PRM
Using SQLAlchemy 2.0 with PostgreSQL
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database URL components (defaults for local development)
DB_USER = os.getenv("DB_USER", "tentabo")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tentabo_dev")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tentabo")

# Construct database URL with proper encoding
# Using postgresql+psycopg for SQLAlchemy with psycopg3
encoded_password = quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Override with environment variable if available
DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_URL)

# SQLAlchemy 2.0 engine configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_pre_ping=True,  # Test connections before using
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Maximum overflow connections
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # SQL query logging
    future=True,  # SQLAlchemy 2.0 style
    connect_args={"connect_timeout": 5},  # 5 second connection timeout
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Base class for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI endpoints

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_database_connection() -> bool:
    """
    Health check for database connectivity

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def create_all_tables():
    """
    Create all tables in the database.

    WARNING: Use Alembic migrations in production instead of this.
    This is only for initial development/testing.
    """
    # Import all models to ensure they are registered with Base.metadata
    # This import must happen before create_all() is called
    from app.models import (
        AdminUser, User, UserRole, APIKey,
        Product, PriceTier, Duration, ProductType,
        Lead, LeadStatus, LeadActivity, LeadNote, LeadStatusHistory,
        Order, OrderItem, OrderStatus, Contract, ContractStatus,
        Partner, Distributor, DistributorPartner,
        ProviderConfig, ProviderType, ProviderSyncLog, Note, AuditLog, WebhookEvent,
        PennylaneConnection, PennylaneInvoice, PennylaneQuote, PennylaneSubscription,
    )

    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """
    Drop all tables in the database.

    WARNING: This will delete all data! Only use in development.
    """
    Base.metadata.drop_all(bind=engine)
