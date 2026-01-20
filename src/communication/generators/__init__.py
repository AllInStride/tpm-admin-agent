"""Communication artifact generators.

Generators produce communication artifacts from input data:
- ExecStatusGenerator: Executive status updates (COM-01)
- TeamStatusGenerator: Team status updates (COM-02)
- EscalationGenerator: Problem-Impact-Ask emails (COM-03)
- TalkingPointsGenerator: Exec meeting talking points (COM-04)
"""

from src.communication.generators.base import BaseGenerator
from src.communication.generators.escalation import EscalationGenerator
from src.communication.generators.exec_status import ExecStatusGenerator
from src.communication.generators.talking_points import TalkingPointsGenerator
from src.communication.generators.team_status import TeamStatusGenerator

__all__ = [
    "BaseGenerator",
    "EscalationGenerator",
    "ExecStatusGenerator",
    "TalkingPointsGenerator",
    "TeamStatusGenerator",
]
