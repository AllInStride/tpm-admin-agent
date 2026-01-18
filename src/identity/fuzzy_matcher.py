"""Fuzzy name matching using RapidFuzz.

Provides Jaro-Winkler based name matching with support for aliases
and name order independence (John Smith = Smith, John).
"""

from rapidfuzz import fuzz, process, utils

from src.identity.schemas import RosterEntry


class FuzzyMatcher:
    """Fuzzy name matching using RapidFuzz.

    Uses token_sort_ratio for name order independence (handles
    "John Smith" vs "Smith, John"). Searches both primary names
    and aliases for best match.
    """

    def __init__(self, threshold: float = 0.85):
        """Initialize matcher with confidence threshold.

        Args:
            threshold: Minimum score (0-1) for a match to be returned.
                      Scores below this return None.
        """
        self._threshold = threshold

    def find_best_match(
        self,
        query: str,
        roster: list[RosterEntry],
    ) -> tuple[RosterEntry | None, float]:
        """Find best matching roster entry for a name.

        Uses token_sort_ratio for name order independence.
        Searches both primary names and all aliases.

        Args:
            query: Name to search for (from transcript)
            roster: List of roster entries to match against

        Returns:
            Tuple of (matched_entry, score) or (None, 0.0) if no match
            above threshold.
        """
        if not roster:
            return None, 0.0

        # Build expanded choices: map each searchable name -> entry
        choices: dict[str, RosterEntry] = {}
        for entry in roster:
            # Add primary name
            choices[entry.name] = entry
            # Add all aliases
            for alias in entry.aliases:
                choices[alias] = entry

        if not choices:
            return None, 0.0

        # Use extractOne with token_sort_ratio (returns 0-100 scale)
        result = process.extractOne(
            query,
            list(choices.keys()),
            scorer=fuzz.token_sort_ratio,
            processor=utils.default_process,
            score_cutoff=self._threshold * 100,  # fuzz uses 0-100 scale
        )

        if result:
            matched_name, score, _index = result
            return choices[matched_name], score / 100  # Normalize to 0-1

        return None, 0.0

    def find_top_matches(
        self,
        query: str,
        roster: list[RosterEntry],
        limit: int = 3,
    ) -> list[tuple[RosterEntry, float]]:
        """Find top N matches for alternatives display.

        Returns matches in descending score order, regardless of threshold.
        Useful for showing alternatives when best match is below threshold.

        Args:
            query: Name to search for
            roster: List of roster entries to match against
            limit: Maximum number of matches to return

        Returns:
            List of (entry, score) tuples sorted by score descending.
            May return fewer than limit if roster is smaller.
        """
        if not roster:
            return []

        # Build expanded choices: map each searchable name -> entry
        choices: dict[str, RosterEntry] = {}
        for entry in roster:
            choices[entry.name] = entry
            for alias in entry.aliases:
                choices[alias] = entry

        if not choices:
            return []

        # Use extract for multiple results (no score_cutoff to get all)
        results = process.extract(
            query,
            list(choices.keys()),
            scorer=fuzz.token_sort_ratio,
            processor=utils.default_process,
            limit=limit * 2,  # Get extra to handle duplicate entries
        )

        # Deduplicate by entry email (an alias and name might map to same entry)
        seen_emails: set[str] = set()
        matches: list[tuple[RosterEntry, float]] = []

        for matched_name, score, _index in results:
            entry = choices[matched_name]
            if entry.email not in seen_emails:
                seen_emails.add(entry.email)
                matches.append((entry, score / 100))
                if len(matches) >= limit:
                    break

        return matches
