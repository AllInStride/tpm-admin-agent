"""Tests for ExecStatusGenerator (COM-01).

Verifies that exec status generation:
- Uses LLM client for structured extraction
- Produces RAG indicators in output
- Includes blockers with explicit asks
- Renders both markdown and plain text
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.communication.generators.exec_status import ExecStatusGenerator
from src.communication.schemas import ExecStatusOutput, StatusData


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client that returns valid ExecStatusOutput."""
    client = MagicMock()
    client.extract = AsyncMock(
        return_value=ExecStatusOutput(
            overall_rag="AMBER",
            scope_rag="GREEN",
            schedule_rag="AMBER",
            risk_rag="GREEN",
            summary=(
                "Good progress on API development. "
                "Schedule at risk due to dependency delays."
            ),
            key_progress=[
                "Backend team completed authentication module",
                "Frontend team delivered dashboard prototype",
                "Infrastructure team set up CI/CD pipeline",
            ],
            key_decisions=[
                "Decided to use JWT for authentication",
                "Approved additional sprint for testing",
            ],
            blockers=[
                {
                    "title": "External API Access",
                    "problem": "Waiting on vendor credentials for 2 weeks",
                    "ask": "Escalate to procurement for expedited approval",
                },
            ],
            risks=[
                "Third-party integration timeline uncertain",
            ],
            next_period=[
                "Complete user management features",
                "Begin integration testing",
                "Finalize API documentation",
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
                "description": "Complete auth module",
                "owner": "Backend Team",
                "due_date": "2026-01-10",
                "status": "completed",
            },
            {
                "id": "2",
                "item_type": "action",
                "description": "Set up CI/CD",
                "owner": "DevOps Team",
                "due_date": "2026-01-12",
                "status": "completed",
            },
        ],
        new_items=[
            {
                "id": "3",
                "item_type": "action",
                "description": "API documentation",
                "owner": "Tech Writing",
                "due_date": "2026-01-20",
                "status": "pending",
            },
        ],
        open_items=[
            {
                "id": "4",
                "item_type": "action",
                "description": "Integration testing",
                "owner": "QA Team",
                "due_date": "2026-01-25",
                "status": "in_progress",
            },
        ],
        decisions=[
            {
                "id": "5",
                "item_type": "decision",
                "description": "Use JWT for auth",
                "owner": "Architecture Team",
                "due_date": None,
                "status": "approved",
            },
        ],
        risks=[
            {
                "id": "6",
                "item_type": "risk",
                "description": "Vendor API delay risk",
                "owner": "PM",
                "due_date": None,
                "status": "open",
            },
        ],
        issues=[],
        blockers=[
            {
                "id": "7",
                "item_type": "action",
                "description": "Blocked on vendor credentials",
                "owner": "Integration Team",
                "due_date": "2026-01-05",
                "status": "blocked",
            },
        ],
        meetings_held=[
            {"id": "m1", "title": "Sprint Planning", "date": "2026-01-01"},
            {"id": "m2", "title": "Architecture Review", "date": "2026-01-08"},
        ],
        item_velocity=1,
        overdue_count=1,
    )


class TestExecStatusGenerator:
    """Test suite for ExecStatusGenerator."""

    @pytest.mark.asyncio
    async def test_generate_returns_artifact(self, mock_llm_client, sample_status_data):
        """Generator returns a GeneratedArtifact."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert result.artifact_type == "exec_status"
        assert result.markdown is not None
        assert result.plain_text is not None

    @pytest.mark.asyncio
    async def test_generate_includes_rag_indicators(
        self, mock_llm_client, sample_status_data
    ):
        """Output includes RAG indicators in metadata."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert result.metadata["rag_overall"] == "AMBER"
        assert result.metadata["rag_scope"] == "GREEN"
        assert result.metadata["rag_schedule"] == "AMBER"
        assert result.metadata["rag_risk"] == "GREEN"

    @pytest.mark.asyncio
    async def test_generate_markdown_contains_rag(
        self, mock_llm_client, sample_status_data
    ):
        """Markdown output contains RAG status."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "AMBER" in result.markdown
        assert "GREEN" in result.markdown
        assert "Overall Status" in result.markdown

    @pytest.mark.asyncio
    async def test_generate_includes_blockers_with_ask(
        self, mock_llm_client, sample_status_data
    ):
        """Blockers include explicit ask field."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "External API Access" in result.markdown
        assert "Escalate to procurement" in result.markdown
        assert "Ask:" in result.markdown
        assert result.metadata["blocker_count"] == 1

    @pytest.mark.asyncio
    async def test_generate_includes_next_period(
        self, mock_llm_client, sample_status_data
    ):
        """Output includes next period section by default."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Next Period" in result.markdown
        assert "Complete user management" in result.markdown

    @pytest.mark.asyncio
    async def test_generate_excludes_next_period_when_disabled(
        self, mock_llm_client, sample_status_data
    ):
        """Next period section excluded when include_lookahead=False."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data, include_lookahead=False)
        assert "Complete user management" not in result.markdown

    @pytest.mark.asyncio
    async def test_generate_calls_llm_with_correct_schema(
        self, mock_llm_client, sample_status_data
    ):
        """LLM client called with ExecStatusOutput schema."""
        generator = ExecStatusGenerator(mock_llm_client)
        await generator.generate(sample_status_data)
        mock_llm_client.extract.assert_called_once()
        call_args = mock_llm_client.extract.call_args
        assert call_args[0][1] == ExecStatusOutput

    @pytest.mark.asyncio
    async def test_generate_plain_text_format(
        self, mock_llm_client, sample_status_data
    ):
        """Plain text output uses non-markdown formatting."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert result.plain_text is not None
        assert "STATUS UPDATE" in result.plain_text
        assert "RAG BREAKDOWN" in result.plain_text
        assert "* " in result.plain_text

    @pytest.mark.asyncio
    async def test_generate_includes_source_meetings(
        self, mock_llm_client, sample_status_data
    ):
        """Output references source meetings."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Sprint Planning" in result.markdown
        assert "Architecture Review" in result.markdown

    @pytest.mark.asyncio
    async def test_generate_includes_decisions(
        self, mock_llm_client, sample_status_data
    ):
        """Output includes decisions made section."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert "Decisions Made" in result.markdown
        assert "JWT for authentication" in result.markdown

    @pytest.mark.asyncio
    async def test_generate_metadata_counts(self, mock_llm_client, sample_status_data):
        """Metadata includes item counts."""
        generator = ExecStatusGenerator(mock_llm_client)
        result = await generator.generate(sample_status_data)
        assert result.metadata["completed_count"] == 2
        assert result.metadata["open_count"] == 1
