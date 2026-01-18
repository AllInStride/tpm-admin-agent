"""Identity resolution module for matching transcript names to roster entries.

This module provides:
- IdentityResolver: Multi-stage resolution pipeline (exact -> learned -> fuzzy -> LLM)
- Fuzzy name matching using RapidFuzz (Jaro-Winkler/token_sort_ratio)
- LLM-assisted inference for ambiguous cases (nicknames, initials)
- Multi-source confidence calculation
- Schemas for roster entries and resolution results
"""

from src.identity.confidence import calculate_confidence
from src.identity.fuzzy_matcher import FuzzyMatcher
from src.identity.llm_matcher import LLMMatcher
from src.identity.resolver import IdentityResolver
from src.identity.schemas import ResolutionResult, ResolutionSource, RosterEntry

__all__ = [
    "FuzzyMatcher",
    "IdentityResolver",
    "LLMMatcher",
    "ResolutionResult",
    "ResolutionSource",
    "RosterEntry",
    "calculate_confidence",
]
