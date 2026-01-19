"""Meeting prep module.

Provides proactive meeting preparation with open item surfacing,
context gathering, and summary generation.
"""

from src.prep.schemas import (
    CalendarEvent,
    MeetingPrepRequest,
    PrepConfig,
    PrepItem,
    PrepSummary,
    TalkingPoint,
)

__all__ = [
    "CalendarEvent",
    "MeetingPrepRequest",
    "PrepConfig",
    "PrepItem",
    "PrepSummary",
    "TalkingPoint",
]
