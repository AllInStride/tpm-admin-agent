"""Tests for prep API endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.prep import router
from src.prep.prep_service import PrepService
from src.prep.scheduler import reset_scheduler
from src.prep.schemas import PrepConfig


@pytest.fixture
def app():
    """Create test app with prep router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_prep_service():
    """Create and register mock PrepService."""
    mock_service = MagicMock()
    mock_service._config = PrepConfig()
    mock_service.scan_and_prepare = AsyncMock(return_value=[])
    mock_service.prepare_for_meeting = AsyncMock(
        return_value={
            "meeting_id": "event1",
            "meeting_title": "Test Meeting",
            "recipients": 2,
            "items": 3,
            "talking_points": 2,
        }
    )
    PrepService.set_instance(mock_service)
    yield mock_service
    PrepService.reset_instance()


class TestTriggerPrep:
    """Tests for POST /prep/trigger endpoint."""

    def setup_method(self):
        """Reset PrepService before each test."""
        PrepService.reset_instance()

    def teardown_method(self):
        """Reset PrepService after each test."""
        PrepService.reset_instance()

    def test_returns_503_when_service_not_initialized(self, client):
        """POST /prep/trigger returns 503 when PrepService not ready."""
        response = client.post(
            "/prep/trigger",
            json={
                "calendar_id": "user@example.com",
                "event_id": "event123",
                "project_id": "proj1",
            },
        )

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]

    def test_triggers_prep_for_meeting(self, client, mock_prep_service):
        """POST /prep/trigger calls prepare_for_meeting."""
        response = client.post(
            "/prep/trigger",
            json={
                "calendar_id": "user@example.com",
                "event_id": "event123",
                "project_id": "proj1",
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert result["meeting_id"] == "event1"
        assert result["recipients"] == 2

        mock_prep_service.prepare_for_meeting.assert_called_once()
        call_kwargs = mock_prep_service.prepare_for_meeting.call_args.kwargs
        assert call_kwargs["event"]["id"] == "event123"
        assert call_kwargs["project_id"] == "proj1"

    def test_requires_all_fields(self, client, mock_prep_service):
        """POST /prep/trigger requires calendar_id, event_id, project_id."""
        # Missing event_id
        response = client.post(
            "/prep/trigger",
            json={
                "calendar_id": "user@example.com",
                "project_id": "proj1",
            },
        )

        assert response.status_code == 422


class TestScanNow:
    """Tests for POST /prep/scan endpoint."""

    def setup_method(self):
        """Reset PrepService before each test."""
        PrepService.reset_instance()

    def teardown_method(self):
        """Reset PrepService after each test."""
        PrepService.reset_instance()

    def test_returns_503_when_service_not_initialized(self, client):
        """POST /prep/scan returns 503 when PrepService not ready."""
        response = client.post("/prep/scan")

        assert response.status_code == 503

    def test_triggers_scan(self, client, mock_prep_service):
        """POST /prep/scan triggers calendar scan."""
        mock_prep_service.scan_and_prepare.return_value = [
            {"meeting_id": "event1"},
            {"meeting_id": "event2"},
        ]

        response = client.post("/prep/scan")

        assert response.status_code == 200
        result = response.json()
        assert result["scanned"] is True
        assert result["preps_sent"] == 2
        assert len(result["results"]) == 2

    def test_accepts_calendar_id_param(self, client, mock_prep_service):
        """POST /prep/scan accepts calendar_id query param."""
        response = client.post("/prep/scan?calendar_id=team@example.com")

        assert response.status_code == 200
        mock_prep_service.scan_and_prepare.assert_called_with("team@example.com")

    def test_uses_primary_by_default(self, client, mock_prep_service):
        """POST /prep/scan uses 'primary' calendar by default."""
        response = client.post("/prep/scan")

        assert response.status_code == 200
        mock_prep_service.scan_and_prepare.assert_called_with("primary")


class TestGetConfig:
    """Tests for GET /prep/config endpoint."""

    def setup_method(self):
        """Reset PrepService before each test."""
        PrepService.reset_instance()

    def teardown_method(self):
        """Reset PrepService after each test."""
        PrepService.reset_instance()

    def test_returns_503_when_service_not_initialized(self, client):
        """GET /prep/config returns 503 when PrepService not ready."""
        response = client.get("/prep/config")

        assert response.status_code == 503

    def test_returns_config(self, client, mock_prep_service):
        """GET /prep/config returns PrepConfig."""
        response = client.get("/prep/config")

        assert response.status_code == 200
        result = response.json()
        assert result["lead_time_minutes"] == 10
        assert result["delivery_method"] == "slack"
        assert result["max_items"] == 10
        assert result["lookback_days"] == 90

    def test_returns_custom_config(self, client):
        """GET /prep/config returns actual config values."""
        mock_service = MagicMock()
        mock_service._config = PrepConfig(
            lead_time_minutes=15,
            max_items=5,
            lookback_days=60,
        )
        PrepService.set_instance(mock_service)

        response = client.get("/prep/config")

        assert response.status_code == 200
        result = response.json()
        assert result["lead_time_minutes"] == 15
        assert result["max_items"] == 5
        assert result["lookback_days"] == 60


class TestGetStatus:
    """Tests for GET /prep/status endpoint."""

    def setup_method(self):
        """Reset scheduler before each test."""
        reset_scheduler()

    def teardown_method(self):
        """Reset scheduler after each test."""
        reset_scheduler()

    def test_returns_status_without_prep_service(self, client):
        """GET /prep/status works without PrepService."""
        # Status endpoint doesn't need PrepService
        response = client.get("/prep/status")

        assert response.status_code == 200
        result = response.json()
        assert "scheduler_running" in result
        assert "jobs" in result

    def test_shows_scheduler_not_running(self, client):
        """GET /prep/status shows scheduler not running initially."""
        response = client.get("/prep/status")

        assert response.status_code == 200
        result = response.json()
        assert result["scheduler_running"] is False

    @pytest.mark.asyncio
    async def test_shows_scheduler_running(self, client):
        """GET /prep/status shows scheduler running after start."""
        from src.prep.scheduler import prep_scheduler_lifespan

        async with prep_scheduler_lifespan():
            response = client.get("/prep/status")

            assert response.status_code == 200
            result = response.json()
            assert result["scheduler_running"] is True
            assert len(result["jobs"]) >= 1

    @pytest.mark.asyncio
    async def test_shows_job_details(self, client):
        """GET /prep/status shows job id and next run time."""
        from src.prep.scheduler import prep_scheduler_lifespan

        async with prep_scheduler_lifespan():
            response = client.get("/prep/status")

            result = response.json()
            jobs = result["jobs"]
            assert any(j["id"] == "meeting_prep_scanner" for j in jobs)
            # Next run should be set
            scanner_job = next(j for j in jobs if j["id"] == "meeting_prep_scanner")
            assert scanner_job["next_run"] is not None
