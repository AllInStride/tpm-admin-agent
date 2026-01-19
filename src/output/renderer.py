"""Jinja2-based template renderer for meeting minutes."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from src.output.schemas import MinutesContext, RenderedMinutes


class MinutesRenderer:
    """Render meeting minutes from Jinja2 templates.

    Supports both Markdown and HTML output formats with
    configurable templates per project.
    """

    def __init__(self, template_dir: str | Path = "templates"):
        """Initialize renderer with template directory.

        Args:
            template_dir: Path to directory containing .j2 templates.
                          Defaults to 'templates' in project root.
        """
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "htm"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        context: MinutesContext,
        template_name: str = "default_minutes",
    ) -> RenderedMinutes:
        """Render meeting minutes in both Markdown and HTML formats.

        Args:
            context: MinutesContext with all meeting data
            template_name: Base name of template (without .md.j2/.html.j2)

        Returns:
            RenderedMinutes with both formats

        Raises:
            TemplateNotFound: If template files don't exist
        """
        markdown = self.render_markdown(context, template_name)
        html = self.render_html(context, template_name)

        return RenderedMinutes(
            meeting_id=context.meeting_id,
            markdown=markdown,
            html=html,
            template_used=template_name,
        )

    def render_markdown(
        self,
        context: MinutesContext,
        template_name: str = "default_minutes",
    ) -> str:
        """Render meeting minutes as Markdown.

        Args:
            context: MinutesContext with all meeting data
            template_name: Base name of template (without .md.j2)

        Returns:
            Rendered Markdown string

        Raises:
            TemplateNotFound: If template file doesn't exist
        """
        template_file = f"{template_name}.md.j2"
        template = self.env.get_template(template_file)
        return template.render(context.model_dump())

    def render_html(
        self,
        context: MinutesContext,
        template_name: str = "default_minutes",
    ) -> str:
        """Render meeting minutes as HTML.

        Args:
            context: MinutesContext with all meeting data
            template_name: Base name of template (without .html.j2)

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFound: If template file doesn't exist
        """
        template_file = f"{template_name}.html.j2"
        template = self.env.get_template(template_file)
        return template.render(context.model_dump())


__all__ = ["MinutesRenderer", "TemplateNotFound"]
