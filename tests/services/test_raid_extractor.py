"""Tests for RAIDExtractor service."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.extraction.schemas import (
    ExtractedActionItem,
    ExtractedActionItems,
    ExtractedDecision,
    ExtractedDecisions,
    ExtractedIssue,
    ExtractedIssues,
    ExtractedRisk,
    ExtractedRisks,
)
from src.models.action_item import ActionItem, ActionItemStatus
from src.models.decision import Decision
from src.models.issue import Issue, IssuePriority, IssueStatus
from src.models.risk import Risk, RiskSeverity
from src.services.llm_client import LLMClient
from src.services.raid_extractor import ExtractionResult, RAIDExtractor

# Fixtures


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock(spec=LLMClient)
    client.extract = AsyncMock()
    return client


@pytest.fixture
def sample_meeting_id() -> UUID:
    """Fixed meeting UUID for tests."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_meeting_date() -> datetime:
    """Fixed meeting datetime for date normalization tests."""
    return datetime(2026, 1, 18, 10, 0, 0)


@pytest.fixture
def sample_transcript_text() -> str:
    """Multi-line formatted transcript for tests."""
    return """[00:01:00] Alice: Let's discuss the deployment timeline.
[00:01:30] Bob: I'll send the updated specs by Friday.
[00:02:00] Alice: Sounds good. The API might be slow if we don't optimize.
[00:02:30] Bob: We decided to use the new database schema.
[00:03:00] Alice: The current build is broken."""


# Test action item extraction


async def test_extract_action_items_filters_by_confidence(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test that only high-confidence items pass the threshold."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            return ExtractedActionItems(
                items=[
                    ExtractedActionItem(
                        description="Send updated specs",
                        assignee_name="Bob",
                        due_date_raw="Friday",
                        source_quote="I'll send the updated specs by Friday",
                        confidence=0.8,
                    ),
                    ExtractedActionItem(
                        description="Review the proposal",
                        assignee_name=None,
                        due_date_raw=None,
                        source_quote="Someone should review this",
                        confidence=0.4,
                    ),
                ]
            )
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(items=[])
        elif response_model == ExtractedRisks:
            return ExtractedRisks(items=[])
        elif response_model == ExtractedIssues:
            return ExtractedIssues(items=[])

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript text", sample_meeting_id, sample_meeting_date
    )

    # Only the 0.8 confidence item should be included
    assert len(result.action_items) == 1
    assert result.action_items[0].description == "Send updated specs"
    assert result.action_items[0].assignee_name == "Bob"
    assert result.action_items[0].confidence == 0.8


async def test_extract_action_items_domain_model_conversion(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test that extraction output converts to ActionItem domain model."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            return ExtractedActionItems(
                items=[
                    ExtractedActionItem(
                        description="Send report",
                        assignee_name="Alice",
                        due_date_raw="Friday",
                        source_quote="I'll send the report",
                        confidence=0.9,
                    ),
                ]
            )
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(items=[])
        elif response_model == ExtractedRisks:
            return ExtractedRisks(items=[])
        elif response_model == ExtractedIssues:
            return ExtractedIssues(items=[])

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    item = result.action_items[0]
    assert isinstance(item, ActionItem)
    assert isinstance(item.id, UUID)
    assert item.meeting_id == sample_meeting_id
    assert item.status == ActionItemStatus.PENDING
    assert item.source_quote == "I'll send the report"
    # Due date normalized: Jan 18 2026 (Sunday) + "Friday" = Jan 23 2026
    assert item.due_date == date(2026, 1, 23)


# Test decision extraction


