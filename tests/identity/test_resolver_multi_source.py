"""Tests for IdentityResolver multi-source verification."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.calendar_adapter import CalendarAdapter
from src.adapters.slack_adapter import SlackAdapter
from src.identity.fuzzy_matcher import FuzzyMatcher
from src.identity.resolver import IdentityResolver
from src.identity.schemas import ResolutionSource, RosterEntry
from src.repositories.mapping_repo import MappingRepository


@pytest.fixture
def roster() -> list[RosterEntry]:
    """Sample roster for testing."""
    return [
        RosterEntry(
            name="John Smith",
            email="john.smith@example.com",
            aliases=["JS"],
        ),
        RosterEntry(
            name="Alice Johnson",
            email="alice.johnson@example.com",
            aliases=["AJ"],
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
def mock_slack_adapter() -> MagicMock:
    """Mock SlackAdapter."""
    adapter = MagicMock(spec=SlackAdapter)
    adapter.verify_member = AsyncMock(return_value=False)
    return adapter


@pytest.fixture
def mock_calendar_adapter() -> MagicMock:
    """Mock CalendarAdapter."""
    adapter = MagicMock(spec=CalendarAdapter)
    adapter.verify_attendee = AsyncMock(return_value=False)
    return adapter


class TestMultiSourceVerification:
    """Tests for multi-source verification boosting confidence."""

    @pytest.mark.asyncio
    async def test_slack_verification_boosts_confidence(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_slack_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """Slack verification should boost confidence above 85%."""
        mock_slack_adapter.verify_member.return_value = True

        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            slack_adapter=mock_slack_adapter,
        )

        # "John Smithe" is close to "John Smith" - fuzzy match
        result = await resolver.resolve("John Smithe", roster, "proj-123")

        assert result.resolved_email == "john.smith@example.com"
        assert result.source == ResolutionSource.FUZZY
        # With Slack verification, should be boosted above 85% cap
        assert result.confidence > 0.85
        assert result.requires_review is False
        mock_slack_adapter.verify_member.assert_awaited_once_with(
            "john.smith@example.com"
        )

    @pytest.mark.asyncio
    async def test_calendar_verification_boosts_confidence(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_calendar_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """Calendar verification should boost confidence above 85%."""
        mock_calendar_adapter.verify_attendee.return_value = True

        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            calendar_adapter=mock_calendar_adapter,
        )

        result = await resolver.resolve(
            "John Smithe",
            roster,
            "proj-123",
            calendar_id="cal@example.com",
            calendar_event_id="event123",
        )

        assert result.resolved_email == "john.smith@example.com"
        assert result.confidence > 0.85
        assert result.requires_review is False
        mock_calendar_adapter.verify_attendee.assert_awaited_once_with(
            "cal@example.com", "event123", "john.smith@example.com"
        )

    @pytest.mark.asyncio
    async def test_both_sources_boost_higher(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_slack_adapter: MagicMock,
        mock_calendar_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """Both sources verifying should boost even higher."""
        mock_slack_adapter.verify_member.return_value = True
        mock_calendar_adapter.verify_attendee.return_value = True

        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            slack_adapter=mock_slack_adapter,
            calendar_adapter=mock_calendar_adapter,
        )

        result = await resolver.resolve(
            "John Smithe",
            roster,
            "proj-123",
            calendar_id="cal@example.com",
            calendar_event_id="event123",
        )

        assert result.resolved_email == "john.smith@example.com"
        # With both sources, should be boosted by 10% (5% each)
        assert result.confidence > 0.90
        assert result.requires_review is False

    @pytest.mark.asyncio
    async def test_no_adapters_caps_at_85(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        roster: list[RosterEntry],
    ):
        """Without adapters, confidence should be capped at 85%."""
        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
        )

        result = await resolver.resolve("John Smithe", roster, "proj-123")

        assert result.resolved_email == "john.smith@example.com"
        assert result.confidence <= 0.85

    @pytest.mark.asyncio
    async def test_verification_failure_still_resolves(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_slack_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """Failed verification should still resolve, just no boost."""
        mock_slack_adapter.verify_member.return_value = False

        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            slack_adapter=mock_slack_adapter,
        )

        result = await resolver.resolve("John Smithe", roster, "proj-123")

        assert result.resolved_email == "john.smith@example.com"
        # No boost, capped at 85%
        assert result.confidence <= 0.85

    @pytest.mark.asyncio
    async def test_calendar_params_optional(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_calendar_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """Calendar verification should be skipped if params not provided."""
        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            calendar_adapter=mock_calendar_adapter,
        )

        # No calendar_id or calendar_event_id
        result = await resolver.resolve("John Smithe", roster, "proj-123")

        assert result.resolved_email == "john.smith@example.com"
        # Calendar adapter should not have been called
        mock_calendar_adapter.verify_attendee.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_resolve_all_with_multi_source(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_slack_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """resolve_all should pass calendar params through."""
        mock_slack_adapter.verify_member.return_value = True

        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            slack_adapter=mock_slack_adapter,
        )

        results = await resolver.resolve_all(
            ["John Smithe", "Alice Johnso"],
            roster,
            "proj-123",
        )

        assert len(results) == 2
        assert results[0].resolved_email == "john.smith@example.com"
        assert results[1].resolved_email == "alice.johnson@example.com"
        # Both should have Slack verification called
        assert mock_slack_adapter.verify_member.await_count == 2


class TestExactAndLearnedBypass:
    """Tests that exact and learned matches bypass multi-source verification."""

    @pytest.mark.asyncio
    async def test_exact_match_bypasses_verification(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_slack_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """Exact matches should not call verification adapters."""
        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            slack_adapter=mock_slack_adapter,
        )

        # Exact match
        result = await resolver.resolve("John Smith", roster, "proj-123")

        assert result.confidence == 1.0
        assert result.source == ResolutionSource.EXACT
        # Should not have called Slack
        mock_slack_adapter.verify_member.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_learned_match_bypasses_verification(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mock_mapping_repo: MagicMock,
        mock_slack_adapter: MagicMock,
        roster: list[RosterEntry],
    ):
        """Learned matches should not call verification adapters."""
        mock_mapping_repo.get_mapping.return_value = (
            "john.smith@example.com",
            "John Smith",
        )

        resolver = IdentityResolver(
            fuzzy_matcher=fuzzy_matcher,
            mapping_repo=mock_mapping_repo,
            slack_adapter=mock_slack_adapter,
        )

        result = await resolver.resolve("Johnny", roster, "proj-123")

        assert result.confidence == 0.95
        assert result.source == ResolutionSource.LEARNED
        # Should not have called Slack
        mock_slack_adapter.verify_member.assert_not_awaited()
