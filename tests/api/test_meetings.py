"""Tests for meetings API endpoints."""

import io

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.meetings import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application with just the meetings router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUploadEndpoint:
    """Tests for POST /meetings/upload endpoint."""

    async def test_upload_missing_file_returns_422(self, client: AsyncClient) -> None:
        """Endpoint returns 422 when no file is provided."""
        response = await client.post("/meetings/upload")
        assert response.status_code == 422

    async def test_upload_valid_vtt_returns_200(self, client: AsyncClient) -> None:
        """Endpoint returns 200 for valid VTT file."""
        content = b"WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello world"
        files = {"file": ("test.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "validated"
        assert data["filename"] == "test.vtt"
        assert data["format"] == ".vtt"

    async def test_upload_valid_srt_returns_200(self, client: AsyncClient) -> None:
        """Endpoint returns 200 for valid SRT file."""
        content = b"1\n00:00:00,000 --> 00:00:05,000\nHello world\n"
        files = {"file": ("test.srt", io.BytesIO(content), "application/x-subrip")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "validated"
        assert data["format"] == ".srt"

    async def test_upload_empty_file_returns_400(self, client: AsyncClient) -> None:
        """Endpoint returns 400 for empty file."""
        files = {"file": ("empty.vtt", io.BytesIO(b""), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    async def test_upload_unsupported_extension_returns_415(
        self, client: AsyncClient
    ) -> None:
        """Endpoint returns 415 for unsupported file extension."""
        files = {"file": ("test.txt", io.BytesIO(b"some content"), "text/plain")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 415
        assert "unsupported" in response.json()["detail"].lower()

    async def test_upload_large_file_returns_413(self, client: AsyncClient) -> None:
        """Endpoint returns 413 for files exceeding size limit."""
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        files = {"file": ("large.vtt", io.BytesIO(large_content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    async def test_upload_utf8_encoded_file(self, client: AsyncClient) -> None:
        """Endpoint handles UTF-8 encoded files."""
        # UTF-8 content with special characters
        content = b"WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello world - cafe"
        files = {"file": ("utf8.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 200

    async def test_upload_latin1_encoded_file(self, client: AsyncClient) -> None:
        """Endpoint handles Latin-1 encoded files."""
        # Latin-1 content with special characters that aren't valid UTF-8
        content = "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\ncafe".encode("latin-1")
        files = {"file": ("latin1.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 200

    async def test_upload_utf8_bom_file(self, client: AsyncClient) -> None:
        """Endpoint handles UTF-8 files with BOM."""
        # UTF-8 with BOM
        content = b"\xef\xbb\xbfWEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello"
        files = {"file": ("bom.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)
        assert response.status_code == 200
