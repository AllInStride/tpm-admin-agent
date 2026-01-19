"""Tests for SmartsheetAdapter."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.smartsheet_adapter import SmartsheetAdapter
from src.integration.schemas import RaidRowData


@pytest.fixture
def mock_smartsheet_client():
    """Mock smartsheet.Smartsheet client."""
    with patch("src.adapters.smartsheet_adapter.smartsheet.Smartsheet") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def smartsheet_adapter():
    """SmartsheetAdapter with test token."""
    return SmartsheetAdapter(access_token="test-token")


@pytest.fixture
def sample_raid_items():
    """Sample RaidRowData items for testing."""
    return [
        RaidRowData(
            type="Action",
            title="Review the project timeline",
            owner="alice@example.com",
            status="Open",
            due_date="2026-01-25",
            source_meeting="Sprint Planning 2026-01-19",
            created_date="2026-01-19",
            confidence=0.9,
            item_hash="abc123",
        ),
        RaidRowData(
            type="Risk",
            title="Budget overrun possible",
            owner="bob@example.com",
            status="Identified",
            due_date=None,
            source_meeting="Sprint Planning 2026-01-19",
            created_date="2026-01-19",
            confidence=0.85,
            item_hash="def456",
        ),
    ]


@pytest.fixture
def mock_column_map():
    """Standard column ID mapping."""
    return {
        "Type": 1001,
        "Title": 1002,
        "Owner": 1003,
        "Status": 1004,
        "Due Date": 1005,
        "Source Meeting": 1006,
        "Created Date": 1007,
        "Confidence": 1008,
        "Item Hash": 1009,
    }


class TestSmartsheetAdapterInit:
    """Tests for SmartsheetAdapter initialization."""

    def test_uses_provided_token(self, mock_smartsheet_client):
        """Should use token passed to constructor."""
        adapter = SmartsheetAdapter(access_token="my-token")
        adapter._get_client()

        # Import to check call
        from src.adapters.smartsheet_adapter import smartsheet

        smartsheet.Smartsheet.assert_called_once_with(access_token="my-token")

    def test_falls_back_to_env_var(self, mock_smartsheet_client, monkeypatch):
        """Should fall back to SMARTSHEET_ACCESS_TOKEN env var."""
        monkeypatch.setenv("SMARTSHEET_ACCESS_TOKEN", "env-token")
        adapter = SmartsheetAdapter()
        adapter._get_client()

        from src.adapters.smartsheet_adapter import smartsheet

        smartsheet.Smartsheet.assert_called_once_with(access_token="env-token")

    def test_no_token_raises_value_error(self, mock_smartsheet_client, monkeypatch):
        """Should raise ValueError when no token available."""
        monkeypatch.delenv("SMARTSHEET_ACCESS_TOKEN", raising=False)
        adapter = SmartsheetAdapter()

        with pytest.raises(ValueError, match="No Smartsheet token"):
            adapter._get_client()


class TestCreateSheet:
    """Tests for create_sheet method."""

    @pytest.mark.asyncio
    async def test_create_sheet_success(
        self, mock_smartsheet_client, smartsheet_adapter
    ):
        """Should create sheet with RAID columns."""
        mock_response = MagicMock()
        mock_response.result.id = 12345
        mock_response.result.permalink = "https://app.smartsheet.com/sheets/12345"
        mock_smartsheet_client.Home.create_sheet.return_value = mock_response

        result = await smartsheet_adapter.create_sheet("Test RAID Log")

        assert result.success is True
        assert result.external_id == "12345"
        assert result.sheet_url == "https://app.smartsheet.com/sheets/12345"
        mock_smartsheet_client.Home.create_sheet.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sheet_in_folder(
        self, mock_smartsheet_client, smartsheet_adapter
    ):
        """Should create sheet in specified folder."""
        mock_response = MagicMock()
        mock_response.result.id = 67890
        mock_response.result.permalink = "https://app.smartsheet.com/sheets/67890"
        mock_smartsheet_client.Folders.create_sheet_in_folder.return_value = (
            mock_response
        )

        result = await smartsheet_adapter.create_sheet("Test RAID Log", folder_id=999)

        assert result.success is True
        mock_smartsheet_client.Folders.create_sheet_in_folder.assert_called_once()
        call_args = mock_smartsheet_client.Folders.create_sheet_in_folder.call_args
        assert call_args[0][0] == 999

    @pytest.mark.asyncio
    async def test_create_sheet_dry_run(self, smartsheet_adapter):
        """Should return success without API call in dry run."""
        result = await smartsheet_adapter.create_sheet("Test Sheet", dry_run=True)

        assert result.success is True
        assert result.dry_run is True
        assert result.item_count == 0


class TestWriteRaidItems:
    """Tests for write_raid_items method."""

    @pytest.mark.asyncio
    async def test_write_raid_items_success(
        self,
        mock_smartsheet_client,
        smartsheet_adapter,
        sample_raid_items,
        mock_column_map,
    ):
        """Should write items and return row IDs."""
        # Mock column fetch
        mock_sheet = MagicMock()
        mock_sheet.columns = [
            MagicMock(title=title, id=col_id)
            for title, col_id in mock_column_map.items()
        ]
        mock_smartsheet_client.Sheets.get_sheet.return_value = mock_sheet

        # Mock add_rows
        mock_row1 = MagicMock(id=101)
        mock_row2 = MagicMock(id=102)
        mock_response = MagicMock()
        mock_response.result = [mock_row1, mock_row2]
        mock_smartsheet_client.Sheets.add_rows.return_value = mock_response

        result = await smartsheet_adapter.write_raid_items(12345, sample_raid_items)

        assert result.success is True
        assert result.item_count == 2
        assert result.row_ids == [101, 102]
        assert result.external_id == "12345"

    @pytest.mark.asyncio
    async def test_write_raid_items_batching(
        self,
        mock_smartsheet_client,
        smartsheet_adapter,
        mock_column_map,
    ):
        """Should chunk items at BATCH_SIZE."""
        # Create 150 items to trigger batching (BATCH_SIZE=100)
        items = [
            RaidRowData(
                type="Action",
                title=f"Item {i}",
                confidence=0.9,
            )
            for i in range(150)
        ]

        # Mock column fetch
        mock_sheet = MagicMock()
        mock_sheet.columns = [
            MagicMock(title=title, id=col_id)
            for title, col_id in mock_column_map.items()
        ]
        mock_smartsheet_client.Sheets.get_sheet.return_value = mock_sheet

        # Mock add_rows to return appropriate number of rows
        def add_rows_side_effect(sheet_id, rows):
            response = MagicMock()
            response.result = [MagicMock(id=i) for i in range(len(rows))]
            return response

        mock_smartsheet_client.Sheets.add_rows.side_effect = add_rows_side_effect

        result = await smartsheet_adapter.write_raid_items(12345, items)

        assert result.success is True
        assert result.item_count == 150
        # Should have made 2 calls (100 + 50)
        assert mock_smartsheet_client.Sheets.add_rows.call_count == 2

    @pytest.mark.asyncio
    async def test_write_raid_items_empty_list(
        self,
        smartsheet_adapter,
    ):
        """Should return success with 0 count for empty items."""
        result = await smartsheet_adapter.write_raid_items(12345, [])

        assert result.success is True
        assert result.item_count == 0

    @pytest.mark.asyncio
    async def test_write_raid_items_dry_run(
        self,
        smartsheet_adapter,
        sample_raid_items,
    ):
        """Should return success without API call in dry run."""
        result = await smartsheet_adapter.write_raid_items(
            12345, sample_raid_items, dry_run=True
        )

        assert result.success is True
        assert result.dry_run is True
        assert result.item_count == 2


class TestColumnMapping:
    """Tests for column mapping functionality."""

    def test_column_map_fetched(
        self,
        mock_smartsheet_client,
        smartsheet_adapter,
        mock_column_map,
    ):
        """Should fetch column IDs from sheet."""
        mock_sheet = MagicMock()
        mock_sheet.columns = [
            MagicMock(title=title, id=col_id)
            for title, col_id in mock_column_map.items()
        ]
        mock_smartsheet_client.Sheets.get_sheet.return_value = mock_sheet

        result = smartsheet_adapter._get_column_map(12345)

        assert result == mock_column_map
        mock_smartsheet_client.Sheets.get_sheet.assert_called_once_with(12345)


class TestItemToRow:
    """Tests for item to row conversion."""

    def test_item_to_row_mapping(
        self,
        smartsheet_adapter,
        sample_raid_items,
        mock_column_map,
    ):
        """Should convert RaidRowData to Row with correct cells."""
        item = sample_raid_items[0]
        row = smartsheet_adapter._item_to_row(item, mock_column_map)

        assert row.to_bottom is True

        # Extract cell values by column_id
        cell_values = {cell.column_id: cell.value for cell in row.cells}

        assert cell_values[1001] == "Action"
        assert cell_values[1002] == "Review the project timeline"
        assert cell_values[1003] == "alice@example.com"
        assert cell_values[1004] == "Open"
        assert cell_values[1005] == "2026-01-25"
        assert cell_values[1008] == "0.9"
        assert cell_values[1009] == "abc123"

    def test_date_format_iso(
        self,
        smartsheet_adapter,
        mock_column_map,
    ):
        """Should format dates as YYYY-MM-DD."""
        item = RaidRowData(
            type="Action",
            title="Test item",
            due_date="2026-12-31",
            created_date="2026-01-15",
            confidence=0.8,
        )

        row = smartsheet_adapter._item_to_row(item, mock_column_map)
        cell_values = {cell.column_id: cell.value for cell in row.cells}

        assert cell_values[1005] == "2026-12-31"
        assert cell_values[1007] == "2026-01-15"

    def test_skips_empty_values(
        self,
        smartsheet_adapter,
        mock_column_map,
    ):
        """Should not create cells for empty/None values."""
        item = RaidRowData(
            type="Risk",
            title="Minimal item",
            confidence=0.7,
        )

        row = smartsheet_adapter._item_to_row(item, mock_column_map)
        column_ids = {cell.column_id for cell in row.cells}

        # Should have Type, Title, Confidence
        assert 1001 in column_ids  # Type
        assert 1002 in column_ids  # Title
        assert 1008 in column_ids  # Confidence

        # Should NOT have Owner, Due Date, etc. (empty values)
        assert 1003 not in column_ids  # Owner (empty string)
        assert 1005 not in column_ids  # Due Date (None)


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        mock_smartsheet_client,
        smartsheet_adapter,
    ):
        """Should return True when API accessible."""
        mock_smartsheet_client.Users.get_current_user.return_value = {"id": 123}

        result = await smartsheet_adapter.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_no_token(self, monkeypatch):
        """Should return False when no token configured."""
        monkeypatch.delenv("SMARTSHEET_ACCESS_TOKEN", raising=False)
        adapter = SmartsheetAdapter()

        result = await adapter.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_api_error(
        self,
        mock_smartsheet_client,
        smartsheet_adapter,
    ):
        """Should return False on API error."""
        mock_smartsheet_client.Users.get_current_user.side_effect = Exception(
            "API Error"
        )

        result = await smartsheet_adapter.health_check()

        assert result is False


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_create_sheet_error(
        self,
        mock_smartsheet_client,
        smartsheet_adapter,
    ):
        """Should return failure result on error."""
        mock_smartsheet_client.Home.create_sheet.side_effect = Exception("API Error")

        result = await smartsheet_adapter.create_sheet("Test Sheet")

        assert result.success is False
        assert "API Error" in result.error_message

    @pytest.mark.asyncio
    async def test_write_items_error(
        self,
        mock_smartsheet_client,
        smartsheet_adapter,
        sample_raid_items,
        mock_column_map,
    ):
        """Should return failure result on write error."""
        # Mock column fetch
        mock_sheet = MagicMock()
        mock_sheet.columns = [
            MagicMock(title=title, id=col_id)
            for title, col_id in mock_column_map.items()
        ]
        mock_smartsheet_client.Sheets.get_sheet.return_value = mock_sheet

        # Mock add_rows to fail
        mock_smartsheet_client.Sheets.add_rows.side_effect = Exception("Write failed")

        result = await smartsheet_adapter.write_raid_items(12345, sample_raid_items)

        assert result.success is False
        assert "Write failed" in result.error_message
