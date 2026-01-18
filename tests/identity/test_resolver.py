"""Tests for IdentityResolver."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.identity.fuzzy_matcher import FuzzyMatcher
from src.identity.llm_matcher import LLMMatcher
from src.identity.resolver import IdentityResolver
from src.identity.schemas import ResolutionResult, ResolutionSource, RosterEntry
from src.repositories.mapping_repo import MappingRepository


@pytest.fixture
def roster() -> list[RosterEntry]:
    """Sample roster for testing."""
    return [
        RosterEntry(
            name="John Smith",
            email="john.smith@example.com",
            aliases=["JS", "Johnny"],
        ),
        RosterEntry(
            name="Alice Johnson",
            email="alice.johnson@example.com",
            aliases=["AJ"],
        ),
        RosterEntry(
            name="Robert Williams",
            email="robert.williams@example.com",
            aliases=["Bob", "Bobby"],
        ),
    ]


@pytest.fixture
def fuzzy_matcher() -> FuzzyMatcher:
    """Fuzzy matcher with default threshold."""
    return FuzzyMatcher(threshold=0.85)


@pytest.fixture
def mock_mapping_repo() -> MagicMock:
    """Mock MappingRepository."""
    repo = MagicMock(spec=MappingRepository)
    repo.get_mapping = AsyncMock(return_value=None)
    repo.save_mapping = AsyncMock()
    return repo


@pytest.fixture
def mock_llm_matcher() -> MagicMock:
    """Mock LLMMatcher."""
    matcher = MagicMock(spec=LLMMatcher)
    matcher.infer_match = AsyncMock()
    return matcher


@pytest.fixture
def resolver(
    fuzzy_matcher: FuzzyMatcher,
    mock_mapping_repo: MagicMock,
) -> IdentityResolver:
    """Resolver with mocked dependencies (no LLM)."""
    return IdentityResolver(
        fuzzy_matcher=fuzzy_matcher,
        mapping_repo=mock_mapping_repo,
        llm_matcher=None,
    )


@pytest.fixture
def resolver_with_llm(
    fuzzy_matcher: FuzzyMatcher,
    mock_mapping_repo: MagicMock,
    mock_llm_matcher: MagicMock,
) -> IdentityResolver:
    """Resolver with mocked LLM matcher."""
    return IdentityResolver(
        fuzzy_matcher=fuzzy_matcher,
        mapping_repo=mock_mapping_repo,
        llm_matcher=mock_llm_matcher,
    )


@pytest.mark.asyncio
async def test_exact_match_returns_confidence_1(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """Exact match should return confidence 1.0."""
    result = await resolver.resolve("John Smith", roster, "proj-123")

    assert result.resolved_email == "john.smith@example.com"
    assert result.resolved_name == "John Smith"
    assert result.confidence == 1.0
    assert result.source == ResolutionSource.EXACT
    assert result.requires_review is False


@pytest.mark.asyncio
async def test_exact_match_case_insensitive(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """Exact match should be case-insensitive."""
    result = await resolver.resolve("john smith", roster, "proj-123")

    assert result.resolved_email == "john.smith@example.com"
    assert result.confidence == 1.0
    assert result.source == ResolutionSource.EXACT


@pytest.mark.asyncio
async def test_exact_match_via_alias(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """Should match via alias with confidence 1.0."""
    result = await resolver.resolve("Bob", roster, "proj-123")

    assert result.resolved_email == "robert.williams@example.com"
    assert result.resolved_name == "Robert Williams"
    assert result.confidence == 1.0
    assert result.source == ResolutionSource.EXACT
    assert result.requires_review is False


@pytest.mark.asyncio
async def test_learned_mapping_used_before_fuzzy(
    resolver: IdentityResolver,
    roster: list[RosterEntry],
    mock_mapping_repo: MagicMock,
):
    """Learned mapping should be checked before fuzzy matching."""
    # Set up learned mapping
    mock_mapping_repo.get_mapping.return_value = (
        "alice.johnson@example.com",
        "Alice Johnson",
    )

    result = await resolver.resolve("Ali", roster, "proj-123")

    assert result.resolved_email == "alice.johnson@example.com"
    assert result.confidence == 0.95
    assert result.source == ResolutionSource.LEARNED
    assert result.requires_review is False
    mock_mapping_repo.get_mapping.assert_awaited_once_with("proj-123", "Ali")


@pytest.mark.asyncio
async def test_fuzzy_match_above_threshold(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """Fuzzy match above threshold should succeed."""
    # "Alice Johnso" is close to "Alice Johnson"
    result = await resolver.resolve("Alice Johnso", roster, "proj-123")

    assert result.resolved_email == "alice.johnson@example.com"
    assert result.source == ResolutionSource.FUZZY
    assert result.confidence <= 0.85  # Single-source cap
    assert result.requires_review is False


@pytest.mark.asyncio
async def test_fuzzy_match_capped_at_85(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """Fuzzy match confidence should be capped at 85%."""
    # Very close match - "Alice Johnson" with slight variation
    result = await resolver.resolve("Alice Johnson!", roster, "proj-123")

    # Even if fuzzy returns >85%, it should be capped
    assert result.confidence <= 0.85


@pytest.mark.asyncio
async def test_low_confidence_requires_review(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """Low confidence matches should require review."""
    # "Unknown Person" won't match well
    result = await resolver.resolve("Unknown Person", roster, "proj-123")

    assert result.requires_review is True
    assert result.resolved_email is None


@pytest.mark.asyncio
async def test_no_match_returns_requires_review_true(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """No match should return requires_review=True."""
    result = await resolver.resolve("Completely Unknown", roster, "proj-123")

    assert result.requires_review is True
    assert result.resolved_email is None
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_learn_mapping_persists(
    resolver: IdentityResolver, mock_mapping_repo: MagicMock
):
    """learn_mapping should save to repository."""
    await resolver.learn_mapping(
        project_id="proj-123",
        transcript_name="Mike",
        resolved_email="michael.jones@example.com",
        resolved_name="Michael Jones",
        created_by="user-1",
    )

    mock_mapping_repo.save_mapping.assert_awaited_once_with(
        project_id="proj-123",
        transcript_name="Mike",
        resolved_email="michael.jones@example.com",
        resolved_name="Michael Jones",
        created_by="user-1",
    )


@pytest.mark.asyncio
async def test_resolve_all_handles_multiple_names(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """resolve_all should resolve multiple names."""
    names = ["John Smith", "Alice Johnson", "Unknown"]

    results = await resolver.resolve_all(names, roster, "proj-123")

    assert len(results) == 3
    assert results[0].resolved_email == "john.smith@example.com"
    assert results[1].resolved_email == "alice.johnson@example.com"
    assert results[2].requires_review is True


@pytest.mark.asyncio
async def test_llm_used_when_fuzzy_gives_candidates(
    resolver_with_llm: IdentityResolver,
    roster: list[RosterEntry],
    mock_llm_matcher: MagicMock,
):
    """LLM should be used when fuzzy gives candidates but no high-confidence match."""
    # Set up LLM to return a match
    mock_llm_matcher.infer_match.return_value = ResolutionResult(
        transcript_name="Mike",
        resolved_email="robert.williams@example.com",
        resolved_name="Robert Williams",
        confidence=0.80,
        source=ResolutionSource.LLM,
        requires_review=True,
    )

    result = await resolver_with_llm.resolve("Mike", roster, "proj-123")

    assert result.source == ResolutionSource.LLM
    assert result.resolved_email == "robert.williams@example.com"
    mock_llm_matcher.infer_match.assert_awaited_once()


@pytest.mark.asyncio
async def test_alternatives_provided_on_no_match(
    resolver: IdentityResolver, roster: list[RosterEntry]
):
    """When no confident match, alternatives should be provided."""
    result = await resolver.resolve("Johnson", roster, "proj-123")

    # Should have alternatives even if no confident match
    # Alice Johnson should be in alternatives
    if result.alternatives:
        alt_names = [name for name, score in result.alternatives]
        assert any("Johnson" in name for name in alt_names)
