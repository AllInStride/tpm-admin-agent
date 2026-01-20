"""API endpoints for communication artifact generation.

Provides REST endpoints for:
- POST /communication/exec-status (COM-01)
- POST /communication/team-status (COM-02)
- POST /communication/escalation (COM-03)
- POST /communication/talking-points (COM-04)
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.communication.schemas import EscalationRequest
from src.communication.service import CommunicationService, GenerationResult

router = APIRouter(prefix="/communication", tags=["communication"])


class StatusRequest(BaseModel):
    """Request body for status generation endpoints."""

    project_id: str = Field(description="Project ID to report on")
    since: datetime = Field(description="Start of reporting period")
    until: datetime | None = Field(
        default=None, description="End of reporting period (default: now)"
    )


class TalkingPointsRequest(BaseModel):
    """Request body for talking points generation."""

    project_id: str = Field(description="Project ID to generate talking points for")
    meeting_type: str = Field(
        default="exec_review",
        description="Type of meeting (e.g., exec_review, board_meeting)",
    )
    since: datetime | None = Field(
        default=None, description="Start of data period (default: 30 days ago)"
    )


class GenerationResponse(BaseModel):
    """Response from generation endpoints."""

    artifact_type: str = Field(description="Type of artifact generated")
    markdown: str = Field(description="Markdown-formatted output")
    plain_text: str = Field(description="Plain text output")
    generated_at: datetime = Field(description="When the artifact was generated")
    metadata: dict = Field(description="Additional metadata (RAG status, counts, etc.)")


def get_communication_service() -> CommunicationService:
    """Dependency to get CommunicationService instance from app state.

    Returns:
        CommunicationService from app state

    Raises:
        HTTPException: If service not initialized
    """
    from src.main import app

    if not hasattr(app.state, "communication_service"):
        raise HTTPException(
            status_code=503,
            detail="CommunicationService not initialized",
        )
    return app.state.communication_service


def _to_response(result: GenerationResult) -> GenerationResponse:
    """Convert GenerationResult to API response.

    Args:
        result: GenerationResult from service

    Returns:
        GenerationResponse for API client
    """
    return GenerationResponse(
        artifact_type=result.artifact_type,
        markdown=result.artifact.markdown,
        plain_text=result.artifact.plain_text,
        generated_at=result.generated_at,
        metadata=result.artifact.metadata,
    )


@router.post("/exec-status", response_model=GenerationResponse)
async def generate_exec_status(
    request: StatusRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate executive status update (COM-01).

    Produces a half-page status update suitable for exec audiences:
    - RAG status breakdown
    - High-level progress summary
    - Blockers with explicit asks
    - Next period outlook
    """
    result = await service.generate_exec_status(
        project_id=request.project_id,
        since=request.since,
        until=request.until,
    )
    return _to_response(result)


@router.post("/team-status", response_model=GenerationResponse)
async def generate_team_status(
    request: StatusRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate team status update (COM-02).

    Produces detailed status update suitable for team audiences:
    - Completed items first (celebrate wins)
    - Full action item list with owners and due dates
    - Decisions, risks, and issues sections
    """
    result = await service.generate_team_status(
        project_id=request.project_id,
        since=request.since,
        until=request.until,
    )
    return _to_response(result)


@router.post("/escalation", response_model=GenerationResponse)
async def generate_escalation(
    request: EscalationRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate escalation email (COM-03).

    Produces Problem-Impact-Ask formatted escalation email with:
    - Clear problem statement
    - Impact assessment
    - 2-3 options with pros/cons
    - Explicit decision deadline
    """
    result = await service.generate_escalation(request)
    return _to_response(result)


@router.post("/talking-points", response_model=GenerationResponse)
async def generate_talking_points(
    request: TalkingPointsRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate exec talking points (COM-04).

    Produces narrative-focused talking points for exec meetings:
    - High-level story summary
    - 5-7 key talking points
    - Anticipated Q&A with categorized questions
    """
    result = await service.generate_talking_points(
        project_id=request.project_id,
        meeting_type=request.meeting_type,
        since=request.since,
    )
    return _to_response(result)
