"""Extraction API endpoints for RAID extraction from meetings."""

import time
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from src.events.bus import EventBus
from src.events.types import (
    ActionItemExtracted,
    DecisionExtracted,
    IssueExtracted,
    MeetingProcessed,
    RiskExtracted,
)
from src.services.llm_client import LLMClient
from src.services.raid_extractor import RAIDExtractor

router = APIRouter(tags=["extraction"])


class ExtractedItemSummary(BaseModel):
    """Summary of an extracted item for API response."""

    id: UUID = Field(description="Unique identifier for the extracted item")
    description: str = Field(description="Description of the item")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")


class ExtractionRequest(BaseModel):
    """Request body for extraction endpoint."""

    transcript_text: str = Field(description="Transcript text to extract from")
    meeting_date: datetime = Field(description="Date/time of the meeting")


class ExtractionResponse(BaseModel):
    """Response model for extraction results."""

    meeting_id: UUID = Field(description="ID of the meeting")
    action_items: list[ExtractedItemSummary] = Field(
        default_factory=list, description="Extracted action items"
    )
    decisions: list[ExtractedItemSummary] = Field(
        default_factory=list, description="Extracted decisions"
    )
    risks: list[ExtractedItemSummary] = Field(
        default_factory=list, description="Extracted risks"
    )
    issues: list[ExtractedItemSummary] = Field(
        default_factory=list, description="Extracted issues"
    )
    total_extracted: int = Field(description="Total number of items extracted")
    processing_time_ms: int = Field(description="Processing time in milliseconds")


def get_event_bus(request: Request) -> EventBus:
    """Dependency to get EventBus from app state."""
    return request.app.state.event_bus


def get_raid_extractor(
    confidence_threshold: float = Query(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to include extracted items",
    ),
) -> RAIDExtractor:
    """Dependency to create RAIDExtractor with LLM client.

    Args:
        confidence_threshold: Minimum confidence score for filtering

    Returns:
        RAIDExtractor instance configured with LLMClient
    """
    llm_client = LLMClient()
    return RAIDExtractor(llm_client, confidence_threshold=confidence_threshold)


@router.post("/{meeting_id}/extract", response_model=ExtractionResponse)
async def extract_raid_items(
    meeting_id: UUID,
    request_body: ExtractionRequest,
    extractor: RAIDExtractor = Depends(get_raid_extractor),
    event_bus: EventBus = Depends(get_event_bus),
) -> ExtractionResponse:
    """Extract RAID items from a meeting transcript.

    Triggers LLM-based extraction of Risks, Action Items, Issues, and
    Decisions from the provided transcript text. Emits events for each
    extracted item and a summary event when complete.

    Args:
        meeting_id: UUID of the meeting to extract from
        request_body: Request containing transcript_text and meeting_date
        extractor: RAIDExtractor instance (injected)
        event_bus: EventBus instance (injected)

    Returns:
        ExtractionResponse with extracted items and timing info
    """
    start_time = time.time()

    # Extract all RAID items
    result = await extractor.extract_all(
        transcript_text=request_body.transcript_text,
        meeting_id=meeting_id,
        meeting_date=request_body.meeting_date,
    )

    # Emit events for each extracted item
    for action_item in result.action_items:
        await event_bus.publish_and_store(
            ActionItemExtracted(
                aggregate_id=action_item.id,
                meeting_id=meeting_id,
                action_item_id=action_item.id,
                description=action_item.description,
                assignee_name=action_item.assignee_name,
                due_date=action_item.due_date,
                confidence=action_item.confidence,
            )
        )

    for decision in result.decisions:
        await event_bus.publish_and_store(
            DecisionExtracted(
                aggregate_id=decision.id,
                meeting_id=meeting_id,
                decision_id=decision.id,
                description=decision.description,
                confidence=decision.confidence,
            )
        )

    for risk in result.risks:
        await event_bus.publish_and_store(
            RiskExtracted(
                aggregate_id=risk.id,
                meeting_id=meeting_id,
                risk_id=risk.id,
                description=risk.description,
                severity=risk.severity.value,
                confidence=risk.confidence,
            )
        )

    for issue in result.issues:
        await event_bus.publish_and_store(
            IssueExtracted(
                aggregate_id=issue.id,
                meeting_id=meeting_id,
                issue_id=issue.id,
                description=issue.description,
                priority=issue.priority.value,
                confidence=issue.confidence,
            )
        )

    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Emit summary event
    await event_bus.publish_and_store(
        MeetingProcessed(
            aggregate_id=meeting_id,
            action_item_count=len(result.action_items),
            decision_count=len(result.decisions),
            risk_count=len(result.risks),
            issue_count=len(result.issues),
            processing_time_ms=processing_time_ms,
        )
    )

    # Build response
    return ExtractionResponse(
        meeting_id=meeting_id,
        action_items=[
            ExtractedItemSummary(
                id=item.id,
                description=item.description,
                confidence=item.confidence,
            )
            for item in result.action_items
        ],
        decisions=[
            ExtractedItemSummary(
                id=item.id,
                description=item.description,
                confidence=item.confidence,
            )
            for item in result.decisions
        ],
        risks=[
            ExtractedItemSummary(
                id=item.id,
                description=item.description,
                confidence=item.confidence,
            )
            for item in result.risks
        ],
        issues=[
            ExtractedItemSummary(
                id=item.id,
                description=item.description,
                confidence=item.confidence,
            )
            for item in result.issues
        ],
        total_extracted=(
            len(result.action_items)
            + len(result.decisions)
            + len(result.risks)
            + len(result.issues)
        ),
        processing_time_ms=processing_time_ms,
    )
