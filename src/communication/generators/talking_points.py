"""Talking points generator (COM-04).

Generates executive meeting talking points with:
- Narrative summary
- Key talking points
- Anticipated Q&A (risk, resource, other categories)
"""

import logging
from datetime import datetime
from typing import Any

from src.communication.generators.base import BaseGenerator
from src.communication.prompts import TALKING_POINTS_PROMPT
from src.communication.schemas import (
    GeneratedArtifact,
    StatusData,
    TalkingPointsOutput,
)

logger = logging.getLogger(__name__)


class TalkingPointsGenerator(BaseGenerator):
    """Generator for exec meeting talking points.

    Produces narrative-focused talking points with:
    - High-level summary telling the project story
    - 5-7 key talking points
    - Anticipated Q&A covering risk, resource, and other categories
    """

    async def generate(
        self,
        data: StatusData,
        *,
        meeting_type: str = "exec_review",
    ) -> GeneratedArtifact:
        """Generate talking points from project status data.

        Args:
            data: StatusData with project metrics and items
            meeting_type: Type of meeting (e.g., 'exec_review', 'board_meeting')

        Returns:
            GeneratedArtifact with talking points and Q&A
        """
        # Format time period
        period_start = data.time_period[0].strftime("%Y-%m-%d")
        period_end = data.time_period[1].strftime("%Y-%m-%d")

        # Format data sections for prompt
        key_progress = self._format_items(data.completed_items[:5])
        decisions = self._format_items(data.decisions[:3])
        risks = self._format_items(data.risks[:5])
        issues = self._format_items(data.issues[:5])
        blockers = self._format_items(data.blockers)
        metrics = self._format_metrics(data)

        # Build prompt
        prompt = TALKING_POINTS_PROMPT.format(
            project_name=data.project_id,
            meeting_type=meeting_type,
            period_start=period_start,
            period_end=period_end,
            key_progress=key_progress,
            decisions=decisions,
            risks=risks,
            issues=issues,
            blockers=blockers,
            metrics=metrics,
        )

        # Extract structured output from LLM
        output = await self._llm.extract(prompt, TalkingPointsOutput)

        # Validate Q&A category coverage
        self._validate_qa_coverage(output)

        # Build template context
        context = self._build_context(output, data, meeting_type)

        # Render templates
        markdown, plain_text = self._render_template("talking_points", context)

        return GeneratedArtifact(
            artifact_type="talking_points",
            markdown=markdown,
            plain_text=plain_text,
            metadata={
                "point_count": len(output.key_points),
                "qa_count": len(output.anticipated_qa),
            },
        )

    def _format_metrics(self, data: StatusData) -> str:
        """Format metrics section for prompt context.

        Args:
            data: StatusData with metrics

        Returns:
            Formatted metrics string
        """
        return f"""Items completed: {len(data.completed_items)}
Items opened: {len(data.new_items)}
Net velocity: {data.item_velocity:+d}
Currently open: {len(data.open_items)}
Overdue items: {data.overdue_count}
Active risks: {len(data.risks)}
Open issues: {len(data.issues)}
Blockers: {len(data.blockers)}
Meetings held: {len(data.meetings_held)}"""

    def _validate_qa_coverage(self, output: TalkingPointsOutput) -> None:
        """Validate Q&A section has required categories.

        Logs warning if risk or resource categories missing.
        Does not raise - LLM may have valid reason for omission.

        Args:
            output: LLM-generated talking points output
        """
        qa_categories = {q.get("category", "") for q in output.anticipated_qa}
        required = {"risk", "resource"}
        missing = required - qa_categories

        if missing:
            logger.warning(
                f"Talking points Q&A missing categories: {missing}. "
                "Consider adding questions about these areas."
            )

    def _build_context(
        self,
        output: TalkingPointsOutput,
        data: StatusData,
        meeting_type: str,
    ) -> dict[str, Any]:
        """Build template context from output and data.

        Args:
            output: LLM-generated output
            data: Source status data
            meeting_type: Type of meeting

        Returns:
            Context dict for template rendering
        """
        context = output.model_dump()
        context["project_name"] = data.project_id
        context["meeting_type"] = meeting_type
        context["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return context
