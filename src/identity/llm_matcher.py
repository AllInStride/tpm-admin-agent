"""LLM-assisted name inference for ambiguous cases.

Handles cases fuzzy matching can't:
- Nicknames (Bob -> Robert)
- Initials (JSmith -> John Smith)
- Transcription errors
"""

from pydantic import BaseModel, Field

from src.identity.schemas import ResolutionResult, ResolutionSource, RosterEntry
from src.services.llm_client import LLMClient, LLMClientError


class LLMMatchResponse(BaseModel):
    """Response from LLM name matching."""

    matched_email: str | None = Field(
        description="Email of matched person, or null if no match"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="How certain of this match (0.0-1.0)"
    )
    reasoning: str = Field(description="Brief explanation of matching logic")


class LLMMatcher:
    """LLM-assisted name inference for ambiguous cases.

    Handles cases fuzzy matching can't:
    - Nicknames (Bob -> Robert)
    - Initials (JSmith -> John Smith)
    - Transcription errors
    """

    # fmt: off
    NAME_INFERENCE_PROMPT = (
        "You are resolving a person's name from a meeting transcript "
        "to a project roster.\n\n"
        "TRANSCRIPT NAME: {transcript_name}\n\n"
        "PROJECT ROSTER:\n"
        "{roster_formatted}\n\n"
        "TASK: Determine which roster person (if any) the transcript name "
        "refers to.\n\n"
        "RULES:\n"
        "1. Consider common nicknames (Bob=Robert, Mike=Michael, Bill=William)\n"
        "2. Consider initials (JSmith might be John Smith)\n"
        "3. Consider typos or transcription errors\n"
        "4. If no confident match, return null for matched_email\n\n"
        "Respond with the email of the matched person (or null), "
        "your confidence (0.0-1.0), and brief reasoning."
    )
    # fmt: on

    def __init__(self, llm_client: LLMClient):
        """Initialize with LLM client.

        Args:
            llm_client: Client for making LLM requests
        """
        self._llm_client = llm_client

    async def infer_match(
        self,
        transcript_name: str,
        roster: list[RosterEntry],
        fuzzy_candidates: list[tuple[RosterEntry, float]] | None = None,
    ) -> ResolutionResult:
        """Use LLM to infer identity for ambiguous name.

        Args:
            transcript_name: Name as it appeared in transcript
            roster: Full project roster
            fuzzy_candidates: Top fuzzy matches if available (for context)

        Returns:
            ResolutionResult with LLM inference
        """
        roster_formatted = self._format_roster(roster)
        prompt = self.NAME_INFERENCE_PROMPT.format(
            transcript_name=transcript_name,
            roster_formatted=roster_formatted,
        )

        try:
            result = await self._llm_client.extract(prompt, LLMMatchResponse)

            if result.matched_email:
                # Find the matching roster entry to get canonical name
                matched_entry = next(
                    (e for e in roster if e.email == result.matched_email),
                    None,
                )
                resolved_name = matched_entry.name if matched_entry else None

                return ResolutionResult(
                    transcript_name=transcript_name,
                    resolved_email=result.matched_email,
                    resolved_name=resolved_name,
                    confidence=min(result.confidence, 0.85),  # LLM capped at 85%
                    source=ResolutionSource.LLM,
                    requires_review=result.confidence < 0.85,
                )

            # No match found
            return ResolutionResult(
                transcript_name=transcript_name,
                resolved_email=None,
                resolved_name=None,
                confidence=0.0,
                source=ResolutionSource.LLM,
                requires_review=True,
            )

        except LLMClientError:
            # Return unresolved result on LLM failure
            return ResolutionResult(
                transcript_name=transcript_name,
                resolved_email=None,
                resolved_name=None,
                confidence=0.0,
                source=ResolutionSource.LLM,
                requires_review=True,
            )

    def _format_roster(self, roster: list[RosterEntry]) -> str:
        """Format roster for LLM prompt.

        Args:
            roster: List of roster entries

        Returns:
            Formatted string with one person per line
        """
        lines = []
        for entry in roster:
            alias_str = (
                f" (aliases: {', '.join(entry.aliases)})" if entry.aliases else ""
            )
            lines.append(f"- {entry.name} <{entry.email}>{alias_str}")
        return "\n".join(lines)
