"""Tests for domain models."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.models.action_item import ActionItem, ActionItemStatus
from src.models.base import BaseEntity
from src.models.decision import Decision
from src.models.issue import Issue, IssuePriority, IssueStatus
from src.models.meeting import Meeting, Utterance
from src.models.participant import Participant, ParticipantRole
from src.models.risk import Risk, RiskSeverity


class TestBaseEntity:
    """Tests for BaseEntity."""

    def test_auto_generates_uuid(self):
        """BaseEntity should auto-generate a UUID."""

        class TestEntity(BaseEntity):
            pass

        entity = TestEntity()
        assert isinstance(entity.id, UUID)

    def test_auto_generates_timestamps(self):
        """BaseEntity should auto-generate created_at and updated_at."""

        class TestEntity(BaseEntity):
            pass

        before = datetime.now(UTC)
        entity = TestEntity()
        after = datetime.now(UTC)

        assert before <= entity.created_at <= after
        assert before <= entity.updated_at <= after

    def test_touch_updates_timestamp(self):
        """touch() should update the updated_at timestamp."""

        class TestEntity(BaseEntity):
            pass

        entity = TestEntity()
        original_updated = entity.updated_at

        # Small delay to ensure timestamp difference
        entity.touch()

        assert entity.updated_at >= original_updated


class TestParticipant:
    """Tests for Participant model."""

    def test_creates_with_required_fields(self):
        """Participant should create with just a name."""
        participant = Participant(name="John Doe")
        assert participant.name == "John Doe"
        assert participant.role == ParticipantRole.ATTENDEE
        assert participant.confidence == 1.0

    def test_strips_whitespace_from_name(self):
        """Name should have whitespace stripped."""
        participant = Participant(name="  John Doe  ")
        assert participant.name == "John Doe"

    def test_rejects_empty_name(self):
        """Empty or whitespace-only name should fail validation."""
        with pytest.raises(ValidationError):
            Participant(name="")

        with pytest.raises(ValidationError):
            Participant(name="   ")

    def test_accepts_valid_email(self):
        """Valid email should be accepted."""
        participant = Participant(name="John", email="john@example.com")
        assert participant.email == "john@example.com"

    def test_rejects_invalid_email(self):
        """Invalid email should fail validation."""
        with pytest.raises(ValidationError):
            Participant(name="John", email="not-an-email")

    def test_all_roles_valid(self):
        """All role enum values should work."""
        for role in ParticipantRole:
            participant = Participant(name="Test", role=role)
            assert participant.role == role


class TestMeeting:
    """Tests for Meeting model."""

    def test_creates_with_required_fields(self):
        """Meeting should create with title and date."""
        meeting = Meeting(title="Weekly Standup", date=datetime.now(UTC))
        assert meeting.title == "Weekly Standup"
        assert meeting.participants == []
        assert meeting.utterances == []

    def test_rejects_empty_title(self):
        """Empty title should fail validation."""
        with pytest.raises(ValidationError):
            Meeting(title="", date=datetime.now(UTC))

    def test_speaker_names_property(self):
        """speaker_names should return unique speakers from utterances."""
        meeting = Meeting(
            title="Test",
            date=datetime.now(UTC),
            utterances=[
                Utterance(speaker="Alice", text="Hello", start_time=0, end_time=1),
                Utterance(speaker="Bob", text="Hi", start_time=1, end_time=2),
                Utterance(
                    speaker="Alice", text="How are you?", start_time=2, end_time=3
                ),
            ],
        )
        assert set(meeting.speaker_names) == {"Alice", "Bob"}

    def test_participant_count_property(self):
        """participant_count should return number of participants."""
        meeting = Meeting(
            title="Test",
            date=datetime.now(UTC),
            participants=[
                Participant(name="Alice"),
                Participant(name="Bob"),
            ],
        )
        assert meeting.participant_count == 2

    def test_has_transcript_property(self):
        """has_transcript should return True if utterances exist."""
        empty_meeting = Meeting(title="Test", date=datetime.now(UTC))
        assert empty_meeting.has_transcript is False

        meeting_with_transcript = Meeting(
            title="Test",
            date=datetime.now(UTC),
            utterances=[
                Utterance(speaker="Alice", text="Hello", start_time=0, end_time=1),
            ],
        )
        assert meeting_with_transcript.has_transcript is True


class TestActionItem:
    """Tests for ActionItem model."""

    def test_creates_with_required_fields(self):
        """ActionItem should create with meeting_id and description."""
        meeting_id = uuid4()
        action = ActionItem(meeting_id=meeting_id, description="Review the PR")
        assert action.meeting_id == meeting_id
        assert action.description == "Review the PR"
        assert action.status == ActionItemStatus.PENDING

    def test_rejects_empty_description(self):
        """Empty description should fail validation."""
        with pytest.raises(ValidationError):
            ActionItem(meeting_id=uuid4(), description="")

    def test_is_assigned_property(self):
        """is_assigned should return True if assignee exists."""
        action_no_assignee = ActionItem(meeting_id=uuid4(), description="Task")
        assert action_no_assignee.is_assigned is False

        action_with_name = ActionItem(
            meeting_id=uuid4(), description="Task", assignee_name="John"
        )
        assert action_with_name.is_assigned is True

        action_with_id = ActionItem(
            meeting_id=uuid4(), description="Task", assignee_id=uuid4()
        )
        assert action_with_id.is_assigned is True

    def test_is_overdue_property(self):
        """is_overdue should return True for past due items."""
        # No due date - not overdue
        action_no_date = ActionItem(meeting_id=uuid4(), description="Task")
        assert action_no_date.is_overdue is False

        # Future due date - not overdue
        action_future = ActionItem(
            meeting_id=uuid4(),
            description="Task",
            due_date=date.today() + timedelta(days=7),
        )
        assert action_future.is_overdue is False

        # Past due date - overdue
        action_past = ActionItem(
            meeting_id=uuid4(),
            description="Task",
            due_date=date.today() - timedelta(days=1),
        )
        assert action_past.is_overdue is True

        # Past due but completed - not overdue
        action_completed = ActionItem(
            meeting_id=uuid4(),
            description="Task",
            due_date=date.today() - timedelta(days=1),
            status=ActionItemStatus.COMPLETED,
        )
        assert action_completed.is_overdue is False

    def test_all_statuses_valid(self):
        """All status enum values should work."""
        for status in ActionItemStatus:
            action = ActionItem(meeting_id=uuid4(), description="Task", status=status)
            assert action.status == status


class TestDecision:
    """Tests for Decision model."""

    def test_creates_with_required_fields(self):
        """Decision should create with meeting_id and description."""
        meeting_id = uuid4()
        decision = Decision(meeting_id=meeting_id, description="Use Python")
        assert decision.meeting_id == meeting_id
        assert decision.description == "Use Python"

    def test_has_rationale_property(self):
        """has_rationale should return True if rationale exists and not empty."""
        decision_no_rationale = Decision(meeting_id=uuid4(), description="Decision")
        assert decision_no_rationale.has_rationale is False

        decision_empty_rationale = Decision(
            meeting_id=uuid4(), description="Decision", rationale="   "
        )
        assert decision_empty_rationale.has_rationale is False

        decision_with_rationale = Decision(
            meeting_id=uuid4(), description="Decision", rationale="Because it's better"
        )
        assert decision_with_rationale.has_rationale is True

    def test_alternatives_count_property(self):
        """alternatives_count should return number of alternatives."""
        decision_no_alts = Decision(meeting_id=uuid4(), description="Decision")
        assert decision_no_alts.alternatives_count == 0

        decision_with_alts = Decision(
            meeting_id=uuid4(),
            description="Decision",
            alternatives=["Option A", "Option B", "Option C"],
        )
        assert decision_with_alts.alternatives_count == 3


class TestRisk:
    """Tests for Risk model."""

    def test_creates_with_required_fields(self):
        """Risk should create with meeting_id and description."""
        meeting_id = uuid4()
        risk = Risk(meeting_id=meeting_id, description="Vendor might be late")
        assert risk.meeting_id == meeting_id
        assert risk.description == "Vendor might be late"
        assert risk.severity == RiskSeverity.MEDIUM

    def test_is_high_severity_property(self):
        """is_high_severity should return True for HIGH and CRITICAL."""
        risk_low = Risk(
            meeting_id=uuid4(), description="Risk", severity=RiskSeverity.LOW
        )
        assert risk_low.is_high_severity is False

        risk_medium = Risk(
            meeting_id=uuid4(), description="Risk", severity=RiskSeverity.MEDIUM
        )
        assert risk_medium.is_high_severity is False

        risk_high = Risk(
            meeting_id=uuid4(), description="Risk", severity=RiskSeverity.HIGH
        )
        assert risk_high.is_high_severity is True

        risk_critical = Risk(
            meeting_id=uuid4(), description="Risk", severity=RiskSeverity.CRITICAL
        )
        assert risk_critical.is_high_severity is True

    def test_has_mitigation_property(self):
        """has_mitigation should return True if mitigation exists and not empty."""
        risk_no_mitigation = Risk(meeting_id=uuid4(), description="Risk")
        assert risk_no_mitigation.has_mitigation is False

        risk_empty_mitigation = Risk(
            meeting_id=uuid4(), description="Risk", mitigation="   "
        )
        assert risk_empty_mitigation.has_mitigation is False

        risk_with_mitigation = Risk(
            meeting_id=uuid4(), description="Risk", mitigation="Add buffer time"
        )
        assert risk_with_mitigation.has_mitigation is True

    def test_all_severities_valid(self):
        """All severity enum values should work."""
        for severity in RiskSeverity:
            risk = Risk(meeting_id=uuid4(), description="Risk", severity=severity)
            assert risk.severity == severity


class TestIssue:
    """Tests for Issue model."""

    def test_creates_with_required_fields(self):
        """Issue should create with meeting_id and description."""
        meeting_id = uuid4()
        issue = Issue(meeting_id=meeting_id, description="Build is broken")
        assert issue.meeting_id == meeting_id
        assert issue.description == "Build is broken"
        assert issue.status == IssueStatus.OPEN
        assert issue.priority == IssuePriority.MEDIUM

    def test_rejects_empty_description(self):
        """Empty description should fail validation."""
        with pytest.raises(ValidationError):
            Issue(meeting_id=uuid4(), description="")

    def test_is_blocking_property(self):
        """is_blocking should return True only for BLOCKED status."""
        issue_open = Issue(
            meeting_id=uuid4(), description="Issue", status=IssueStatus.OPEN
        )
        assert issue_open.is_blocking is False

        issue_blocked = Issue(
            meeting_id=uuid4(), description="Issue", status=IssueStatus.BLOCKED
        )
        assert issue_blocked.is_blocking is True

    def test_is_high_priority_property(self):
        """is_high_priority should return True for HIGH and CRITICAL."""
        issue_low = Issue(
            meeting_id=uuid4(), description="Issue", priority=IssuePriority.LOW
        )
        assert issue_low.is_high_priority is False

        issue_medium = Issue(
            meeting_id=uuid4(), description="Issue", priority=IssuePriority.MEDIUM
        )
        assert issue_medium.is_high_priority is False

        issue_high = Issue(
            meeting_id=uuid4(), description="Issue", priority=IssuePriority.HIGH
        )
        assert issue_high.is_high_priority is True

        issue_critical = Issue(
            meeting_id=uuid4(), description="Issue", priority=IssuePriority.CRITICAL
        )
        assert issue_critical.is_high_priority is True

    def test_is_resolved_property(self):
        """is_resolved should return True for RESOLVED and CLOSED."""
        issue_open = Issue(
            meeting_id=uuid4(), description="Issue", status=IssueStatus.OPEN
        )
        assert issue_open.is_resolved is False

        issue_in_progress = Issue(
            meeting_id=uuid4(), description="Issue", status=IssueStatus.IN_PROGRESS
        )
        assert issue_in_progress.is_resolved is False

        issue_resolved = Issue(
            meeting_id=uuid4(), description="Issue", status=IssueStatus.RESOLVED
        )
        assert issue_resolved.is_resolved is True

        issue_closed = Issue(
            meeting_id=uuid4(), description="Issue", status=IssueStatus.CLOSED
        )
        assert issue_closed.is_resolved is True

    def test_all_statuses_valid(self):
        """All status enum values should work."""
        for status in IssueStatus:
            issue = Issue(meeting_id=uuid4(), description="Issue", status=status)
            assert issue.status == status

    def test_all_priorities_valid(self):
        """All priority enum values should work."""
        for priority in IssuePriority:
            issue = Issue(meeting_id=uuid4(), description="Issue", priority=priority)
            assert issue.priority == priority


class TestConfidenceScores:
    """Tests for confidence score validation across models."""

    def test_confidence_must_be_between_0_and_1(self):
        """Confidence scores must be in range [0, 1]."""
        # Valid values
        ActionItem(meeting_id=uuid4(), description="Task", confidence=0.0)
        ActionItem(meeting_id=uuid4(), description="Task", confidence=0.5)
        ActionItem(meeting_id=uuid4(), description="Task", confidence=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            ActionItem(meeting_id=uuid4(), description="Task", confidence=-0.1)

        with pytest.raises(ValidationError):
            ActionItem(meeting_id=uuid4(), description="Task", confidence=1.1)
