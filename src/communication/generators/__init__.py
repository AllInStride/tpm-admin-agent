"""Communication artifact generators.

Generators produce communication artifacts from input data:
- EscalationGenerator: Problem-Impact-Ask emails (COM-03)
- TalkingPointsGenerator: Exec meeting talking points (COM-04)
"""

from src.communication.generators.base import BaseGenerator
from src.communication.generators.escalation import EscalationGenerator

__all__ = [
    "BaseGenerator",
    "EscalationGenerator",
]
