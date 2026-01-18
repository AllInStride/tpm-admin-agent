"""Tests for RAID extraction prompts.

These are structural tests ensuring prompts meet requirements.
Actual extraction quality is tested via integration tests.
"""

import pytest

from src.extraction.prompts import (
    ACTION_ITEM_PROMPT,
    DECISION_PROMPT,
    ISSUE_PROMPT,
    RISK_PROMPT,
)


class TestPromptStructure:
    """Test that all prompts are properly structured."""

    def test_action_item_prompt_is_non_empty_string(self):
        """ACTION_ITEM_PROMPT should be a non-empty string."""
        assert isinstance(ACTION_ITEM_PROMPT, str)
        assert len(ACTION_ITEM_PROMPT) > 0

    def test_decision_prompt_is_non_empty_string(self):
        """DECISION_PROMPT should be a non-empty string."""
        assert isinstance(DECISION_PROMPT, str)
        assert len(DECISION_PROMPT) > 0

    def test_risk_prompt_is_non_empty_string(self):
        """RISK_PROMPT should be a non-empty string."""
        assert isinstance(RISK_PROMPT, str)
        assert len(RISK_PROMPT) > 0

    def test_issue_prompt_is_non_empty_string(self):
        """ISSUE_PROMPT should be a non-empty string."""
        assert isinstance(ISSUE_PROMPT, str)
        assert len(ISSUE_PROMPT) > 0


class TestConfidenceRubric:
    """Test that all prompts contain confidence calibration rubric."""

    @pytest.mark.parametrize(
        "prompt,name",
        [
            (ACTION_ITEM_PROMPT, "ACTION_ITEM_PROMPT"),
            (DECISION_PROMPT, "DECISION_PROMPT"),
            (RISK_PROMPT, "RISK_PROMPT"),
            (ISSUE_PROMPT, "ISSUE_PROMPT"),
        ],
    )
    def test_prompt_contains_confidence_rubric(self, prompt, name):
        """Each prompt should contain confidence thresholds."""
        assert "0.9" in prompt, f"{name} should contain 0.9 confidence threshold"
        assert "0.7" in prompt, f"{name} should contain 0.7 confidence threshold"
        assert "0.5" in prompt, f"{name} should contain 0.5 confidence threshold"

    @pytest.mark.parametrize(
        "prompt,name",
        [
            (ACTION_ITEM_PROMPT, "ACTION_ITEM_PROMPT"),
            (DECISION_PROMPT, "DECISION_PROMPT"),
            (RISK_PROMPT, "RISK_PROMPT"),
            (ISSUE_PROMPT, "ISSUE_PROMPT"),
        ],
    )
    def test_prompt_contains_confidence_range(self, prompt, name):
        """Each prompt should contain the full confidence rubric ranges."""
        assert "0.9-1.0" in prompt, f"{name} should contain 0.9-1.0 range"
        assert "0.7-0.9" in prompt, f"{name} should contain 0.7-0.9 range"
        assert "0.5-0.7" in prompt, f"{name} should contain 0.5-0.7 range"


class TestSourceQuoteRequirement:
    """Test that all prompts require source quote extraction."""

    @pytest.mark.parametrize(
        "prompt,name",
        [
            (ACTION_ITEM_PROMPT, "ACTION_ITEM_PROMPT"),
            (DECISION_PROMPT, "DECISION_PROMPT"),
            (RISK_PROMPT, "RISK_PROMPT"),
            (ISSUE_PROMPT, "ISSUE_PROMPT"),
        ],
    )
    def test_prompt_requires_source_quote(self, prompt, name):
        """Each prompt should require source_quote for audit trail."""
        assert "source_quote" in prompt, f"{name} should require source_quote"


