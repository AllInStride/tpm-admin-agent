"""Tests for multi-source confidence calculation."""

import pytest

from src.identity.confidence import calculate_confidence


class TestCalculateConfidence:
    """Tests for calculate_confidence function."""

    def test_single_source_capped_at_85(self):
        """Single-source (roster only) is capped at 0.85."""
        # Even with perfect fuzzy score, single source caps at 0.85
        result = calculate_confidence(
            fuzzy_score=1.0,
            roster_match=True,
            slack_match=False,
            calendar_match=False,
        )

        assert result == 0.85

    def test_single_source_below_cap_unchanged(self):
        """Scores below 0.85 are returned unchanged with single source."""
        result = calculate_confidence(
            fuzzy_score=0.80,
            roster_match=True,
            slack_match=False,
            calendar_match=False,
        )

        assert result == 0.80

    def test_multi_source_boosts_confidence(self):
        """Two sources agreeing boosts confidence by 0.05."""
        result = calculate_confidence(
            fuzzy_score=0.90,
            roster_match=True,
            slack_match=True,
            calendar_match=False,
        )

        # 0.90 + 0.05 boost for 2 sources
        assert result == pytest.approx(0.95)

    def test_no_roster_match_returns_zero(self):
        """No roster match returns 0.0 regardless of other sources."""
        result = calculate_confidence(
            fuzzy_score=1.0,
            roster_match=False,
            slack_match=True,
            calendar_match=True,
        )

        assert result == 0.0

    def test_three_sources_boost_higher_than_two(self):
        """Three sources gives 0.10 boost (2 * 0.05)."""
        result = calculate_confidence(
            fuzzy_score=0.85,
            roster_match=True,
            slack_match=True,
            calendar_match=True,
        )

        # 0.85 + 0.10 boost for 3 sources
        assert result == pytest.approx(0.95)

    def test_cannot_exceed_1_0(self):
        """Confidence cannot exceed 1.0 even with maximum boost."""
        result = calculate_confidence(
            fuzzy_score=0.98,
            roster_match=True,
            slack_match=True,
            calendar_match=True,
        )

        # 0.98 + 0.10 would be 1.08, but capped at 1.0
        assert result == 1.0

    def test_exact_match_with_verification_returns_1_0(self):
        """Perfect fuzzy score with multi-source verification returns 1.0."""
        result = calculate_confidence(
            fuzzy_score=1.0,
            roster_match=True,
            slack_match=True,
            calendar_match=False,
        )

        # 1.0 + 0.05 = 1.05, capped at 1.0
        assert result == 1.0

    def test_calendar_only_verification(self):
        """Calendar verification alone can break the 0.85 cap."""
        result = calculate_confidence(
            fuzzy_score=0.90,
            roster_match=True,
            slack_match=False,
            calendar_match=True,
        )

        # 0.90 + 0.05 boost
        assert result == pytest.approx(0.95)

    def test_low_fuzzy_score_with_verification(self):
        """Low fuzzy score is boosted but remains low."""
        result = calculate_confidence(
            fuzzy_score=0.70,
            roster_match=True,
            slack_match=True,
            calendar_match=False,
        )

        # 0.70 + 0.05 boost
        assert result == pytest.approx(0.75)
