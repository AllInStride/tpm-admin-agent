"""Identity resolution API endpoints.

Provides endpoints for resolving names from transcripts to project roster,
and for human review workflow to confirm/correct matches.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.adapters.roster_adapter import RosterAdapter
from src.identity.resolver import IdentityResolver
from src.identity.schemas import ResolutionResult

router = APIRouter(prefix="/identity", tags=["identity"])


class ResolveRequest(BaseModel):
    """Request to resolve names from extraction."""

    names: list[str] = Field(description="Names to resolve (from transcript)")
    project_id: str = Field(description="Project ID for roster lookup")
    roster_spreadsheet_id: str = Field(description="Google Sheets ID for roster")


class ResolvedIdentity(BaseModel):
    """Single resolved identity for API response."""

    transcript_name: str = Field(description="Original name from transcript")
    resolved_email: str | None = Field(
        default=None, description="Matched person's email"
    )
    resolved_name: str | None = Field(default=None, description="Canonical name")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence (0-1)")
    source: str = Field(description="How match was determined")
    requires_review: bool = Field(description="True if needs human confirmation")
    alternatives: list[tuple[str, float]] = Field(
        default_factory=list,
        description="Other possible matches with scores [(name, score), ...]",
    )

    @classmethod
    def from_resolution_result(cls, result: ResolutionResult) -> "ResolvedIdentity":
        """Convert internal ResolutionResult to API response model."""
        return cls(
            transcript_name=result.transcript_name,
            resolved_email=result.resolved_email,
            resolved_name=result.resolved_name,
            confidence=result.confidence,
            source=result.source.value,
            requires_review=result.requires_review,
            alternatives=result.alternatives,
        )


class ResolveResponse(BaseModel):
    """Response with resolved identities."""

    resolved: list[ResolvedIdentity] = Field(description="Resolved identity matches")
    pending_review_count: int = Field(description="Count needing human review")
    review_summary: str | None = Field(
        default=None,
        description="Human-readable summary if items need review",
    )


class ConfirmRequest(BaseModel):
    """Request to confirm/correct an identity match."""

    project_id: str = Field(description="Project ID for learned mapping")
    transcript_name: str = Field(description="Original name from transcript")
    confirmed_email: str = Field(description="Correct email address")
    confirmed_name: str = Field(description="Correct canonical name")


class ConfirmResponse(BaseModel):
    """Response after confirming identity."""

    transcript_name: str = Field(description="Original name that was corrected")
    confirmed_email: str = Field(description="Confirmed email address")
    confirmed_name: str = Field(description="Confirmed canonical name")
    learned: bool = Field(description="True if mapping was saved for future use")


def get_roster_adapter(request: Request) -> RosterAdapter:
    """Dependency to get RosterAdapter from app state."""
    return request.app.state.roster_adapter


def get_identity_resolver(request: Request) -> IdentityResolver:
    """Dependency to get IdentityResolver from app state."""
    return request.app.state.identity_resolver


def _generate_review_summary(
    resolved: list[ResolvedIdentity], pending_count: int
) -> str | None:
    """Generate human-readable summary of items needing review.

    Args:
        resolved: List of resolved identities
        pending_count: Number requiring review

    Returns:
        Summary string or None if no review needed
    """
    if pending_count == 0:
        return None

    review_items = [r for r in resolved if r.requires_review]
    if not review_items:
        return None

    lines = [f"{pending_count} name(s) need review:"]
    for item in review_items[:5]:  # Show first 5
        if item.resolved_name and item.confidence > 0:
            lines.append(
                f"  - '{item.transcript_name}' -> "
                f"'{item.resolved_name}' ({item.confidence:.0%} confidence)"
            )
        elif item.alternatives:
            top_alt = item.alternatives[0]
            lines.append(
                f"  - '{item.transcript_name}' -> "
                f"'{top_alt[0]}' ({top_alt[1]:.0%})? (needs confirmation)"
            )
        else:
            lines.append(f"  - '{item.transcript_name}' -> no match found")

    if pending_count > 5:
        lines.append(f"  ... and {pending_count - 5} more")

    return "\n".join(lines)


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_identities(
    request: ResolveRequest,
    roster_adapter: RosterAdapter = Depends(get_roster_adapter),
    resolver: IdentityResolver = Depends(get_identity_resolver),
) -> ResolveResponse:
    """Resolve transcript names to project roster.

    Attempts to match each name against the project roster using:
    1. Exact match
    2. Learned mappings (from previous corrections)
    3. Fuzzy matching (Jaro-Winkler)
    4. LLM inference (for ambiguous cases)

    Returns matches with confidence scores. Items with confidence < 85%
    are flagged for human review (requires_review=True).

    Args:
        request: Names to resolve with project and roster info
        roster_adapter: Adapter for loading roster from Google Sheets
        resolver: Identity resolution service

    Returns:
        ResolveResponse with matches and review summary
    """
    # Load roster from Google Sheets
    roster = roster_adapter.load_roster(request.roster_spreadsheet_id)

    # Resolve each name
    results = await resolver.resolve_all(
        names=request.names,
        roster=roster,
        project_id=request.project_id,
    )

    # Convert to API response models
    resolved = [ResolvedIdentity.from_resolution_result(r) for r in results]
    pending_count = sum(1 for r in resolved if r.requires_review)
    review_summary = _generate_review_summary(resolved, pending_count)

    return ResolveResponse(
        resolved=resolved,
        pending_review_count=pending_count,
        review_summary=review_summary,
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_identity(
    request: ConfirmRequest,
    resolver: IdentityResolver = Depends(get_identity_resolver),
) -> ConfirmResponse:
    """Confirm or correct an identity match.

    Saves the mapping for future resolution. Next time this transcript_name
    appears in this project, it will automatically resolve to confirmed_email.

    Args:
        request: Confirmation with correct identity
        resolver: Identity resolution service

    Returns:
        ConfirmResponse indicating mapping was saved
    """
    # Save learned mapping
    await resolver.learn_mapping(
        project_id=request.project_id,
        transcript_name=request.transcript_name,
        resolved_email=request.confirmed_email,
        resolved_name=request.confirmed_name,
    )

    return ConfirmResponse(
        transcript_name=request.transcript_name,
        confirmed_email=request.confirmed_email,
        confirmed_name=request.confirmed_name,
        learned=True,
    )


@router.get("/pending/{project_id}", response_model=list[ResolvedIdentity])
async def get_pending_reviews(
    project_id: str,
) -> list[ResolvedIdentity]:
    """Get all identities pending review for a project.

    Returns items that were resolved but have requires_review=True
    and haven't been confirmed yet.

    Note: For MVP, reviews are handled inline in extraction response.
    This endpoint is a placeholder for future queue-based review workflow.

    Args:
        project_id: Project to get pending reviews for

    Returns:
        List of identities pending review (currently empty for MVP)
    """
    # For MVP, return empty list - reviews are handled inline in extraction response
    # Future: Query pending_reviews table for unresolved items
    return []
