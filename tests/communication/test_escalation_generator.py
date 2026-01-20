"""Tests for EscalationGenerator."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.communication.generators.escalation import EscalationGenerator
from src.communication.schemas import (
    EscalationOutput,
    EscalationRequest,
)
from src.services.llm_client import LLMClient


@pytest.fixture
def mock_llm_client() -> LLMClient:
    """Create mock LLM client."""
    client = LLMClient(client=None)
    client.extract = AsyncMock()
    return client


@pytest.fixture
def sample_request() -> EscalationRequest:
    """Create sample escalation request."""
    return EscalationRequest(
        problem_description="Database running out of storage space.",
        timeline_impact="May delay launch by 2 weeks",
        resource_impact="Need additional budget for storage expansion",
        business_impact="Customer data at risk of being lost",
        history_context="Issue identified during routine monitoring last week",
        options=[
            {
                "description": "Emergency storage expansion this weekend",
                "pros": "Immediate resolution",
                "cons": "Higher cost, weekend work required",
            },
            {
                "description": "Archive old data to reduce usage",
                "pros": "No additional cost",
                "cons": "Temporary solution, takes 1-2 weeks",
            },
        ],
        decision_deadline=datetime(2024, 1, 25),
        recipient="vp-engineering@company.com",
    )


@pytest.fixture
def valid_llm_output() -> EscalationOutput:
    """Create valid LLM output."""
    return EscalationOutput(
        subject="Decision Needed: Database Storage Expansion",
        problem="Database is running critically low on storage.",
        impact="If not resolved, we risk data loss and launch delay.",
        deadline="2024-01-25",
        options=[
            {
                "label": "A",
                "description": "Emergency expansion this weekend",
                "pros": "Immediate resolution",
                "cons": "Higher cost",
            },
            {
                "label": "B",
                "description": "Archive old data",
                "pros": "No additional cost",
                "cons": "Temporary, takes time",
            },
        ],
        recommendation="Option A",
        context_summary="Monitoring revealed issue last week.",
    )


class TestEscalationGenerator:
    """Tests for EscalationGenerator."""

    @pytest.mark.asyncio
    async def test_generate_produces_artifact(
        self,
        mock_llm_client: LLMClient,
        sample_request: EscalationRequest,
        valid_llm_output: EscalationOutput,
    ):
        """Generator produces valid artifact with expected fields."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = EscalationGenerator(mock_llm_client)
        artifact = await generator.generate(sample_request)

        assert artifact.artifact_type == "escalation"
        assert artifact.plain_text
        assert "Decision Needed" in artifact.metadata["subject"]
        assert artifact.metadata["deadline"] == "2024-01-25"
        assert artifact.metadata["option_count"] == 2

    @pytest.mark.asyncio
    async def test_generate_includes_subject_in_metadata(
        self,
        mock_llm_client: LLMClient,
        sample_request: EscalationRequest,
        valid_llm_output: EscalationOutput,
    ):
        """Output contains subject line in metadata."""
        mock_llm_client.extract.return_value = valid_llm_output

        generator = EscalationGenerator(mock_llm_client)
        artifact = await generator.generate(sample_request)

        assert "subject" in artifact.metadata
        assert "Database" in artifact.metadata["subject"]

    @pytest.mark.asyncio
    async def test_generate_rejects_insufficient_options(
        self, mock_llm_client: LLMClient, sample_request: EscalationRequest
    ):
        """Generator rejects output with fewer than 2 options."""
        output_with_one_option = EscalationOutput(
            subject="Subject",
            problem="Problem",
            impact="Impact",
            deadline="2024-01-25",
            options=[{"label": "A", "description": "Only one option"}],
        )
        mock_llm_client.extract.return_value = output_with_one_option

        generator = EscalationGenerator(mock_llm_client)

        with pytest.raises(ValueError, match="at least 2 options"):
            await generator.generate(sample_request)

    @pytest.mark.asyncio
    async def test_generate_rejects_empty_options(
        self, mock_llm_client: LLMClient, sample_request: EscalationRequest
    ):
        """Generator rejects output with no options."""
        output_no_options = EscalationOutput(
            subject="Subject",
            problem="Problem",
            impact="Impact",
            deadline="2024-01-25",
            options=[],
        )
        mock_llm_client.extract.return_value = output_no_options

        generator = EscalationGenerator(mock_llm_client)

        with pytest.raises(ValueError, match="at least 2 options"):
            await generator.generate(sample_request)

    @pytest.mark.asyncio
    async def test_generate_rejects_missing_deadline(
        self, mock_llm_client: LLMClient, sample_request: EscalationRequest
    ):
        """Generator rejects output without explicit deadline."""
        output_no_deadline = EscalationOutput(
            subject="Subject",
            problem="Problem",
            impact="Impact",
            deadline="",
            options=[
                {"label": "A", "description": "Option A"},
                {"label": "B", "description": "Option B"},
            ],
        )
        mock_llm_client.extract.return_value = output_no_deadline

        generator = EscalationGenerator(mock_llm_client)

        with pytest.raises(ValueError, match="explicit deadline"):
            await generator.generate(sample_request)


class TestFormatOptions:
    """Tests for _format_options helper."""

    def test_format_options_labels_alphabetically(self, mock_llm_client: LLMClient):
        """Options are labeled A, B, C, etc."""
        generator = EscalationGenerator(mock_llm_client)

        options = [
            {"description": "First", "pros": "Pro1", "cons": "Con1"},
            {"description": "Second", "pros": "Pro2", "cons": "Con2"},
            {"description": "Third", "pros": "Pro3", "cons": "Con3"},
        ]

        result = generator._format_options(options)

        assert "Option A: First" in result
        assert "Option B: Second" in result
        assert "Option C: Third" in result

    def test_format_options_includes_pros_cons(self, mock_llm_client: LLMClient):
        """Formatted options include pros and cons."""
        generator = EscalationGenerator(mock_llm_client)

        options = [
            {"description": "Option one", "pros": "Good stuff", "cons": "Bad stuff"},
        ]

        result = generator._format_options(options)

        assert "Pros: Good stuff" in result
        assert "Cons: Bad stuff" in result

    def test_format_options_empty_list(self, mock_llm_client: LLMClient):
        """Empty options list returns placeholder."""
        generator = EscalationGenerator(mock_llm_client)

        result = generator._format_options([])

        assert result == "None provided"

    def test_format_options_missing_pros_cons(self, mock_llm_client: LLMClient):
        """Missing pros/cons uses default text."""
        generator = EscalationGenerator(mock_llm_client)

        options = [{"description": "Bare option"}]

        result = generator._format_options(options)

        assert "Pros: Not specified" in result
        assert "Cons: Not specified" in result
