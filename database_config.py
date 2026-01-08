"""
Database configuration for Tentabo PRM
Using SQLAlchemy 2.0 with PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from typing import Generator

# Database URL components
DB_USER = "tentabo_oxibox"
DB_PASSWORD = "CN1IdxkA^waY9tVdEivk%2Q&fpQWA4y!"
DB_HOST = "marshmallow02.oxileo.net"
DB_PORT = "5432"
DB_NAME = "tentabo_oxibox"

# Construct database URL - properly encode special characters
from urllib.parse import quote_plus

encoded_password = quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Alternative: Use environment variable if available
DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_URL)

# SQLAlchemy engine configuration
engine = create_engine(
    DATABASE_URL,
    # Connection pool settings
    pool_pre_ping=True,  # Test connections before using
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Maximum overflow connections
    echo=False,  # Set to True for SQL query logging
    future=True,  # Use SQLAlchemy 2.0 style
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db() -> Generator:
    """
    Database session dependency for FastAPI endpoints
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check function
async def check_database_connection():
    """
    Check if database is accessible
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

# Create all tables (use Alembic in production)
def create_tables():
    """
    Create all tables in the database.
    Note: Use Alembic migrations in production instead of this.
    """
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """
    Drop all tables in the database.
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)