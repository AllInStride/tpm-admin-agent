"""Tests for DriveAdapter extended methods (search_project_docs)."""

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


class TestSearchProjectDocs:
    """Tests for search_project_docs method."""

    @pytest.mark.asyncio
    async def test_returns_docs_from_folder(self, mock_build, mock_credentials):
        """Should return documents from specified folder."""
        mock_service = MagicMock()
        mock_files = [
            {
                "id": "doc1",
                "name": "Project Spec.docx",
                "webViewLink": "https://drive.google.com/file/d/doc1/view",
                "modifiedTime": "2026-01-15T10:00:00.000Z",
                "mimeType": "application/vnd.google-apps.document",
            },
        ]
        mock_service.files().list().execute.return_value = {"files": mock_files}
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")
        result = await adapter.search_project_docs("folder123")

        assert len(result) == 1
        assert result[0]["id"] == "doc1"

    @pytest.mark.asyncio
    async def test_empty_folder_returns_empty_list(self, mock_build, mock_credentials):
        """Should return empty list for folder with no documents."""
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {"files": []}
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")
        result = await adapter.search_project_docs("folder123")

        assert result == []

    @pytest.mark.asyncio
    async def test_error_returns_empty_list(self, mock_build, mock_credentials):
        """Should return empty list on API error."""
        mock_service = MagicMock()
        mock_service.files().list().execute.side_effect = Exception("API error")
        mock_build.return_value = mock_service

        adapter = DriveAdapter(credentials_path="/test/creds.json")
        result = await adapter.search_project_docs("folder123")

        assert result == []
