"""Health check endpoints for monitoring and orchestration."""

from datetime import UTC, datetime

from fastapi import APIRouter
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
async def readiness() -> ReadinessResponse:
    """Readiness probe - app can serve traffic.

    Note: Database check will be added in Plan 03 when event store is implemented.
    """
    checks = {
        "api": "ok",
        # "database": "ok" - added in Plan 03
    }
    status = "ready" if all(v == "ok" for v in checks.values()) else "not_ready"
    return ReadinessResponse(status=status, checks=checks)
