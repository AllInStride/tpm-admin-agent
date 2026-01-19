"""Tests for the output renderer and schemas."""

from datetime import date, datetime
from uuid import uuid4

import pytest
from jinja2 import TemplateNotFound

from src.models.action_item import ActionItem
from src.models.decision import Decision
from src.models.issue import Issue, IssuePriority, IssueStatus
from src.models.meeting import Meeting
from src.models.participant import Participant, ParticipantRole
from src.models.risk import Risk, RiskSeverity
from src.output.renderer import MinutesRenderer
from src.output.schemas import (
    ActionItemData,
    DecisionItem,
    IssueItem,
    MinutesContext,
    RiskItem,
)


@pytest.fixture
def meeting_id():
    """Generate a meeting ID for tests."""
    return uuid4()


@pytest.fixture
def empty_context(meeting_id):
    """Create a MinutesContext with empty RAID lists."""
    return MinutesContext(
        meeting_id=meeting_id,
        meeting_title="Empty Test Meeting",
        meeting_date=datetime(2026, 1, 18, 10, 0),
        duration_minutes=30,
        attendees=["Alice (PM)", "Bob (Dev)"],
        decisions=[],
        action_items=[],
        risks=[],
        issues=[],
        next_steps=[],
    )


@pytest.fixture
def full_context(meeting_id):
    """Create a MinutesContext with one of each RAID type."""
    return MinutesContext(
        meeting_id=meeting_id,
        meeting_title="Full Test Meeting",
        meeting_date=datetime(2026, 1, 18, 14, 0),
        duration_minutes=60,
        attendees=["Alice (PM)", "Bob (Dev)", "Charlie (QA)"],
        decisions=[
            DecisionItem(
                description="Use PostgreSQL for production",
                rationale="Better performance than SQLite",
                alternatives=["MySQL", "MongoDB"],
                confidence=0.9,
            )
        ],
        action_items=[
            ActionItemData(
                description="Set up database migration",
                assignee_name="Bob",
                due_date="2026-01-25",
                confidence=0.85,
            )
        ],
        risks=[
            RiskItem(
                description="Migration might cause downtime",
                severity="HIGH",
                owner_name="Alice",
                mitigation="Schedule during maintenance window",
                confidence=0.8,
            )
        ],
        issues=[
            IssueItem(
                description="Current database is slow",
                priority="HIGH",
                status="Open",
                owner_name="Bob",
                impact="Users experiencing delays",
                confidence=0.95,
            )
        ],
        next_steps=["Set up database migration"],
    )


@pytest.fixture
def renderer():
    """Create a MinutesRenderer."""
    return MinutesRenderer()


class TestRenderEmptyMeeting:
    """Test rendering with empty RAID lists."""

    def test_markdown_renders_without_error(self, renderer, empty_context):
        """Empty context should render valid Markdown."""
        result = renderer.render(empty_context)
        assert result.markdown is not None
        assert len(result.markdown) > 0

    def test_html_renders_without_error(self, renderer, empty_context):
        """Empty context should render valid HTML."""
        result = renderer.render(empty_context)
        assert result.html is not None
        assert len(result.html) > 0

    def test_shows_no_decisions_message(self, renderer, empty_context):
        """Empty decisions should show placeholder message."""
        result = renderer.render(empty_context)
        assert "No decisions recorded" in result.markdown
        assert "No decisions recorded" in result.html

    def test_shows_no_action_items_message(self, renderer, empty_context):
        """Empty action items should show placeholder message."""
        result = renderer.render(empty_context)
        assert "No action items recorded" in result.markdown
        assert "No action items recorded" in result.html


class TestRenderWithRaidItems:
    """Test rendering with RAID items."""

    def test_all_items_appear_in_markdown(self, renderer, full_context):
        """All RAID items should appear in Markdown output."""
        result = renderer.render(full_context)
        assert "Use PostgreSQL for production" in result.markdown
        assert "Set up database migration" in result.markdown
        assert "Migration might cause downtime" in result.markdown
        assert "Current database is slow" in result.markdown

    def test_all_items_appear_in_html(self, renderer, full_context):
        """All RAID items should appear in HTML output."""
        result = renderer.render(full_context)
        assert "Use PostgreSQL for production" in result.html
        assert "Set up database migration" in result.html
        assert "Migration might cause downtime" in result.html
        assert "Current database is slow" in result.html

    def test_dari_section_order_markdown(self, renderer, full_context):
        """Sections should appear in D-A-R-I order in Markdown."""
        result = renderer.render(full_context)
        md = result.markdown

        decisions_pos = md.find("## Decisions")
        actions_pos = md.find("## Action Items")
        risks_pos = md.find("## Risks")
        issues_pos = md.find("## Issues")

        assert decisions_pos < actions_pos < risks_pos < issues_pos

    def test_dari_section_order_html(self, renderer, full_context):
        """Sections should appear in D-A-R-I order in HTML."""
        result = renderer.render(full_context)
        html = result.html

        decisions_pos = html.find(">Decisions</h2>")
        actions_pos = html.find(">Action Items</h2>")
        risks_pos = html.find(">Risks</h2>")
        issues_pos = html.find(">Issues</h2>")

        assert decisions_pos < actions_pos < risks_pos < issues_pos


