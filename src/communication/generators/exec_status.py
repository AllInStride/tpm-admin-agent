"""Exec status generator for COM-01.

Generates executive-level status updates with:
- RAG indicators (overall + scope/schedule/risk breakdown)
- Summary (5-7 bullet points)
- Team references (not individual names)
- Blockers with explicit asks
- Next period lookahead
"""

from datetime import datetime

from src.communication.generators.base import BaseGenerator
from src.communication.prompts import EXEC_STATUS_PROMPT
from src.communication.schemas import (
    ExecStatusOutput,
    GeneratedArtifact,
    StatusData,
)


class ExecStatusGenerator(BaseGenerator):
    """Generator for executive status updates (COM-01).

    Produces half-page status updates suitable for exec audiences:
    - RAG status breakdown
    - High-level progress summary
    - Blockers with explicit asks
    - Next period outlook
    """

    async def generate(
        self,
        data: StatusData,
        *,
        include_lookahead: bool = True,
    ) -> GeneratedArtifact:
        """Generate an executive status update.

        Args:
            data: StatusData with project information
            include_lookahead: Whether to include next period section

        Returns:
            GeneratedArtifact with markdown and plain text formats
        """
        # Build prompt with data - limit to top 5 items per category
        prompt = EXEC_STATUS_PROMPT.format(
            project_name=data.project_id,
            period_start=data.time_period[0].strftime("%Y-%m-%d"),
            period_end=data.time_period[1].strftime("%Y-%m-%d"),
            completed_count=len(data.completed_items),
            completed_items=self._format_items(data.completed_items, max_items=5),
            new_count=len(data.new_items),
            new_items=self._format_items(data.new_items, max_items=5),
            open_count=len(data.open_items),
            open_items=self._format_items(data.open_items, max_items=5),
            decisions_count=len(data.decisions),
            decisions=self._format_items(data.decisions, max_items=5),
            risks_count=len(data.risks),
            risks=self._format_items(data.risks, max_items=5),
            issues_count=len(data.issues),
            issues=self._format_items(data.issues, max_items=5),
            blockers_count=len(data.blockers),
            blockers=self._format_items(data.blockers, max_items=5),
            meetings_count=len(data.meetings_held),
            velocity=data.item_velocity,
            overdue_count=data.overdue_count,
        )

        # Extract structured output from LLM
        output = await self._llm.extract(prompt, ExecStatusOutput)

        # Build template context
        context = {
            "project_name": data.project_id,
            "period_start": data.time_period[0].strftime("%Y-%m-%d"),
            "period_end": data.time_period[1].strftime("%Y-%m-%d"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source_meetings": [m.get("title", "Untitled") for m in data.meetings_held],
            "overall_rag": output.overall_rag,
            "scope_rag": output.scope_rag,
            "schedule_rag": output.schedule_rag,
            "risk_rag": output.risk_rag,
            "summary": output.summary,
            "key_progress": output.key_progress,
            "key_decisions": output.key_decisions,
            "blockers": output.blockers,
            "risks": output.risks,
            "next_period": output.next_period if include_lookahead else [],
        }

        # Render templates
        markdown, plain_text = self._render_template("exec_status", context)

        return GeneratedArtifact(
            artifact_type="exec_status",
            markdown=markdown,
            plain_text=plain_text,
            metadata={
                "rag_overall": output.overall_rag,
                "rag_scope": output.scope_rag,
                "rag_schedule": output.schedule_rag,
                "rag_risk": output.risk_rag,
                "completed_count": len(data.completed_items),
                "open_count": len(data.open_items),
                "blocker_count": len(output.blockers),
            },
        )
