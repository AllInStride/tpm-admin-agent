"""Tests for TeamStatusGenerator (COM-02).

Verifies that team status generation:
- Uses LLM client for structured extraction
- Includes completed items section first
- Provides full action item list with owners and dates
- Renders both markdown and plain text
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.communication.generators.team_status import TeamStatusGenerator
from src.communication.schemas import StatusData, TeamStatusOutput


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client that returns valid TeamStatusOutput."""
    client = MagicMock()
    client.extract = AsyncMock(
        return_value=TeamStatusOutput(
            summary=(
                "Strong sprint with 3 items completed. "
                "Team velocity remains positive."
            ),
            completed_items=[
                {
                    "description": "Implemented user authentication",
                    "owner": "Alice",
                    "completed_date": "2026-01-10",
                },
                {
                    "description": "Set up CI/CD pipeline",
                    "owner": "Bob",
                    "completed_date": "2026-01-12",
                },
                {
                    "description": "Created API documentation",
                    "owner": "Charlie",
                    "completed_date": "2026-01-14",
                },
            ],
            open_items=[
                {
                    "description": "Integration testing",
                    "owner": "Dave",
                    "due_date": "2026-01-20",
                    "status": "in_progress",
                },
                {
                    "description": "Performance optimization",
                    "owner": "Eve",
                    "due_date": "2026-01-25",
                    "status": "pending",
                },
            ],
            decisions=[
                "Use JWT for authentication tokens",
                "Adopt feature flag system for releases",
            ],
            risks=[
                "Third-party API rate limits may affect performance",
            ],
            issues=[
                "Build times exceeding 10 minutes",
            ],
        )
    )
    return client


@pytest.fixture
def sample_status_data():
    """Create sample StatusData for testing."""
    return StatusData(
        project_id="ProjectX",
        time_period=(datetime(2026, 1, 1), datetime(2026, 1, 15)),
        completed_items=[
            {
                "id": "1",
                "item_type": "action",
                "description": "Implement auth",
                "owner": "Alice",
                "due_date": "2026-01-10",
                "status": "completed",
            },
            {
                "id": "2",
                "item_type": "action",
                "description": "Set up CI/CD",
                "owner": "Bob",
                "due_date": "2026-01-12",
                "status": "completed",
            },
            {
                "id": "3",
                "item_type": "action",
                "description": "Create API docs",
                "owner": "Charlie",
                "due_date": "2026-01-14",
                "status": "completed",
            },
        ],
        new_items=[
            {
                "id": "4",
                "item_type": "action",
                "description": "Performance opt",
                "owner": "Eve",
                "due_date": "2026-01-25",
                "status": "pending",
            },
        ],
        open_items=[
            {
                "id": "5",
                "item_type": "action",
                "description": "Integration testing",
                "owner": "Dave",
                "due_date": "2026-01-20",
                "status": "in_progress",
            },
            {
                "id": "4",
                "item_type": "action",
                "description": "Performance opt",
                "owner": "Eve",
                "due_date": "2026-01-25",
                "status": "pending",
            },
        ],
        decisions=[
            {
                "id": "6",
                "item_type": "decision",
                "description": "Use JWT for auth",
                "owner": "Architecture Team",
                "due_date": None,
                "status": "approved",
            },
        ],
        risks=[
            {
                "id": "7",
                "item_type": "risk",
                "description": "API rate limits risk",
                "owner": "PM",
                "due_date": None,
                "status": "open",
            },
        ],
        issues=[
            {
                "id": "8",
                "item_type": "issue",
                "description": "Build times too long",
                "owner": "DevOps",
                "due_date": None,
                "status": "open",
            },
        ],
        blockers=[],
        meetings_held=[
            {"id": "m1", "title": "Sprint Standup", "date": "2026-01-08"},
        ],
        item_velocity=2,
        overdue_count=0,
    )


class TestTeamStatusGenerator:
    """Test suite for TeamStatusGenerator."""

    @pytest.mark.asyncio
    async def test_generate_returns_artifact(self, mock_llm_client, sample_status_data):
        """Generator returns a GeneratedArtifact."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert result.artifact_type == "team_status"
        assert result.markdown is not None
        assert result.plain_text is not None

    @pytest.mark.asyncio
    async def test_generate_includes_completed_items(
        self, mock_llm_client, sample_status_data
    ):
        """Output includes completed items section."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Completed" in result.markdown
        assert "Alice" in result.markdown
        assert "authentication" in result.markdown
        assert result.metadata["completed_count"] == 3

    @pytest.mark.asyncio
    async def test_generate_completed_items_before_open(
        self, mock_llm_client, sample_status_data
    ):
        """Completed items appear before open items (celebrate wins)."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        completed_pos = result.markdown.find("Completed")
        open_pos = result.markdown.find("Open Items")
        assert completed_pos < open_pos

    @pytest.mark.asyncio
    async def test_generate_open_items_have_owners(
        self, mock_llm_client, sample_status_data
    ):
        """Open items include owner information."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Dave" in result.markdown
        assert "Eve" in result.markdown
        assert result.metadata["item_count"] == 2

    @pytest.mark.asyncio
    async def test_generate_open_items_have_due_dates(
        self, mock_llm_client, sample_status_data
    ):
        """Open items include due date information."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "2026-01-20" in result.markdown
        assert "2026-01-25" in result.markdown

    @pytest.mark.asyncio
    async def test_generate_includes_decisions(
        self, mock_llm_client, sample_status_data
    ):
        """Output includes decisions section."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Decisions" in result.markdown
        assert "JWT" in result.markdown
        assert result.metadata["decisions_count"] == 2

    @pytest.mark.asyncio
    async def test_generate_includes_risks(self, mock_llm_client, sample_status_data):
        """Output includes risks section."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Risks" in result.markdown
        assert "rate limits" in result.markdown
        assert result.metadata["risks_count"] == 1

    @pytest.mark.asyncio
    async def test_generate_includes_issues(self, mock_llm_client, sample_status_data):
        """Output includes issues section."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Issues" in result.markdown
        assert "Build times" in result.markdown
        assert result.metadata["issues_count"] == 1

    @pytest.mark.asyncio
    async def test_generate_calls_llm_with_correct_schema(
        self, mock_llm_client, sample_status_data
    ):
        """LLM client called with TeamStatusOutput schema."""
        generator = TeamStatusGenerator(mock_llm_client)
        await generator.generate(sample_status_data)
        mock_llm_client.extract.assert_called_once()
        call_args = mock_llm_client.extract.call_args
        assert call_args[0][1] == TeamStatusOutput

    @pytest.mark.asyncio
    async def test_generate_plain_text_format(
        self, mock_llm_client, sample_status_data
    ):
        """Plain text output uses non-markdown formatting."""
        generator = TeamStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert result.plain_text is not None
        assert "TEAM STATUS" in result.plain_text
        assert "COMPLETED" in result.plain_text
        assert "[DONE]" in result.plain_text

    @pytest.mark.asyncio
    async def test_generate_no_truncation(self, mock_llm_client, sample_status_data):
        """Team status does not truncate items (unlike exec status)."""
        generator = TeamStatusGenerator(mock_llm_client)
        await generator.generate(sample_status_data)
        call_args = mock_llm_client.extract.call_args
        prompt = call_args[0][0]
        assert "and 95 more" not in prompt