class TestLowConfidenceMarking:
    """Test low confidence item marking."""

    def test_low_confidence_action_item_marked(self, renderer, meeting_id):
        """Action item with confidence < 0.7 should be marked."""
        context = MinutesContext(
            meeting_id=meeting_id,
            meeting_title="Test",
            meeting_date=datetime.now(),
            attendees=[],
            action_items=[
                ActionItemData(
                    description="Low confidence action",
                    confidence=0.6,
                )
            ],
        )
        result = renderer.render(context)
        # Markdown uses [?] for action items
        assert "[?]" in result.markdown
        assert "[?]" in result.html or "[LOW CONFIDENCE]" in result.html

    def test_high_confidence_action_item_not_marked(self, renderer, meeting_id):
        """Action item with confidence >= 0.7 should not be marked."""
        context = MinutesContext(
            meeting_id=meeting_id,
            meeting_title="Test",
            meeting_date=datetime.now(),
            attendees=[],
            action_items=[
                ActionItemData(
                    description="High confidence action",
                    confidence=0.8,
                )
            ],
        )
        result = renderer.render(context)
        # Should not have low confidence marker near the action
        action_line = [
            ln for ln in result.markdown.split("\n") if "High confidence action" in ln
        ][0]
        assert "[?]" not in action_line
        assert "[LOW CONFIDENCE]" not in action_line

    def test_low_confidence_decision_marked(self, renderer, meeting_id):
        """Decision with confidence < 0.7 should be marked."""
        context = MinutesContext(
            meeting_id=meeting_id,
            meeting_title="Test",
            meeting_date=datetime.now(),
            attendees=[],
            decisions=[
                DecisionItem(
                    description="Low confidence decision",
                    confidence=0.5,
                )
            ],
        )
        result = renderer.render(context)
        assert "[LOW CONFIDENCE]" in result.markdown
        assert "[LOW CONFIDENCE]" in result.html


class TestMissingDueDateShowsTbd:
    """Test TBD placeholder for missing due dates."""

    def test_missing_due_date_shows_tbd(self, renderer, meeting_id):
        """Action item without due date should show TBD."""
        context = MinutesContext(
            meeting_id=meeting_id,
            meeting_title="Test",
            meeting_date=datetime.now(),
            attendees=[],
            action_items=[
                ActionItemData(
                    description="Action without due date",
                    due_date=None,
                    confidence=0.9,
                )
            ],
        )
        result = renderer.render(context)
        assert "TBD" in result.markdown
        assert "TBD" in result.html


class TestMissingAssigneeShowsUnassigned:
    """Test Unassigned placeholder for missing assignees."""

    def test_missing_assignee_shows_unassigned(self, renderer, meeting_id):
        """Action item without assignee should show Unassigned."""
        context = MinutesContext(
            meeting_id=meeting_id,
            meeting_title="Test",
            meeting_date=datetime.now(),
            attendees=[],
            action_items=[
                ActionItemData(
                    description="Action without assignee",
                    assignee_name=None,
                    confidence=0.9,
                )
            ],
        )
        result = renderer.render(context)
        assert "Unassigned" in result.markdown
        assert "Unassigned" in result.html


class TestNextStepsGeneration:
    """Test next steps section."""

    def test_next_steps_limited_to_five(self, renderer, meeting_id):
        """Only top 5 action items should appear in next steps."""
        context = MinutesContext(
            meeting_id=meeting_id,
            meeting_title="Test",
            meeting_date=datetime.now(),
            attendees=[],
            action_items=[
                ActionItemData(description=f"Action {i}", confidence=0.9)
                for i in range(7)
            ],
            next_steps=[f"Action {i}" for i in range(5)],  # Only first 5
        )
        result = renderer.render(context)
        next_steps_section = result.markdown.split("## Next Steps")[1]

        # Should have Action 0-4, not Action 5-6
        for i in range(5):
            assert f"Action {i}" in next_steps_section
        assert "Action 5" not in next_steps_section
        assert "Action 6" not in next_steps_section


