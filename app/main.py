"""
Main FastAPI application for Tentabo PRM

This is the entry point for the Tentabo Partner Relationship Management system.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.database import check_database_connection
from app.auth.ldap_auth import check_ldap_connection
from app.middleware.authentication import (
    AuthenticationMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.v1 import auth, products, partners, leads, orders, contracts, users, product_types
from app.api import dashboard, providers
from app.providers.registry import get_registry, ProviderType
from app.providers.mock_providers import MockCRMProvider, MockBillingProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Runs on startup and shutdown to initialize/cleanup resources.
    """
    # Startup
    logger.info("Starting Tentabo PRM...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize provider registry with mock providers
    registry = get_registry()
    registry.register(ProviderType.CRM, "mock", MockCRMProvider, set_active=True)
    registry.register(ProviderType.BILLING, "mock", MockBillingProvider, set_active=True)
    logger.info("Provider registry initialized with mock providers")

    # Check database connection
    db_ok = await check_database_connection()
    if db_ok:
        logger.info("Database connection: OK")
    else:
        logger.error("Database connection: FAILED")

    # Check LDAP connection
    ldap_ok = check_ldap_connection()
    if ldap_ok:
        logger.info("LDAP connection: OK")
    else:
        logger.warning("LDAP connection: FAILED (will retry on authentication)")

    logger.info("Tentabo PRM started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Tentabo PRM...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Partner Relationship Management System",
    docs_url="/api/docs" if settings.api_docs_enabled else None,
    redoc_url="/api/redoc" if settings.api_docs_enabled else None,
    openapi_url="/api/openapi.json" if settings.api_docs_enabled else None,
    lifespan=lifespan,
)


# Add CORS middleware
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        **settings.get_cors_config()
    )
    logger.info(f"CORS enabled for origins: {settings.cors_origins}")


# Add custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuthenticationMiddleware)


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions with consistent JSON format
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with detailed information
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "status_code": 422,
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Don't expose internal errors in production
    if settings.is_production():
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "status_code": 500,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(exc),
                "status_code": 500,
                "type": type(exc).__name__,
            },
        )


# Include routers
app.include_router(
    auth.router,
    prefix=settings.api_v1_prefix,
    tags=["Authentication"]
)

app.include_router(
    products.router,
    prefix=settings.api_v1_prefix,
    tags=["Products"]
)

app.include_router(
    product_types.router,
    prefix=settings.api_v1_prefix,
    tags=["ProductTypes"]
)

app.include_router(
    partners.router,
    prefix=settings.api_v1_prefix,
    tags=["Partners", "Distributors"]
)

app.include_router(
    leads.router,
    prefix=settings.api_v1_prefix,
    tags=["Leads"]
)

app.include_router(
    orders.router,
    prefix=settings.api_v1_prefix,
    tags=["Orders"]
)

app.include_router(
    contracts.router,
    prefix=settings.api_v1_prefix,
    tags=["Contracts"]
)

app.include_router(
    users.router,
    prefix=settings.api_v1_prefix,
    tags=["Users"]
)

app.include_router(
    dashboard.router,
    tags=["Dashboard"]
)

app.include_router(
    providers.router,
    tags=["Providers"]
)


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check endpoint

    Returns 200 if the application is running.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health/db", tags=["Health"])
async def database_health_check():
    """
    Database connectivity health check

    Returns 200 if database is accessible, 503 otherwise.
    """
    db_ok = await check_database_connection()

    if db_ok:
        return {
            "status": "ok",
            "database": "connected",
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": "disconnected",
            },
        )


@app.get("/health/ldap", tags=["Health"])
async def ldap_health_check():
    """
    LDAP connectivity health check

    Returns 200 if LDAP is accessible, 503 otherwise.
    """
    ldap_ok = check_ldap_connection()

    if ldap_ok:
        return {
            "status": "ok",
            "ldap": "connected",
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "ldap": "disconnected",
            },
        )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs" if settings.api_docs_enabled else None,
        "health": "/health",
        "api": {
            "v1": settings.api_v1_prefix,
        },
    }


# For development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development(),
        log_level=settings.log_level.lower(),
    )
