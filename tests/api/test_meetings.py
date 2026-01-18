"""Integration tests for meetings API endpoints."""

import io
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.meetings import router
from src.events.bus import EventBus


@pytest.fixture
def mock_event_bus() -> EventBus:
    """Create a mock EventBus for testing."""
    bus = EventBus(store=None)
    bus.publish_and_store = AsyncMock()  # type: ignore[method-assign]
    return bus


@pytest.fixture
def app(mock_event_bus: EventBus) -> FastAPI:
    """Create a test FastAPI application with mock EventBus."""
    test_app = FastAPI()
    test_app.state.event_bus = mock_event_bus
    test_app.include_router(router)
    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUploadEndpoint:
    """Integration tests for POST /meetings/upload endpoint."""

    async def test_upload_missing_file_returns_422(self, client: AsyncClient) -> None:
        """Endpoint returns 422 when no file is provided."""
        response = await client.post("/meetings/upload")
        assert response.status_code == 422

    async def test_upload_valid_vtt_returns_200(
        self, client: AsyncClient, mock_event_bus: EventBus
    ) -> None:
        """Endpoint returns 200 for valid VTT file with speaker tags."""
        content = b"""WEBVTT

00:00:01.000 --> 00:00:05.000
<v Alice>Let's start the meeting

00:00:05.000 --> 00:00:10.000
<v Bob>Sounds good, I have an update

00:00:10.000 --> 00:00:15.000
<v Alice>Go ahead Bob
"""
        files = {"file": ("team_standup.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "id" in data
        assert data["title"] == "team standup"
        assert data["speaker_count"] == 2  # Alice and Bob
        assert data["utterance_count"] == 3
        assert data["duration_seconds"] == 15.0
        assert "date" in data

        # Verify events were published
        assert mock_event_bus.publish_and_store.call_count == 2  # type: ignore[attr-defined]

    async def test_upload_valid_srt_returns_200(
        self, client: AsyncClient, mock_event_bus: EventBus
    ) -> None:
        """Endpoint returns 200 for valid SRT file (no voice tags)."""
        content = b"""1
00:00:00,000 --> 00:00:05,000
Hello world

2
00:00:05,000 --> 00:00:10,000
This is a test
"""
        files = {"file": ("test.srt", io.BytesIO(content), "application/x-subrip")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["title"] == "test"
        assert data["speaker_count"] == 1  # Unknown Speaker (no voice tags in SRT)
        assert data["utterance_count"] == 2

        # Verify events were published
        assert mock_event_bus.publish_and_store.call_count == 2  # type: ignore[attr-defined]

    async def test_upload_invalid_extension_returns_415(
        self, client: AsyncClient
    ) -> None:
        """Endpoint returns 415 for unsupported file extension."""
        files = {"file": ("test.txt", io.BytesIO(b"some content"), "text/plain")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 415
        assert "unsupported" in response.json()["detail"].lower()

    async def test_upload_empty_file_returns_400(self, client: AsyncClient) -> None:
        """Endpoint returns 400 for empty file."""
        files = {"file": ("empty.vtt", io.BytesIO(b""), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    async def test_upload_malformed_vtt_returns_400(self, client: AsyncClient) -> None:
        """Endpoint returns 400 for malformed VTT content."""
        content = b"not a valid vtt file at all\n\nrandom garbage content"
        files = {"file": ("bad.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 400
        assert "parse" in response.json()["detail"].lower()

    async def test_upload_large_file_returns_413(self, client: AsyncClient) -> None:
        """Endpoint returns 413 for files exceeding size limit."""
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        files = {"file": ("large.vtt", io.BytesIO(large_content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    async def test_upload_vtt_with_underscores_formats_title(
        self, client: AsyncClient
    ) -> None:
        """Endpoint replaces underscores and dashes with spaces in title."""
        content = b"WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello"
        files = {"file": ("project_status_update.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 200
        assert response.json()["title"] == "project status update"

    async def test_upload_vtt_with_dashes_formats_title(
        self, client: AsyncClient
    ) -> None:
        """Endpoint replaces dashes with spaces in title."""
        content = b"WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello"
        files = {"file": ("weekly-sync-call.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 200
        assert response.json()["title"] == "weekly sync call"

    async def test_upload_utf8_bom_file(self, client: AsyncClient) -> None:
        """Endpoint handles UTF-8 files with BOM."""
        # UTF-8 with BOM
        content = b"\xef\xbb\xbfWEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello"
        files = {"file": ("bom.vtt", io.BytesIO(content), "text/vtt")}
        response = await client.post("/meetings/upload", files=files)

        assert response.status_code == 200

    async def test_upload_meeting_created_event(
        self, client: AsyncClient, mock_event_bus: EventBus
    ) -> None:
        """Endpoint emits MeetingCreated event with correct data."""
        content = b"""WEBVTT

00:00:01.000 --> 00:00:05.000
<v Speaker1>Hello

00:00:05.000 --> 00:00:10.000
<v Speaker2>World
"""
        files = {"file": ("test.vtt", io.BytesIO(content), "text/vtt")}
        await client.post("/meetings/upload", files=files)

        # Check first call was MeetingCreated
        calls = mock_event_bus.publish_and_store.call_args_list  # type: ignore[attr-defined]
        meeting_created = calls[0][0][0]

        assert meeting_created.title == "test"
        assert meeting_created.participant_count == 2
        assert meeting_created.transcript_filename == "test.vtt"

    async def test_upload_transcript_parsed_event(
        self, client: AsyncClient, mock_event_bus: EventBus
    ) -> None:
        """Endpoint emits TranscriptParsed event with correct data."""
        content = b"""WEBVTT

00:00:01.000 --> 00:00:05.000
<v Alice>Hello

00:00:05.000 --> 00:00:10.000
<v Alice>World
"""
        files = {"file": ("test.vtt", io.BytesIO(content), "text/vtt")}
        await client.post("/meetings/upload", files=files)

        # Check second call was TranscriptParsed
        calls = mock_event_bus.publish_and_store.call_args_list  # type: ignore[attr-defined]
        transcript_parsed = calls[1][0][0]

        assert transcript_parsed.utterance_count == 2
        assert transcript_parsed.speaker_count == 1  # Just Alice
        assert transcript_parsed.duration_seconds == 10.0
