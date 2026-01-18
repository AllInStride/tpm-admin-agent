"""Tests for identity resolution API endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.identity import router
from src.identity.schemas import ResolutionResult, ResolutionSource, RosterEntry


@pytest.fixture
def mock_roster_adapter():
    """Create mock RosterAdapter."""
    adapter = MagicMock()
    adapter.load_roster.return_value = [
        RosterEntry(name="Alice Chen", email="alice@example.com"),
        RosterEntry(name="Bob Smith", email="bob@example.com"),
    ]
    return adapter


@pytest.fixture
def mock_identity_resolver():
    """Create mock IdentityResolver."""
    resolver = MagicMock()
    resolver.resolve_all = AsyncMock()
    resolver.learn_mapping = AsyncMock()
    return resolver


@pytest.fixture
def test_client(mock_roster_adapter, mock_identity_resolver):
    """Create test client with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)
    app.state.roster_adapter = mock_roster_adapter
    app.state.identity_resolver = mock_identity_resolver
    return TestClient(app)


class TestResolveEndpoint:
    """Tests for POST /identity/resolve endpoint."""

    def test_resolve_returns_matches(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should return resolved identities for provided names."""
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="Alice",
                resolved_email="alice@example.com",
                resolved_name="Alice Chen",
                confidence=1.0,
                source=ResolutionSource.EXACT,
                requires_review=False,
            ),
            ResolutionResult(
                transcript_name="Bob",
                resolved_email="bob@example.com",
                resolved_name="Bob Smith",
                confidence=0.92,
                source=ResolutionSource.FUZZY,
                requires_review=False,
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["Alice", "Bob"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["resolved"]) == 2
        assert data["resolved"][0]["transcript_name"] == "Alice"
        assert data["resolved"][0]["resolved_email"] == "alice@example.com"
        assert data["resolved"][0]["confidence"] == 1.0
        assert data["resolved"][0]["source"] == "exact"
        assert data["resolved"][1]["transcript_name"] == "Bob"
        assert data["resolved"][1]["source"] == "fuzzy"

    def test_resolve_marks_low_confidence_for_review(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should flag items with confidence < 85% for review."""
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="Alice",
                resolved_email="alice@example.com",
                resolved_name="Alice Chen",
                confidence=1.0,
                source=ResolutionSource.EXACT,
                requires_review=False,
            ),
            ResolutionResult(
                transcript_name="JSmith",
                resolved_email="bob@example.com",
                resolved_name="Bob Smith",
                confidence=0.72,
                source=ResolutionSource.FUZZY,
                requires_review=True,
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["Alice", "JSmith"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pending_review_count"] == 1
        assert data["resolved"][0]["requires_review"] is False
        assert data["resolved"][1]["requires_review"] is True

    def test_resolve_includes_review_summary_when_pending(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should include human-readable summary when items need review."""
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="JSmith",
                resolved_email="bob@example.com",
                resolved_name="Bob Smith",
                confidence=0.72,
                source=ResolutionSource.FUZZY,
                requires_review=True,
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["JSmith"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["review_summary"] is not None
        assert "1 name(s) need review" in data["review_summary"]
        assert "JSmith" in data["review_summary"]
        assert "Bob Smith" in data["review_summary"]

    def test_resolve_no_summary_when_all_resolved(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should have no review_summary when all items resolved."""
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="Alice",
                resolved_email="alice@example.com",
                resolved_name="Alice Chen",
                confidence=1.0,
                source=ResolutionSource.EXACT,
                requires_review=False,
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["Alice"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pending_review_count"] == 0
        assert data["review_summary"] is None

    def test_resolve_loads_roster_from_spreadsheet(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should load roster using provided spreadsheet ID."""
        mock_identity_resolver.resolve_all.return_value = []

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": [],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-xyz-789",
            },
        )

        assert response.status_code == 200
        mock_roster_adapter.load_roster.assert_called_once_with("sheet-xyz-789")

    def test_resolve_includes_alternatives(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should include alternative matches in response."""
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="Unknown Person",
                resolved_email=None,
                resolved_name=None,
                confidence=0.0,
                source=ResolutionSource.FUZZY,
                requires_review=True,
                alternatives=[("Alice Chen", 0.65), ("Bob Smith", 0.58)],
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["Unknown Person"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["resolved"][0]["alternatives"]) == 2
        assert data["resolved"][0]["alternatives"][0] == ["Alice Chen", 0.65]


class TestConfirmEndpoint:
    """Tests for POST /identity/confirm endpoint."""

    def test_confirm_saves_mapping(self, test_client, mock_identity_resolver):
        """Should save learned mapping via resolver."""
        response = test_client.post(
            "/identity/confirm",
            json={
                "project_id": "proj-123",
                "transcript_name": "JSmith",
                "confirmed_email": "john.smith@example.com",
                "confirmed_name": "John Smith",
            },
        )

        assert response.status_code == 200
        mock_identity_resolver.learn_mapping.assert_called_once_with(
            project_id="proj-123",
            transcript_name="JSmith",
            resolved_email="john.smith@example.com",
            resolved_name="John Smith",
        )

    def test_confirm_returns_learned_true(self, test_client, mock_identity_resolver):
        """Should return learned=True to indicate mapping saved."""
        response = test_client.post(
            "/identity/confirm",
            json={
                "project_id": "proj-123",
                "transcript_name": "JSmith",
                "confirmed_email": "john.smith@example.com",
                "confirmed_name": "John Smith",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["learned"] is True
        assert data["transcript_name"] == "JSmith"
        assert data["confirmed_email"] == "john.smith@example.com"
        assert data["confirmed_name"] == "John Smith"


class TestPendingReviewsEndpoint:
    """Tests for GET /identity/pending/{project_id} endpoint."""

    def test_pending_returns_empty_list_for_mvp(self, test_client):
        """Should return empty list for MVP implementation."""
        response = test_client.get("/identity/pending/proj-123")

        assert response.status_code == 200
        assert response.json() == []


class TestResolveUsesLearnedMapping:
    """Tests for learned mapping integration in resolve flow."""

    def test_resolve_uses_learned_mapping(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Learned mappings should be used in resolution (via resolver)."""
        # This test verifies the API passes data through correctly.
        # The actual learned mapping logic is tested in test_resolver.py.
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="JSmith",
                resolved_email="john.smith@example.com",
                resolved_name="John Smith",
                confidence=0.95,
                source=ResolutionSource.LEARNED,
                requires_review=False,
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["JSmith"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resolved"][0]["source"] == "learned"
        assert data["resolved"][0]["confidence"] == 0.95
        assert data["resolved"][0]["requires_review"] is False


class TestReviewSummaryGeneration:
    """Tests for review summary text generation."""

    def test_summary_with_no_match(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should indicate no match found for unresolved names."""
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="Unknown Person",
                resolved_email=None,
                resolved_name=None,
                confidence=0.0,
                source=ResolutionSource.FUZZY,
                requires_review=True,
                alternatives=[],
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["Unknown Person"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "no match found" in data["review_summary"]

    def test_summary_with_alternatives(
        self, test_client, mock_roster_adapter, mock_identity_resolver
    ):
        """Should show top alternative in summary when available."""
        mock_identity_resolver.resolve_all.return_value = [
            ResolutionResult(
                transcript_name="JohnS",
                resolved_email=None,
                resolved_name=None,
                confidence=0.0,
                source=ResolutionSource.FUZZY,
                requires_review=True,
                alternatives=[("John Smith", 0.75), ("Jane Simmons", 0.68)],
            ),
        ]

        response = test_client.post(
            "/identity/resolve",
            json={
                "names": ["JohnS"],
                "project_id": "proj-123",
                "roster_spreadsheet_id": "sheet-abc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "John Smith" in data["review_summary"]
        assert "75%" in data["review_summary"]
        assert "needs confirmation" in data["review_summary"]
