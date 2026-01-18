"""Tests for fuzzy name matching."""

import pytest

from src.identity.fuzzy_matcher import FuzzyMatcher
from src.identity.schemas import RosterEntry


@pytest.fixture
def sample_roster() -> list[RosterEntry]:
    """Sample roster for testing."""
    return [
        RosterEntry(
            name="John Smith",
            email="john.smith@example.com",
            aliases=["Johnny", "JS"],
        ),
        RosterEntry(
            name="Jane Doe",
            email="jane.doe@example.com",
            aliases=["Janet"],
        ),
        RosterEntry(
            name="Robert Johnson",
            email="robert.johnson@example.com",
            aliases=["Bob", "Bobby"],
        ),
    ]


@pytest.fixture
def matcher() -> FuzzyMatcher:
    """Default matcher with 0.85 threshold."""
    return FuzzyMatcher(threshold=0.85)


class TestFindBestMatch:
    """Tests for find_best_match method."""

    def test_exact_match_returns_1_0(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """Exact name match returns score of 1.0."""
        entry, score = matcher.find_best_match("John Smith", sample_roster)

        assert entry is not None
        assert entry.email == "john.smith@example.com"
        assert score == 1.0

    def test_similar_name_scores_above_threshold(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """Similar names with minor differences score above threshold."""
        # "John Smyth" should match "John Smith" well enough
        entry, score = matcher.find_best_match("John Smyth", sample_roster)

        assert entry is not None
        assert entry.email == "john.smith@example.com"
        assert score >= 0.85

    def test_dissimilar_name_scores_below_threshold(
        self, sample_roster: list[RosterEntry]
    ):
        """Very different names return None when below threshold."""
        matcher = FuzzyMatcher(threshold=0.85)
        entry, score = matcher.find_best_match("Michael Williams", sample_roster)

        assert entry is None
        assert score == 0.0

    def test_alias_matches_entry(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """Searching for an alias returns the correct entry."""
        entry, score = matcher.find_best_match("Bobby", sample_roster)

        assert entry is not None
        assert entry.email == "robert.johnson@example.com"
        assert score == 1.0

    def test_name_order_independence(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """'Smith, John' matches 'John Smith' with high score."""
        entry, score = matcher.find_best_match("Smith, John", sample_roster)

        assert entry is not None
        assert entry.email == "john.smith@example.com"
        # token_sort_ratio handles reordering
        assert score >= 0.95

    def test_empty_roster_returns_none(self, matcher: FuzzyMatcher):
        """Empty roster returns None with 0.0 score."""
        entry, score = matcher.find_best_match("John Smith", [])

        assert entry is None
        assert score == 0.0

    def test_case_insensitive_matching(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """Matching is case-insensitive."""
        entry, score = matcher.find_best_match("JOHN SMITH", sample_roster)

        assert entry is not None
        assert entry.email == "john.smith@example.com"
        assert score == 1.0


class TestFindTopMatches:
    """Tests for find_top_matches method."""

    def test_find_top_matches_returns_multiple(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """Returns multiple matches sorted by score."""
        matches = matcher.find_top_matches("John", sample_roster, limit=3)

        assert len(matches) >= 1
        # Scores should be in descending order
        scores = [score for _, score in matches]
        assert scores == sorted(scores, reverse=True)

    def test_find_top_matches_respects_limit(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """Returns at most 'limit' entries."""
        matches = matcher.find_top_matches("John", sample_roster, limit=2)

        assert len(matches) <= 2

    def test_find_top_matches_deduplicates_entries(
        self, matcher: FuzzyMatcher, sample_roster: list[RosterEntry]
    ):
        """Doesn't return same entry twice (via name + alias)."""
        # "Bob" is an alias for Robert Johnson
        matches = matcher.find_top_matches("Robert", sample_roster, limit=3)

        emails = [entry.email for entry, _ in matches]
        # No duplicate emails
        assert len(emails) == len(set(emails))

    def test_find_top_matches_empty_roster(self, matcher: FuzzyMatcher):
        """Empty roster returns empty list."""
        matches = matcher.find_top_matches("John", [])

        assert matches == []
