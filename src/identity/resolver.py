"""IdentityResolver orchestrates multi-stage identity resolution.

Resolution pipeline (in order):
1. Exact match (O(n) string comparison)
2. Learned mapping lookup (O(1) with index)
3. Fuzzy match (O(n) Jaro-Winkler)
4. LLM inference (for ambiguous cases)
"""

from src.identity.fuzzy_matcher import FuzzyMatcher
from src.identity.llm_matcher import LLMMatcher
from src.identity.schemas import ResolutionResult, ResolutionSource, RosterEntry
from src.repositories.mapping_repo import MappingRepository


class IdentityResolver:
    """Orchestrates multi-stage identity resolution.

    Resolution pipeline (in order):
    1. Exact match (O(n) string comparison)
    2. Learned mapping lookup (O(1) with index)
    3. Fuzzy match (O(n) Jaro-Winkler)
    4. LLM inference (for ambiguous cases)
    """

    def __init__(
        self,
        fuzzy_matcher: FuzzyMatcher,
        mapping_repo: MappingRepository,
        llm_matcher: LLMMatcher | None = None,
        auto_accept_threshold: float = 0.85,
    ):
        """Initialize resolver with required components.

        Args:
            fuzzy_matcher: Fuzzy name matching service
            mapping_repo: Repository for learned mappings
            llm_matcher: Optional LLM matcher for ambiguous cases
            auto_accept_threshold: Confidence threshold for auto-accept (default 0.85)
        """
        self._fuzzy = fuzzy_matcher
        self._mappings = mapping_repo
        self._llm = llm_matcher
        self._threshold = auto_accept_threshold

    async def resolve(
        self,
        transcript_name: str,
        roster: list[RosterEntry],
        project_id: str,
    ) -> ResolutionResult:
        """Resolve a transcript name to roster entry.

        Tries stages in order: exact -> learned -> fuzzy -> LLM.
        Returns first match above threshold or flags for review.

        Args:
            transcript_name: Name as it appeared in transcript
            roster: Project roster entries
            project_id: Project ID for learned mappings

        Returns:
            ResolutionResult with match or requires_review=True
        """
        # Stage 1: Exact match
        exact = self._exact_match(transcript_name, roster)
        if exact:
            return ResolutionResult(
                transcript_name=transcript_name,
                resolved_email=exact.email,
                resolved_name=exact.name,
                confidence=1.0,
                source=ResolutionSource.EXACT,
                requires_review=False,
            )

        # Stage 2: Learned mapping
        learned = await self._mappings.get_mapping(project_id, transcript_name)
        if learned:
            email, name = learned
            return ResolutionResult(
                transcript_name=transcript_name,
                resolved_email=email,
                resolved_name=name,
                confidence=0.95,  # High confidence for learned
                source=ResolutionSource.LEARNED,
                requires_review=False,
            )

        # Stage 3: Fuzzy match
        match, score = self._fuzzy.find_best_match(transcript_name, roster)
        alternatives = self._fuzzy.find_top_matches(transcript_name, roster, limit=3)

        if match and score >= self._threshold:
            return ResolutionResult(
                transcript_name=transcript_name,
                resolved_email=match.email,
                resolved_name=match.name,
                confidence=min(score, 0.85),  # Single-source cap
                source=ResolutionSource.FUZZY,
                alternatives=[
                    (e.name, s) for e, s in alternatives if e.email != match.email
                ],
                requires_review=False,
            )

        # Stage 4: LLM inference (if available and fuzzy gave candidates)
        if self._llm and alternatives:
            llm_result = await self._llm.infer_match(
                transcript_name, roster, alternatives
            )
            if llm_result.resolved_email:
                return llm_result

        # No match found - return for review
        return ResolutionResult(
            transcript_name=transcript_name,
            resolved_email=None,
            resolved_name=None,
            confidence=0.0,
            source=ResolutionSource.FUZZY,
            alternatives=[(e.name, s) for e, s in alternatives] if alternatives else [],
            requires_review=True,
        )

    def _exact_match(
        self,
        transcript_name: str,
        roster: list[RosterEntry],
    ) -> RosterEntry | None:
        """Check for exact name match (case-insensitive).

        Args:
            transcript_name: Name to match
            roster: Roster entries to search

        Returns:
            Matched entry or None
        """
        normalized = transcript_name.strip().lower()
        for entry in roster:
            if entry.name.strip().lower() == normalized:
                return entry
            if normalized in [a.strip().lower() for a in entry.aliases]:
                return entry
        return None

    async def resolve_all(
        self,
        names: list[str],
        roster: list[RosterEntry],
        project_id: str,
    ) -> list[ResolutionResult]:
        """Resolve multiple names.

        Args:
            names: List of transcript names to resolve
            roster: Project roster entries
            project_id: Project ID for learned mappings

        Returns:
            List of resolution results in same order as names
        """
        return [await self.resolve(name, roster, project_id) for name in names]

    async def learn_mapping(
        self,
        project_id: str,
        transcript_name: str,
        resolved_email: str,
        resolved_name: str,
        created_by: str | None = None,
    ) -> None:
        """Save a user-confirmed mapping for future use.

        Args:
            project_id: Project identifier
            transcript_name: Name as it appeared in transcript
            resolved_email: Correct email address
            resolved_name: Canonical name
            created_by: Optional user who created this mapping
        """
        await self._mappings.save_mapping(
            project_id=project_id,
            transcript_name=transcript_name,
            resolved_email=resolved_email,
            resolved_name=resolved_name,
            created_by=created_by,
        )
