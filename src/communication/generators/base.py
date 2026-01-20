"""Base generator class for communication artifacts.

Provides common infrastructure for LLM-powered generators:
- LLM client integration for structured output extraction
- Jinja2 template rendering for markdown and plain text output
- Common formatting helpers
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.communication.schemas import GeneratedArtifact
from src.services.llm_client import LLMClient


class BaseGenerator(ABC):
    """Abstract base class for communication artifact generators.

    Provides:
    - LLM client for structured output extraction
    - Jinja2 template rendering with both .md.j2 and .txt.j2 support
    - Item formatting helpers for prompt building
    """

    def __init__(
        self,
        llm_client: LLMClient,
        template_dir: str = "src/communication/templates",
    ):
        """Initialize generator with LLM client and template directory.

        Args:
            llm_client: LLMClient for structured output extraction
            template_dir: Path to Jinja2 template directory
        """
        self._llm = llm_client
        self._template_dir = Path(template_dir)
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @abstractmethod
    async def generate(self, *args: Any, **kwargs: Any) -> GeneratedArtifact:
        """Generate a communication artifact.

        Subclasses must implement this method with their specific
        input types and generation logic.

        Returns:
            GeneratedArtifact with markdown, plain_text, and metadata
        """
        pass

    def _render_template(
        self, template_name: str, context: dict[str, Any]
    ) -> tuple[str, str]:
        """Render both markdown and plain text versions of a template.

        Args:
            template_name: Base name of template (without extension)
            context: Template context variables

        Returns:
            Tuple of (markdown_content, plain_text_content)
        """
        # Try to render markdown version (may not exist for email templates)
        try:
            md_template = self._env.get_template(f"{template_name}.md.j2")
            markdown = md_template.render(context)
        except Exception:
            markdown = ""

        # Render plain text version (always exists)
        txt_template = self._env.get_template(f"{template_name}.txt.j2")
        plain_text = txt_template.render(context)

        return markdown, plain_text

    def _format_items(self, items: list[dict], max_items: int = 10) -> str:
        """Format a list of items for prompt context.

        Args:
            items: List of item dicts (must have 'description' key)
            max_items: Maximum items to include (default 10)

        Returns:
            Formatted string with numbered items, or "None" if empty
        """
        if not items:
            return "None"

        limited = items[:max_items]
        lines = []
        for i, item in enumerate(limited, 1):
            desc = item.get("description", str(item))
            owner = item.get("owner", "")
            due = item.get("due_date", "")
            parts = [f"{i}. {desc}"]
            if owner:
                parts.append(f"(Owner: {owner})")
            if due:
                parts.append(f"(Due: {due})")
            lines.append(" ".join(parts))

        if len(items) > max_items:
            lines.append(f"... and {len(items) - max_items} more")

        return "\n".join(lines)