class TestTypeSpecificGuidance:
    """Test that each prompt has type-specific extraction guidance."""

    def test_action_item_prompt_mentions_assignee(self):
        """ACTION_ITEM_PROMPT should mention assignee extraction."""
        assert "assignee" in ACTION_ITEM_PROMPT.lower()

    def test_action_item_prompt_mentions_due_date(self):
        """ACTION_ITEM_PROMPT should mention due date extraction."""
        assert "due_date" in ACTION_ITEM_PROMPT or "due date" in ACTION_ITEM_PROMPT

    def test_decision_prompt_mentions_rationale(self):
        """DECISION_PROMPT should mention rationale extraction."""
        assert "rationale" in DECISION_PROMPT.lower()

    def test_decision_prompt_mentions_alternatives(self):
        """DECISION_PROMPT should mention alternatives extraction."""
        assert "alternatives" in DECISION_PROMPT.lower()

    def test_risk_prompt_mentions_severity_levels(self):
        """RISK_PROMPT should mention all severity levels."""
        assert "critical" in RISK_PROMPT.lower()
        assert "high" in RISK_PROMPT.lower()
        assert "medium" in RISK_PROMPT.lower()
        assert "low" in RISK_PROMPT.lower()

    def test_issue_prompt_mentions_priority_levels(self):
        """ISSUE_PROMPT should mention all priority levels."""
        assert "critical" in ISSUE_PROMPT.lower()
        assert "high" in ISSUE_PROMPT.lower()
        assert "medium" in ISSUE_PROMPT.lower()
        assert "low" in ISSUE_PROMPT.lower()


class TestTranscriptPlaceholder:
    """Test that prompts contain transcript placeholder."""

    @pytest.mark.parametrize(
        "prompt,name",
        [
            (ACTION_ITEM_PROMPT, "ACTION_ITEM_PROMPT"),
            (DECISION_PROMPT, "DECISION_PROMPT"),
            (RISK_PROMPT, "RISK_PROMPT"),
            (ISSUE_PROMPT, "ISSUE_PROMPT"),
        ],
    )
    def test_prompt_contains_transcript_placeholder(self, prompt, name):
        """Each prompt should contain {transcript} placeholder."""
        assert (
            "{transcript}" in prompt
        ), f"{name} should contain {{transcript}} placeholder"

    @pytest.mark.parametrize(
        "prompt,name",
        [
            (ACTION_ITEM_PROMPT, "ACTION_ITEM_PROMPT"),
            (DECISION_PROMPT, "DECISION_PROMPT"),
            (RISK_PROMPT, "RISK_PROMPT"),
            (ISSUE_PROMPT, "ISSUE_PROMPT"),
        ],
    )
    def test_instructions_after_transcript(self, prompt, name):
        """Instructions should come after transcript (lost-in-middle mitigation)."""
        transcript_pos = prompt.find("{transcript}")
        instruction_pos = prompt.find("Extract all")

        assert (
            transcript_pos < instruction_pos
        ), f"{name} should have transcript before extraction instructions"


class TestDistinctionGuidance:
    """Test that prompts include guidance on distinguishing RAID types."""

    def test_action_item_distinguishes_commitment_from_discussion(self):
        """ACTION_ITEM_PROMPT should distinguish commitments from discussions."""
        assert (
            "discussion" in ACTION_ITEM_PROMPT.lower()
            or "discuss" in ACTION_ITEM_PROMPT.lower()
        )

    def test_decision_distinguishes_made_from_being_discussed(self):
        """DECISION_PROMPT should distinguish decisions made from being discussed."""
        assert "decision" in DECISION_PROMPT.lower()

    def test_risk_distinguishes_from_issue(self):
        """RISK_PROMPT should distinguish risks from issues."""
        assert "issue" in RISK_PROMPT.lower()
        assert "potential" in RISK_PROMPT.lower() or "might" in RISK_PROMPT.lower()

    def test_issue_distinguishes_from_risk(self):
        """ISSUE_PROMPT should distinguish issues from risks."""
        assert "risk" in ISSUE_PROMPT.lower()
        assert "current" in ISSUE_PROMPT.lower()
