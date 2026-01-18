"""Tests for RosterAdapter - Google Sheets roster loading."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.roster_adapter import RosterAdapter
from src.identity.schemas import RosterEntry


class TestRosterEntryFromSheetRow:
    """Tests for RosterEntry.from_sheet_row parsing."""

    def test_from_sheet_row_parses_required_fields(self):
        """Should parse Name and Email from sheet row."""
        row = {
            "Name": "John Smith",
            "Email": "john.smith@example.com",
        }

        entry = RosterEntry.from_sheet_row(row)

        assert entry.name == "John Smith"
        assert entry.email == "john.smith@example.com"
        assert entry.aliases == []
        assert entry.slack_handle is None
        assert entry.role is None

    def test_from_sheet_row_parses_aliases(self):
        """Should parse comma-separated aliases."""
        row = {
            "Name": "Robert Johnson",
            "Email": "robert.johnson@example.com",
            "Aliases": "Bob, Bobby, RJ",
        }

        entry = RosterEntry.from_sheet_row(row)

        assert entry.name == "Robert Johnson"
        assert entry.email == "robert.johnson@example.com"
        assert entry.aliases == ["Bob", "Bobby", "RJ"]

    def test_from_sheet_row_handles_empty_aliases(self):
        """Should handle empty aliases string."""
        row = {
            "Name": "Alice Chen",
            "Email": "alice.chen@example.com",
            "Aliases": "",
        }

        entry = RosterEntry.from_sheet_row(row)

        assert entry.aliases == []

    def test_from_sheet_row_parses_all_optional_fields(self):
        """Should parse all optional columns when present."""
        row = {
            "Name": "Sarah Williams",
            "Email": "sarah.williams@example.com",
            "Slack handle": "@swilliams",
            "Role": "Tech Lead",
            "Aliases": "Sarah, SW",
        }

        entry = RosterEntry.from_sheet_row(row)

        assert entry.name == "Sarah Williams"
        assert entry.email == "sarah.williams@example.com"
        assert entry.slack_handle == "@swilliams"
        assert entry.role == "Tech Lead"
        assert entry.aliases == ["Sarah", "SW"]

    def test_from_sheet_row_handles_missing_optional(self):
        """Should handle missing optional columns gracefully."""
        row = {
            "Name": "Tom Davis",
            "Email": "tom.davis@example.com",
        }

        entry = RosterEntry.from_sheet_row(row)

        assert entry.name == "Tom Davis"
        assert entry.email == "tom.davis@example.com"
        assert entry.slack_handle is None
        assert entry.role is None
        assert entry.aliases == []


class TestRosterAdapterInit:
    """Tests for RosterAdapter initialization."""

    def test_init_with_explicit_path(self):
        """Should store explicit credentials path."""
        adapter = RosterAdapter(credentials_path="/path/to/creds.json")
        assert adapter._credentials_path == "/path/to/creds.json"

    def test_init_with_env_var(self):
        """Should fall back to env var when no path provided."""
        with patch.dict("os.environ", {"GOOGLE_SHEETS_CREDENTIALS": "/env/creds.json"}):
            adapter = RosterAdapter()
            assert adapter._credentials_path == "/env/creds.json"

    def test_init_no_credentials(self):
        """Should store None if no credentials configured."""
        with patch.dict("os.environ", {}, clear=True):
            adapter = RosterAdapter()
            assert adapter._credentials_path is None


class TestRosterAdapterGetClient:
    """Tests for RosterAdapter._get_client authentication."""

    def test_get_client_raises_without_credentials(self):
        """Should raise ValueError if no credentials configured."""
        with patch.dict("os.environ", {}, clear=True):
            adapter = RosterAdapter()

            with pytest.raises(ValueError) as exc:
                adapter._get_client()

            assert "No credentials" in str(exc.value)
            assert "GOOGLE_SHEETS_CREDENTIALS" in str(exc.value)

    @patch("src.adapters.roster_adapter.gspread.authorize")
    @patch("src.adapters.roster_adapter.Credentials.from_service_account_file")
    def test_get_client_authenticates_with_scopes(
        self, mock_creds_from_file, mock_authorize
    ):
        """Should authenticate with correct scopes."""
        mock_creds = MagicMock()
        mock_creds_from_file.return_value = mock_creds
        mock_client = MagicMock()
        mock_authorize.return_value = mock_client

        adapter = RosterAdapter(credentials_path="/path/to/creds.json")
        client = adapter._get_client()

        mock_creds_from_file.assert_called_once_with(
            "/path/to/creds.json",
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        mock_authorize.assert_called_once_with(mock_creds)
        assert client == mock_client

    @patch("src.adapters.roster_adapter.gspread.authorize")
    @patch("src.adapters.roster_adapter.Credentials.from_service_account_file")
    def test_get_client_caches_client(self, mock_creds_from_file, mock_authorize):
        """Should reuse cached client on subsequent calls."""
        mock_client = MagicMock()
        mock_authorize.return_value = mock_client

        adapter = RosterAdapter(credentials_path="/path/to/creds.json")
        client1 = adapter._get_client()
        client2 = adapter._get_client()

        assert client1 is client2
        assert mock_authorize.call_count == 1


class TestRosterAdapterLoadRoster:
    """Tests for RosterAdapter.load_roster functionality."""

    def _create_adapter_with_mocked_client(self, records: list[dict]) -> RosterAdapter:
        """Create adapter with mocked gspread client returning given records."""
        adapter = RosterAdapter(credentials_path="/path/to/creds.json")

        # Create mock chain: client -> spreadsheet -> worksheet -> records
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = records

        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet

        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet

        adapter._client = mock_client
        return adapter

    def test_load_roster_returns_entries(self):
        """Should return RosterEntry list from sheet records."""
        records = [
            {"Name": "Alice Chen", "Email": "alice@example.com"},
            {"Name": "Bob Smith", "Email": "bob@example.com"},
        ]
        adapter = self._create_adapter_with_mocked_client(records)

        entries = adapter.load_roster("spreadsheet-id-123")

        assert len(entries) == 2
        assert entries[0].name == "Alice Chen"
        assert entries[0].email == "alice@example.com"
        assert entries[1].name == "Bob Smith"

    def test_load_roster_validates_required_columns(self):
        """Should raise ValueError if required columns missing."""
        records = [
            {"Person": "Alice Chen", "Contact": "alice@example.com"},
        ]
        adapter = self._create_adapter_with_mocked_client(records)

        with pytest.raises(ValueError) as exc:
            adapter.load_roster("spreadsheet-id-123")

        assert "Name" in str(exc.value)
        assert "Email" in str(exc.value)

    def test_load_roster_handles_empty_sheet(self):
        """Should return empty list for empty sheet."""
        adapter = self._create_adapter_with_mocked_client([])

        entries = adapter.load_roster("spreadsheet-id-123")

        assert entries == []

    def test_load_roster_skips_malformed_rows(self):
        """Should skip rows with missing required fields."""
        records = [
            {"Name": "Alice Chen", "Email": "alice@example.com"},
            {"Name": "", "Email": "noname@example.com"},  # Empty name
            {"Name": "NoEmail", "Email": ""},  # Empty email
            {"Name": "Bob Smith", "Email": "bob@example.com"},
        ]
        adapter = self._create_adapter_with_mocked_client(records)

        entries = adapter.load_roster("spreadsheet-id-123")

        assert len(entries) == 2
        assert entries[0].name == "Alice Chen"
        assert entries[1].name == "Bob Smith"

    def test_load_roster_with_custom_sheet_name(self):
        """Should use custom sheet name when provided."""
        adapter = self._create_adapter_with_mocked_client([])

        # Access the mock spreadsheet to verify worksheet name
        adapter.load_roster("spreadsheet-id-123", sheet_name="Team Members")

        mock_spreadsheet = adapter._client.open_by_key.return_value
        mock_spreadsheet.worksheet.assert_called_once_with("Team Members")

    def test_load_roster_parses_all_fields(self):
        """Should parse all optional fields from records."""
        records = [
            {
                "Name": "Sarah Williams",
                "Email": "sarah@example.com",
                "Slack handle": "@sarah",
                "Role": "PM",
                "Aliases": "SW, Sarah W",
            },
        ]
        adapter = self._create_adapter_with_mocked_client(records)

        entries = adapter.load_roster("spreadsheet-id-123")

        assert len(entries) == 1
        entry = entries[0]
        assert entry.name == "Sarah Williams"
        assert entry.email == "sarah@example.com"
        assert entry.slack_handle == "@sarah"
        assert entry.role == "PM"
        assert entry.aliases == ["SW", "Sarah W"]
