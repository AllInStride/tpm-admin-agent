"""Tests for output generation API endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.base import WriteResult
from src.main import app
from src.output.router import OutputResult, OutputRouter
from src.output.schemas import RenderedMinutes


@pytest.fixture
def sample_request_data():
    """Create sample request data for testing."""
    return {
        "meeting_id": str(uuid4()),
        "meeting_title": "Sprint Planning",
        "meeting_date": "2026-01-15T10:00:00Z",
        "duration_minutes": 60,
        "attendees": ["Alice (PM)", "Bob (Engineer)"],
        "decisions": [
            {"description": "Use Python 3.12", "confidence": 0.95},
        ],
        "action_items": [
            {
                "description": "Create design doc",
                "assignee_name": "Bob",
                "due_date": "2026-01-20",
                "confidence": 0.9,
            },
        ],
        "risks": [
            {
                "description": "API rate limits",
                "severity": "HIGH",
                "owner_name": "Alice",
                "confidence": 0.85,
            },
        ],
        "issues": [
            {
                "description": "CI pipeline slow",
                "priority": "MEDIUM",
                "status": "Open",
                "confidence": 0.8,
            },
        ],
    }


@pytest.fixture
def mock_output_router():
    """Create mock OutputRouter."""
    router = MagicMock(spec=OutputRouter)
    router.generate_output = AsyncMock(
        return_value=OutputResult(
            rendered=RenderedMinutes(
                meeting_id=uuid4(),
                markdown="# Sprint Planning Meeting\n\nContent here with more text",
                html="<h1>Sprint Planning Meeting</h1><p>Content here</p>",
                template_used="default_minutes",
            ),
            minutes_result=WriteResult(
                success=True,
                dry_run=True,
                item_count=1,
                url="https://drive.google.com/file/d/abc123",
            ),
            raid_result=WriteResult(
                success=True,
                dry_run=True,
                item_count=4,
                url="https://docs.google.com/spreadsheets/d/xyz789",
            ),
            total_items_written=4,
        )
    )
    router.drive_adapter = MagicMock()
    router.drive_adapter.health_check = AsyncMock(return_value=True)
    router.sheets_adapter = MagicMock()
    router.sheets_adapter.health_check = AsyncMock(return_value=True)
    return router


@pytest.mark.asyncio
async def test_output_endpoint_dry_run(sample_request_data, mock_output_router):
    """POST with dry_run=true returns 200 response."""
    with patch("src.api.output.get_output_router", return_value=mock_output_router):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/output?dry_run=true",
                json=sample_request_data,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["minutes_url"] == "https://drive.google.com/file/d/abc123"
    assert data["sheets_url"] == "https://docs.google.com/spreadsheets/d/xyz789"


@pytest.mark.asyncio
async def test_output_endpoint_returns_preview(sample_request_data, mock_output_router):
    """Verify markdown_preview in response."""
    with patch("src.api.output.get_output_router", return_value=mock_output_router):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/output?dry_run=true",
                json=sample_request_data,
            )

    assert response.status_code == 200
    data = response.json()
    assert "markdown_preview" in data
    assert data["markdown_preview"].startswith("# Sprint Planning Meeting")


@pytest.mark.asyncio
async def test_output_endpoint_with_config(sample_request_data, mock_output_router):
    """Provide custom config, verify used."""
    sample_request_data["config"] = {
        "minutes_destination": "custom_folder",
        "raid_destination": "custom_sheet",
        "raid_sheet_name": "CustomRAID",
        "template_name": "custom_template",
        "enabled_targets": ["drive"],
    }

    with patch("src.api.output.get_output_router", return_value=mock_output_router):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/output",
                json=sample_request_data,
            )

    assert response.status_code == 200
    # Verify config was passed to generate_output
    call_args = mock_output_router.generate_output.call_args
    config = call_args.kwargs.get("config") or call_args.args[2]
    assert config.minutes_destination == "custom_folder"
    assert config.raid_destination == "custom_sheet"


@pytest.mark.asyncio
async def test_output_endpoint_missing_meeting_id():
    """Verify 422 validation error for missing meeting_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/output",
            json={
                "meeting_title": "Test",
                "meeting_date": "2026-01-15T10:00:00Z",
                # missing meeting_id
            },
        )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_output_health_endpoint(mock_output_router):
    """GET /output/health returns status."""
    with patch("src.api.output.get_output_router", return_value=mock_output_router):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/output/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "adapters" in data
    assert data["adapters"]["drive"] is True
    assert data["adapters"]["sheets"] is True


@pytest.mark.asyncio
async def test_output_endpoint_with_raid_items(sample_request_data, mock_output_router):
    """Full request with all RAID types."""
    # Add more items of each type
    sample_request_data["decisions"].append(
        {"description": "Weekly syncs on Tuesday", "confidence": 0.88}
    )
    sample_request_data["action_items"].append(
        {"description": "Set up CI", "assignee_name": "Alice", "confidence": 0.92}
    )

    with patch("src.api.output.get_output_router", return_value=mock_output_router):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/output?dry_run=true",
                json=sample_request_data,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["items_written"] == 4  # From mock


@pytest.mark.asyncio
async def test_output_endpoint_empty_raid(mock_output_router):
    """Request with empty RAID lists."""
    empty_request = {
        "meeting_id": str(uuid4()),
        "meeting_title": "Quick Sync",
        "meeting_date": "2026-01-15T10:00:00Z",
        "attendees": ["Alice"],
        "decisions": [],
        "action_items": [],
        "risks": [],
        "issues": [],
    }

    # Update mock to return empty results
    mock_output_router.generate_output = AsyncMock(
        return_value=OutputResult(
            rendered=RenderedMinutes(
                meeting_id=uuid4(),
                markdown="# Quick Sync\n\nNo items",
                html="<h1>Quick Sync</h1><p>No items</p>",
                template_used="default_minutes",
            ),
            minutes_result=WriteResult(success=True, dry_run=True, item_count=1),
            raid_result=WriteResult(success=True, dry_run=True, item_count=0),
            total_items_written=0,
        )
    )

    with patch("src.api.output.get_output_router", return_value=mock_output_router):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/output?dry_run=true",
                json=empty_request,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["items_written"] == 0
