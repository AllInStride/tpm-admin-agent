"""Communication service orchestrating all artifact generators.

Provides unified interface for generating:
- Executive status updates (COM-01)
- Team status updates (COM-02)
- Escalation emails (COM-03)
- Exec talking points (COM-04)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import structlog

from src.communication.data_aggregator import DataAggregator, StatusData
from src.communication.generators.escalation import EscalationGenerator
from src.communication.generators.exec_status import ExecStatusGenerator
from src.communication.generators.talking_points import TalkingPointsGenerator
from src.communication.generators.team_status import TeamStatusGenerator
from src.communication.schemas import EscalationRequest, GeneratedArtifact
from src.services.llm_client import LLMClient

logger = structlog.get_logger()

ArtifactType = Literal["exec_status", "team_status", "escalation", "talking_points"]


@dataclass
class GenerationResult:
    """Result of artifact generation."""

    artifact_type: ArtifactType
    artifact: GeneratedArtifact
    data_used: StatusData | None
    generated_at: datetime


class CommunicationService:
    """Orchestrates communication artifact generation.

    Provides methods for generating all four artifact types,
    coordinating between data aggregation and LLM-powered generators.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        data_aggregator: DataAggregator,
    ):
        """Initialize the communication service.

        Args:
            llm_client: LLM client for structured extraction
            data_aggregator: Data aggregator for gathering project data
        """
        self._llm = llm_client
        self._aggregator = data_aggregator

        # Initialize generators
        self._exec_status = ExecStatusGenerator(llm_client)
        self._team_status = TeamStatusGenerator(llm_client)
        self._escalation = EscalationGenerator(llm_client)
        self._talking_points = TalkingPointsGenerator(llm_client)

    async def generate_exec_status(
        self,
        project_id: str,
        since: datetime,
        until: datetime | None = None,
    ) -> GenerationResult:
        """Generate executive status update (COM-01).

        Args:
            project_id: Project to report on
            since: Start of reporting period
            until: End of reporting period (default: now)

        Returns:
            GenerationResult with artifact and metadata
        """
        logger.info(
            "generating exec status",
            project_id=project_id,
            since=since.isoformat(),
        )

        data = await self._aggregator.gather_for_status(project_id, since, until)
        artifact = await self._exec_status.generate(data)

        logger.info(
            "exec status generated",
            project_id=project_id,
            rag=artifact.metadata.get("rag_overall"),
        )

        return GenerationResult(
            artifact_type="exec_status",
            artifact=artifact,
            data_used=data,
            generated_at=datetime.now(),
        )

    async def generate_team_status(
        self,
        project_id: str,
        since: datetime,
        until: datetime | None = None,
    ) -> GenerationResult:
        """Generate team status update (COM-02).

        Args:
            project_id: Project to report on
            since: Start of reporting period
            until: End of reporting period (default: now)

        Returns:
            GenerationResult with artifact and metadata
        """
        logger.info(
            "generating team status",
            project_id=project_id,
            since=since.isoformat(),
        )

        data = await self._aggregator.gather_for_status(project_id, since, until)
        artifact = await self._team_status.generate(data)

        logger.info(
            "team status generated",
            project_id=project_id,
            item_count=artifact.metadata.get("item_count"),
        )

        return GenerationResult(
            artifact_type="team_status",
            artifact=artifact,
            data_used=data,
            generated_at=datetime.now(),
        )

    async def generate_escalation(
        self,
        request: EscalationRequest,
    ) -> GenerationResult:
        """Generate escalation email (COM-03).

        Args:
            request: Escalation request with problem, options, deadline

        Returns:
            GenerationResult with escalation email artifact
        """
        logger.info(
            "generating escalation",
            deadline=request.decision_deadline.isoformat(),
            option_count=len(request.options),
        )

        artifact = await self._escalation.generate(request)

        logger.info(
            "escalation generated",
            subject=artifact.metadata.get("subject"),
        )

        return GenerationResult(
            artifact_type="escalation",
            artifact=artifact,
            data_used=None,
            generated_at=datetime.now(),
        )

    async def generate_talking_points(
        self,
        project_id: str,
        meeting_type: str = "exec_review",
        since: datetime | None = None,
    ) -> GenerationResult:
        """Generate exec talking points (COM-04).

        Args:
            project_id: Project to generate talking points for
            meeting_type: Type of meeting (default: exec_review)
            since: Start of data period (default: 30 days ago)

        Returns:
            GenerationResult with talking points artifact
        """
        # Default to 30 days ago if no since provided
        if since is None:
            since = datetime.now() - timedelta(days=30)

        logger.info(
            "generating talking points",
            project_id=project_id,
            meeting_type=meeting_type,
            since=since.isoformat(),
        )

        data = await self._aggregator.gather_for_status(project_id, since)
        artifact = await self._talking_points.generate(data, meeting_type=meeting_type)

        logger.info(
            "talking points generated",
            project_id=project_id,
            point_count=artifact.metadata.get("point_count"),
        )

        return GenerationResult(
            artifact_type="talking_points",
            artifact=artifact,
            data_used=data,
            generated_at=datetime.now(),
        )
