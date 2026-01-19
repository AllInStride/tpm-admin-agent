"""API endpoints for system integration (Smartsheet + Slack).

Provides endpoints for processing RAID bundles through the integration
pipeline and checking adapter health status.
"""

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from src.adapters import SlackAdapter, SmartsheetAdapter
from src.integration import IntegrationResult, IntegrationRouter, NotificationService
from src.output.config import ProjectOutputConfig
from src.output.schemas import RaidBundle

logger = structlog.get_logger()
router = APIRouter(prefix="/integration", tags=["integration"])


class IntegrationRequest(BaseModel):
    """Request body for integration endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    raid_bundle: RaidBundle = Field(description="RAID bundle to process")
    config: ProjectOutputConfig | None = Field(
        default=None, description="Output configuration (uses default if not provided)"
    )


class IntegrationHealthResponse(BaseModel):
    """Response for integration health check."""

    model_config = ConfigDict(str_strip_whitespace=True)

    smartsheet_configured: bool = Field(description="Smartsheet adapter has token")
    smartsheet_healthy: bool = Field(description="Smartsheet API is accessible")
    slack_configured: bool = Field(description="Slack adapter has token")
    slack_healthy: bool = Field(description="Slack API is accessible")


@router.post("", response_model=IntegrationResult)
async def process_integration(
    request: IntegrationRequest,
    dry_run: bool = Query(default=False, description="Validate without writing"),
) -> IntegrationResult:
    """Process RAID bundle through Smartsheet and Slack notifications.

    Writes RAID items to Smartsheet and sends DMs to action item owners.

    Args:
        request: IntegrationRequest with RAID bundle and optional config
        dry_run: If True, validate without actually writing

    Returns:
        IntegrationResult with write and notification results
    """
    config = request.config or ProjectOutputConfig.default()

    # Initialize adapters (lazy - only if configured)
    smartsheet = SmartsheetAdapter() if config.smartsheet_sheet_id else None
    slack = SlackAdapter() if config.notify_owners else None
    notifications = NotificationService(slack) if slack else None

    integration_router = IntegrationRouter(
        smartsheet_adapter=smartsheet,
        notification_service=notifications,
    )

    try:
        result = await integration_router.process(
            raid_bundle=request.raid_bundle,
            config=config,
            dry_run=dry_run,
        )
        logger.info(
            "integration complete",
            meeting_id=str(request.raid_bundle.meeting_id),
            smartsheet_success=result.smartsheet_result.success
            if result.smartsheet_result
            else None,
            notifications_sent=result.notifications_sent,
            dry_run=dry_run,
        )
        return result
    except Exception as e:
        logger.error("integration failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=IntegrationHealthResponse)
async def integration_health() -> IntegrationHealthResponse:
    """Check health of integration adapters.

    Returns:
        IntegrationHealthResponse with adapter status
    """
    smartsheet = SmartsheetAdapter()
    slack = SlackAdapter()

    ss_configured = smartsheet._token is not None
    ss_healthy = await smartsheet.health_check() if ss_configured else False

    slack_configured = slack._token is not None
    # SlackAdapter doesn't have health_check, verify by checking token presence
    slack_healthy = slack_configured

    return IntegrationHealthResponse(
        smartsheet_configured=ss_configured,
        smartsheet_healthy=ss_healthy,
        slack_configured=slack_configured,
        slack_healthy=slack_healthy,
    )
