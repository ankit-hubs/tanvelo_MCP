"""
Tanvelo FastAPI Main Application
"""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.memories import router as memories_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("tanvelo")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for database initialization and cleanup."""
    logger.info("Initializing Tanvelo Memory Layer...")
    await init_db()
    logger.info("Tanvelo Database initialized successfully.")
    yield
    logger.info("Shutting down Tanvelo.")


app = FastAPI(
    title="Tanvelo Memory Layer",
    description="Universal long-term memory layer for AI developer tools (MCP + FastAPI + pgvector).",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware for structured request logging and latency measurement."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000.0
    logger.info(
        f"{request.method} {request.url.path} status={response.status_code} latency={duration_ms:.2f}ms"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to avoid exposing raw stack traces."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing the request.",
            "path": request.url.path
        }
    )


# Mount routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(memories_router)


@app.get("/")
async def root():
    return {
        "product": "Tanvelo Memory",
        "tagline": "Connect Once. Remember Everywhere.",
        "version": "1.0.0",
        "health_check": "/health",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
