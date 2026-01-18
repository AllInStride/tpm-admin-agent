"""Identity resolution module for matching transcript names to roster entries.

This module provides:
- Fuzzy name matching using RapidFuzz (Jaro-Winkler/token_sort_ratio)
- Multi-source confidence calculation
- Schemas for roster entries and resolution results
"""

from src.identity.confidence import calculate_confidence
from src.identity.fuzzy_matcher import FuzzyMatcher
from src.identity.schemas import ResolutionResult, ResolutionSource, RosterEntry

__all__ = [
    "FuzzyMatcher",
    "ResolutionResult",
    "ResolutionSource",
    "RosterEntry",
    "calculate_confidence",
]
