"""Tests for communication schemas."""

from datetime import datetime

from src.communication.schemas import (
    EscalationOutput,
    EscalationRequest,
    ExecStatusOutput,
    GeneratedArtifact,
    StatusData,
    TalkingPointsOutput,
    TeamStatusOutput,
)


class TestStatusData:
    """Tests for StatusData dataclass."""

    def test_minimal_creation(self):
        """StatusData can be created with required fields only."""
        now = datetime.now()
        data = StatusData(
            project_id="project-1",
            time_period=(now, now),
        )

        assert data.project_id == "project-1"
        assert data.time_period[0] == now
        assert data.completed_items == []
        assert data.new_items == []
        assert data.open_items == []
        assert data.item_velocity == 0
        assert data.overdue_count == 0

    def test_full_creation(self):
        """StatusData can be created with all fields."""
        now = datetime.now()
        data = StatusData(
            project_id="project-1",
            time_period=(now, now),
            completed_items=[{"id": "1", "description": "Done task"}],
            new_items=[{"id": "2", "description": "New task"}],
            open_items=[{"id": "3", "description": "Open task"}],
            decisions=[{"id": "4", "description": "Decision made"}],
            risks=[{"id": "5", "description": "Risk identified"}],
            issues=[{"id": "6", "description": "Issue found"}],
            blockers=[{"id": "7", "description": "Blocker"}],
            meetings_held=[{"id": "m1", "title": "Standup"}],
            item_velocity=5,
            overdue_count=2,
        )

        assert len(data.completed_items) == 1
        assert len(data.new_items) == 1
        assert len(data.risks) == 1
        assert data.item_velocity == 5
        assert data.overdue_count == 2


class TestExecStatusOutput:
    """Tests for ExecStatusOutput schema."""

    def test_valid_exec_status(self):
        """Valid exec status output parses correctly."""
        output = ExecStatusOutput(
            overall_rag="GREEN",
            scope_rag="GREEN",
            schedule_rag="AMBER",
            risk_rag="GREEN",
            summary="Project is on track with minor schedule risk.",
            key_progress=[
                "Backend team completed API integration",
                "Frontend team shipped new dashboard",
            ],
            key_decisions=["Decided to use PostgreSQL"],
            blockers=[
                {
                    "title": "AWS quota",
                    "problem": "Need higher EC2 quota",
                    "ask": "Approve quota increase request",
                }
            ],
            risks=["Third-party API may have rate limits"],
            next_period=[
                "Complete integration testing",
                "Begin UAT",
            ],
        )

        assert output.overall_rag == "GREEN"
        assert output.schedule_rag == "AMBER"
        assert len(output.key_progress) == 2
        assert len(output.blockers) == 1
        assert output.blockers[0]["ask"] == "Approve quota increase request"

    def test_exec_status_optional_fields(self):
        """Exec status works with minimal fields."""
        output = ExecStatusOutput(
            overall_rag="GREEN",
            scope_rag="GREEN",
            schedule_rag="GREEN",
            risk_rag="GREEN",
            summary="All on track.",
            key_progress=["Made progress"],
            next_period=["Continue work"],
        )

        assert output.key_decisions == []
        assert output.blockers == []
        assert output.risks == []


class TestTeamStatusOutput:
    """Tests for TeamStatusOutput schema."""

    def test_valid_team_status(self):
        """Valid team status output parses correctly."""
        output = TeamStatusOutput(
            summary="Productive week with 5 items completed.",
            completed_items=[
                {
                    "description": "Implement login",
                    "owner": "Alice",
                    "completed_date": "2024-01-15",
                }
            ],
            open_items=[
                {
                    "description": "Fix bug",
                    "owner": "Bob",
                    "due_date": "2024-01-20",
                    "status": "in_progress",
                }
            ],
            decisions=["Use JWT for auth"],
            risks=["API rate limits"],
            issues=["Build time too long"],
        )

        assert output.summary.startswith("Productive")
        assert len(output.completed_items) == 1
        assert output.completed_items[0]["owner"] == "Alice"
        assert len(output.open_items) == 1

    def test_team_status_empty_lists(self):
        """Team status works with empty lists."""
        output = TeamStatusOutput(
            summary="Quiet week.",
        )

        assert output.completed_items == []
        assert output.open_items == []


