"""Tests for CommunicationService orchestrator.

Verifies that CommunicationService:
- Orchestrates all four generator types
- Returns GenerationResult with artifact and metadata
- Logs generation requests for audit
- Properly delegates to DataAggregator and generators
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.communication.schemas import (
    EscalationRequest,
    GeneratedArtifact,
    StatusData,
)
from src.communication.service import CommunicationService, GenerationResult


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return MagicMock()


@pytest.fixture
def mock_data_aggregator():
    """Create a mock DataAggregator."""
    aggregator = MagicMock()
    aggregator.gather_for_status = AsyncMock(
        return_value=StatusData(
            project_id="TestProject",
            time_period=(datetime(2026, 1, 1), datetime(2026, 1, 15)),
            completed_items=[{"id": "1", "description": "Done"}],
            new_items=[{"id": "2", "description": "New"}],
            open_items=[{"id": "3", "description": "Open"}],
            decisions=[],
            risks=[],
            issues=[],
            blockers=[],
            meetings_held=[],
            item_velocity=0,
            overdue_count=0,
        )
    )
    return aggregator


@pytest.fixture
def mock_artifact():
    """Create a mock GeneratedArtifact."""
    return GeneratedArtifact(
        artifact_type="exec_status",
        markdown="# Status\n\nAll good.",
        plain_text="Status: All good.",
        metadata={"rag_overall": "GREEN"},
    )


@pytest.fixture
def service(mock_llm_client, mock_data_aggregator):
    """Create CommunicationService with mocked dependencies."""
    return CommunicationService(
        llm_client=mock_llm_client,
        data_aggregator=mock_data_aggregator,
    )


class TestCommunicationServiceInit:
    """Tests for CommunicationService initialization."""

    def test_initializes_with_dependencies(self, mock_llm_client, mock_data_aggregator):
        """Service initializes with LLM client and data aggregator."""
        service = CommunicationService(
            llm_client=mock_llm_client,
            data_aggregator=mock_data_aggregator,
        )
        assert service._llm is mock_llm_client
        assert service._aggregator is mock_data_aggregator

    def test_initializes_all_generators(self, mock_llm_client, mock_data_aggregator):
        """Service initializes all four generators."""
        service = CommunicationService(
            llm_client=mock_llm_client,
            data_aggregator=mock_data_aggregator,
        )
        assert service._exec_status is not None
        assert service._team_status is not None
        assert service._escalation is not None
        assert service._talking_points is not None


class TestGenerateExecStatus:
    """Tests for generate_exec_status method."""

    @pytest.mark.asyncio
    async def test_returns_generation_result(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """generate_exec_status returns GenerationResult."""
        with patch.object(
            service._exec_status, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            result = await service.generate_exec_status(
                project_id="TestProject",
                since=datetime(2026, 1, 1),
            )

            assert isinstance(result, GenerationResult)
            assert result.artifact_type == "exec_status"
            assert result.artifact == mock_artifact

    @pytest.mark.asyncio
    async def test_gathers_data_from_aggregator(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """generate_exec_status gathers data via aggregator."""
        with patch.object(
            service._exec_status, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            since = datetime(2026, 1, 1)
            until = datetime(2026, 1, 15)
            await service.generate_exec_status(
                project_id="TestProject",
                since=since,
                until=until,
            )

            mock_data_aggregator.gather_for_status.assert_called_once_with(
                "TestProject", since, until
            )

    @pytest.mark.asyncio
    async def test_includes_data_used_in_result(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """Result includes the StatusData that was used."""
        with patch.object(
            service._exec_status, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            result = await service.generate_exec_status(
                project_id="TestProject",
                since=datetime(2026, 1, 1),
            )

            assert result.data_used is not None
            assert result.data_used.project_id == "TestProject"

    @pytest.mark.asyncio
    async def test_includes_generated_at_timestamp(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """Result includes generation timestamp."""
        with patch.object(
            service._exec_status, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            before = datetime.now()
            result = await service.generate_exec_status(
                project_id="TestProject",
                since=datetime(2026, 1, 1),
            )
            after = datetime.now()

            assert before <= result.generated_at <= after


class TestGenerateTeamStatus:
    """Tests for generate_team_status method."""

    @pytest.mark.asyncio
    async def test_returns_generation_result(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """generate_team_status returns GenerationResult."""
        team_artifact = GeneratedArtifact(
            artifact_type="team_status",
            markdown="# Team Status",
            plain_text="Team Status",
            metadata={"item_count": 5},
        )
        with patch.object(
            service._team_status, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = team_artifact

            result = await service.generate_team_status(
                project_id="TestProject",
                since=datetime(2026, 1, 1),
            )

            assert isinstance(result, GenerationResult)
            assert result.artifact_type == "team_status"

    @pytest.mark.asyncio
    async def test_gathers_data_from_aggregator(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """generate_team_status gathers data via aggregator."""
        with patch.object(
            service._team_status, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            since = datetime(2026, 1, 1)
            await service.generate_team_status(
                project_id="TestProject",
                since=since,
            )

            mock_data_aggregator.gather_for_status.assert_called()


class TestGenerateEscalation:
    """Tests for generate_escalation method."""

    @pytest.fixture
    def escalation_request(self):
        """Create sample escalation request."""
        return EscalationRequest(
            problem_description="Critical bug in production",
            timeline_impact="2 weeks delay",
            business_impact="Revenue loss",
            options=[
                {
                    "description": "Fix now",
                    "pros": "Fast",
                    "cons": "Resource intensive",
                },
                {"description": "Wait", "pros": "Cheap", "cons": "Slow"},
            ],
            decision_deadline=datetime(2026, 1, 20),
        )

    @pytest.mark.asyncio
    async def test_returns_generation_result(self, service, escalation_request):
        """generate_escalation returns GenerationResult."""
        escalation_artifact = GeneratedArtifact(
            artifact_type="escalation",
            markdown="Subject: Critical Issue",
            plain_text="Subject: Critical Issue",
            metadata={"subject": "Critical Issue", "deadline": "2026-01-20"},
        )
        with patch.object(
            service._escalation, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = escalation_artifact

            result = await service.generate_escalation(escalation_request)

            assert isinstance(result, GenerationResult)
            assert result.artifact_type == "escalation"

    @pytest.mark.asyncio
    async def test_data_used_is_none(self, service, escalation_request):
        """Escalation does not use StatusData."""
        escalation_artifact = GeneratedArtifact(
            artifact_type="escalation",
            markdown="Subject: Critical Issue",
            plain_text="Subject: Critical Issue",
            metadata={},
        )
        with patch.object(
            service._escalation, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = escalation_artifact

            result = await service.generate_escalation(escalation_request)

            assert result.data_used is None


class TestGenerateTalkingPoints:
    """Tests for generate_talking_points method."""

    @pytest.mark.asyncio
    async def test_returns_generation_result(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """generate_talking_points returns GenerationResult."""
        tp_artifact = GeneratedArtifact(
            artifact_type="talking_points",
            markdown="# Talking Points",
            plain_text="Talking Points",
            metadata={"point_count": 5, "qa_count": 3},
        )
        with patch.object(
            service._talking_points, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = tp_artifact

            result = await service.generate_talking_points(
                project_id="TestProject",
            )

            assert isinstance(result, GenerationResult)
            assert result.artifact_type == "talking_points"

    @pytest.mark.asyncio
    async def test_defaults_to_30_days_ago(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """Without since param, defaults to 30 days ago."""
        with patch.object(
            service._talking_points, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            await service.generate_talking_points(project_id="TestProject")

            call_args = mock_data_aggregator.gather_for_status.call_args
            since = call_args[0][1]  # Second positional arg is 'since'
            # Should be approximately 30 days ago
            expected = datetime.now() - timedelta(days=30)
            assert abs((since - expected).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_passes_meeting_type(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """Meeting type is passed to generator."""
        with patch.object(
            service._talking_points, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            await service.generate_talking_points(
                project_id="TestProject",
                meeting_type="board_meeting",
            )

            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["meeting_type"] == "board_meeting"

    @pytest.mark.asyncio
    async def test_respects_custom_since(
        self, service, mock_data_aggregator, mock_artifact
    ):
        """Custom since date is passed to aggregator."""
        with patch.object(
            service._talking_points, "generate", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_artifact

            custom_since = datetime(2025, 12, 1)
            await service.generate_talking_points(
                project_id="TestProject",
                since=custom_since,
            )

            call_args = mock_data_aggregator.gather_for_status.call_args
            assert call_args[0][1] == custom_since


class TestGenerationResultDataclass:
    """Tests for GenerationResult dataclass."""

    def test_dataclass_fields(self, mock_artifact):
        """GenerationResult has expected fields."""
        result = GenerationResult(
            artifact_type="exec_status",
            artifact=mock_artifact,
            data_used=None,
            generated_at=datetime.now(),
        )

        assert result.artifact_type == "exec_status"
        assert result.artifact == mock_artifact
        assert result.data_used is None
        assert isinstance(result.generated_at, datetime)
