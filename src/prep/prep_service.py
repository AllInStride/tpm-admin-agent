"""PrepService orchestrates meeting prep generation and delivery.

Coordinates context gathering, item prioritization, formatting,
and delivery to meeting attendees via Slack.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from src.prep.formatter import format_prep_blocks, format_prep_text
from src.prep.item_matcher import generate_talking_points, prioritize_items
from src.prep.schemas import CalendarEvent, PrepConfig

if TYPE_CHECKING:
    from src.adapters.calendar_adapter import CalendarAdapter
    from src.adapters.slack_adapter import SlackAdapter
    from src.prep.context_gatherer import ContextGatherer
    from src.prep.item_matcher import ItemMatcher

logger = structlog.get_logger()


class PrepService:
    """Orchestrates meeting prep generation and delivery.

    Singleton pattern with class-level instance for scheduler access.
    """

    _instance: "PrepService | None" = None

    def __init__(
        self,
        calendar_adapter: "CalendarAdapter",
        slack_adapter: "SlackAdapter",
        item_matcher: "ItemMatcher",
        context_gatherer: "ContextGatherer",
        config: PrepConfig | None = None,
    ):
        """Initialize PrepService with dependencies.

        Args:
            calendar_adapter: Adapter for Google Calendar API
            slack_adapter: Adapter for Slack API
            item_matcher: Service for matching open items
            context_gatherer: Service for gathering meeting context
            config: Prep configuration (defaults used if None)
        """
        self._calendar = calendar_adapter
        self._slack = slack_adapter
        self._item_matcher = item_matcher
        self._context_gatherer = context_gatherer
        self._config = config or PrepConfig()
        self._sent_preps: set[str] = set()  # Track sent: "event_id:date"

    @classmethod
    def get_instance(cls) -> "PrepService":
        """Get the singleton instance.

        Raises:
            RuntimeError: If PrepService not initialized
        """
        if cls._instance is None:
            raise RuntimeError("PrepService not initialized")
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "PrepService") -> None:
        """Set the singleton instance.

        Args:
            instance: PrepService instance to set as singleton
        """
        cls._instance = instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    async def scan_and_prepare(self, calendar_id: str = "primary") -> list[dict]:
        """Scan for upcoming meetings and send prep summaries.

        Calculates time window: now + lead_time to now + lead_time + 5min
        to catch meetings starting soon. Uses 5-minute window to align
        with scheduler interval.

        Args:
            calendar_id: Calendar to scan (default: primary)

        Returns:
            List of results for each prep sent
        """
        now = datetime.now(UTC)
        lead_time = timedelta(minutes=self._config.lead_time_minutes)
        window_size = timedelta(minutes=5)

        time_min = now + lead_time
        time_max = now + lead_time + window_size

        logger.info(
            "scanning for upcoming meetings",
            calendar_id=calendar_id,
            time_min=time_min.isoformat(),
            time_max=time_max.isoformat(),
        )

        events = await self._calendar.list_upcoming_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
        )

        results = []
        for event in events:
            event_id = event.get("id", "")
            start = event.get("start", {}).get("dateTime", "")[:10]  # YYYY-MM-DD
            prep_key = f"{event_id}:{start}"

            if prep_key in self._sent_preps:
                logger.debug("skipping already prepped meeting", prep_key=prep_key)
                continue

            try:
                result = await self.prepare_for_meeting(
                    event=event,
                    project_id="",  # Project scoping deferred
                )
                self._sent_preps.add(prep_key)
                results.append(result)
            except Exception as e:
                logger.error(
                    "failed to prepare meeting",
                    event_id=event_id,
                    error=str(e),
                )

        return results

    async def prepare_for_meeting(
        self,
        event: dict,
        project_id: str,
        project_folder_id: str | None = None,
        slack_channel_id: str | None = None,
    ) -> dict:
        """Generate and deliver prep for a specific meeting.

        Args:
            event: Calendar event dict
            project_id: Project ID for scoping items
            project_folder_id: Google Drive folder ID for context docs
            slack_channel_id: Slack channel ID for context messages

        Returns:
            Dict with meeting_id, recipients count, items count
        """
        # Convert event dict to CalendarEvent
        event_id = event.get("id", "")
        summary = event.get("summary", "Untitled Meeting")
        start_str = event.get("start", {}).get("dateTime", "")
        end_str = event.get("end", {}).get("dateTime", "")
        attendees = event.get("attendees", [])

        # Parse datetime
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            start_dt = datetime.now(UTC)

        try:
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            end_dt = start_dt + timedelta(hours=1)

        calendar_event = CalendarEvent(
            id=event_id,
            summary=summary,
            start=start_dt,
            end=end_dt,
            attendees=attendees,
        )

        # Gather context
        context = await self._context_gatherer.gather_for_meeting(
            meeting=calendar_event,
            project_id=project_id,
            project_folder_id=project_folder_id,
            slack_channel_id=slack_channel_id,
            lookback_days=self._config.lookback_days,
        )

        # Prioritize items
        last_meeting_date = None
        if context.previous_meeting:
            prev_date = context.previous_meeting.get("date")
            if prev_date:
                try:
                    last_meeting_date = datetime.fromisoformat(prev_date)
                except ValueError:
                    pass

        prioritized = prioritize_items(
            items=context.open_items,
            max_items=self._config.max_items,
            last_meeting_date=last_meeting_date,
        )

        # Generate talking points
        points = generate_talking_points(prioritized)
        point_texts = [p.text for p in points]

        # Build attendee info
        attendee_info = []
        for a in attendees:
            name = a.get("displayName") or a.get("email", "").split("@")[0]
            role = a.get("role")  # Optional role field
            attendee_info.append({"name": name, "role": role})

        # Format blocks
        recent_url = None
        if context.previous_meeting:
            recent_url = context.previous_meeting.get("url")

        blocks = format_prep_blocks(
            meeting_title=summary,
            attendees=attendee_info,
            open_items=prioritized,
            talking_points=point_texts,
            recent_meeting_url=recent_url,
            full_prep_url=None,  # Full prep URL deferred
        )

        # Format text fallback
        text_fallback = format_prep_text(
            meeting_title=summary,
            open_items=prioritized,
            talking_points=point_texts,
        )

        # Send to attendees
        recipients_sent = 0
        for attendee in attendees:
            email = attendee.get("email")
            if not email:
                continue

            # Look up Slack user
            user = await self._slack.lookup_user_by_email(email)
            if not user:
                logger.debug(
                    "no slack user for attendee",
                    email=email,
                    meeting_id=event_id,
                )
                continue

            user_id = user.get("id")
            if not user_id:
                continue

            # Send prep DM
            result = await self._slack.send_prep_dm(
                user_id=user_id,
                blocks=blocks,
                text_fallback=text_fallback,
            )

            if result.get("success"):
                recipients_sent += 1
                logger.info(
                    "sent meeting prep",
                    user_id=user_id,
                    meeting_id=event_id,
                )
            else:
                logger.warning(
                    "failed to send prep",
                    user_id=user_id,
                    meeting_id=event_id,
                    error=result.get("error"),
                )

        return {
            "meeting_id": event_id,
            "meeting_title": summary,
            "recipients": recipients_sent,
            "items": len(prioritized),
            "talking_points": len(point_texts),
        }