class TestEscalationOutput:
    """Tests for EscalationOutput schema."""

    def test_valid_escalation(self):
        """Valid escalation output parses correctly."""
        output = EscalationOutput(
            subject="Decision Needed: Database Migration Timeline",
            problem="Current database cannot handle projected load.",
            impact="System may become unavailable during peak hours.",
            deadline="2024-01-25",
            options=[
                {
                    "label": "A",
                    "description": "Emergency migration this weekend",
                    "pros": "Immediate resolution",
                    "cons": "Higher risk, weekend work",
                },
                {
                    "label": "B",
                    "description": "Planned migration next month",
                    "pros": "Lower risk, proper planning",
                    "cons": "Performance issues for 4 weeks",
                },
            ],
            recommendation="Option B",
            context_summary="Issue identified during load testing.",
        )

        assert "Database" in output.subject
        assert len(output.options) == 2
        assert output.recommendation == "Option B"
        assert output.deadline == "2024-01-25"

    def test_escalation_without_recommendation(self):
        """Escalation works without recommendation."""
        output = EscalationOutput(
            subject="Decision Needed",
            problem="Need decision.",
            impact="Impact statement.",
            deadline="2024-01-25",
            options=[{"label": "A", "description": "Option A"}],
        )

        assert output.recommendation is None
        assert output.context_summary is None


class TestTalkingPointsOutput:
    """Tests for TalkingPointsOutput schema."""

    def test_valid_talking_points(self):
        """Valid talking points output parses correctly."""
        output = TalkingPointsOutput(
            narrative_summary="Project is progressing well with strong velocity.",
            key_points=[
                "Completed major milestone ahead of schedule",
                "Team ramped up successfully",
                "No critical blockers",
            ],
            anticipated_qa=[
                {
                    "category": "risk",
                    "question": "What if vendor delays delivery?",
                    "answer": "We have backup vendor identified.",
                },
                {
                    "category": "resource",
                    "question": "Do you need more headcount?",
                    "answer": "Current team is sufficient.",
                },
            ],
        )

        assert "progressing" in output.narrative_summary
        assert len(output.key_points) == 3
        assert len(output.anticipated_qa) == 2

        # Verify Q&A categories
        categories = {qa["category"] for qa in output.anticipated_qa}
        assert "risk" in categories
        assert "resource" in categories


class TestGeneratedArtifact:
    """Tests for GeneratedArtifact schema."""

    def test_valid_artifact(self):
        """Valid artifact parses correctly."""
        artifact = GeneratedArtifact(
            artifact_type="exec_status",
            markdown="# Status Update\n\nContent here",
            plain_text="Status Update\n\nContent here",
            metadata={"rag_overall": "GREEN", "item_count": 10},
        )

        assert artifact.artifact_type == "exec_status"
        assert artifact.markdown.startswith("#")
        assert "GREEN" in str(artifact.metadata)

    def test_artifact_empty_metadata(self):
        """Artifact works with empty metadata."""
        artifact = GeneratedArtifact(
            artifact_type="team_status",
            markdown="Content",
            plain_text="Content",
        )

        assert artifact.metadata == {}


class TestEscalationRequest:
    """Tests for EscalationRequest schema."""

    def test_valid_request(self):
        """Valid escalation request parses correctly."""
        request = EscalationRequest(
            problem_description="Database is running out of space.",
            timeline_impact="May delay launch by 2 weeks",
            resource_impact="Need additional budget for storage",
            business_impact="Customer data at risk",
            history_context="Identified during routine monitoring",
            options=[
                {"description": "Add more storage", "pros": "Quick", "cons": "Costly"},
                {
                    "description": "Archive old data",
                    "pros": "Free",
                    "cons": "Time consuming",
                },
            ],
            decision_deadline=datetime(2024, 1, 25),
            recipient="vp-engineering@company.com",
        )

        assert "Database" in request.problem_description
        assert len(request.options) == 2
        assert request.recipient == "vp-engineering@company.com"

    def test_minimal_request(self):
        """Request works with minimal fields."""
        request = EscalationRequest(
            problem_description="Problem statement",
            options=[{"description": "Only option"}],
            decision_deadline=datetime(2024, 1, 25),
        )

        assert request.timeline_impact is None
        assert request.history_context is None
        assert request.recipient is None
