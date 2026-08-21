"""
Production Security & Operational Middlewares for Tanvelo:
1. Security Headers Middleware
2. Request ID / Correlation Tracing Middleware
3. Sliding-Window Rate Limiting Middleware
4. Request Body Size Limiting Middleware
"""

import time
import uuid
import logging
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.config import settings

logger = logging.getLogger("tanvelo.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects standard security headers into all HTTP responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates X-Request-ID for end-to-end distributed tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum payload size to prevent denial of service attacks."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "message": f"Request body exceeds maximum allowed size of {settings.MAX_REQUEST_BODY_BYTES} bytes."
                        }
                    )
            except ValueError:
                pass
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window in-memory rate limiter per client IP / API Key.
    Ensures abuse prevention without requiring external Redis in single-node setups.
    """

    def __init__(self, app, max_requests: int = settings.RATE_LIMIT_PER_MINUTE, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_history: Dict[str, List[float]] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        # Check API key first, then fall back to client IP
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer tv_"):
            return auth_header
        x_key = request.headers.get("X-API-Key")
        if x_key:
            return x_key
        client_host = request.client.host if request.client else "unknown"
        return f"ip_{client_host}"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health check, docs, and during testing
        if not settings.RATE_LIMIT_ENABLED or settings.is_testing:
            return await call_next(request)

        path = request.url.path
        if path.startswith("/health") or path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
            return await call_next(request)

        client_key = self._get_client_key(request)
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean history
        history = self.request_history[client_key]
        self.request_history[client_key] = [t for t in history if t > cutoff]

        if len(self.request_history[client_key]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - self.request_history[client_key][0]))
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Maximum {self.max_requests} requests per minute.",
                    "retry_after_seconds": max(1, retry_after)
                },
                headers={"Retry-After": str(max(1, retry_after))}
            )

        self.request_history[client_key].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.max_requests - len(self.request_history[client_key])))
        return response
