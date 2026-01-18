"""Tests for extraction schemas."""

import pytest
from pydantic import ValidationError

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


class TestExtractedActionItem:
    """Tests for ExtractedActionItem schema."""

    def test_valid_action_item_all_fields(self):
        """Test creating action item with all fields."""
        item = ExtractedActionItem(
            description="Send the report to stakeholders",
            assignee_name="John Smith",
            due_date_raw="next Friday",
            source_quote="John said: I'll send the report by next Friday",
            confidence=0.95,
        )
        assert item.description == "Send the report to stakeholders"
        assert item.assignee_name == "John Smith"
        assert item.due_date_raw == "next Friday"
        assert item.confidence == 0.95

    def test_valid_action_item_optional_fields_none(self):
        """Test creating action item with optional fields as None."""
        item = ExtractedActionItem(
            description="Review the design doc",
            assignee_name=None,
            due_date_raw=None,
            source_quote="We need to review the design doc",
            confidence=0.6,
        )
        assert item.assignee_name is None
        assert item.due_date_raw is None

    def test_confidence_lower_bound(self):
        """Test confidence cannot be negative."""
        with pytest.raises(ValidationError):
            ExtractedActionItem(
                description="Test",
                source_quote="Test quote",
                confidence=-0.1,
            )

    def test_confidence_upper_bound(self):
        """Test confidence cannot exceed 1.0."""
        with pytest.raises(ValidationError):
            ExtractedActionItem(
                description="Test",
                source_quote="Test quote",
                confidence=1.1,
            )

    def test_confidence_valid_bounds(self):
        """Test confidence at exact boundaries."""
        item_low = ExtractedActionItem(
            description="Test",
            source_quote="Quote",
            confidence=0.0,
        )
        item_high = ExtractedActionItem(
            description="Test",
            source_quote="Quote",
            confidence=1.0,
        )
        assert item_low.confidence == 0.0
        assert item_high.confidence == 1.0


class TestExtractedActionItems:
    """Tests for ExtractedActionItems container."""

    def test_empty_list(self):
        """Test container with empty list."""
        container = ExtractedActionItems(items=[])
        assert len(container.items) == 0

    def test_populated_list(self):
        """Test container with multiple items."""
        items = [
            ExtractedActionItem(
                description="Task 1",
                source_quote="Quote 1",
                confidence=0.9,
            ),
            ExtractedActionItem(
                description="Task 2",
                assignee_name="Alice",
                source_quote="Quote 2",
                confidence=0.8,
            ),
        ]
        container = ExtractedActionItems(items=items)
        assert len(container.items) == 2
        assert container.items[0].description == "Task 1"
        assert container.items[1].assignee_name == "Alice"


class TestExtractedDecision:
    """Tests for ExtractedDecision schema."""

    def test_valid_decision_with_alternatives(self):
        """Test decision with alternatives list."""
        decision = ExtractedDecision(
            description="Use PostgreSQL for the database",
            rationale="Better JSON support and community",
            alternatives=["MySQL", "MongoDB", "SQLite"],
            source_quote="Let's go with PostgreSQL - it has better JSON support",
            confidence=0.9,
        )
        assert decision.description == "Use PostgreSQL for the database"
        assert len(decision.alternatives) == 3
        assert "MySQL" in decision.alternatives

    def test_decision_empty_alternatives(self):
        """Test decision with no alternatives discussed."""
        decision = ExtractedDecision(
            description="Ship by end of month",
            rationale=None,
            alternatives=[],
            source_quote="We'll ship by end of month",
            confidence=0.85,
        )
        assert decision.alternatives == []
        assert decision.rationale is None


class TestExtractedDecisions:
    """Tests for ExtractedDecisions container."""

    def test_empty_decisions(self):
        """Test container with no decisions."""
        container = ExtractedDecisions(items=[])
        assert len(container.items) == 0


class TestExtractedRisk:
    """Tests for ExtractedRisk schema."""

    def test_valid_risk_all_severities(self):
        """Test risk with all valid severity values."""
        for severity in ["low", "medium", "high", "critical"]:
            risk = ExtractedRisk(
                description=f"Test {severity} risk",
                severity=severity,
                source_quote="Test quote",
                confidence=0.8,
            )
            assert risk.severity == severity

    def test_risk_invalid_severity(self):
        """Test risk with invalid severity raises error."""
        with pytest.raises(ValidationError):
            ExtractedRisk(
                description="Test risk",
                severity="extreme",  # Invalid
                source_quote="Quote",
                confidence=0.8,
            )

    def test_risk_with_all_optional_fields(self):
        """Test risk with impact, mitigation, and owner."""
        risk = ExtractedRisk(
            description="API might be slow under load",
            severity="high",
            impact="Users experience timeouts during peak hours",
            mitigation="Add caching layer and load balancing",
            owner_name="Sarah Chen",
            source_quote="I'm worried the API might slow down under load",
            confidence=0.85,
        )
        assert risk.impact is not None
        assert risk.mitigation is not None
        assert risk.owner_name == "Sarah Chen"


class TestExtractedRisks:
    """Tests for ExtractedRisks container."""

    def test_populated_risks(self):
        """Test container with risks."""
        risks = [
            ExtractedRisk(
                description="Risk 1",
                severity="low",
                source_quote="Q1",
                confidence=0.7,
            ),
            ExtractedRisk(
                description="Risk 2",
                severity="critical",
                source_quote="Q2",
                confidence=0.9,
            ),
        ]
        container = ExtractedRisks(items=risks)
        assert len(container.items) == 2


class TestExtractedIssue:
    """Tests for ExtractedIssue schema."""

    def test_valid_issue_all_priorities(self):
        """Test issue with all valid priority values."""
        for priority in ["low", "medium", "high", "critical"]:
            issue = ExtractedIssue(
                description=f"Test {priority} issue",
                priority=priority,
                source_quote="Test quote",
                confidence=0.8,
            )
            assert issue.priority == priority

    def test_issue_invalid_priority(self):
        """Test issue with invalid priority raises error."""
        with pytest.raises(ValidationError):
            ExtractedIssue(
                description="Test issue",
                priority="urgent",  # Invalid
                source_quote="Quote",
                confidence=0.8,
            )

    def test_issue_default_status_is_open(self):
        """Test issue status defaults to 'open'."""
        issue = ExtractedIssue(
            description="The deployment is failing",
            priority="high",
            source_quote="Our deployment keeps failing",
            confidence=0.9,
        )
        assert issue.status == "open"

    def test_issue_with_impact_and_owner(self):
        """Test issue with impact and owner fields."""
        issue = ExtractedIssue(
            description="CI pipeline is broken",
            priority="critical",
            impact="No deployments can happen",
            owner_name="DevOps Team Lead",
            source_quote="The CI pipeline has been broken since Monday",
            confidence=0.95,
        )
        assert issue.impact == "No deployments can happen"
        assert issue.owner_name == "DevOps Team Lead"


class TestExtractedIssues:
    """Tests for ExtractedIssues container."""

    def test_empty_issues(self):
        """Test container with no issues."""
        container = ExtractedIssues(items=[])
        assert len(container.items) == 0

    def test_issues_with_items(self):
        """Test container with issues."""
        issue = ExtractedIssue(
            description="Bug in login flow",
            priority="high",
            source_quote="Users can't log in",
            confidence=0.9,
        )
        container = ExtractedIssues(items=[issue])
        assert len(container.items) == 1
        assert container.items[0].description == "Bug in login flow"
