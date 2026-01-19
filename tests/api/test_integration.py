"""Integration tests for integration API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.integration import router
from src.integration import NotificationResult
from src.integration.schemas import SmartsheetWriteResult
from src.output.config import ProjectOutputConfig
from src.output.schemas import (
    ActionItemData,
    DecisionItem,
    IssueItem,
    RaidBundle,
    RiskItem,
)


@pytest.fixture
def sample_meeting_id() -> UUID:
    """Fixed meeting UUID for testing."""
    return UUID("12345678-1234-1234-1234-123456789abc")


@pytest.fixture
def sample_raid_bundle(sample_meeting_id: UUID) -> RaidBundle:
    """Sample RAID bundle with mixed item types."""
    return RaidBundle(
        meeting_id=sample_meeting_id,
        decisions=[
            DecisionItem(
                description="Use Redis for caching",
                rationale="Better performance",
                confidence=0.95,
            ),
        ],
        action_items=[
            ActionItemData(
                description="Implement caching layer",
                assignee_name="bob@example.com",
                due_date="2026-01-20",
                confidence=0.9,
            ),
            ActionItemData(
                description="Write documentation",
                assignee_name="alice@example.com",
                due_date="2026-01-25",
                confidence=0.85,
            ),
        ],
        risks=[
            RiskItem(
                description="Cache invalidation complexity",
                severity="HIGH",
                owner_name="bob@example.com",
                confidence=0.8,
            ),
        ],
        issues=[
            IssueItem(
                description="Legacy system incompatibility",
                priority="MEDIUM",
                status="Open",
                owner_name="carol@example.com",
                confidence=0.75,
            ),
        ],
    )


@pytest.fixture
def sample_config() -> ProjectOutputConfig:
    """Sample config with Smartsheet settings."""
    return ProjectOutputConfig(
        smartsheet_sheet_id=123456789,
        notify_owners=True,
        fallback_email="fallback@example.com",
    )


@pytest.fixture
def mock_smartsheet_adapter() -> MagicMock:
    """Mocked SmartsheetAdapter."""
    adapter = MagicMock()
    adapter._token = "test-token"
    adapter.write_raid_items = AsyncMock(
        return_value=SmartsheetWriteResult(
            success=True,
            item_count=4,
            external_id="123456789",
            sheet_url="https://app.smartsheet.com/sheets/123456789",
            row_ids=[1, 2, 3, 4],
        )
    )
    adapter.health_check = AsyncMock(return_value=True)
    return adapter


@pytest.fixture
def mock_slack_adapter() -> MagicMock:
    """Mocked SlackAdapter."""
    adapter = MagicMock()
    adapter._token = "xoxb-test-token"
    adapter.lookup_user_by_email = AsyncMock(
        side_effect=lambda email: {"id": f"U{hash(email) % 10000:04d}", "name": email}
    )
    adapter.send_dm = AsyncMock(
        return_value={"success": True, "ts": "1234567890.123456"}
    )
    return adapter


@pytest.fixture
def mock_notification_service(mock_slack_adapter: MagicMock) -> MagicMock:
    """Mocked NotificationService."""
    service = MagicMock()

    async def mock_notify_owner(owner_email, item, **kw):
        return NotificationResult(
            success=True,
            recipient_email=owner_email,
            recipient_slack_id=f"U{hash(owner_email) % 10000:04d}",
            message_ts="1234567890.123456",
        )

    service.notify_owner = AsyncMock(side_effect=mock_notify_owner)
    return service


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app with integration router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app: FastAPI):
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


class TestProcessIntegration:
    """Tests for POST /integration endpoint."""

    @pytest.mark.asyncio
    async def test_integration_success(
        self,
        client: AsyncClient,
        sample_raid_bundle: RaidBundle,
        sample_config: ProjectOutputConfig,
        mock_smartsheet_adapter: MagicMock,
        mock_notification_service: MagicMock,
    ):
        """Full pipeline succeeds with mocked adapters."""
        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=mock_smartsheet_adapter,
            ),
            patch(
                "src.api.integration.SlackAdapter",
            ),
            patch(
                "src.api.integration.NotificationService",
                return_value=mock_notification_service,
            ),
        ):
            response = await client.post(
                "/integration",
                json={
                    "raid_bundle": sample_raid_bundle.model_dump(mode="json"),
                    "config": sample_config.model_dump(mode="json"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_result"]["success"] is True
        assert data["smartsheet_result"]["item_count"] == 4
        assert data["notifications_sent"] == 2  # Two action items with email assignees

    @pytest.mark.asyncio
    async def test_integration_dry_run(
        self,
        client: AsyncClient,
        sample_raid_bundle: RaidBundle,
        sample_config: ProjectOutputConfig,
        mock_smartsheet_adapter: MagicMock,
    ):
        """Dry run validates without writing or notifying."""
        mock_smartsheet_adapter.write_raid_items = AsyncMock(
            return_value=SmartsheetWriteResult(
                success=True,
                dry_run=True,
                item_count=4,
            )
        )

        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=mock_smartsheet_adapter,
            ),
            patch("src.api.integration.SlackAdapter"),
            patch("src.api.integration.NotificationService"),
        ):
            response = await client.post(
                "/integration?dry_run=true",
                json={
                    "raid_bundle": sample_raid_bundle.model_dump(mode="json"),
                    "config": sample_config.model_dump(mode="json"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Dry run skips notifications
        assert data["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_integration_smartsheet_only(
        self,
        client: AsyncClient,
        sample_raid_bundle: RaidBundle,
        mock_smartsheet_adapter: MagicMock,
    ):
        """Config without notify_owners only writes to Smartsheet."""
        config = ProjectOutputConfig(
            smartsheet_sheet_id=123456789,
            notify_owners=False,
        )

        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=mock_smartsheet_adapter,
            ),
        ):
            response = await client.post(
                "/integration",
                json={
                    "raid_bundle": sample_raid_bundle.model_dump(mode="json"),
                    "config": config.model_dump(mode="json"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_result"]["success"] is True
        assert data["notifications_sent"] == 0
        assert data["notification_results"] == []

    @pytest.mark.asyncio
    async def test_integration_notifications_only(
        self,
        client: AsyncClient,
        sample_raid_bundle: RaidBundle,
        mock_notification_service: MagicMock,
    ):
        """Config without smartsheet_sheet_id only sends notifications."""
        config = ProjectOutputConfig(
            smartsheet_sheet_id=None,
            notify_owners=True,
        )

        with (
            patch("src.api.integration.SlackAdapter"),
            patch(
                "src.api.integration.NotificationService",
                return_value=mock_notification_service,
            ),
        ):
            response = await client.post(
                "/integration",
                json={
                    "raid_bundle": sample_raid_bundle.model_dump(mode="json"),
                    "config": config.model_dump(mode="json"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_result"] is None
        assert data["notifications_sent"] == 2

    @pytest.mark.asyncio
    async def test_integration_no_config(
        self,
        client: AsyncClient,
        sample_raid_bundle: RaidBundle,
        mock_notification_service: MagicMock,
    ):
        """Uses default config when none provided."""
        with (
            patch("src.api.integration.SlackAdapter"),
            patch(
                "src.api.integration.NotificationService",
                return_value=mock_notification_service,
            ),
        ):
            response = await client.post(
                "/integration",
                json={
                    "raid_bundle": sample_raid_bundle.model_dump(mode="json"),
                },
            )

        # Default config has no smartsheet_sheet_id, so no writes
        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_result"] is None
        # Default config has notify_owners=True, but no smartsheet URL
        assert data["notifications_sent"] == 2

    @pytest.mark.asyncio
    async def test_integration_smartsheet_failure(
        self,
        client: AsyncClient,
        sample_raid_bundle: RaidBundle,
        sample_config: ProjectOutputConfig,
        mock_notification_service: MagicMock,
    ):
        """Handle Smartsheet write failure gracefully."""
        failed_adapter = MagicMock()
        failed_adapter._token = "test-token"
        failed_adapter.write_raid_items = AsyncMock(
            return_value=SmartsheetWriteResult(
                success=False,
                error_message="Rate limit exceeded",
            )
        )

        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=failed_adapter,
            ),
            patch("src.api.integration.SlackAdapter"),
            patch(
                "src.api.integration.NotificationService",
                return_value=mock_notification_service,
            ),
        ):
            response = await client.post(
                "/integration",
                json={
                    "raid_bundle": sample_raid_bundle.model_dump(mode="json"),
                    "config": sample_config.model_dump(mode="json"),
                },
            )

        # Endpoint returns 200 but result shows failure
        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_result"]["success"] is False
        assert "Rate limit" in data["smartsheet_result"]["error_message"]
        # Notifications still sent (partial success)
        assert data["notifications_sent"] == 2

    @pytest.mark.asyncio
    async def test_integration_notification_partial_failure(
        self,
        client: AsyncClient,
        sample_raid_bundle: RaidBundle,
        sample_config: ProjectOutputConfig,
        mock_smartsheet_adapter: MagicMock,
    ):
        """Some notifications fail, others succeed."""
        partial_service = MagicMock()
        call_count = [0]

        async def partial_notify(owner_email, item, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return NotificationResult(
                    success=True,
                    recipient_email=owner_email,
                    recipient_slack_id="U1234",
                    message_ts="1234567890.123456",
                )
            return NotificationResult(
                success=False,
                recipient_email=owner_email,
                error="user_not_found",
            )

        partial_service.notify_owner = AsyncMock(side_effect=partial_notify)

        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=mock_smartsheet_adapter,
            ),
            patch("src.api.integration.SlackAdapter"),
            patch(
                "src.api.integration.NotificationService",
                return_value=partial_service,
            ),
        ):
            response = await client.post(
                "/integration",
                json={
                    "raid_bundle": sample_raid_bundle.model_dump(mode="json"),
                    "config": sample_config.model_dump(mode="json"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["notifications_sent"] == 1
        assert data["notifications_failed"] == 1


class TestIntegrationHealth:
    """Tests for GET /integration/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_all_configured(
        self,
        client: AsyncClient,
        mock_smartsheet_adapter: MagicMock,
        mock_slack_adapter: MagicMock,
    ):
        """Both adapters configured and healthy."""
        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=mock_smartsheet_adapter,
            ),
            patch(
                "src.api.integration.SlackAdapter",
                return_value=mock_slack_adapter,
            ),
        ):
            response = await client.get("/integration/health")

        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_configured"] is True
        assert data["smartsheet_healthy"] is True
        assert data["slack_configured"] is True
        assert data["slack_healthy"] is True

    @pytest.mark.asyncio
    async def test_health_smartsheet_only(
        self,
        client: AsyncClient,
        mock_smartsheet_adapter: MagicMock,
    ):
        """Only Smartsheet configured."""
        no_slack = MagicMock()
        no_slack._token = None

        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=mock_smartsheet_adapter,
            ),
            patch(
                "src.api.integration.SlackAdapter",
                return_value=no_slack,
            ),
        ):
            response = await client.get("/integration/health")

        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_configured"] is True
        assert data["smartsheet_healthy"] is True
        assert data["slack_configured"] is False
        assert data["slack_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_none_configured(
        self,
        client: AsyncClient,
    ):
        """Neither adapter configured."""
        no_ss = MagicMock()
        no_ss._token = None

        no_slack = MagicMock()
        no_slack._token = None

        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=no_ss,
            ),
            patch(
                "src.api.integration.SlackAdapter",
                return_value=no_slack,
            ),
        ):
            response = await client.get("/integration/health")

        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_configured"] is False
        assert data["smartsheet_healthy"] is False
        assert data["slack_configured"] is False
        assert data["slack_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_smartsheet_unhealthy(
        self,
        client: AsyncClient,
        mock_slack_adapter: MagicMock,
    ):
        """Smartsheet configured but unhealthy."""
        unhealthy_ss = MagicMock()
        unhealthy_ss._token = "test-token"
        unhealthy_ss.health_check = AsyncMock(return_value=False)

        with (
            patch(
                "src.api.integration.SmartsheetAdapter",
                return_value=unhealthy_ss,
            ),
            patch(
                "src.api.integration.SlackAdapter",
                return_value=mock_slack_adapter,
            ),
        ):
            response = await client.get("/integration/health")

        assert response.status_code == 200
        data = response.json()
        assert data["smartsheet_configured"] is True
        assert data["smartsheet_healthy"] is False
        assert data["slack_configured"] is True
        assert data["slack_healthy"] is True
