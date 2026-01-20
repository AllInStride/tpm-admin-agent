"""Tests for TalkingPointsGenerator."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.communication.generators.talking_points import TalkingPointsGenerator
from src.communication.schemas import (
    StatusData,
    TalkingPointsOutput,
)
from src.services.llm_client import LLMClient


@pytest.fixture
def mock_llm_client() -> LLMClient:
    """Create mock LLM client."""
    client = LLMClient(client=None)
    client.extract = AsyncMock()
    return client


@pytest.fixture
def sample_status_data() -> StatusData:
    """Create sample StatusData for testing."""
    return StatusData(
        project_id="ProjectX",
        time_period=(datetime(2024, 1, 1), datetime(2024, 1, 15)),
        completed_items=[
            {"description": "Completed API integration", "owner": "Backend Team"},
            {"description": "Shipped dashboard v2", "owner": "Frontend Team"},
            {"description": "Set up CI/CD pipeline", "owner": "DevOps"},
        ],
        new_items=[
            {"description": "New feature request", "owner": "PM"},
        ],
        open_items=[
            {
                "description": "Integration testing",
                "owner": "QA",
                "due_date": "2024-01-20",
            },
        ],
        decisions=[
            {"description": "Use JWT for authentication"},
        ],
        risks=[
            {"description": "Vendor API delay risk"},
        ],
        issues=[
            {"description": "Build time degraded"},
        ],
        blockers=[
            {"description": "Waiting on vendor credentials"},
        ],
        meetings_held=[
            {"id": "m1", "title": "Sprint Planning"},
            {"id": "m2", "title": "Architecture Review"},
        ],
        item_velocity=2,
        overdue_count=1,
    )


@pytest.fixture
def valid_llm_output() -> TalkingPointsOutput:
    """Create valid LLM output with all required categories."""
    return TalkingPointsOutput(
        narrative_summary=(
            "ProjectX is progressing well with strong velocity. "
            "The team completed key milestones ahead of schedule."
        ),
        key_points=[
            "API integration completed ahead of schedule",
            "Dashboard v2 shipped with positive feedback",
            "CI/CD pipeline now operational",
            "One vendor dependency blocking next phase",
            "Team morale high after successful sprint",
        ],
        anticipated_qa=[
            {
                "category": "risk",
                "question": "What if the vendor delays further?",
                "answer": "We have identified a backup vendor and can pivot if needed.",
            },
            {
                "category": "resource",
                "question": "Do you need additional headcount?",
                "answer": (
                    "Current team is sufficient, "
                    "but we may need QA support next quarter."
                ),
            },
            {
                "category": "other",
                "question": "When is the launch date?",
                "answer": "Target is March 15, on track per current velocity.",
            },
        ],
    )


class TestTalkingPointsGenerator:
    """Tests for TalkingPointsGenerator."""

    @pytest.mark.asyncio
    async def test_generate_produces_artifact(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        valid_llm_output: TalkingPointsOutput,
    ):
        """Generator produces valid artifact with expected fields."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = TalkingPointsGenerator(mock_llm_client)
        artifact = await generator.generate(sample_status_data)

        assert artifact.artifact_type == "talking_points"
        assert artifact.markdown
        assert artifact.plain_text
        assert artifact.metadata["point_count"] == 5
        assert artifact.metadata["qa_count"] == 3

    @pytest.mark.asyncio
    async def test_generate_key_points_in_output(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        valid_llm_output: TalkingPointsOutput,
    ):
        """Key talking points appear in output."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = TalkingPointsGenerator(mock_llm_client)
        artifact = await generator.generate(sample_status_data)

        assert "API integration completed" in artifact.markdown
        assert "CI/CD pipeline" in artifact.markdown

    @pytest.mark.asyncio
    async def test_generate_qa_section_exists(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        valid_llm_output: TalkingPointsOutput,
    ):
        """Q&A section exists in output."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = TalkingPointsGenerator(mock_llm_client)
        artifact = await generator.generate(sample_status_data)

        assert "Q&A" in artifact.markdown
        assert "What if the vendor delays" in artifact.markdown
        assert "backup vendor" in artifact.markdown

    @pytest.mark.asyncio
    async def test_generate_qa_has_risk_category(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        valid_llm_output: TalkingPointsOutput,
    ):
        """Q&A includes risk category questions."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = TalkingPointsGenerator(mock_llm_client)
        artifact = await generator.generate(sample_status_data)

        assert "Risk" in artifact.markdown
        assert "vendor delays" in artifact.markdown

    @pytest.mark.asyncio
    async def test_generate_qa_has_resource_category(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        valid_llm_output: TalkingPointsOutput,
    ):
        """Q&A includes resource category questions."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = TalkingPointsGenerator(mock_llm_client)
        artifact = await generator.generate(sample_status_data)

        assert "Resource" in artifact.markdown
        assert "headcount" in artifact.markdown

    @pytest.mark.asyncio
    async def test_generate_accepts_meeting_type(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        valid_llm_output: TalkingPointsOutput,
    ):
        """Generator accepts custom meeting type."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = TalkingPointsGenerator(mock_llm_client)
        artifact = await generator.generate(
            sample_status_data, meeting_type="board_meeting"
        )

        assert artifact.artifact_type == "talking_points"
        # Template renders meeting type
        assert "board_meeting" in artifact.markdown

    @pytest.mark.asyncio
    async def test_generate_warns_on_missing_risk_category(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        caplog,
    ):
        """Warning logged when risk category missing from Q&A."""
        output_missing_risk = TalkingPointsOutput(
            narrative_summary="Summary",
            key_points=["Point 1"],
            anticipated_qa=[
                {
                    "category": "resource",
                    "question": "Question?",
                    "answer": "Answer.",
                },
            ],
        )
        mock_llm_client.extract.return_value = output_missing_risk

        generator = TalkingPointsGenerator(mock_llm_client)
        await generator.generate(sample_status_data)

        assert "missing categories" in caplog.text
        assert "risk" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_warns_on_missing_resource_category(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
        caplog,
    ):
        """Warning logged when resource category missing from Q&A."""
        output_missing_resource = TalkingPointsOutput(
            narrative_summary="Summary",
            key_points=["Point 1"],
            anticipated_qa=[
                {
                    "category": "risk",
                    "question": "Question?",
                    "answer": "Answer.",
                },
            ],
        )
        mock_llm_client.extract.return_value = output_missing_resource

        generator = TalkingPointsGenerator(mock_llm_client)
        await generator.generate(sample_status_data)

        assert "missing categories" in caplog.text
        assert "resource" in caplog.text


class TestFormatMetrics:
    """Tests for _format_metrics helper."""

    def test_format_metrics_includes_all_fields(
        self,
        mock_llm_client: LLMClient,
        sample_status_data: StatusData,
    ):
        """Metrics formatting includes all required fields."""
        generator = TalkingPointsGenerator(mock_llm_client)

        result = generator._format_metrics(sample_status_data)

        assert "Items completed: 3" in result
        assert "Items opened: 1" in result
        assert "Net velocity: +2" in result
        assert "Currently open: 1" in result
        assert "Overdue items: 1" in result
        assert "Active risks: 1" in result
        assert "Open issues: 1" in result
        assert "Blockers: 1" in result
        assert "Meetings held: 2" in result

    def test_format_metrics_negative_velocity(self, mock_llm_client: LLMClient):
        """Metrics shows negative velocity correctly."""
        data = StatusData(
            project_id="TestProject",
            time_period=(datetime(2024, 1, 1), datetime(2024, 1, 15)),
            item_velocity=-3,
        )

        generator = TalkingPointsGenerator(mock_llm_client)
        result = generator._format_metrics(data)

        assert "Net velocity: -3" in result
