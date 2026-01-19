"""Integration router for orchestrating Smartsheet and Slack notifications.

Coordinates RAID item writes to Smartsheet and owner notifications via Slack,
providing a unified integration pipeline for meeting extraction output.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel, ConfigDict, Field

from src.integration.notification_service import NotificationService
from src.integration.schemas import (
    NotificationResult,
    RaidRowData,
    SmartsheetWriteResult,
)
from src.output.config import ProjectOutputConfig
from src.output.queue import write_with_retry
from src.output.schemas import ActionItemData, RaidBundle

if TYPE_CHECKING:
    from src.adapters.smartsheet_adapter import SmartsheetAdapter

logger = structlog.get_logger()


class IntegrationResult(BaseModel):
    """Result of full integration pipeline."""

    model_config = ConfigDict(str_strip_whitespace=True)

    smartsheet_result: SmartsheetWriteResult | None = Field(
        default=None, description="Result from Smartsheet write"
    )
    notifications_sent: int = Field(
        default=0, description="Number of successful notifications"
    )
    notifications_failed: int = Field(
        default=0, description="Number of failed notifications"
    )
    notification_results: list[NotificationResult] = Field(
        default_factory=list, description="Individual notification results"
    )


class IntegrationRouter:
    """Orchestrates Smartsheet writes and owner notifications.

    Coordinates SmartsheetAdapter and NotificationService to:
    1. Convert RaidBundle to Smartsheet rows
    2. Write rows to Smartsheet (with optional auto-creation)
    3. Send Slack DMs to action item owners
    """

    def __init__(
        self,
        smartsheet_adapter: SmartsheetAdapter | None = None,
        notification_service: NotificationService | None = None,
    ):
        """Initialize with optional adapters.

        Args:
            smartsheet_adapter: SmartsheetAdapter for RAID item writes
            notification_service: NotificationService for owner notifications
        """
        self.smartsheet = smartsheet_adapter
        self.notifications = notification_service

    async def process(
        self,
        raid_bundle: RaidBundle,
        config: ProjectOutputConfig,
        *,
        dry_run: bool = False,
    ) -> IntegrationResult:
        """Process RAID items through Smartsheet and notifications.

        1. Convert RaidBundle to RaidRowData list
        2. Write to Smartsheet (creates sheet if needed)
        3. Send notifications to action item owners
        4. Return aggregated results

        Args:
            raid_bundle: Bundle of RAID items to process
            config: Project output configuration
            dry_run: If True, validate without writing

        Returns:
            IntegrationResult with aggregated results
        """
        result = IntegrationResult()

        # Convert bundle to row data
        rows = self._bundle_to_rows(raid_bundle)

        # Write to Smartsheet
        smartsheet_url: str | None = None
        if self.smartsheet and config.smartsheet_sheet_id:
            ss_result = await self._write_to_smartsheet(rows, config, dry_run=dry_run)
            result.smartsheet_result = ss_result
            smartsheet_url = ss_result.sheet_url if ss_result.success else None

        # Send notifications for action items
        if self.notifications and config.notify_owners and not dry_run:
            notif_results = await self._send_notifications(
                raid_bundle.action_items,
                smartsheet_url,
                config.fallback_email,
            )
            result.notification_results = notif_results
            result.notifications_sent = sum(1 for r in notif_results if r.success)
            result.notifications_failed = sum(1 for r in notif_results if not r.success)

        logger.info(
            "integration pipeline complete",
            meeting_id=str(raid_bundle.meeting_id),
            smartsheet_success=result.smartsheet_result.success
            if result.smartsheet_result
            else None,
            notifications_sent=result.notifications_sent,
            notifications_failed=result.notifications_failed,
            dry_run=dry_run,
        )

        return result

    async def _write_to_smartsheet(
        self,
        rows: list[RaidRowData],
        config: ProjectOutputConfig,
        *,
        dry_run: bool = False,
    ) -> SmartsheetWriteResult:
        """Write RAID rows to Smartsheet with optional sheet creation.

        Args:
            rows: List of RaidRowData to write
            config: Project configuration
            dry_run: If True, validate without writing

        Returns:
            SmartsheetWriteResult with write status
        """
        sheet_id = config.smartsheet_sheet_id

        # Auto-create sheet if needed and enabled
        if not sheet_id and config.auto_create_sheet and config.smartsheet_folder_id:
            create_result = await self.smartsheet.create_sheet(
                name=f"RAID Log - {datetime.now().strftime('%Y-%m-%d')}",
                folder_id=config.smartsheet_folder_id,
                dry_run=dry_run,
            )
            if create_result.success:
                sheet_id = (
                    int(create_result.external_id)
                    if create_result.external_id
                    else None
                )

        if not sheet_id:
            return SmartsheetWriteResult(
                success=False,
                error_message="No Smartsheet sheet ID configured",
            )

        # Write with retry (tenacity decorator)
        @write_with_retry
        async def write():
            return await self.smartsheet.write_raid_items(
                sheet_id, rows, dry_run=dry_run
            )

        return await write()

    async def _send_notifications(
        self,
        action_items: list[ActionItemData],
        smartsheet_url: str | None,
        fallback_email: str | None,
    ) -> list[NotificationResult]:
        """Send notifications to action item owners.

        Args:
            action_items: List of action items to notify about
            smartsheet_url: URL to Smartsheet for linking
            fallback_email: Fallback email for unresolved owners

        Returns:
            List of NotificationResult for each notification attempt
        """
        results = []
        for item in action_items:
            # Skip items without assignee
            if not item.assignee_name:
                continue

            # Resolve email (assume assignee_name is email or use fallback)
            # Future: integrate with identity resolution
            email = item.assignee_name if "@" in item.assignee_name else fallback_email

            if not email:
                results.append(
                    NotificationResult(
                        success=False,
                        recipient_email="",
                        error="no_email_available",
                    )
                )
                continue

            result = await self.notifications.notify_owner(
                owner_email=email,
                item=item,
                smartsheet_url=smartsheet_url,
            )
            results.append(result)

        return results

    def _bundle_to_rows(self, bundle: RaidBundle) -> list[RaidRowData]:
        """Convert RaidBundle to flat list of RaidRowData.

        Args:
            bundle: RaidBundle with typed items

        Returns:
            List of RaidRowData ready for Smartsheet
        """
        rows = []
        meeting_id = str(bundle.meeting_id)

        for decision in bundle.decisions:
            rows.append(
                RaidRowData(
                    type="Decision",
                    title=decision.description,
                    owner="",
                    status="Documented",
                    due_date=None,
                    source_meeting=meeting_id,
                    confidence=decision.confidence,
                )
            )

        for action in bundle.action_items:
            rows.append(
                RaidRowData(
                    type="Action",
                    title=action.description,
                    owner=action.assignee_name or "",
                    status="Open",
                    due_date=action.due_date,
                    source_meeting=meeting_id,
                    confidence=action.confidence,
                )
            )

        for risk in bundle.risks:
            rows.append(
                RaidRowData(
                    type="Risk",
                    title=risk.description,
                    owner=risk.owner_name or "",
                    status="Identified",
                    due_date=None,
                    source_meeting=meeting_id,
                    confidence=risk.confidence,
                )
            )

        for issue in bundle.issues:
            rows.append(
                RaidRowData(
                    type="Issue",
                    title=issue.description,
                    owner=issue.owner_name or "",
                    status=issue.status if hasattr(issue, "status") else "Open",
                    due_date=None,
                    source_meeting=meeting_id,
                    confidence=issue.confidence,
                )
            )

        return rows
