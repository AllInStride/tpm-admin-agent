"""API endpoints for meeting prep management.

Provides endpoints to trigger manual prep, scan for meetings,
get configuration, and check scheduler status.
"""

from fastapi import APIRouter, HTTPException

from src.prep.prep_service import PrepService
from src.prep.scheduler import get_scheduler
from src.prep.schemas import MeetingPrepRequest, PrepConfig

router = APIRouter(prefix="/prep", tags=["prep"])


@router.post("/trigger")
async def trigger_prep(request: MeetingPrepRequest) -> dict:
    """Manually trigger prep for a specific meeting.

    Args:
        request: MeetingPrepRequest with calendar_id, event_id, project_id

    Returns:
        Dict with meeting_id, recipients, items count
    """
    try:
        prep_service = PrepService.get_instance()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="PrepService not initialized",
        )

    # Build minimal event dict - prepare_for_meeting will fetch full details
    event = {"id": request.event_id}

    result = await prep_service.prepare_for_meeting(
        event=event,
        project_id=request.project_id,
    )

    return result


@router.post("/scan")
async def scan_now(calendar_id: str = "primary") -> dict:
    """Manually trigger a scan for upcoming meetings.

    Args:
        calendar_id: Calendar to scan (default: primary)

    Returns:
        Dict with scanned status, preps_sent count, and results
    """
    try:
        prep_service = PrepService.get_instance()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="PrepService not initialized",
        )

    results = await prep_service.scan_and_prepare(calendar_id)

    return {
        "scanned": True,
        "preps_sent": len(results),
        "results": results,
    }


@router.get("/config")
async def get_config() -> PrepConfig:
    """Get current prep configuration.

    Returns:
        PrepConfig with lead_time_minutes, delivery_method, max_items, lookback_days
    """
    try:
        prep_service = PrepService.get_instance()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="PrepService not initialized",
        )

    return prep_service._config


@router.get("/status")
async def get_status() -> dict:
    """Get scheduler status and job information.

    Returns:
        Dict with scheduler_running, jobs list (id, next_run)
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    return {
        "scheduler_running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
            for job in jobs
        ],
    }
