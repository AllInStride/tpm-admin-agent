"""Context gatherer for meeting prep.

Aggregates context from multiple sources in parallel for meeting preparation,
including open items, related docs, Slack channel activity, and previous meetings.
"""

import asyncio
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from src.prep.schemas import CalendarEvent

if TYPE_CHECKING:
    from src.adapters.drive_adapter import DriveAdapter
    from src.adapters.slack_adapter import SlackAdapter
    from src.prep.item_matcher import ItemMatcher
    from src.search.fts_service import FTSService

logger = structlog.get_logger()


@dataclass
class PrepContext:
    """Aggregated context for meeting preparation."""

    open_items: list[dict]
    """Open RAID items matching attendees and project."""

    related_docs: list[dict]
    """Project documents from Google Drive."""

    slack_highlights: list[dict]
    """Recent Slack channel messages."""

    previous_meeting: dict | None
    """Most recent meeting in the same series, if found."""


def normalize_series_key(title: str) -> str:
    """Normalize meeting title for series matching.

    Strips dates, numbers, and normalizes for comparison.

    Args:
        title: Meeting title

    Returns:
        Normalized key for series matching
    """
    if not title:
        return ""

    normalized = title

    # Remove common date patterns
    normalized = re.sub(r"\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?", "", normalized)
    normalized = re.sub(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", "", normalized)

    # Remove standalone numbers
    normalized = re.sub(r"\s+\d+\s*", " ", normalized)
    normalized = re.sub(r"^\d+\s+", "", normalized)
    normalized = re.sub(r"\s+\d+$", "", normalized)

    # Lowercase and strip
    normalized = normalized.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized


class ContextGatherer:
    """Gathers context from multiple sources for meeting preparation."""

    def __init__(
        self,
        item_matcher: "ItemMatcher | None" = None,
        drive_adapter: "DriveAdapter | None" = None,
        slack_adapter: "SlackAdapter | None" = None,
        fts_service: "FTSService | None" = None,
    ):
        """Initialize context gatherer with dependencies."""
        self._item_matcher = item_matcher
        self._drive = drive_adapter
        self._slack = slack_adapter
        self._fts = fts_service

    async def gather_for_meeting(
        self,
        meeting: CalendarEvent,
        project_id: str,
        project_folder_id: str | None = None,
        slack_channel_id: str | None = None,
        lookback_days: int = 90,
    ) -> PrepContext:
        """Gather all context for an upcoming meeting."""
        attendee_emails = [
            a.get("email", "").lower() for a in meeting.attendees if a.get("email")
        ]

        tasks = [
            self._get_open_items(attendee_emails, project_id, lookback_days),
            self._get_related_docs(project_folder_id),
            self._get_slack_highlights(slack_channel_id),
            self._get_previous_meeting(meeting),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        open_items = self._extract_result(results[0], "open_items", [])
        related_docs = self._extract_result(results[1], "related_docs", [])
        slack_highlights = self._extract_result(results[2], "slack_highlights", [])
        previous_meeting = self._extract_result(results[3], "previous_meeting", None)

        logger.info(
            "gathered meeting context",
            meeting_id=meeting.id,
            meeting_title=meeting.summary,
            open_items_count=len(open_items),
            docs_count=len(related_docs),
            slack_count=len(slack_highlights),
            has_previous=previous_meeting is not None,
        )

        return PrepContext(
            open_items=open_items,
            related_docs=related_docs,
            slack_highlights=slack_highlights,
            previous_meeting=previous_meeting,
        )

    def _extract_result(self, result, source_name: str, default):
        """Extract result from asyncio.gather, handling exceptions."""
        if isinstance(result, Exception):
            logger.warning(
                "context source failed",
                source=source_name,
                error=str(result),
            )
            return default
        return result

    async def _get_open_items(
        self,
        attendee_emails: list[str],
        project_id: str,
        lookback_days: int,
    ) -> list[dict]:
        """Get open items from ItemMatcher."""
        if self._item_matcher is None:
            return []

        return await self._item_matcher.get_items_for_prep(
            attendee_emails=attendee_emails,
            project_id=project_id,
            lookback_days=lookback_days,
        )

    async def _get_related_docs(
        self,
        project_folder_id: str | None,
    ) -> list[dict]:
        """Get related docs from DriveAdapter."""
        if self._drive is None or project_folder_id is None:
            return []

        return await self._drive.search_project_docs(
            folder_id=project_folder_id,
            max_results=10,
        )

    async def _get_slack_highlights(
        self,
        slack_channel_id: str | None,
    ) -> list[dict]:
        """Get recent Slack activity from channel."""
        if self._slack is None or slack_channel_id is None:
            return []

        return await self._slack.get_channel_history(
            channel_id=slack_channel_id,
            days=7,
            limit=100,
        )

    async def _get_previous_meeting(
        self,
        meeting: CalendarEvent,
    ) -> dict | None:
        """Find the previous meeting in the same series."""
        if self._fts is None:
            return None

        series_key = normalize_series_key(meeting.summary)
        if not series_key:
            return None

        try:
            await self._fts.search(series_key, limit=10)
            logger.debug(
                "previous meeting search",
                series_key=series_key,
                current_meeting_start=meeting.start.isoformat(),
            )
            # TODO: Implement meeting projection search when available
            return None

        except Exception as e:
            logger.warning(
                "failed to find previous meeting",
                series_key=series_key,
                error=str(e),
            )
            return None
