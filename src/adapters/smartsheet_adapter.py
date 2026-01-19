"""Adapter for writing RAID items to Smartsheet.

Uses the Smartsheet Python SDK for sheet creation, column mapping,
and batch row writes with proper async handling.
"""

import asyncio
import os
import time

import smartsheet
import structlog
from smartsheet.models import Cell, Column, Row, Sheet

from src.integration.schemas import RAID_COLUMNS, RaidRowData, SmartsheetWriteResult

logger = structlog.get_logger()


class SmartsheetAdapter:
    """Adapter for writing RAID items to Smartsheet.

    Follows established adapter pattern with lazy client initialization,
    asyncio.to_thread for sync SDK calls, and WriteResult return type.
    """

    # Conservative batch size (API max is 500)
    BATCH_SIZE = 100

    def __init__(self, access_token: str | None = None):
        """Initialize with access token.

        Args:
            access_token: Smartsheet API token.
                         Falls back to SMARTSHEET_ACCESS_TOKEN env var.
        """
        self._token = access_token or os.environ.get("SMARTSHEET_ACCESS_TOKEN")
        self._client: smartsheet.Smartsheet | None = None

    def _get_client(self) -> smartsheet.Smartsheet:
        """Get or create authenticated Smartsheet client.

        Returns:
            Authenticated Smartsheet client instance

        Raises:
            ValueError: If no token is configured
        """
        if self._client is None:
            if not self._token:
                raise ValueError(
                    "No Smartsheet token. Set SMARTSHEET_ACCESS_TOKEN env var "
                    "or pass access_token to constructor."
                )
            self._client = smartsheet.Smartsheet(access_token=self._token)
            # Disable SDK's default "assume user" behavior
            self._client.errors_as_exceptions(True)
        return self._client

    async def create_sheet(
        self,
        name: str,
        folder_id: int | None = None,
        *,
        dry_run: bool = False,
    ) -> SmartsheetWriteResult:
        """Create a new RAID sheet with standard columns.

        Args:
            name: Name for the new sheet
            folder_id: Folder ID to create sheet in (None for default)
            dry_run: If True, validate but don't actually create

        Returns:
            SmartsheetWriteResult with sheet ID and URL
        """
        if dry_run:
            logger.info(
                "dry_run: would create sheet",
                name=name,
                folder_id=folder_id,
            )
            return SmartsheetWriteResult(
                success=True,
                dry_run=True,
                item_count=0,
            )

        return await asyncio.to_thread(self._create_sheet_sync, name, folder_id)

    def _create_sheet_sync(
        self,
        name: str,
        folder_id: int | None,
    ) -> SmartsheetWriteResult:
        """Synchronous sheet creation implementation.

        Args:
            name: Sheet name
            folder_id: Optional folder ID

        Returns:
            SmartsheetWriteResult with created sheet info
        """
        start_time = time.monotonic()

        try:
            client = self._get_client()

            # Build column specs from RAID_COLUMNS
            columns = []
            for col_def in RAID_COLUMNS:
                col = Column()
                col.title = col_def["title"]
                col.type = col_def["type"]

                if col_def.get("primary"):
                    col.primary = True

                if "options" in col_def:
                    col.options = col_def["options"]

                columns.append(col)

            # Create sheet spec
            sheet_spec = Sheet()
            sheet_spec.name = name
            sheet_spec.columns = columns

            # Create in folder or at root
            if folder_id:
                response = client.Folders.create_sheet_in_folder(folder_id, sheet_spec)
            else:
                response = client.Home.create_sheet(sheet_spec)

            sheet = response.result
            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "created Smartsheet",
                sheet_id=sheet.id,
                name=name,
                folder_id=folder_id,
                duration_ms=duration_ms,
            )

            return SmartsheetWriteResult(
                success=True,
                dry_run=False,
                item_count=0,
                external_id=str(sheet.id),
                url=sheet.permalink,
                sheet_url=sheet.permalink,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "failed to create Smartsheet",
                name=name,
                error=str(e),
                duration_ms=duration_ms,
            )
            return SmartsheetWriteResult(
                success=False,
                dry_run=False,
                error_message=str(e),
                duration_ms=duration_ms,
            )

    async def write_raid_items(
        self,
        sheet_id: int,
        items: list[RaidRowData],
        *,
        dry_run: bool = False,
    ) -> SmartsheetWriteResult:
        """Write RAID items to Smartsheet as rows.

        Items are chunked into batches of BATCH_SIZE for API efficiency.

        Args:
            sheet_id: Target sheet ID
            items: List of RaidRowData to write
            dry_run: If True, validate but don't actually write

        Returns:
            SmartsheetWriteResult with row IDs
        """
        if dry_run:
            logger.info(
                "dry_run: would write RAID items",
                sheet_id=sheet_id,
                item_count=len(items),
            )
            return SmartsheetWriteResult(
                success=True,
                dry_run=True,
                item_count=len(items),
                external_id=str(sheet_id),
            )

        if not items:
            return SmartsheetWriteResult(
                success=True,
                dry_run=False,
                item_count=0,
                external_id=str(sheet_id),
            )

        return await asyncio.to_thread(self._write_items_sync, sheet_id, items)

    def _write_items_sync(
        self,
        sheet_id: int,
        items: list[RaidRowData],
    ) -> SmartsheetWriteResult:
        """Synchronous batch write implementation.

        Args:
            sheet_id: Target sheet ID
            items: List of items to write

        Returns:
            SmartsheetWriteResult with created row IDs
        """
        start_time = time.monotonic()

        try:
            # Get column mapping
            column_map = self._get_column_map(sheet_id)

            all_row_ids: list[int] = []

            # Process in batches
            for i in range(0, len(items), self.BATCH_SIZE):
                chunk = items[i : i + self.BATCH_SIZE]
                row_ids = self._write_batch_sync(sheet_id, chunk, column_map)
                all_row_ids.extend(row_ids)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "wrote RAID items to Smartsheet",
                sheet_id=sheet_id,
                item_count=len(items),
                row_count=len(all_row_ids),
                duration_ms=duration_ms,
            )

            return SmartsheetWriteResult(
                success=True,
                dry_run=False,
                item_count=len(items),
                external_id=str(sheet_id),
                url=f"https://app.smartsheet.com/sheets/{sheet_id}",
                sheet_url=f"https://app.smartsheet.com/sheets/{sheet_id}",
                row_ids=all_row_ids,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "failed to write RAID items",
                sheet_id=sheet_id,
                error=str(e),
                duration_ms=duration_ms,
            )
            return SmartsheetWriteResult(
                success=False,
                dry_run=False,
                item_count=0,
                error_message=str(e),
                duration_ms=duration_ms,
            )

    def _write_batch_sync(
        self,
        sheet_id: int,
        items: list[RaidRowData],
        column_map: dict[str, int],
    ) -> list[int]:
        """Write a single batch of items.

        Args:
            sheet_id: Target sheet ID
            items: Items to write (max BATCH_SIZE)
            column_map: Column title to ID mapping

        Returns:
            List of created row IDs
        """
        client = self._get_client()

        rows = [self._item_to_row(item, column_map) for item in items]
        response = client.Sheets.add_rows(sheet_id, rows)

        return [row.id for row in response.result]

    def _get_column_map(self, sheet_id: int) -> dict[str, int]:
        """Fetch column mapping for a sheet.

        Args:
            sheet_id: Sheet to get columns from

        Returns:
            Dict mapping column title to column ID
        """
        client = self._get_client()
        sheet = client.Sheets.get_sheet(sheet_id)

        return {col.title: col.id for col in sheet.columns}

    def _item_to_row(
        self,
        item: RaidRowData,
        column_map: dict[str, int],
    ) -> Row:
        """Convert RaidRowData to Smartsheet Row.

        Args:
            item: RAID item data
            column_map: Column title to ID mapping

        Returns:
            Smartsheet Row object ready for API
        """
        row = Row()
        row.to_bottom = True  # Per RESEARCH.md pitfall

        cells = []

        # Map fields to columns
        field_mapping = {
            "Type": item.type,
            "Title": item.title,
            "Owner": item.owner,
            "Status": item.status,
            "Due Date": item.due_date,  # Already YYYY-MM-DD format
            "Source Meeting": item.source_meeting,
            "Created Date": item.created_date,  # Already YYYY-MM-DD format
            "Confidence": str(item.confidence),
            "Item Hash": item.item_hash,
        }

        for col_title, value in field_mapping.items():
            if col_title in column_map and value:
                cell = Cell()
                cell.column_id = column_map[col_title]
                cell.value = value
                cells.append(cell)

        row.cells = cells
        return row

    async def health_check(self) -> bool:
        """Verify API access is working.

        Returns:
            True if can connect to API, False otherwise
        """
        if not self._token:
            return False

        try:
            client = self._get_client()
            # Simple API call to verify access
            await asyncio.to_thread(client.Users.get_current_user)
            return True
        except Exception as e:
            logger.warning(
                "Smartsheet health check failed",
                error=str(e),
            )
            return False
