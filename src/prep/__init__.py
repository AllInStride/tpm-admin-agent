"""Meeting prep module.

Provides proactive meeting preparation with open item surfacing,
context gathering, and summary generation.
"""

from src.prep.context_gatherer import (
    ContextGatherer,
    PrepContext,
    normalize_series_key,
)
from src.prep.formatter import format_prep_blocks, format_prep_text
from src.prep.item_matcher import (
    ItemMatcher,
    generate_talking_points,
    prioritize_items,
)
from src.prep.prep_service import PrepService
from src.prep.scheduler import get_scheduler, prep_scheduler_lifespan
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
    "ContextGatherer",
    "ItemMatcher",
    "MeetingPrepRequest",
    "PrepConfig",
    "PrepContext",
    "PrepItem",
    "PrepService",
    "PrepSummary",
    "TalkingPoint",
    "format_prep_blocks",
    "format_prep_text",
    "generate_talking_points",
    "get_scheduler",
    "normalize_series_key",
    "prep_scheduler_lifespan",
    "prioritize_items",
]
