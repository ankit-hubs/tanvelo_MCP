"""
Shared Async HTTP Client Manager with Connection Pooling and Lifecycle Support.
Ensures connection reuse, keep-alive, and event loop safety.
"""

import asyncio
import logging
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger("tanvelo.http_client")


class HTTPClientManager:
    """Singleton HTTP client manager with persistent connection pooling."""
    _client: Optional[httpx.AsyncClient] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if (
            cls._client is None
            or cls._client.is_closed
            or (cls._loop is not None and current_loop is not None and cls._loop != current_loop)
        ):
            limits = httpx.Limits(
                max_keepalive_connections=50,
                max_connections=200,
                keepalive_expiry=30.0
            )
            timeout = httpx.Timeout(
                timeout=settings.HTTP_TIMEOUT_SECONDS,
                connect=5.0,
                read=settings.HTTP_TIMEOUT_SECONDS,
                write=5.0
            )
            cls._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                follow_redirects=True
            )
            cls._loop = current_loop
            logger.debug("Initialized/Reset async HTTP client pool for event loop.")
        return cls._client

    @classmethod
    async def close_client(cls):
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None
            cls._loop = None
            logger.debug("Closed global async HTTP client pool.")


http_client_manager = HTTPClientManager
