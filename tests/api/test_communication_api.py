"""Tests for communication API endpoints.

Verifies that communication endpoints:
- Accept correct request bodies
- Return GenerationResponse with markdown and plain_text
- Include metadata in responses
- Return 503 when service not initialized
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.api.communication import get_communication_service, router
from src.communication.schemas import GeneratedArtifact
from src.communication.service import CommunicationService, GenerationResult


@pytest.fixture
def mock_communication_service():
    """Create mock CommunicationService."""
    service = MagicMock(spec=CommunicationService)

    # Default return values for each method
    exec_artifact = GeneratedArtifact(
        artifact_type="exec_status",
        markdown="# Executive Status\n\nAll systems go.",
        plain_text="EXECUTIVE STATUS\nAll systems go.",
        metadata={"rag_overall": "GREEN", "blocker_count": 0},
    )
    service.generate_exec_status = AsyncMock(
        return_value=GenerationResult(
            artifact_type="exec_status",
            artifact=exec_artifact,
            data_used=None,
            generated_at=datetime(2026, 1, 15, 12, 0, 0),
        )
    )

    team_artifact = GeneratedArtifact(
        artifact_type="team_status",
        markdown="# Team Status\n\n3 items completed.",
        plain_text="TEAM STATUS\n3 items completed.",
        metadata={"item_count": 5, "completed_count": 3},
    )
    service.generate_team_status = AsyncMock(
        return_value=GenerationResult(
            artifact_type="team_status",
            artifact=team_artifact,
            data_used=None,
            generated_at=datetime(2026, 1, 15, 12, 0, 0),
        )
    )

    escalation_artifact = GeneratedArtifact(
        artifact_type="escalation",
        markdown="Subject: Critical Decision Needed",
        plain_text="Subject: Critical Decision Needed",
        metadata={"subject": "Critical Decision Needed", "deadline": "2026-01-20"},
    )
    service.generate_escalation = AsyncMock(
        return_value=GenerationResult(
            artifact_type="escalation",
            artifact=escalation_artifact,
            data_used=None,
            generated_at=datetime(2026, 1, 15, 12, 0, 0),
        )
    )

    talking_points_artifact = GeneratedArtifact(
        artifact_type="talking_points",
        markdown="# Talking Points\n\n- Point 1",
        plain_text="TALKING POINTS\n- Point 1",
        metadata={"point_count": 5, "qa_count": 3},
    )
    service.generate_talking_points = AsyncMock(
        return_value=GenerationResult(
            artifact_type="talking_points",
            artifact=talking_points_artifact,
            data_used=None,
            generated_at=datetime(2026, 1, 15, 12, 0, 0),
        )
    )

    return service


@pytest.fixture
def app_with_service(mock_communication_service):
    """Create test app with communication router and mocked service."""
    test_app = FastAPI()
    test_app.include_router(router)

    # Override dependency to return mock service
    def override_get_service():
        return mock_communication_service

    test_app.dependency_overrides[get_communication_service] = override_get_service
    return test_app


@pytest.fixture
def client(app_with_service, mock_communication_service):
    """Create test client with mocked service."""
    # Store mock service on fixture for inspection in tests
    client = TestClient(app_with_service)
    client._mock_service = mock_communication_service
    return client


@pytest.fixture
def client_no_service():
    """Create test client without service initialized."""
    test_app = FastAPI()
    test_app.include_router(router)

    # Override dependency to raise 503
    def override_no_service():
        raise HTTPException(
            status_code=503, detail="CommunicationService not initialized"
        )

    test_app.dependency_overrides[get_communication_service] = override_no_service
    return TestClient(test_app)


class TestExecStatusEndpoint:
    """Tests for POST /communication/exec-status endpoint."""

    def test_returns_generation_response(self, client):
        """Endpoint returns GenerationResponse."""
        response = client.post(
            "/communication/exec-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["artifact_type"] == "exec_status"
        assert "markdown" in data
        assert "plain_text" in data
        assert "metadata" in data
        assert "generated_at" in data

    def test_includes_markdown_content(self, client):
        """Response includes markdown content."""
        response = client.post(
            "/communication/exec-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        data = response.json()
        assert "# Executive Status" in data["markdown"]

    def test_includes_plain_text_content(self, client):
        """Response includes plain text content."""
        response = client.post(
            "/communication/exec-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        data = response.json()
        assert "EXECUTIVE STATUS" in data["plain_text"]

    def test_includes_metadata(self, client):
        """Response includes metadata."""
        response = client.post(
            "/communication/exec-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        data = response.json()
        assert data["metadata"]["rag_overall"] == "GREEN"

    def test_accepts_until_parameter(self, client):
        """Endpoint accepts optional until parameter."""
        response = client.post(
            "/communication/exec-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
                "until": "2026-01-15T00:00:00Z",
            },
        )

        assert response.status_code == 200
        call_kwargs = client._mock_service.generate_exec_status.call_args.kwargs
        assert call_kwargs["until"] is not None

    def test_returns_503_when_service_not_initialized(self, client_no_service):
        """Endpoint returns 503 when CommunicationService not initialized."""
        response = client_no_service.post(
            "/communication/exec-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]


class TestTeamStatusEndpoint:
    """Tests for POST /communication/team-status endpoint."""

    def test_returns_generation_response(self, client):
        """Endpoint returns GenerationResponse."""
        response = client.post(
            "/communication/team-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["artifact_type"] == "team_status"

    def test_includes_item_counts_in_metadata(self, client):
        """Response metadata includes item counts."""
        response = client.post(
            "/communication/team-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        data = response.json()
        assert data["metadata"]["item_count"] == 5
        assert data["metadata"]["completed_count"] == 3

    def test_returns_503_when_service_not_initialized(self, client_no_service):
        """Endpoint returns 503 when service not initialized."""
        response = client_no_service.post(
            "/communication/team-status",
            json={
                "project_id": "TestProject",
                "since": "2026-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 503


class TestEscalationEndpoint:
    """Tests for POST /communication/escalation endpoint."""

    def test_returns_generation_response(self, client):
        """Endpoint returns GenerationResponse."""
        response = client.post(
            "/communication/escalation",
            json={
                "problem_description": "Critical production issue",
                "timeline_impact": "2 week delay",
                "business_impact": "Revenue impact",
                "options": [
                    {"description": "Option A", "pros": "Fast", "cons": "Costly"},
                    {"description": "Option B", "pros": "Cheap", "cons": "Slow"},
                ],
                "decision_deadline": "2026-01-20T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["artifact_type"] == "escalation"

    def test_includes_subject_in_metadata(self, client):
        """Response metadata includes email subject."""
        response = client.post(
            "/communication/escalation",
            json={
                "problem_description": "Critical production issue",
                "options": [
                    {"description": "Option A", "pros": "Fast", "cons": "Costly"},
                    {"description": "Option B", "pros": "Cheap", "cons": "Slow"},
                ],
                "decision_deadline": "2026-01-20T00:00:00Z",
            },
        )

        data = response.json()
        assert "subject" in data["metadata"]

    def test_requires_problem_description(self, client):
        """Endpoint requires problem_description field."""
        response = client.post(
            "/communication/escalation",
            json={
                "options": [
                    {"description": "Option A", "pros": "Fast", "cons": "Costly"},
                ],
                "decision_deadline": "2026-01-20T00:00:00Z",
            },
        )

        assert response.status_code == 422

    def test_requires_options(self, client):
        """Endpoint requires options field."""
        response = client.post(
            "/communication/escalation",
            json={
                "problem_description": "Critical issue",
                "decision_deadline": "2026-01-20T00:00:00Z",
            },
        )

        assert response.status_code == 422

    def test_requires_decision_deadline(self, client):
        """Endpoint requires decision_deadline field."""
        response = client.post(
            "/communication/escalation",
            json={
                "problem_description": "Critical issue",
                "options": [
                    {"description": "Option A", "pros": "Fast", "cons": "Costly"},
                ],
            },
        )

        assert response.status_code == 422

    def test_returns_503_when_service_not_initialized(self, client_no_service):
        """Endpoint returns 503 when service not initialized."""
        response = client_no_service.post(
            "/communication/escalation",
            json={
                "problem_description": "Critical issue",
                "options": [
                    {"description": "Option A", "pros": "Fast", "cons": "Costly"},
                    {"description": "Option B", "pros": "Cheap", "cons": "Slow"},
                ],
                "decision_deadline": "2026-01-20T00:00:00Z",
            },
        )

        assert response.status_code == 503


class TestTalkingPointsEndpoint:
    """Tests for POST /communication/talking-points endpoint."""

    def test_returns_generation_response(self, client):
        """Endpoint returns GenerationResponse."""
        response = client.post(
            "/communication/talking-points",
            json={
                "project_id": "TestProject",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["artifact_type"] == "talking_points"

    def test_includes_point_count_in_metadata(self, client):
        """Response metadata includes point count."""
        response = client.post(
            "/communication/talking-points",
            json={
                "project_id": "TestProject",
            },
        )

        data = response.json()
        assert data["metadata"]["point_count"] == 5
        assert data["metadata"]["qa_count"] == 3

    def test_accepts_meeting_type(self, client):
        """Endpoint accepts optional meeting_type parameter."""
        response = client.post(
            "/communication/talking-points",
            json={
                "project_id": "TestProject",
                "meeting_type": "board_meeting",
            },
        )

        assert response.status_code == 200
        call_kwargs = client._mock_service.generate_talking_points.call_args.kwargs
        assert call_kwargs["meeting_type"] == "board_meeting"

    def test_accepts_since_parameter(self, client):
        """Endpoint accepts optional since parameter."""
        response = client.post(
            "/communication/talking-points",
            json={
                "project_id": "TestProject",
                "since": "2025-12-01T00:00:00Z",
            },
        )

        assert response.status_code == 200
        call_kwargs = client._mock_service.generate_talking_points.call_args.kwargs
        assert call_kwargs["since"] is not None

    def test_defaults_meeting_type_to_exec_review(self, client):
        """Default meeting_type is exec_review."""
        response = client.post(
            "/communication/talking-points",
            json={
                "project_id": "TestProject",
            },
        )

        assert response.status_code == 200
        call_kwargs = client._mock_service.generate_talking_points.call_args.kwargs
        assert call_kwargs["meeting_type"] == "exec_review"

    def test_returns_503_when_service_not_initialized(self, client_no_service):
        """Endpoint returns 503 when service not initialized."""
        response = client_no_service.post(
            "/communication/talking-points",
            json={
                "project_id": "TestProject",
            },
        )

        assert response.status_code == 503
