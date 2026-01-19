"""Meeting prep module.

Provides proactive meeting preparation with open item surfacing,
context gathering, and summary generation.
"""

from src.prep.item_matcher import (
    ItemMatcher,
    generate_talking_points,
    prioritize_items,
)
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
    "ItemMatcher",
    "MeetingPrepRequest",
    "PrepConfig",
    "PrepItem",
    "PrepSummary",
    "TalkingPoint",
    "generate_talking_points",
    "prioritize_items",
]
