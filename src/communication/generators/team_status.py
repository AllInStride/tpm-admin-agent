"""Team status generator for COM-02.

Generates team-level status updates with:
- Completed items first (celebrate wins)
- Full action item list with owners and due dates
- Detailed enough for team reference
- Aggregated meeting notes
"""

from datetime import datetime

from src.communication.generators.base import BaseGenerator
from src.communication.prompts import TEAM_STATUS_PROMPT
from src.communication.schemas import (
    GeneratedArtifact,
    StatusData,
    TeamStatusOutput,
)


class TeamStatusGenerator(BaseGenerator):
    """Generator for team status updates (COM-02).

    Produces detailed status updates suitable for team audiences:
    - Completed items first to celebrate wins
    - Full action item list (no truncation)
    - Owner and due date for every item
    - Decisions, risks, and issues sections
    """

    async def generate(
        self,
        data: StatusData,
        *,
        include_metrics: bool = True,
    ) -> GeneratedArtifact:
        """Generate a team status update.

        Args:
            data: StatusData with project information
            include_metrics: Whether to include velocity metrics

        Returns:
            GeneratedArtifact with markdown and plain text formats
        """
        # Build prompt - include ALL items for team view (no truncation)
        prompt = TEAM_STATUS_PROMPT.format(
            project_name=data.project_id,
            period_start=data.time_period[0].strftime("%Y-%m-%d"),
            period_end=data.time_period[1].strftime("%Y-%m-%d"),
            completed_count=len(data.completed_items),
            completed_items=self._format_items(data.completed_items, max_items=100),
            new_count=len(data.new_items),
            new_items=self._format_items(data.new_items, max_items=100),
            open_count=len(data.open_items),
            open_items=self._format_items(data.open_items, max_items=100),
            decisions_count=len(data.decisions),
            decisions=self._format_items(data.decisions, max_items=100),
            risks_count=len(data.risks),
            risks=self._format_items(data.risks, max_items=100),
            issues_count=len(data.issues),
            issues=self._format_items(data.issues, max_items=100),
            meetings_count=len(data.meetings_held),
        )

        # Extract structured output from LLM
        output = await self._llm.extract(prompt, TeamStatusOutput)

        # Build template context
        context = {
            "project_name": data.project_id,
            "period_start": data.time_period[0].strftime("%Y-%m-%d"),
            "period_end": data.time_period[1].strftime("%Y-%m-%d"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": output.summary,
            "completed_items": output.completed_items,
            "open_items": output.open_items,
            "decisions": output.decisions,
            "risks": output.risks,
            "issues": output.issues,
        }

        # Render templates
        markdown, plain_text = self._render_template("team_status", context)

        return GeneratedArtifact(
            artifact_type="team_status",
            markdown=markdown,
            plain_text=plain_text,
            metadata={
                "item_count": len(output.open_items),
                "completed_count": len(output.completed_items),
                "decisions_count": len(output.decisions),
                "risks_count": len(output.risks),
                "issues_count": len(output.issues),
            },
        )
