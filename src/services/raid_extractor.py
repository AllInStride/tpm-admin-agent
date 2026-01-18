"""RAIDExtractor service for extracting RAID items from transcripts.

Orchestrates LLM-based extraction of all RAID types (Risks, Action Items,
Issues, Decisions) from meeting transcripts, converting extraction output
to domain models.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from src.extraction.date_normalizer import normalize_due_date
from src.extraction.prompts import (
    ACTION_ITEM_PROMPT,
    DECISION_PROMPT,
    ISSUE_PROMPT,
    RISK_PROMPT,
)
from src.extraction.schemas import (
    ExtractedActionItems,
    ExtractedDecisions,
    ExtractedIssues,
    ExtractedRisks,
)
from src.models.action_item import ActionItem, ActionItemStatus
from src.models.decision import Decision
from src.models.issue import Issue, IssuePriority, IssueStatus
from src.models.risk import Risk, RiskSeverity
from src.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of RAID extraction from a transcript."""

    action_items: list[ActionItem]
    decisions: list[Decision]
    risks: list[Risk]
    issues: list[Issue]


class RAIDExtractor:
    """Extracts RAID items from meeting transcripts using LLM.

    Uses separate prompts for each RAID type for better precision.
    Applies confidence threshold filtering and converts extraction
    output to domain models.
    """

    def __init__(self, llm_client: LLMClient, confidence_threshold: float = 0.5):
        """Initialize extractor with LLM client and threshold.

        Args:
            llm_client: LLM client for structured extraction
            confidence_threshold: Minimum confidence to include item (0.0-1.0)
        """
        self._llm_client = llm_client
        self._confidence_threshold = confidence_threshold

    async def extract_all(
        self,
        transcript_text: str,
        meeting_id: UUID,
        meeting_date: datetime,
    ) -> ExtractionResult:
        """Extract all RAID items from transcript text.

        Extracts in sequence (not parallel) to avoid rate limits.

        Args:
            transcript_text: Formatted transcript text
            meeting_id: UUID of the meeting
            meeting_date: Datetime of the meeting (for date normalization)

        Returns:
            ExtractionResult with all extracted items
        """
        action_items = await self._extract_action_items(
            transcript_text, meeting_id, meeting_date
        )
        decisions = await self._extract_decisions(transcript_text, meeting_id)
        risks = await self._extract_risks(transcript_text, meeting_id)
        issues = await self._extract_issues(transcript_text, meeting_id)

        return ExtractionResult(
            action_items=action_items,
            decisions=decisions,
            risks=risks,
            issues=issues,
        )

    @staticmethod
    def format_transcript(utterances: list) -> str:
        """Format utterances as readable transcript for LLM.

        Args:
            utterances: List of Utterance objects with start_time, speaker, text

        Returns:
            Formatted transcript string
        """
        lines = []
        for u in utterances:
            lines.append(f"[{u.start_time}] {u.speaker}: {u.text}")
        return "\n".join(lines)

    async def _extract_action_items(
        self,
        transcript_text: str,
        meeting_id: UUID,
        meeting_date: datetime,
    ) -> list[ActionItem]:
        """Extract action items from transcript.

        Args:
            transcript_text: Formatted transcript text
            meeting_id: UUID of the meeting
            meeting_date: Datetime for date normalization

        Returns:
            List of ActionItem domain models
        """
        try:
            prompt = ACTION_ITEM_PROMPT.format(transcript=transcript_text)
            result = await self._llm_client.extract(prompt, ExtractedActionItems)

            action_items = []
            for item in result.items:
                if item.confidence < self._confidence_threshold:
                    continue

                action_items.append(
                    ActionItem(
                        id=uuid4(),
                        meeting_id=meeting_id,
                        description=item.description,
                        assignee_name=item.assignee_name,
                        due_date=normalize_due_date(item.due_date_raw, meeting_date),
                        status=ActionItemStatus.PENDING,
                        source_quote=item.source_quote,
                        confidence=item.confidence,
                    )
                )

            return action_items

        except Exception as e:
            logger.error(f"Failed to extract action items: {e}")
            return []

    async def _extract_decisions(
        self,
        transcript_text: str,
        meeting_id: UUID,
    ) -> list[Decision]:
        """Extract decisions from transcript.

        Args:
            transcript_text: Formatted transcript text
            meeting_id: UUID of the meeting

        Returns:
            List of Decision domain models
        """
        try:
            prompt = DECISION_PROMPT.format(transcript=transcript_text)
            result = await self._llm_client.extract(prompt, ExtractedDecisions)

            decisions = []
            for item in result.items:
                if item.confidence < self._confidence_threshold:
                    continue

                decisions.append(
                    Decision(
                        id=uuid4(),
                        meeting_id=meeting_id,
                        description=item.description,
                        rationale=item.rationale,
                        alternatives=item.alternatives,
                        source_quote=item.source_quote,
                        confidence=item.confidence,
                    )
                )

            return decisions

        except Exception as e:
            logger.error(f"Failed to extract decisions: {e}")
            return []

    async def _extract_risks(
        self,
        transcript_text: str,
        meeting_id: UUID,
    ) -> list[Risk]:
        """Extract risks from transcript.

        Args:
            transcript_text: Formatted transcript text
            meeting_id: UUID of the meeting

        Returns:
            List of Risk domain models
        """
        try:
            prompt = RISK_PROMPT.format(transcript=transcript_text)
            result = await self._llm_client.extract(prompt, ExtractedRisks)

            risks = []
            for item in result.items:
                if item.confidence < self._confidence_threshold:
                    continue

                # Map severity string to enum
                severity_map = {
                    "low": RiskSeverity.LOW,
                    "medium": RiskSeverity.MEDIUM,
                    "high": RiskSeverity.HIGH,
                    "critical": RiskSeverity.CRITICAL,
                }

                risks.append(
                    Risk(
                        id=uuid4(),
                        meeting_id=meeting_id,
                        description=item.description,
                        severity=severity_map.get(item.severity, RiskSeverity.MEDIUM),
                        impact=item.impact,
                        mitigation=item.mitigation,
                        owner_name=item.owner_name,
                        source_quote=item.source_quote,
                        confidence=item.confidence,
                    )
                )

            return risks

        except Exception as e:
            logger.error(f"Failed to extract risks: {e}")
            return []

    async def _extract_issues(
        self,
        transcript_text: str,
        meeting_id: UUID,
    ) -> list[Issue]:
        """Extract issues from transcript.

        Args:
            transcript_text: Formatted transcript text
            meeting_id: UUID of the meeting

        Returns:
            List of Issue domain models
        """
        try:
            prompt = ISSUE_PROMPT.format(transcript=transcript_text)
            result = await self._llm_client.extract(prompt, ExtractedIssues)

            issues = []
            for item in result.items:
                if item.confidence < self._confidence_threshold:
                    continue

                # Map priority string to enum
                priority_map = {
                    "low": IssuePriority.LOW,
                    "medium": IssuePriority.MEDIUM,
                    "high": IssuePriority.HIGH,
                    "critical": IssuePriority.CRITICAL,
                }

                issues.append(
                    Issue(
                        id=uuid4(),
                        meeting_id=meeting_id,
                        description=item.description,
                        priority=priority_map.get(item.priority, IssuePriority.MEDIUM),
                        status=IssueStatus.OPEN,
                        impact=item.impact,
                        owner_name=item.owner_name,
                        source_quote=item.source_quote,
                        confidence=item.confidence,
                    )
                )

            return issues

        except Exception as e:
            logger.error(f"Failed to extract issues: {e}")
            return []