class TestFromMeetingData:
    """Test MinutesContext.from_meeting_data conversion."""

    def test_converts_meeting_data(self):
        """Should convert domain models to MinutesContext."""
        meeting = Meeting(
            title="Sprint Planning",
            date=datetime(2026, 1, 18, 10, 0),
            duration_minutes=60,
            participants=[
                Participant(name="Alice", role=ParticipantRole.HOST),
                Participant(name="Bob", role=ParticipantRole.ATTENDEE),
            ],
        )
        decisions = [
            Decision(
                meeting_id=meeting.id,
                description="Use Postgres",
                rationale="Better performance",
                alternatives=["MySQL"],
                confidence=0.9,
            )
        ]
        action_items = [
            ActionItem(
                meeting_id=meeting.id,
                description="Set up DB",
                assignee_name="Bob",
                due_date=date(2026, 1, 25),
                confidence=0.85,
            )
        ]
        risks = [
            Risk(
                meeting_id=meeting.id,
                description="Migration risk",
                severity=RiskSeverity.HIGH,
                owner_name="Alice",
                mitigation="Test first",
                confidence=0.8,
            )
        ]
        issues = [
            Issue(
                meeting_id=meeting.id,
                description="DB is slow",
                priority=IssuePriority.HIGH,
                status=IssueStatus.OPEN,
                owner_name="Bob",
                impact="User delays",
                confidence=0.95,
            )
        ]

        ctx = MinutesContext.from_meeting_data(
            meeting=meeting,
            decisions=decisions,
            action_items=action_items,
            risks=risks,
            issues=issues,
        )

        assert ctx.meeting_title == "Sprint Planning"
        assert ctx.duration_minutes == 60
        assert len(ctx.attendees) == 2
        assert "Alice (Host)" in ctx.attendees
        assert "Bob (Attendee)" in ctx.attendees
        assert len(ctx.decisions) == 1
        assert len(ctx.action_items) == 1
        assert len(ctx.risks) == 1
        assert len(ctx.issues) == 1

    def test_next_steps_auto_populated(self):
        """Next steps should be auto-populated from action items."""
        meeting = Meeting(
            title="Test",
            date=datetime.now(),
        )
        action_items = [
            ActionItem(
                meeting_id=meeting.id,
                description=f"Task {i}",
                confidence=0.9,
            )
            for i in range(7)
        ]

        ctx = MinutesContext.from_meeting_data(
            meeting=meeting,
            decisions=[],
            action_items=action_items,
            risks=[],
            issues=[],
        )

        # Should have exactly 5 next steps
        assert len(ctx.next_steps) == 5
        assert ctx.next_steps[0] == "Task 0"
        assert ctx.next_steps[4] == "Task 4"

    def test_formats_due_date(self):
        """Due dates should be formatted as YYYY-MM-DD strings."""
        meeting = Meeting(title="Test", date=datetime.now())
        action_items = [
            ActionItem(
                meeting_id=meeting.id,
                description="Task with date",
                due_date=date(2026, 1, 25),
                confidence=0.9,
            )
        ]

        ctx = MinutesContext.from_meeting_data(
            meeting=meeting,
            decisions=[],
            action_items=action_items,
            risks=[],
            issues=[],
        )

        assert ctx.action_items[0].due_date == "2026-01-25"


class TestHtmlHasStyling:
    """Test HTML output has proper styling."""

    def test_has_css_styles(self, renderer, full_context):
        """HTML output should include CSS styles."""
        result = renderer.render(full_context)
        assert "<style>" in result.html
        assert "font-family:" in result.html

    def test_has_table_styling(self, renderer, full_context):
        """HTML should have table styling for action items."""
        result = renderer.render(full_context)
        assert "<table>" in result.html
        assert "border-collapse:" in result.html


class TestCustomTemplateName:
    """Test custom template loading."""

    def test_loads_template_by_name(self, renderer, empty_context):
        """Should be able to specify template name."""
        result = renderer.render(empty_context, template_name="default_minutes")
        assert result.template_used == "default_minutes"

    def test_raises_for_nonexistent_template(self, renderer, empty_context):
        """Should raise TemplateNotFound for missing templates."""
        with pytest.raises(TemplateNotFound):
            renderer.render(empty_context, template_name="nonexistent_template")


class TestAttendeesFormat:
    """Test attendees formatting."""

    def test_attendees_comma_separated(self, renderer, empty_context):
        """Attendees should be rendered as comma-separated list."""
        result = renderer.render(empty_context)
        assert "Alice (PM), Bob (Dev)" in result.markdown
        assert "Alice (PM), Bob (Dev)" in result.html

    def test_empty_attendees_shows_none(self, renderer, meeting_id):
        """Empty attendees should show 'None recorded'."""
        context = MinutesContext(
            meeting_id=meeting_id,
            meeting_title="Test",
            meeting_date=datetime.now(),
            attendees=[],
        )
        result = renderer.render(context)
        assert "None recorded" in result.markdown
        assert "None recorded" in result.html
