"""Adapter for loading project rosters from Google Sheets.

Uses gspread library with service account authentication to read
roster data from Google Sheets.
"""

import os

import gspread
import structlog
from google.oauth2.service_account import Credentials

from src.identity.schemas import RosterEntry

logger = structlog.get_logger()


class RosterAdapter:
    """Adapter for loading project rosters from Google Sheets.

    Expected sheet format (per CONTEXT.md):
    - Required columns: Name, Email
    - Optional columns: Slack handle, Role, Aliases (comma-separated)
    """

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
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

    def load_roster(
        self, spreadsheet_id: str, sheet_name: str = "Roster"
    ) -> list[RosterEntry]:
        """Load roster from Google Sheet.

        Args:
            spreadsheet_id: Google Sheets ID (from URL)
            sheet_name: Name of worksheet (default: "Roster")

        Returns:
            List of RosterEntry objects

        Raises:
            ValueError: If required columns missing
        """
        client = self._get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)

        # Get all records as list of dicts (header row becomes keys)
        records = worksheet.get_all_records()

        # Validate required columns
        if not records:
            return []

        first_row = records[0]
        if "Name" not in first_row or "Email" not in first_row:
            raise ValueError(
                "Roster sheet must have 'Name' and 'Email' columns. "
                f"Found columns: {list(first_row.keys())}"
            )

        # Parse entries (best effort - skip malformed rows)
        entries = []
        for row in records:
            try:
                if row.get("Name") and row.get("Email"):
                    entries.append(RosterEntry.from_sheet_row(row))
            except Exception as e:
                logger.warning(
                    "Skipping malformed roster row",
                    row=row,
                    error=str(e),
                )

        return entries
