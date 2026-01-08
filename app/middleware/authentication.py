"""
Authentication middleware for Tentabo PRM

This middleware is optional - authentication is primarily handled via
FastAPI dependencies (Depends(get_current_user)).

This middleware can be used for:
- Request logging with user context
- Rate limiting per user/IP
- Request timing and performance monitoring
"""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authentication-related functionality

    Note: This does NOT enforce authentication - that's done via dependencies.
    This middleware adds context and logging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add authentication context

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Start timing
        start_time = time.time()

        # Extract authentication info (if present)
        auth_header = request.headers.get("authorization", "")
        has_auth = bool(auth_header and auth_header.startswith("Bearer "))

        # Determine auth type
        auth_type = None
        if has_auth:
            token = auth_header.replace("Bearer ", "")
            if token.startswith("tnt_"):
                auth_type = "api_key"
            else:
                auth_type = "jwt"

        # Add to request state for use in handlers
        request.state.auth_type = auth_type
        request.state.start_time = start_time

        # Log request
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"{request.method} {request.url.path} from {client_ip} "
            f"(auth: {auth_type or 'none'})"
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} "
                f"({duration:.3f}s)"
            )

            # Add timing header
            response.headers["X-Process-Time"] = f"{duration:.3f}"

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} failed after {duration:.3f}s: {e}"
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware

    For production, use Redis-based rate limiting like slowapi or similar.
    """

    def __init__(self, app, calls: int = 60, period: int = 60):
        """
        Initialize rate limiter

        Args:
            app: FastAPI app
            calls: Number of calls allowed
            period: Time period in seconds
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = {}  # In-memory storage (use Redis in production)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limit before processing request

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or 429 if rate limited
        """
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"

        # For now, just pass through
        # TODO: Implement proper rate limiting with Redis
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Remove server header
        if "Server" in response.headers:
            del response.headers["Server"]

        return response
