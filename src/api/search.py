"""Search API endpoints for cross-meeting intelligence.

Provides endpoints for full-text search, open items dashboard,
item history, and duplicate detection.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.repositories.open_items_repo import OpenItemsRepository
from src.search.duplicate_detector import (
    DuplicateCheckResult,
    DuplicateDetector,
)
from src.search.fts_service import FTSService, SearchResponse
from src.search.open_items import (
    GroupedOpenItems,
    ItemHistory,
    OpenItemFilter,
    OpenItemSummary,
)

search_router = APIRouter(prefix="/search", tags=["search"])


# Pydantic models for request/response
class CloseItemRequest(BaseModel):
    """Request body for closing an item."""

    status: str = Field(default="completed", description="New status for the item")


class CloseItemResponse(BaseModel):
    """Response for close item endpoint."""

    success: bool = Field(description="Whether the operation succeeded")
    item_id: str = Field(description="ID of the closed item")
    new_status: str = Field(description="New status of the item")


class DuplicateCheckRequest(BaseModel):
    """Request body for duplicate check."""

    description: str = Field(description="Description to check for duplicates")
    item_type: str | None = Field(default=None, description="Optional item type filter")


class RejectDuplicateRequest(BaseModel):
    """Request body for rejecting a duplicate."""

    duplicate_id: str = Field(description="ID of the duplicate to reject")


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = Field(description="Whether the operation succeeded")


# Dependency functions
def get_fts_service(request: Request) -> FTSService:
    """Get FTSService from app state."""
    if not hasattr(request.app.state, "fts_service"):
        raise HTTPException(status_code=500, detail="FTSService not initialized")
    return request.app.state.fts_service


def get_open_items_repo(request: Request) -> OpenItemsRepository:
    """Get OpenItemsRepository from app state."""
    if not hasattr(request.app.state, "open_items_repo"):
        raise HTTPException(
            status_code=500, detail="OpenItemsRepository not initialized"
        )
    return request.app.state.open_items_repo


def get_duplicate_detector(request: Request) -> DuplicateDetector:
    """Get DuplicateDetector from app state."""
    if not hasattr(request.app.state, "duplicate_detector"):
        raise HTTPException(status_code=500, detail="DuplicateDetector not initialized")
    return request.app.state.duplicate_detector


@search_router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum results"),
    fts_service: FTSService = Depends(get_fts_service),
) -> SearchResponse:
    """Search across RAID items and transcripts.

    Supports structured filter syntax like 'type:action owner:john'.
    Returns results with highlighted snippets and relevance scores.
    """
    return await fts_service.search(q, limit)


@search_router.get("/open-items", response_model=GroupedOpenItems)
async def get_open_items(
    item_type: str | None = Query(default=None, description="Filter by item type"),
    owner: str | None = Query(default=None, description="Filter by owner"),
    meeting_id: str | None = Query(default=None, description="Filter by meeting"),
    overdue_only: bool = Query(default=False, description="Only show overdue items"),
    due_within_days: int | None = Query(
        default=None, ge=0, description="Items due within N days"
    ),
    group_by: Literal["due_date", "owner", "item_type"] = Query(
        default="due_date", description="How to group results"
    ),
    repo: OpenItemsRepository = Depends(get_open_items_repo),
) -> GroupedOpenItems:
    """Get open items for dashboard display.

    Returns items grouped by the specified field with summary counts.
    """
    filter_obj = OpenItemFilter(
        item_type=item_type,
        owner=owner,
        meeting_id=meeting_id,
        overdue_only=overdue_only,
        due_within_days=due_within_days,
    )
    return await repo.get_items(filter_obj, group_by)


@search_router.get("/open-items/summary", response_model=OpenItemSummary)
async def get_open_items_summary(
    repo: OpenItemsRepository = Depends(get_open_items_repo),
) -> OpenItemSummary:
    """Get summary counts of open items.

    Returns totals for overdue, due today, and due this week.
    """
    return await repo.get_summary()


@search_router.post("/items/{item_id}/close", response_model=CloseItemResponse)
async def close_item(
    item_id: str,
    body: CloseItemRequest | None = None,
    repo: OpenItemsRepository = Depends(get_open_items_repo),
) -> CloseItemResponse:
    """Close an item by updating its status.

    Marks an item as completed, cancelled, or another closed status.
    """
    new_status = body.status if body else "completed"
    updated = await repo.close_item(item_id, new_status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return CloseItemResponse(
        success=True,
        item_id=item_id,
        new_status=new_status,
    )


@search_router.get("/items/{item_id}/history", response_model=ItemHistory)
async def get_item_history(
    item_id: str,
    repo: OpenItemsRepository = Depends(get_open_items_repo),
) -> ItemHistory:
    """Get history of an item across meetings.

    Returns a timeline showing when the item was created, updated, or mentioned.
    """
    history = await repo.get_item_history(item_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return history


@search_router.post("/items/check-duplicates", response_model=DuplicateCheckResult)
async def check_duplicates(
    body: DuplicateCheckRequest,
    detector: DuplicateDetector = Depends(get_duplicate_detector),
) -> DuplicateCheckResult:
    """Check if a description has potential duplicates.

    Uses fuzzy matching to find similar items in the database.
    """
    return await detector.find_duplicates(
        body.description,
        item_type=body.item_type,
    )


@search_router.post("/items/{item_id}/reject-duplicate", response_model=SuccessResponse)
async def reject_duplicate(
    item_id: str,
    body: RejectDuplicateRequest,
    detector: DuplicateDetector = Depends(get_duplicate_detector),
) -> SuccessResponse:
    """Record rejection of a duplicate suggestion.

    Prevents the system from re-suggesting this duplicate pair.
    """
    await detector.record_rejection(item_id, body.duplicate_id)
    return SuccessResponse(success=True)
