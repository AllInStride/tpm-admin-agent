"""Identity resolution module for matching transcript names to roster entries.

This module provides:
- Fuzzy name matching using RapidFuzz (Jaro-Winkler/token_sort_ratio)
- Multi-source confidence calculation
- Schemas for roster entries and resolution results
"""

from src.identity.schemas import ResolutionResult, ResolutionSource, RosterEntry

__all__ = ["RosterEntry", "ResolutionResult", "ResolutionSource"]
