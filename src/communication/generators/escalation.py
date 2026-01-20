"""Escalation email generator (COM-03).

Generates Problem-Impact-Ask formatted escalation emails
with options, pros/cons, and explicit deadlines.
"""

from datetime import datetime

from src.communication.generators.base import BaseGenerator
from src.communication.prompts import ESCALATION_PROMPT
from src.communication.schemas import (
    EscalationOutput,
    EscalationRequest,
    GeneratedArtifact,
)


class EscalationGenerator(BaseGenerator):
    """Generator for escalation emails.

    Produces Problem-Impact-Ask formatted emails with:
    - Clear problem statement
    - Impact assessment
    - 2-3 options with pros/cons
    - Explicit decision deadline
    """

    async def generate(self, request: EscalationRequest) -> GeneratedArtifact:
        """Generate an escalation email from request data.

        Args:
            request: EscalationRequest with problem, impacts, options, deadline

        Returns:
            GeneratedArtifact with email content

        Raises:
            ValueError: If output validation fails (< 2 options or missing deadline)
        """
        # Format options for prompt
        options_data = self._format_options(request.options)

        # Build prompt with request data
        prompt = ESCALATION_PROMPT.format(
            problem_description=request.problem_description,
            timeline_impact=request.timeline_impact or "Not specified",
            resource_impact=request.resource_impact or "Not specified",
            business_impact=request.business_impact or "Not specified",
            history_context=request.history_context or "No prior history",
            options_data=options_data,
            decision_deadline=request.decision_deadline.strftime("%Y-%m-%d"),
        )

        # Extract structured output from LLM
        output = await self._llm.extract(prompt, EscalationOutput)

        # Validate output requirements
        if not output.options or len(output.options) < 2:
            raise ValueError("Escalation must have at least 2 options")
        if not output.deadline:
            raise ValueError("Escalation must have explicit deadline")

        # Build template context
        context = output.model_dump()
        context["recipient"] = request.recipient
        context["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Render template (escalation is email-only, so markdown not needed)
        _, plain_text = self._render_template("escalation_email", context)

        return GeneratedArtifact(
            artifact_type="escalation",
            markdown=plain_text,  # Use plain text for both (email format)
            plain_text=plain_text,
            metadata={
                "subject": output.subject,
                "deadline": output.deadline,
                "option_count": len(output.options),
            },
        )

    def _format_options(self, options: list[dict]) -> str:
        """Format options list for prompt context.

        Args:
            options: List of option dicts with description, pros, cons

        Returns:
            Formatted string with labeled options (A, B, C, ...)
        """
        if not options:
            return "None provided"

        labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        lines = []

        for i, option in enumerate(options):
            label = labels[i] if i < len(labels) else str(i + 1)
            desc = option.get("description", str(option))
            pros = option.get("pros", "Not specified")
            cons = option.get("cons", "Not specified")

            lines.append(f"Option {label}: {desc}")
            lines.append(f"  Pros: {pros}")
            lines.append(f"  Cons: {cons}")
            lines.append("")

        return "\n".join(lines).strip()
