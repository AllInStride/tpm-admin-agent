"""Communication automation module for generating status updates and artifacts."""

from src.communication.data_aggregator import DataAggregator
from src.communication.schemas import (
    EscalationOutput,
    EscalationRequest,
    ExecStatusOutput,
    GeneratedArtifact,
    StatusData,
    TalkingPointsOutput,
    TeamStatusOutput,
)

__all__ = [
    "DataAggregator",
    "StatusData",
    "ExecStatusOutput",
    "TeamStatusOutput",
    "EscalationOutput",
    "TalkingPointsOutput",
    "GeneratedArtifact",
    "EscalationRequest",
]
