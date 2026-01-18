"""Date normalization utility for meeting-relative date parsing.

Converts natural language dates (e.g., "next Friday", "end of month")
to concrete dates, using the meeting date as the reference point.
"""

from datetime import date, datetime

import dateparser


def normalize_due_date(
    raw_date: str | None,
    meeting_date: datetime,
) -> date | None:
    """Convert natural language date to date, relative to meeting date.

    Args:
        raw_date: Natural language date string (e.g., "next Friday", "end of month")
        meeting_date: The datetime of the meeting (reference point for relative dates)

    Returns:
        Parsed date, or None if raw_date is None or parsing fails

    Examples:
        >>> from datetime import datetime
        >>> meeting = datetime(2026, 1, 18)
        >>> normalize_due_date("next Friday", meeting)
        datetime.date(2026, 1, 24)  # The Friday after Jan 18, 2026
        >>> normalize_due_date(None, meeting)
        None
    """
    if raw_date is None:
        return None

    if not raw_date.strip():
        return None

    settings: dict = {
        "RELATIVE_BASE": meeting_date,
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }

    try:
        parsed = dateparser.parse(raw_date, settings=settings)
        if parsed is None:
            return None
        return parsed.date()
    except Exception:
        # dateparser can raise various exceptions on malformed input
        return None
