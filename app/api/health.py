"""
Health, Liveness, and Readiness Diagnostic Endpoints
Provides probes for container orchestrators (Kubernetes, AWS ECS, Docker Compose).
"""

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, check_database_health
from app.services.embedding_service import embedding_service

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """General health check confirming service status and database connectivity."""
    db_ok, db_msg = await check_database_health()
    status_str = "ok" if db_ok else "degraded"

    return {
        "status": status_str,
        "service": "tanvelo-memory",
        "version": "1.0.0",
        "environment": settings.TANVELO_ENV,
        "database": db_msg,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER
    }


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe — returns 200 OK if server process is running."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(response: Response):
    """
    Kubernetes readiness probe — verifies database and embedding subsystems are ready
    to serve customer traffic.
    """
    db_ok, db_msg = await check_database_health()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": f"Database check failed: {db_msg}"
        }

    return {
        "status": "ready",
        "database": "connected",
        "cache_entries": len(embedding_service._cache)
    }
