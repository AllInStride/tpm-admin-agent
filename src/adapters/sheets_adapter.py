"""Adapter for writing RAID items to Google Sheets.

Uses gspread library with service account authentication to batch
write RAID items to Google Sheets for tracking.
"""

import asyncio
import os
import time

import gspread
import structlog
from google.oauth2.service_account import Credentials

from src.adapters.base import WriteResult

logger = structlog.get_logger()


class SheetsAdapter:
    """Adapter for writing RAID items to Google Sheets.

    Batch writes RAID items to a spreadsheet using gspread.
    Follows the established adapter pattern with lazy client initialization.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]

    # Default headers for RAID sheet
    RAID_HEADERS = [
        "UUID",
        "Type",
        "Description",
        "Owner",
        "Due Date",
        "Status",
        "Confidence",
    ]

    def __init__(self, credentials_path: str | None = None):
        """Initialize with service account credentials.

        Args:
            credentials_path: Path to service account JSON.
                             Falls back to GOOGLE_SHEETS_CREDENTIALS env var.
        """
        self._credentials_path = credentials_path or os.environ.get(
            "GOOGLE_SHEETS_CREDENTIALS"
        )
        self._client: gspread.Client | None = None

    def _get_client(self) -> gspread.Client:
        """Get or create authenticated gspread client.

        Returns:
            Authenticated gspread Client instance

        Raises:
            ValueError: If no credentials path configured
        """
        if self._client is None:
            if not self._credentials_path:
                raise ValueError(
                    "No credentials. Set GOOGLE_SHEETS_CREDENTIALS env var "
                    "or pass credentials_path to constructor."
                )
            creds = Credentials.from_service_account_file(
                self._credentials_path,
                scopes=self.SCOPES,
            )
            self._client = gspread.authorize(creds)
        return self._client

    async def write_raid_items(
        self,
        spreadsheet_id: str,
        items: list[dict],
        sheet_name: str = "RAID",
        *,
        dry_run: bool = False,
    ) -> WriteResult:
        """Write RAID items to Google Sheet.

        Args:
            spreadsheet_id: Google Sheets ID (from URL)
            sheet_name: Name of worksheet (default: "RAID")
            items: List of dicts with item data
            dry_run: If True, log and return without writing

        Returns:
            WriteResult with operation outcome
        """
        if dry_run:
            logger.info(
                "dry_run: would write RAID items",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                item_count=len(items),
            )
            return WriteResult(
                success=True,
                dry_run=True,
                item_count=len(items),
                external_id=spreadsheet_id,
            )

        # Use asyncio.to_thread for non-blocking I/O
        return await asyncio.to_thread(
            self._write_sync, spreadsheet_id, items, sheet_name
        )

    def _write_sync(
        self, spreadsheet_id: str, items: list[dict], sheet_name: str
    ) -> WriteResult:
        """Synchronous write implementation.

        Args:
            spreadsheet_id: Google Sheets ID
            items: List of dicts with item data
            sheet_name: Worksheet name

        Returns:
            WriteResult with operation outcome
        """
        start_time = time.monotonic()

        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_id)

            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name, rows=100, cols=len(self.RAID_HEADERS)
                )
                # Add headers to new sheet
                worksheet.update("A1", [self.RAID_HEADERS])

            # Check if headers exist (empty sheet check)
            existing_values = worksheet.get_all_values()
            if not existing_values:
                worksheet.update("A1", [self.RAID_HEADERS])
                start_row = 2
            else:
                # Find next empty row
                start_row = len(existing_values) + 1

            # Prepare data rows
            rows = []
            for item in items:
                rows.append(
                    [
                        str(item.get("uuid", "")),
                        str(item.get("type", "")),
                        str(item.get("description", "")),
                        str(item.get("owner", "")),
                        str(item.get("due_date", "")),
                        str(item.get("status", "")),
                        str(item.get("confidence", "")),
                    ]
                )

            # Batch update with single API call
            if rows:
                range_notation = f"A{start_row}:G{start_row + len(rows) - 1}"
                worksheet.update(
                    range_notation, rows, value_input_option="USER_ENTERED"
                )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "wrote RAID items to sheet",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                item_count=len(items),
                duration_ms=duration_ms,
            )

            return WriteResult(
                success=True,
                dry_run=False,
                item_count=len(items),
                external_id=spreadsheet_id,
                url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "failed to write RAID items",
                spreadsheet_id=spreadsheet_id,
                error=str(e),
                duration_ms=duration_ms,
            )
            return WriteResult(
                success=False,
                dry_run=False,
                item_count=0,
                error_message=str(e),
                duration_ms=duration_ms,
            )

    async def health_check(self) -> bool:
        """Check if adapter is properly configured.

        Returns:
            True if credentials can authenticate, False otherwise
        """
        try:
            self._get_client()
            return True
        except Exception:
            return False
