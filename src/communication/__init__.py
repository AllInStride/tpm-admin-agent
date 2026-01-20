"""Communication automation module for generating status updates and artifacts."""

from src.communication.data_aggregator import DataAggregator
from src.communication.generators.escalation import EscalationGenerator
from src.communication.generators.exec_status import ExecStatusGenerator
from src.communication.generators.talking_points import TalkingPointsGenerator
from src.communication.generators.team_status import TeamStatusGenerator
from src.communication.schemas import (
    EscalationOutput,
    EscalationRequest,
    ExecStatusOutput,
    GeneratedArtifact,
    StatusData,
    TalkingPointsOutput,
    TeamStatusOutput,
)
from src.communication.service import CommunicationService, GenerationResult

__all__ = [
    "CommunicationService",
    "GenerationResult",
    "DataAggregator",
    "StatusData",
    "ExecStatusOutput",
    "TeamStatusOutput",
    "EscalationOutput",
    "TalkingPointsOutput",
    "GeneratedArtifact",
    "EscalationRequest",
    "ExecStatusGenerator",
    "TeamStatusGenerator",
    "EscalationGenerator",
    "TalkingPointsGenerator",
]
