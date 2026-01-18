"""Google Calendar adapter for attendee verification.

Uses Google Calendar API to get meeting attendees for identity corroboration.
"""

import os
from datetime import datetime, timedelta

import structlog
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = structlog.get_logger()

# Required scopes for calendar read access
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarAdapter:
    """Adapter for Google Calendar attendee verification.

    Uses Google Calendar API to get meeting attendees for cross-reference.
    """

    def __init__(self, credentials_path: str | None = None):
        """Initialize with service account credentials.

        Args:
            credentials_path: Path to service account JSON.
                             Falls back to GOOGLE_CALENDAR_CREDENTIALS or
                             GOOGLE_SHEETS_CREDENTIALS env vars.
        """
        self._credentials_path = (
            credentials_path
            or os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
            or os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        )
        self._service = None

    def _get_service(self):
        """Get or create Calendar API service."""
        if self._service is None:
            if not self._credentials_path:
                raise ValueError(
                    "No credentials. Set GOOGLE_CALENDAR_CREDENTIALS env var "
                    "or pass credentials_path to constructor."
                )
            creds = Credentials.from_service_account_file(
                self._credentials_path,
                scopes=CALENDAR_SCOPES,
            )
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    async def get_event_attendees(
        self,
        calendar_id: str,
        event_id: str,
    ) -> list[dict]:
        """Get attendees for a calendar event.

        Args:
            calendar_id: Calendar ID (usually primary user's email)
            event_id: Event ID from calendar

        Returns:
            List of attendee dicts with email, displayName, responseStatus
        """
        try:
            service = self._get_service()
            event = (
                service.events()
                .get(
                    calendarId=calendar_id,
                    eventId=event_id,
                )
                .execute()
            )
            return event.get("attendees", [])
        except Exception as e:
            logger.warning(
                "Error getting calendar event",
                calendar_id=calendar_id,
                event_id=event_id,
                error=str(e),
            )
            return []

    async def verify_attendee(
        self,
        calendar_id: str,
        event_id: str,
        email: str,
    ) -> bool:
        """Check if email was attendee of calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            email: Email to verify

        Returns:
            True if email was attendee
        """
        attendees = await self.get_event_attendees(calendar_id, event_id)
        attendee_emails = {
            a.get("email", "").lower() for a in attendees if a.get("email")
        }
        return email.lower() in attendee_emails

    async def find_meeting_by_time(
        self,
        calendar_id: str,
        meeting_time: datetime,
        tolerance_minutes: int = 15,
    ) -> str | None:
        """Find event ID by meeting time.

        Args:
            calendar_id: Calendar ID
            meeting_time: When meeting occurred
            tolerance_minutes: Minutes before/after to search

        Returns:
            Event ID if found, None otherwise
        """
        try:
            service = self._get_service()
            time_min = (
                meeting_time - timedelta(minutes=tolerance_minutes)
            ).isoformat() + "Z"
            time_max = (
                meeting_time + timedelta(minutes=tolerance_minutes)
            ).isoformat() + "Z"

            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=5,
                    singleEvents=True,
                )
                .execute()
            )

            events = events_result.get("items", [])
            if events:
                return events[0].get("id")
            return None
        except Exception as e:
            logger.warning(
                "Error finding meeting",
                calendar_id=calendar_id,
                meeting_time=meeting_time.isoformat(),
                error=str(e),
            )
            return None
