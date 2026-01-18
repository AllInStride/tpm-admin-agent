"""Health check endpoints for monitoring and orchestration."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.config import settings

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    timestamp: datetime
    version: str
    environment: str


class LivenessResponse(BaseModel):
    """Response model for liveness probe."""

    status: str


class ReadinessResponse(BaseModel):
    """Response model for readiness probe."""

    status: str
    checks: dict[str, str]


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Liveness probe - app is running."""
    return LivenessResponse(status="alive")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse:
    """Readiness probe - app can serve traffic.

    Checks:
    - API is responding
    - Database is connected and healthy
    """
    checks: dict[str, str] = {"api": "ok"}

    # Check database if available
    db = getattr(request.app.state, "db", None)
    if db:
        try:
            is_healthy = await db.is_healthy()
            checks["database"] = "ok" if is_healthy else "failed"
        except Exception:
            checks["database"] = "failed"
    else:
        checks["database"] = "not_configured"

    status = "ready" if all(v == "ok" for v in checks.values()) else "not_ready"
    return ReadinessResponse(status=status, checks=checks)
