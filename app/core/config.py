"""
Configuration management for Tentabo PRM

Uses pydantic-settings for type-safe configuration with environment variables.
Generates secure secrets if not provided.
"""

import secrets
import os
from typing import List, Optional
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """
    Application settings with environment variable support

    All settings can be overridden via environment variables.
    Sensitive values should always be set via environment variables in production.
    """

    # Application
    app_name: str = "Tentabo PRM"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment: development, staging, production")

    # API
    api_v1_prefix: str = "/api/v1"
    api_docs_enabled: bool = Field(default=True, description="Enable API documentation")

    # Security
    jwt_secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT token signing (256-bit)"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        description="JWT token expiration in minutes"
    )

    # API Keys
    api_key_prefix: str = "tnt_"
    api_key_length: int = 32  # bytes, results in ~43 characters in base64url

    # CORS
    cors_enabled: bool = True
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "https://tentabo.oxileo.net",
        ],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = Field(default=60, description="Requests per minute per IP")
    login_rate_limit_per_minute: int = Field(default=5, description="Login attempts per minute per IP")

    # Database (from app.database, but can override)
    database_url: Optional[str] = Field(default=None, description="Database connection URL")
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = "json"  # json or text
    log_auth_attempts: bool = True

    # LDAP (from ldap_config, but can override)
    ldap_server: Optional[str] = None
    ldap_port: Optional[int] = None
    ldap_use_ssl: bool = True
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password: Optional[str] = None

    # Session
    session_cookie_secure: bool = True  # HTTPS only in production
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"

    # Admin Account
    default_admin_username: str = "admin"
    default_admin_email: str = "admin@tentabo.local"

    # Audit logging
    audit_log_enabled: bool = True
    audit_log_retention_days: int = 365

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is long enough"""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        return v

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {', '.join(allowed)}")
        return v

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    def get_cors_config(self) -> dict:
        """Get CORS configuration for FastAPI"""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": self.cors_allow_methods,
            "allow_headers": self.cors_allow_headers,
        }

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance

    Using lru_cache ensures we only create one Settings instance
    and parse environment variables once.
    """
    return Settings()


# Export for convenience
settings = get_settings()


# Generate secure secret key helper
def generate_secret_key() -> str:
    """
    Generate a cryptographically secure secret key

    Returns:
        256-bit random string (URL-safe base64 encoded)
    """
    return secrets.token_urlsafe(32)


# Environment helpers
def is_production() -> bool:
    """Check if running in production"""
    return get_settings().is_production()


def is_development() -> bool:
    """Check if running in development"""
    return get_settings().is_development()
