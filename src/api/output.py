"""Output generation API endpoint.

Exposes the output generation pipeline via REST API,
accepting meeting data and returning generated output URLs.
"""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from src.adapters.drive_adapter import DriveAdapter
from src.adapters.sheets_adapter import SheetsAdapter
from src.output.config import ProjectOutputConfig
from src.output.router import OutputRouter
from src.output.schemas import (
    ActionItemData,
    DecisionItem,
    IssueItem,
    MinutesContext,
    RaidBundle,
    RiskItem,
)

logger = structlog.get_logger()
router = APIRouter()

# Module-level router instance (can be replaced via dependency injection)
_output_router: OutputRouter | None = None


def get_output_router() -> OutputRouter:
    """Get or create the OutputRouter instance.

    Returns:
        OutputRouter configured with available adapters
    """
    global _output_router
    if _output_router is None:
        # Try to create adapters if credentials available
        try:
            sheets = SheetsAdapter()
        except Exception:
            sheets = None

        try:
            drive = DriveAdapter()
        except Exception:
            drive = None

        _output_router = OutputRouter(
            sheets_adapter=sheets,
            drive_adapter=drive,
        )
    return _output_router


class OutputRequest(BaseModel):
    """Request body for output generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    meeting_id: UUID = Field(description="Meeting UUID")
    meeting_title: str = Field(description="Meeting title")
    meeting_date: datetime = Field(description="When the meeting occurred")
    duration_minutes: int | None = Field(default=None, description="Meeting duration")
    attendees: list[str] = Field(default_factory=list, description="List of attendees")
    decisions: list[dict] = Field(default_factory=list, description="Raw decision data")
    action_items: list[dict] = Field(
        default_factory=list, description="Raw action item data"
    )
    risks: list[dict] = Field(default_factory=list, description="Raw risk data")
    issues: list[dict] = Field(default_factory=list, description="Raw issue data")
    config: ProjectOutputConfig | None = Field(
        default=None,
        description="Optional output config (uses default if not provided)",
    )


class OutputResponse(BaseModel):
    """Response from output generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    success: bool = Field(description="Overall success status")
    meeting_id: UUID = Field(description="Meeting ID processed")
    minutes_url: str | None = Field(
        default=None, description="Google Drive URL for minutes"
    )
    sheets_url: str | None = Field(
        default=None, description="Google Sheets URL for RAID items"
    )
    markdown_preview: str = Field(description="First 500 chars of rendered markdown")
    items_written: int = Field(default=0, description="Number of RAID items written")
    errors: list[str] = Field(default_factory=list, description="Error messages if any")


class HealthResponse(BaseModel):
    """Response from health check endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: str = Field(description="Overall status")
    adapters: dict[str, bool] = Field(description="Adapter health status")


@router.post("", response_model=OutputResponse)
async def generate_output(
    request: OutputRequest,
    dry_run: bool = Query(default=False, description="If true, render without writing"),
) -> OutputResponse:
    """Generate meeting output from meeting data.

    Takes meeting information and RAID items, renders minutes,
    and routes to configured destinations (Drive, Sheets).

    Args:
        request: OutputRequest with meeting data
        dry_run: If true, render but don't write to destinations

    Returns:
        OutputResponse with URLs and status
    """
    output_router = get_output_router()
    config = request.config or ProjectOutputConfig.default()

    # Build MinutesContext from request
    context = MinutesContext(
        meeting_id=request.meeting_id,
        meeting_title=request.meeting_title,
        meeting_date=request.meeting_date,
        duration_minutes=request.duration_minutes,
        attendees=request.attendees,
        decisions=[DecisionItem(**d) for d in request.decisions],
        action_items=[ActionItemData(**a) for a in request.action_items],
        risks=[RiskItem(**r) for r in request.risks],
        issues=[IssueItem(**i) for i in request.issues],
        next_steps=[a.get("description", "") for a in request.action_items[:5]],
    )

    # Build RaidBundle
    bundle = RaidBundle(
        meeting_id=request.meeting_id,
        decisions=context.decisions,
        action_items=context.action_items,
        risks=context.risks,
        issues=context.issues,
    )

    logger.info(
        "generating output",
        meeting_id=str(request.meeting_id),
        dry_run=dry_run,
        decisions=len(request.decisions),
        actions=len(request.action_items),
        risks=len(request.risks),
        issues=len(request.issues),
    )

    # Generate output
    result = await output_router.generate_output(
        context, bundle, config, dry_run=dry_run
    )

    # Build response
    errors = []
    if result.minutes_result and not result.minutes_result.success:
        errors.append(result.minutes_result.error_message or "Minutes upload failed")
    if result.raid_result and not result.raid_result.success:
        errors.append(result.raid_result.error_message or "RAID items write failed")

    # Truncate markdown preview to 500 chars
    preview = result.rendered.markdown[:500]
    if len(result.rendered.markdown) > 500:
        preview += "..."

    return OutputResponse(
        success=result.all_successful,
        meeting_id=request.meeting_id,
        minutes_url=result.minutes_result.url if result.minutes_result else None,
        sheets_url=result.raid_result.url if result.raid_result else None,
        markdown_preview=preview,
        items_written=result.total_items_written,
        errors=errors,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check health of output adapters.

    Returns:
        HealthResponse with adapter status
    """
    output_router = get_output_router()

    adapters = {}

    # Check Drive adapter
    if output_router.drive_adapter:
        adapters["drive"] = await output_router.drive_adapter.health_check()
    else:
        adapters["drive"] = False

    # Check Sheets adapter
    if output_router.sheets_adapter:
        adapters["sheets"] = await output_router.sheets_adapter.health_check()
    else:
        adapters["sheets"] = False

    # Overall status based on at least one working adapter
    status = "ok" if any(adapters.values()) else "degraded"
    if not any([output_router.drive_adapter, output_router.sheets_adapter]):
        status = "no_adapters"

    return HealthResponse(status=status, adapters=adapters)
