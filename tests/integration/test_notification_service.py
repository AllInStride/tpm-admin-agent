"""Tests for NotificationService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.slack_adapter import SlackAdapter
from src.integration.notification_service import NotificationService
from src.output.schemas import ActionItemData


@pytest.fixture
def mock_slack_adapter():
    """Create mock SlackAdapter."""
    adapter = MagicMock(spec=SlackAdapter)
    adapter.lookup_user_by_email = AsyncMock()
    adapter.send_dm = AsyncMock()
    return adapter


@pytest.fixture
def notification_service(mock_slack_adapter):
    """Create NotificationService with mocked adapter."""
    return NotificationService(mock_slack_adapter)


@pytest.fixture
def sample_action_item():
    """Create sample ActionItemData for testing."""
    return ActionItemData(
        description="Complete the quarterly report",
        assignee_name="John Doe",
        due_date="2026-01-25",
        confidence=0.9,
    )


@pytest.fixture
def sample_action_item_no_due_date():
    """Create sample ActionItemData without due date."""
    return ActionItemData(
        description="Review the design document",
        assignee_name="Jane Smith",
        confidence=0.85,
    )


class TestNotifyOwnerSuccess:
    """Tests for successful notification scenarios."""

    @pytest.mark.asyncio
    async def test_notify_owner_success(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should send DM when user found."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
            "profile": {"email": "john@example.com"},
        }
        mock_slack_adapter.send_dm.return_value = {
            "success": True,
            "ts": "1234567890.123456",
        }

        result = await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
            smartsheet_url="https://smartsheet.com/row/123",
        )

        assert result.success is True
        assert result.recipient_email == "john@example.com"
        assert result.recipient_slack_id == "U123"
        assert result.message_ts == "1234567890.123456"
        assert result.error is None

        mock_slack_adapter.lookup_user_by_email.assert_called_once_with(
            "john@example.com"
        )
        mock_slack_adapter.send_dm.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_log_populated_on_success(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should record audit entry on successful notification."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
        )

        audit_log = notification_service.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0].recipient_email == "john@example.com"
        assert audit_log[0].item_description == "Complete the quarterly report"
        assert audit_log[0].item_type == "Action"
        assert audit_log[0].success is True
        assert audit_log[0].error is None


class TestNotifyOwnerFailure:
    """Tests for notification failure scenarios."""

    @pytest.mark.asyncio
    async def test_notify_owner_user_not_found(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should return error when user not found."""
        mock_slack_adapter.lookup_user_by_email.return_value = None

        result = await notification_service.notify_owner(
            "unknown@example.com",
            sample_action_item,
        )

        assert result.success is False
        assert result.recipient_email == "unknown@example.com"
        assert result.recipient_slack_id is None
        assert result.error == "user_not_found"

        mock_slack_adapter.send_dm.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_owner_dm_fails(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should return error when DM fails."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {
            "success": False,
            "error": "channel_not_found",
        }

        result = await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
        )

        assert result.success is False
        assert result.recipient_slack_id == "U123"
        assert result.error == "channel_not_found"

    @pytest.mark.asyncio
    async def test_audit_log_populated_on_failure(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should record audit entry on failed notification."""
        mock_slack_adapter.lookup_user_by_email.return_value = None

        await notification_service.notify_owner(
            "unknown@example.com",
            sample_action_item,
        )

        audit_log = notification_service.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0].success is False
        assert audit_log[0].error == "user_not_found"


class TestMessageFormatting:
    """Tests for message formatting."""

    @pytest.mark.asyncio
    async def test_format_message_with_due_date(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should include due date in message."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
        )

        call_args = mock_slack_adapter.send_dm.call_args
        message = call_args[0][1]  # Second positional arg
        assert "*Due:* 2026-01-25" in message

    @pytest.mark.asyncio
    async def test_format_message_without_due_date(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item_no_due_date,
    ):
        """Should omit due date line when not present."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item_no_due_date,
        )

        call_args = mock_slack_adapter.send_dm.call_args
        message = call_args[0][1]
        assert "*Due:*" not in message
        assert "Review the design document" in message

    @pytest.mark.asyncio
    async def test_format_message_with_smartsheet_url(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should include Smartsheet link in message."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
            smartsheet_url="https://smartsheet.com/row/456",
        )

        call_args = mock_slack_adapter.send_dm.call_args
        message = call_args[0][1]
        assert "<https://smartsheet.com/row/456|View in Smartsheet>" in message

    @pytest.mark.asyncio
    async def test_format_message_without_url(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should omit link when no URL provided."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
        )

        call_args = mock_slack_adapter.send_dm.call_args
        message = call_args[0][1]
        assert "View in Smartsheet" not in message

    @pytest.mark.asyncio
    async def test_format_message_includes_title(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should include item description as title."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
        )

        call_args = mock_slack_adapter.send_dm.call_args
        message = call_args[0][1]
        assert "*New action item assigned to you:*" in message
        assert "> Complete the quarterly report" in message


class TestAuditLog:
    """Tests for audit log functionality."""

    @pytest.mark.asyncio
    async def test_get_audit_log_returns_copy(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should return copy of audit log, not reference."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
        )

        log1 = notification_service.get_audit_log()
        log2 = notification_service.get_audit_log()

        assert log1 is not log2
        assert log1 == log2

    @pytest.mark.asyncio
    async def test_audit_log_cleared(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should clear audit log."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
        )
        assert len(notification_service.get_audit_log()) == 1

        notification_service.clear_audit_log()
        assert len(notification_service.get_audit_log()) == 0

    @pytest.mark.asyncio
    async def test_audit_log_multiple_entries(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should accumulate multiple audit entries."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner("user1@example.com", sample_action_item)
        await notification_service.notify_owner("user2@example.com", sample_action_item)

        audit_log = notification_service.get_audit_log()
        assert len(audit_log) == 2
        assert audit_log[0].recipient_email == "user1@example.com"
        assert audit_log[1].recipient_email == "user2@example.com"

    @pytest.mark.asyncio
    async def test_audit_log_includes_smartsheet_url(
        self,
        notification_service,
        mock_slack_adapter,
        sample_action_item,
    ):
        """Should include Smartsheet URL in audit record."""
        mock_slack_adapter.lookup_user_by_email.return_value = {
            "id": "U123",
            "name": "johndoe",
        }
        mock_slack_adapter.send_dm.return_value = {"success": True, "ts": "123"}

        await notification_service.notify_owner(
            "john@example.com",
            sample_action_item,
            smartsheet_url="https://smartsheet.com/row/789",
        )

        audit_log = notification_service.get_audit_log()
        assert audit_log[0].smartsheet_url == "https://smartsheet.com/row/789"
