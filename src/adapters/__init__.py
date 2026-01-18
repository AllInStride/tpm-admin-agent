"""Adapters for external data sources.

This module provides adapters for integrating with external systems:
- RosterAdapter: Load project rosters from Google Sheets
- SlackAdapter: Verify workspace membership for identity corroboration
- CalendarAdapter: Verify meeting attendees for identity corroboration
"""

from src.adapters.calendar_adapter import CalendarAdapter
from src.adapters.roster_adapter import RosterAdapter
from src.adapters.slack_adapter import SlackAdapter

__all__ = ["CalendarAdapter", "RosterAdapter", "SlackAdapter"]
