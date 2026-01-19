"""Output router for orchestrating meeting output generation.

Routes rendered minutes to Google Drive and RAID items to Google Sheets,
with retry logic and audit logging.
"""

import re
from datetime import datetime

import structlog
from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.adapters.base import WriteResult
from src.adapters.drive_adapter import DriveAdapter
from src.adapters.sheets_adapter import SheetsAdapter
from src.output.config import ProjectOutputConfig
from src.output.queue import write_with_retry
from src.output.renderer import MinutesRenderer
from src.output.schemas import MinutesContext, RaidBundle, RenderedMinutes

logger = structlog.get_logger()


class OutputResult(BaseModel):
    """Result of complete output generation pipeline.

    Aggregates results from renderer and all adapters.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    rendered: RenderedMinutes = Field(description="Rendered minutes content")
    minutes_result: WriteResult | None = Field(
        default=None, description="Drive upload result"
    )
    raid_result: WriteResult | None = Field(
        default=None, description="Sheets write result"
    )
    total_items_written: int = Field(default=0, description="Total RAID items written")

    @computed_field
    @property
    def all_successful(self) -> bool:
        """Check if all write operations succeeded.

        Returns:
            True if all attempted writes succeeded
        """
        results = [self.minutes_result, self.raid_result]
        attempted = [r for r in results if r is not None]
        if not attempted:
            return True  # No writes attempted (dry-run with no destinations)
        return all(r.success for r in attempted)


class OutputRouter:
    """Orchestrates output generation pipeline.

    Coordinates MinutesRenderer and output adapters to generate
    and deliver meeting minutes and RAID items.
    """

    def __init__(
        self,
        renderer: MinutesRenderer | None = None,
        sheets_adapter: SheetsAdapter | None = None,
        drive_adapter: DriveAdapter | None = None,
    ):
        """Initialize router with optional adapters.

        Args:
            renderer: MinutesRenderer instance (created if not provided)
            sheets_adapter: SheetsAdapter for RAID items (optional)
            drive_adapter: DriveAdapter for minutes (optional)
        """
        self.renderer = renderer or MinutesRenderer()
        self.sheets_adapter = sheets_adapter
        self.drive_adapter = drive_adapter

    async def generate_output(
        self,
        context: MinutesContext,
        raid_bundle: RaidBundle,
        config: ProjectOutputConfig,
        *,
        dry_run: bool = False,
    ) -> OutputResult:
        """Generate and route meeting output to configured destinations.

        Args:
            context: MinutesContext with meeting data
            raid_bundle: RaidBundle with RAID items
            config: ProjectOutputConfig with destination settings
            dry_run: If True, render but don't write to destinations

        Returns:
            OutputResult with all results
        """
        # Render minutes
        rendered = self.renderer.render(context, config.template_name)

        logger.info(
            "rendered minutes",
            meeting_id=str(context.meeting_id),
            template=config.template_name,
            markdown_len=len(rendered.markdown),
        )

        minutes_result = None
        raid_result = None
        total_items = 0

        # Route minutes to Drive if enabled
        if "drive" in config.enabled_targets and config.minutes_destination:
            minutes_result = await self.route_minutes(
                rendered,
                config.minutes_destination,
                meeting_date=context.meeting_date,
                dry_run=dry_run,
            )
            logger.info(
                "routed minutes to drive",
                success=minutes_result.success,
                dry_run=minutes_result.dry_run,
                url=minutes_result.url,
            )

        # Route RAID items to Sheets if enabled
        if "sheets" in config.enabled_targets and config.raid_destination:
            raid_result = await self.route_raid_items(
                raid_bundle,
                config.raid_destination,
                config.raid_sheet_name,
                dry_run=dry_run,
            )
            if raid_result.success:
                total_items = raid_result.item_count
            logger.info(
                "routed raid items to sheets",
                success=raid_result.success,
                dry_run=raid_result.dry_run,
                item_count=raid_result.item_count,
            )

        return OutputResult(
            rendered=rendered,
            minutes_result=minutes_result,
            raid_result=raid_result,
            total_items_written=total_items,
        )

    async def route_minutes(
        self,
        minutes: RenderedMinutes,
        folder_id: str,
        *,
        meeting_date: datetime | None = None,
        dry_run: bool = False,
    ) -> WriteResult:
        """Route rendered minutes to Google Drive.

        Args:
            minutes: RenderedMinutes with content
            folder_id: Google Drive folder ID
            meeting_date: Optional date for filename
            dry_run: If True, don't actually upload

        Returns:
            WriteResult from Drive adapter
        """
        if self.drive_adapter is None:
            logger.warning("drive adapter not configured, skipping minutes upload")
            return WriteResult(
                success=False,
                error_message="Drive adapter not configured",
            )

        # Generate filename: {date}-{title-slug}.md
        date_str = meeting_date.strftime("%Y-%m-%d") if meeting_date else "undated"
        title_slug = self._slugify(minutes.template_used)
        filename = f"{date_str}-{title_slug}.md"

        @write_with_retry
        async def upload():
            return await self.drive_adapter.upload_minutes(
                content=minutes.markdown,
                filename=filename,
                folder_id=folder_id,
                dry_run=dry_run,
            )

        return await upload()

    async def route_raid_items(
        self,
        bundle: RaidBundle,
        spreadsheet_id: str,
        sheet_name: str = "RAID",
        *,
        dry_run: bool = False,
    ) -> WriteResult:
        """Route RAID items to Google Sheets.

        Args:
            bundle: RaidBundle with all RAID items
            spreadsheet_id: Google Sheets ID
            sheet_name: Worksheet name
            dry_run: If True, don't actually write

        Returns:
            WriteResult from Sheets adapter
        """
        if self.sheets_adapter is None:
            logger.warning("sheets adapter not configured, skipping RAID items")
            return WriteResult(
                success=False,
                error_message="Sheets adapter not configured",
            )

        # Convert bundle to flat list with type field
        items = self._bundle_to_items(bundle)

        @write_with_retry
        async def write():
            return await self.sheets_adapter.write_raid_items(
                spreadsheet_id=spreadsheet_id,
                items=items,
                sheet_name=sheet_name,
                dry_run=dry_run,
            )

        return await write()

    def _bundle_to_items(self, bundle: RaidBundle) -> list[dict]:
        """Convert RaidBundle to flat list of dicts with type field.

        Args:
            bundle: RaidBundle with typed items

        Returns:
            List of dicts ready for Sheets adapter
        """
        items = []

        for decision in bundle.decisions:
            items.append(
                {
                    "uuid": str(bundle.meeting_id),
                    "type": "Decision",
                    "description": decision.description,
                    "owner": "",
                    "due_date": "",
                    "status": "Decided",
                    "confidence": str(decision.confidence),
                }
            )

        for action in bundle.action_items:
            items.append(
                {
                    "uuid": str(bundle.meeting_id),
                    "type": "Action",
                    "description": action.description,
                    "owner": action.assignee_name or "",
                    "due_date": action.due_date or "",
                    "status": "Open",
                    "confidence": str(action.confidence),
                }
            )

        for risk in bundle.risks:
            items.append(
                {
                    "uuid": str(bundle.meeting_id),
                    "type": "Risk",
                    "description": risk.description,
                    "owner": risk.owner_name or "",
                    "due_date": "",
                    "status": f"Severity: {risk.severity}",
                    "confidence": str(risk.confidence),
                }
            )

        for issue in bundle.issues:
            items.append(
                {
                    "uuid": str(bundle.meeting_id),
                    "type": "Issue",
                    "description": issue.description,
                    "owner": issue.owner_name or "",
                    "due_date": "",
                    "status": issue.status,
                    "confidence": str(issue.confidence),
                }
            )

        return items

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-safe slug.

        Args:
            text: Text to slugify

        Returns:
            Lowercase slug with hyphens
        """
        # Lowercase and replace non-alphanumeric with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
        # Remove leading/trailing hyphens
        return slug.strip("-")
