"""Multi-source confidence calculation for identity resolution.

Implements the confidence boosting rules from CONTEXT.md:
- Single-source (roster only) capped at 85%
- Multi-source agreement adds boost
- Cannot exceed 1.0
"""


def calculate_confidence(
    fuzzy_score: float,
    roster_match: bool,
    slack_match: bool = False,
    calendar_match: bool = False,
) -> float:
    """Calculate final confidence with multi-source boosting.

    Rules from CONTEXT.md:
    - Single-source (roster only) capped at 0.85
    - Multi-source agreement adds 5% boost per additional source
    - Cannot exceed 1.0

    Args:
        fuzzy_score: Base score from fuzzy matching (0-1)
        roster_match: Match found in roster
        slack_match: Verified in Slack
        calendar_match: Verified in Calendar

    Returns:
        Final confidence score (0-1)
    """
    # If no roster match, no confidence
    if not roster_match:
        return 0.0

    base = fuzzy_score

    # Single-source cap per CONTEXT.md
    if not (slack_match or calendar_match):
        return min(base, 0.85)

    # Multi-source boost
    sources_agreeing = sum([roster_match, slack_match, calendar_match])
    if sources_agreeing >= 2:
        boost = 0.05 * (sources_agreeing - 1)
        return min(base + boost, 1.0)

    return base
