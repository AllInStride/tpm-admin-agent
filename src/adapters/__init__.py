"""Adapters for external data sources and output destinations.

This module provides adapters for integrating with external systems:
- RosterAdapter: Load project rosters from Google Sheets
- SlackAdapter: Verify workspace membership for identity corroboration
- CalendarAdapter: Verify meeting attendees for identity corroboration
- OutputAdapter: Protocol for write adapters
- WriteResult: Result model for write operations
"""

from src.adapters.base import OutputAdapter, WriteResult
from src.adapters.calendar_adapter import CalendarAdapter
from src.adapters.roster_adapter import RosterAdapter
from src.adapters.slack_adapter import SlackAdapter

__all__ = [
    "CalendarAdapter",
    "OutputAdapter",
    "RosterAdapter",
    "SlackAdapter",
    "WriteResult",
]