async def test_extract_decisions_with_rationale_and_alternatives(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test decision extraction with rationale and alternatives."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            return ExtractedActionItems(items=[])
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(
                items=[
                    ExtractedDecision(
                        description="Use the new database schema",
                        rationale="Better performance and scalability",
                        alternatives=["Keep old schema", "Hybrid approach"],
                        source_quote="We decided to use the new database schema",
                        confidence=0.85,
                    ),
                ]
            )
        elif response_model == ExtractedRisks:
            return ExtractedRisks(items=[])
        elif response_model == ExtractedIssues:
            return ExtractedIssues(items=[])

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    assert len(result.decisions) == 1
    decision = result.decisions[0]
    assert isinstance(decision, Decision)
    assert decision.description == "Use the new database schema"
    assert decision.rationale == "Better performance and scalability"
    assert decision.alternatives == ["Keep old schema", "Hybrid approach"]
    assert decision.meeting_id == sample_meeting_id


# Test risk extraction


async def test_extract_risks_maps_severity_enum(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test that severity string maps to RiskSeverity enum."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            return ExtractedActionItems(items=[])
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(items=[])
        elif response_model == ExtractedRisks:
            return ExtractedRisks(
                items=[
                    ExtractedRisk(
                        description="API might be slow",
                        severity="high",
                        impact="Users will experience latency",
                        mitigation="Optimize queries",
                        owner_name="Bob",
                        source_quote="The API might be slow",
                        confidence=0.75,
                    ),
                ]
            )
        elif response_model == ExtractedIssues:
            return ExtractedIssues(items=[])

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    assert len(result.risks) == 1
    risk = result.risks[0]
    assert isinstance(risk, Risk)
    assert risk.severity == RiskSeverity.HIGH
    assert risk.owner_name == "Bob"
    assert risk.impact == "Users will experience latency"
    assert risk.mitigation == "Optimize queries"


# Test issue extraction


async def test_extract_issues_maps_priority_and_status(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test that priority string maps to IssuePriority and status is OPEN."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            return ExtractedActionItems(items=[])
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(items=[])
        elif response_model == ExtractedRisks:
            return ExtractedRisks(items=[])
        elif response_model == ExtractedIssues:
            return ExtractedIssues(
                items=[
                    ExtractedIssue(
                        description="Build is broken",
                        priority="critical",
                        impact="Cannot deploy",
                        owner_name="Alice",
                        source_quote="The current build is broken",
                        confidence=0.9,
                    ),
                ]
            )

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert isinstance(issue, Issue)
    assert issue.priority == IssuePriority.CRITICAL
    assert issue.status == IssueStatus.OPEN
    assert issue.owner_name == "Alice"


# Test extract_all orchestration


async def test_extract_all_returns_all_raid_types(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test that extract_all returns items from all four RAID types."""

    # Track call order
    call_order = []

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            call_order.append("action_items")
            return ExtractedActionItems(
                items=[
                    ExtractedActionItem(
                        description="Action 1",
                        source_quote="quote",
                        confidence=0.9,
                    )
                ]
            )
        elif response_model == ExtractedDecisions:
            call_order.append("decisions")
            return ExtractedDecisions(
                items=[
                    ExtractedDecision(
                        description="Decision 1",
                        source_quote="quote",
                        confidence=0.9,
                    )
                ]
            )
        elif response_model == ExtractedRisks:
            call_order.append("risks")
            return ExtractedRisks(
                items=[
                    ExtractedRisk(
                        description="Risk 1",
                        severity="medium",
                        source_quote="quote",
                        confidence=0.9,
                    )
                ]
            )
        elif response_model == ExtractedIssues:
            call_order.append("issues")
            return ExtractedIssues(
                items=[
                    ExtractedIssue(
                        description="Issue 1",
                        priority="medium",
                        source_quote="quote",
                        confidence=0.9,
                    )
                ]
            )

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    # Verify all types returned
    assert isinstance(result, ExtractionResult)
    assert len(result.action_items) == 1
    assert len(result.decisions) == 1
    assert len(result.risks) == 1
    assert len(result.issues) == 1

    # Verify sequential order (not parallel)
    assert call_order == ["action_items", "decisions", "risks", "issues"]


# Test error handling


async def test_extraction_error_returns_empty_list_for_failed_type(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test that one extraction failure doesn't stop other extractions."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            raise Exception("API Error")
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(
                items=[
                    ExtractedDecision(
                        description="Decision 1",
                        source_quote="quote",
                        confidence=0.9,
                    )
                ]
            )
        elif response_model == ExtractedRisks:
            return ExtractedRisks(items=[])
        elif response_model == ExtractedIssues:
            return ExtractedIssues(items=[])

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    # Action items should be empty due to error
    assert len(result.action_items) == 0
    # Decision should still be extracted
    assert len(result.decisions) == 1
    assert result.decisions[0].description == "Decision 1"


# Test confidence filtering


async def test_confidence_filtering_threshold_boundary(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test confidence filtering at threshold boundary."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            return ExtractedActionItems(
                items=[
                    ExtractedActionItem(
                        description="Below threshold",
                        source_quote="quote",
                        confidence=0.6,
                    ),
                    ExtractedActionItem(
                        description="At threshold",
                        source_quote="quote",
                        confidence=0.7,
                    ),
                    ExtractedActionItem(
                        description="Above threshold",
                        source_quote="quote",
                        confidence=0.8,
                    ),
                ]
            )
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(items=[])
        elif response_model == ExtractedRisks:
            return ExtractedRisks(items=[])
        elif response_model == ExtractedIssues:
            return ExtractedIssues(items=[])

    mock_llm_client.extract.side_effect = mock_extract

    # Threshold is 0.7 - items at or above should be included
    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.7)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    assert len(result.action_items) == 2
    descriptions = [item.description for item in result.action_items]
    assert "At threshold" in descriptions
    assert "Above threshold" in descriptions
    assert "Below threshold" not in descriptions


# Test format_transcript helper


def test_format_transcript_formats_utterances():
    """Test that format_transcript correctly formats utterances."""

    class MockUtterance:
        def __init__(self, start_time, speaker, text):
            self.start_time = start_time
            self.speaker = speaker
            self.text = text

    utterances = [
        MockUtterance("00:01:00", "Alice", "Hello everyone"),
        MockUtterance("00:01:30", "Bob", "Hi Alice"),
    ]

    result = RAIDExtractor.format_transcript(utterances)

    assert result == "[00:01:00] Alice: Hello everyone\n[00:01:30] Bob: Hi Alice"


# Test empty extraction


async def test_extract_all_with_no_items(
    mock_llm_client, sample_meeting_id, sample_meeting_date
):
    """Test extraction when LLM returns no items."""

    async def mock_extract(prompt, response_model):
        if response_model == ExtractedActionItems:
            return ExtractedActionItems(items=[])
        elif response_model == ExtractedDecisions:
            return ExtractedDecisions(items=[])
        elif response_model == ExtractedRisks:
            return ExtractedRisks(items=[])
        elif response_model == ExtractedIssues:
            return ExtractedIssues(items=[])

    mock_llm_client.extract.side_effect = mock_extract

    extractor = RAIDExtractor(mock_llm_client, confidence_threshold=0.5)
    result = await extractor.extract_all(
        "transcript", sample_meeting_id, sample_meeting_date
    )

    assert len(result.action_items) == 0
    assert len(result.decisions) == 0
    assert len(result.risks) == 0
    assert len(result.issues) == 0
