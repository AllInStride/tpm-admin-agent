"""Tests for SlackAdapter."""

from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from src.adapters.slack_adapter import SlackAdapter


@pytest.fixture
def mock_web_client():
    """Mock Slack WebClient."""
    with patch("src.adapters.slack_adapter.WebClient") as mock:
        yield mock


class TestSlackAdapterInit:
    """Tests for SlackAdapter initialization."""

    def test_uses_provided_token(self, mock_web_client):
        """Should use token passed to constructor."""
        adapter = SlackAdapter(bot_token="xoxb-test-token")
        adapter._get_client()

        mock_web_client.assert_called_once_with(token="xoxb-test-token")

    def test_falls_back_to_env_var(self, mock_web_client, monkeypatch):
        """Should fall back to SLACK_BOT_TOKEN env var."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-env-token")
        adapter = SlackAdapter()
        adapter._get_client()

        mock_web_client.assert_called_once_with(token="xoxb-env-token")

    def test_no_token_raises_value_error(self, mock_web_client, monkeypatch):
        """Should raise ValueError when no token available."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        adapter = SlackAdapter()

        with pytest.raises(ValueError, match="No Slack token"):
            adapter._get_client()


class TestVerifyMember:
    """Tests for verify_member method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_found(self, mock_web_client):
        """Should return True when user found by email."""
        mock_client = MagicMock()
        mock_client.users_lookupByEmail.return_value = {"ok": True}
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.verify_member("john@example.com")

        assert result is True
        mock_client.users_lookupByEmail.assert_called_once_with(
            email="john@example.com"
        )

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, mock_web_client):
        """Should return False when users_not_found error."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value = "users_not_found"
        error = SlackApiError("User not found", response=mock_response)
        mock_client.users_lookupByEmail.side_effect = error
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.verify_member("unknown@example.com")

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_other_api_error(self, mock_web_client):
        """Should return False and log warning on other API errors."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value = "rate_limited"
        error = SlackApiError("Rate limited", response=mock_response)
        mock_client.users_lookupByEmail.side_effect = error
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.verify_member("john@example.com")

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self, mock_web_client):
        """Should return False on unexpected errors."""
        mock_client = MagicMock()
        mock_client.users_lookupByEmail.side_effect = RuntimeError("Connection failed")
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.verify_member("john@example.com")

        assert result is False


class TestGetChannelMembers:
    """Tests for get_channel_members method."""

    @pytest.mark.asyncio
    async def test_returns_member_emails(self, mock_web_client):
        """Should return set of member emails."""
        mock_client = MagicMock()
        mock_client.conversations_members.return_value = {
            "members": ["U123", "U456"],
        }
        mock_client.users_info.side_effect = [
            {"user": {"profile": {"email": "alice@example.com"}}},
            {"user": {"profile": {"email": "BOB@example.com"}}},
        ]
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_members("C123")

        assert result == {"alice@example.com", "bob@example.com"}

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self, mock_web_client):
        """Should return empty set on error."""
        mock_client = MagicMock()
        mock_client.conversations_members.side_effect = RuntimeError("API error")
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_members("C123")

        assert result == set()

    @pytest.mark.asyncio
    async def test_skips_members_without_email(self, mock_web_client):
        """Should skip members who don't have email in profile."""
        mock_client = MagicMock()
        mock_client.conversations_members.return_value = {
            "members": ["U123", "U456"],
        }
        mock_client.users_info.side_effect = [
            {"user": {"profile": {"email": "alice@example.com"}}},
            {"user": {"profile": {}}},  # No email
        ]
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_members("C123")

        assert result == {"alice@example.com"}
