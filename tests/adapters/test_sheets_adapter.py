"""Tests for SheetsAdapter."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.sheets_adapter import SheetsAdapter


@pytest.fixture
def mock_gspread():
    """Mock gspread module."""
    with patch("src.adapters.sheets_adapter.gspread") as mock:
        yield mock


@pytest.fixture
def mock_credentials():
    """Mock google.oauth2.service_account.Credentials."""
    with patch("src.adapters.sheets_adapter.Credentials") as mock:
        yield mock


class TestSheetsAdapterInit:
    """Tests for SheetsAdapter initialization."""

    def test_uses_provided_credentials(self, mock_gspread, mock_credentials):
        """Should use credentials path passed to constructor."""
        adapter = SheetsAdapter(credentials_path="/path/to/creds.json")
        adapter._get_client()

        mock_credentials.from_service_account_file.assert_called_once()
        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/path/to/creds.json"

    def test_falls_back_to_env_var(self, mock_gspread, mock_credentials, monkeypatch):
        """Should fall back to GOOGLE_SHEETS_CREDENTIALS env var."""
        monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/env/creds.json")
        adapter = SheetsAdapter()
        adapter._get_client()

        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/env/creds.json"

    def test_missing_credentials_raises_value_error(self, mock_gspread, monkeypatch):
        """Should raise ValueError when no credentials available."""
        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
        adapter = SheetsAdapter()

        with pytest.raises(ValueError, match="No credentials"):
            adapter._get_client()


class TestWriteRaidItems:
    """Tests for write_raid_items method."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_success_without_api_call(
        self, mock_gspread, mock_credentials
    ):
        """Dry run should return success without calling API."""
        adapter = SheetsAdapter(credentials_path="/test/creds.json")
        items = [
            {"uuid": "123", "type": "Action", "description": "Test task"},
            {"uuid": "456", "type": "Risk", "description": "Test risk"},
        ]

        result = await adapter.write_raid_items(
            spreadsheet_id="sheet123",
            items=items,
            dry_run=True,
        )

        assert result.success is True
        assert result.dry_run is True
        assert result.item_count == 2
        assert result.external_id == "sheet123"
        # No API call should be made
        mock_gspread.authorize.assert_not_called()

    @pytest.mark.asyncio
    async def test_write_raid_items_with_mock(self, mock_gspread, mock_credentials):
        """Should call batch_update with correct data."""
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_values.return_value = [
            ["UUID", "Type", "Description", "Owner", "Due Date", "Status", "Confidence"]
        ]
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_gspread.authorize.return_value = mock_client

        adapter = SheetsAdapter(credentials_path="/test/creds.json")
        items = [
            {
                "uuid": "item-1",
                "type": "Action",
                "description": "Follow up with team",
                "owner": "Alice",
                "due_date": "2025-01-20",
                "status": "Open",
                "confidence": "0.85",
            }
        ]

        result = await adapter.write_raid_items(
            spreadsheet_id="sheet123",
            items=items,
            sheet_name="RAID",
        )

        assert result.success is True
        assert result.dry_run is False
        assert result.item_count == 1
        mock_worksheet.update.assert_called()
        call_args = mock_worksheet.update.call_args
        # Check data was passed correctly
        assert call_args[0][1][0][0] == "item-1"
        assert call_args[0][1][0][1] == "Action"
        assert call_args[0][1][0][2] == "Follow up with team"

    @pytest.mark.asyncio
    async def test_write_result_fields_populated(self, mock_gspread, mock_credentials):
        """WriteResult should have all fields populated."""
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_values.return_value = [[]]
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_gspread.authorize.return_value = mock_client

        adapter = SheetsAdapter(credentials_path="/test/creds.json")
        items = [{"uuid": "1", "type": "Decision", "description": "Test"}]

        result = await adapter.write_raid_items(
            spreadsheet_id="abc123",
            items=items,
        )

        assert result.success is True
        assert result.dry_run is False
        assert result.item_count == 1
        assert result.external_id == "abc123"
        assert result.url == "https://docs.google.com/spreadsheets/d/abc123"
        assert result.duration_ms is not None
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_creates_worksheet_if_not_found(self, mock_gspread, mock_credentials):
        """Should create worksheet if it doesn't exist."""
        import gspread

        mock_new_worksheet = MagicMock()
        mock_new_worksheet.get_all_values.return_value = []
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound("RAID")
        mock_spreadsheet.add_worksheet.return_value = mock_new_worksheet
        mock_client = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_gspread.authorize.return_value = mock_client
        mock_gspread.WorksheetNotFound = gspread.WorksheetNotFound

        adapter = SheetsAdapter(credentials_path="/test/creds.json")
        items = [{"uuid": "1", "type": "Action", "description": "Test"}]

        result = await adapter.write_raid_items(
            spreadsheet_id="sheet123",
            items=items,
        )

        assert result.success is True
        mock_spreadsheet.add_worksheet.assert_called_once()


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_gspread, mock_credentials):
        """Should return True when credentials work."""
        adapter = SheetsAdapter(credentials_path="/test/creds.json")

        result = await adapter.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_gspread, mock_credentials):
        """Should return False when credentials fail."""
        mock_credentials.from_service_account_file.side_effect = Exception(
            "Invalid credentials"
        )
        adapter = SheetsAdapter(credentials_path="/test/creds.json")

        result = await adapter.health_check()

        assert result is False
