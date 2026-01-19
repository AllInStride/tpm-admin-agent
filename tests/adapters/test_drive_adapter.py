"""Tests for DriveAdapter."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.drive_adapter import DriveAdapter


@pytest.fixture
def mock_build():
    """Mock googleapiclient.discovery.build."""
    with patch("src.adapters.drive_adapter.build") as mock:
        yield mock


@pytest.fixture
def mock_credentials():
    """Mock google.oauth2.service_account.Credentials."""
    with patch("src.adapters.drive_adapter.Credentials") as mock:
        yield mock


class TestDriveAdapterInit:
    """Tests for DriveAdapter initialization."""

    def test_uses_provided_credentials(self, mock_build, mock_credentials):
        """Should use credentials path passed to constructor."""
        adapter = DriveAdapter(credentials_path="/path/to/creds.json")
        adapter._get_service()

        mock_credentials.from_service_account_file.assert_called_once()
        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/path/to/creds.json"

    def test_falls_back_to_drive_env_var(
        self, mock_build, mock_credentials, monkeypatch
    ):
        """Should fall back to GOOGLE_DRIVE_CREDENTIALS env var."""
        monkeypatch.setenv("GOOGLE_DRIVE_CREDENTIALS", "/drive/creds.json")
        adapter = DriveAdapter()
        adapter._get_service()

        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/drive/creds.json"

    def test_falls_back_to_sheets_env_var(
        self, mock_build, mock_credentials, monkeypatch
    ):
        """Should fall back to GOOGLE_SHEETS_CREDENTIALS if drive not set."""
        monkeypatch.delenv("GOOGLE_DRIVE_CREDENTIALS", raising=False)
        monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/sheets/creds.json")
        adapter = DriveAdapter()
        adapter._get_service()

        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/sheets/creds.json"

    def test_missing_credentials_raises_value_error(self, mock_build, monkeypatch):
        """Should raise ValueError when no credentials available."""
        monkeypatch.delenv("GOOGLE_DRIVE_CREDENTIALS", raising=False)
        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
        adapter = DriveAdapter()

        with pytest.raises(ValueError, match="No credentials"):
            adapter._get_service()


class TestUploadMinutes:
    """Tests for upload_minutes method."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_success_without_api_call(
        self, mock_build, mock_credentials
    ):
        """Dry run should return success without calling API."""
        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.upload_minutes(
            content="# Meeting Minutes\n\nTest content",
            filename="2025-01-15-meeting.md",
            folder_id="folder123",
            dry_run=True,
        )

        assert result.success is True
        assert result.dry_run is True
        assert result.item_count == 1
        # No API call should be made
        mock_build.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_minutes_with_mock(self, mock_build, mock_credentials):
        """Should call files().create() with correct parameters."""
        mock_service = MagicMock()
        mock_service.files().create().execute.return_value = {
            "id": "file123",
            "webViewLink": "https://drive.google.com/file/d/file123/view",
        }
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.upload_minutes(
            content="# Meeting Minutes\n\nTest content",
            filename="2025-01-15-meeting.md",
            folder_id="folder123",
        )

        assert result.success is True
        assert result.dry_run is False
        mock_service.files().create.assert_called()

    @pytest.mark.asyncio
    async def test_upload_returns_file_id(self, mock_build, mock_credentials):
        """Should populate external_id from API response."""
        mock_service = MagicMock()
        mock_service.files().create().execute.return_value = {
            "id": "uploaded-file-id",
            "webViewLink": "https://drive.google.com/file/d/uploaded-file-id/view",
        }
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.upload_minutes(
            content="Content",
            filename="test.md",
            folder_id="folder123",
        )

        assert result.external_id == "uploaded-file-id"

    @pytest.mark.asyncio
    async def test_upload_returns_web_link(self, mock_build, mock_credentials):
        """Should populate url from API response webViewLink."""
        mock_service = MagicMock()
        mock_service.files().create().execute.return_value = {
            "id": "file123",
            "webViewLink": "https://drive.google.com/file/d/file123/view",
        }
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.upload_minutes(
            content="Content",
            filename="test.md",
            folder_id="folder123",
        )

        assert result.url == "https://drive.google.com/file/d/file123/view"

    @pytest.mark.asyncio
    async def test_mime_type_markdown(self, mock_build, mock_credentials):
        """Should work with text/markdown MIME type."""
        mock_service = MagicMock()
        mock_service.files().create().execute.return_value = {"id": "f1"}
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.upload_minutes(
            content="# Markdown",
            filename="test.md",
            folder_id="folder123",
            mime_type="text/markdown",
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_mime_type_html(self, mock_build, mock_credentials):
        """Should work with text/html MIME type."""
        mock_service = MagicMock()
        mock_service.files().create().execute.return_value = {"id": "f2"}
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.upload_minutes(
            content="<html><body>Test</body></html>",
            filename="test.html",
            folder_id="folder123",
            mime_type="text/html",
        )

        assert result.success is True


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_build, mock_credentials):
        """Should return True when credentials work."""
        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_build, mock_credentials):
        """Should return False when credentials fail."""
        mock_credentials.from_service_account_file.side_effect = Exception(
            "Invalid credentials"
        )
        adapter = DriveAdapter(credentials_path="/test/creds.json")

        result = await adapter.health_check()

        assert result is False
