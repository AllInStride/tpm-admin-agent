"""Tests for date normalizer utility."""

from datetime import date, datetime

from src.extraction.date_normalizer import normalize_due_date

# Use fixed meeting date for deterministic tests
MEETING_DATE = datetime(2026, 1, 18, 10, 0, 0)  # Saturday, January 18, 2026


class TestNormalizeDueDate:
    """Tests for normalize_due_date function."""

    def test_none_input_returns_none(self):
        """Test that None input returns None."""
        result = normalize_due_date(None, MEETING_DATE)
        assert result is None

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = normalize_due_date("", MEETING_DATE)
        assert result is None

    def test_whitespace_only_returns_none(self):
        """Test that whitespace-only string returns None."""
        result = normalize_due_date("   ", MEETING_DATE)
        assert result is None

    def test_invalid_string_returns_none(self):
        """Test that unparseable string returns None, not raises."""
        result = normalize_due_date("asdfghjkl not a date", MEETING_DATE)
        assert result is None

    def test_friday_relative_to_meeting(self):
        """Test 'Friday' returns next Friday relative to meeting date."""
        # Note: dateparser parses "Friday" but not "next Friday"
        result = normalize_due_date("Friday", MEETING_DATE)
        assert result is not None
        # Meeting is Saturday Jan 18, 2026
        # Friday should be Jan 23, 2026 (next occurrence)
        assert result == date(2026, 1, 23)

    def test_next_friday_unparseable(self):
        """Test 'next Friday' is unparseable by dateparser."""
        # Note: dateparser doesn't parse "next Friday" - returns None
        result = normalize_due_date("next Friday", MEETING_DATE)
        assert result is None

    def test_explicit_date_january_25th(self):
        """Test explicit date like 'January 25th' works."""
        result = normalize_due_date("January 25th", MEETING_DATE)
        assert result is not None
        # Should parse to January 25, 2026 (same year as meeting)
        assert result.month == 1
        assert result.day == 25

    def test_explicit_full_date(self):
        """Test fully specified date like 'February 15, 2026'."""
        result = normalize_due_date("February 15, 2026", MEETING_DATE)
        assert result is not None
        assert result == date(2026, 2, 15)

    def test_monday_relative_to_meeting(self):
        """Test 'Monday' returns next Monday relative to meeting date."""
        # Note: dateparser parses "Monday" but not "next Monday"
        result = normalize_due_date("Monday", MEETING_DATE)
        assert result is not None
        # Meeting is Saturday Jan 18, 2026
        # Monday should be Jan 19, 2026 (next occurrence)
        assert result == date(2026, 1, 19)

    def test_in_two_weeks(self):
        """Test 'in two weeks' adds 14 days to meeting date."""
        result = normalize_due_date("in two weeks", MEETING_DATE)
        assert result is not None
        # Two weeks from Jan 18 = Feb 1
        assert result == date(2026, 2, 1)

    def test_tomorrow(self):
        """Test 'tomorrow' returns day after meeting date."""
        result = normalize_due_date("tomorrow", MEETING_DATE)
        assert result is not None
        # Tomorrow from Jan 18 = Jan 19
        assert result == date(2026, 1, 19)

    def test_end_of_week_unparseable(self):
        """Test 'end of week' is unparseable by dateparser."""
        # Note: dateparser doesn't parse "end of week" - returns None
        result = normalize_due_date("end of week", MEETING_DATE)
        assert result is None

    def test_prefers_future_dates(self):
        """Test that ambiguous dates prefer future (PREFER_DATES_FROM setting)."""
        # "Friday" without "next" should still be future Friday
        result = normalize_due_date("Friday", MEETING_DATE)
        assert result is not None
        # Should be Jan 24, 2026 (next Friday, not last Friday)
        assert result >= MEETING_DATE.date()
