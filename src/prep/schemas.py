"""Schemas for meeting prep functionality.

Defines data models for prep configuration, calendar events,
prep items, talking points, and prep summaries.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PrepConfig(BaseModel):
    """Configuration for meeting prep generation."""

    lead_time_minutes: int = Field(
        default=10,
        description="Minutes before meeting to send prep",
        ge=1,
        le=60,
    )
    delivery_method: Literal["slack", "email"] = Field(
        default="slack",
        description="How to deliver prep: slack DM or email",
    )
    max_items: int = Field(
        default=10,
        description="Maximum open items to include in prep",
        ge=1,
        le=50,
    )
    lookback_days: int = Field(
        default=90,
        description="Days to look back for related open items",
        ge=1,
        le=365,
    )


class CalendarEvent(BaseModel):
    """Calendar event data from Google Calendar API."""

    id: str = Field(description="Calendar event ID")
    summary: str = Field(description="Event title/summary")
    start: datetime = Field(description="Event start time (UTC)")
    end: datetime = Field(description="Event end time (UTC)")
    attendees: list[dict] = Field(
        default_factory=list,
        description="List of attendees with email, displayName, responseStatus",
    )


class PrepItem(BaseModel):
    """Open item formatted for meeting prep display."""

    id: str = Field(description="RAID item ID")
    item_type: str = Field(description="Item type: action, risk, issue, decision")
    description: str = Field(description="Item description")
    owner: str | None = Field(default=None, description="Item owner name/email")
    due_date: str | None = Field(default=None, description="Due date as ISO string")
    is_overdue: bool = Field(default=False, description="Whether item is past due date")
    is_new: bool = Field(
        default=False,
        description="Whether item was created since last meeting",
    )


class TalkingPoint(BaseModel):
    """Suggested talking point for meeting prep."""

    text: str = Field(description="Talking point text")
    category: Literal["overdue", "risk", "new_item", "general"] = Field(
        description="Category of talking point",
    )


class PrepSummary(BaseModel):
    """Complete meeting prep package."""

    meeting: CalendarEvent = Field(description="The upcoming meeting")
    open_items: list[PrepItem] = Field(
        default_factory=list,
        description="Prioritized open items for the meeting",
    )
    talking_points: list[TalkingPoint] = Field(
        default_factory=list,
        description="Suggested talking points (2-3 items)",
    )
    recent_meeting_url: str | None = Field(
        default=None,
        description="URL to most recent meeting notes in series",
    )
    full_prep_url: str | None = Field(
        default=None,
        description="URL to full prep document",
    )
    attendees: list[dict] = Field(
        default_factory=list,
        description="Attendee list with name and role",
    )


class MeetingPrepRequest(BaseModel):
    """API request for generating meeting prep."""

    calendar_id: str = Field(description="Calendar ID (usually user email)")
    event_id: str = Field(description="Calendar event ID to prepare for")
    project_id: str = Field(description="Project ID for scoping open items")
