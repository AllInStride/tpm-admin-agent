"""Tests for SlackAdapter extended methods (channel history and Block Kit DMs)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from src.adapters.slack_adapter import SlackAdapter


@pytest.fixture
def mock_web_client():
    """Mock Slack WebClient."""
    with patch("src.adapters.slack_adapter.WebClient") as mock:
        yield mock


class TestGetChannelHistory:
    """Tests for get_channel_history method."""

    @pytest.mark.asyncio
    async def test_returns_messages_from_channel(self, mock_web_client):
        """Should return messages from channel history."""
        mock_client = MagicMock()
        mock_messages = [
            {"text": "Hello world", "user": "U123", "ts": "1234567890.123456"},
            {"text": "Reply", "user": "U456", "ts": "1234567891.123456"},
        ]
        mock_client.conversations_history.return_value = {"messages": mock_messages}
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_history("C123")

        assert result == mock_messages
        mock_client.conversations_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_days_parameter_converts_to_oldest(self, mock_web_client):
        """Should convert days to oldest timestamp."""
        mock_client = MagicMock()
        mock_client.conversations_history.return_value = {"messages": []}
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        await adapter.get_channel_history("C123", days=7)

        call_kwargs = mock_client.conversations_history.call_args[1]
        oldest = float(call_kwargs["oldest"])
        now = datetime.now(UTC).timestamp()
        # oldest should be approximately 7 days ago (within 1 minute tolerance)
        expected_oldest = now - (7 * 24 * 60 * 60)
        assert abs(oldest - expected_oldest) < 60

    @pytest.mark.asyncio
    async def test_limit_parameter_passed(self, mock_web_client):
        """Should pass limit parameter to API."""
        mock_client = MagicMock()
        mock_client.conversations_history.return_value = {"messages": []}
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        await adapter.get_channel_history("C123", limit=50)

        call_kwargs = mock_client.conversations_history.call_args[1]
        assert call_kwargs["limit"] == 50

    @pytest.mark.asyncio
    async def test_empty_channel_returns_empty_list(self, mock_web_client):
        """Should return empty list for channel with no messages."""
        mock_client = MagicMock()
        mock_client.conversations_history.return_value = {"messages": []}
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_history("C123")

        assert result == []

    @pytest.mark.asyncio
    async def test_channel_not_found_returns_empty_list(self, mock_web_client):
        """Should return empty list when channel not found."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value = "channel_not_found"
        error = SlackApiError("Channel not found", response=mock_response)
        mock_client.conversations_history.side_effect = error
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_history("C_INVALID")

        assert result == []

    @pytest.mark.asyncio
    async def test_other_api_error_returns_empty_list(self, mock_web_client):
        """Should return empty list on other API errors."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value = "rate_limited"
        error = SlackApiError("Rate limited", response=mock_response)
        mock_client.conversations_history.side_effect = error
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_history("C123")

        assert result == []

    @pytest.mark.asyncio
    async def test_generic_exception_returns_empty_list(self, mock_web_client):
        """Should return empty list on unexpected errors."""
        mock_client = MagicMock()
        mock_client.conversations_history.side_effect = RuntimeError("Network error")
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_history("C123")

        assert result == []

    @pytest.mark.asyncio
    async def test_includes_thread_replies(self, mock_web_client):
        """Should include messages with thread_ts (replies)."""
        mock_client = MagicMock()
        mock_messages = [
            {"text": "Thread start", "user": "U123", "ts": "1234567890.123456"},
            {
                "text": "Reply in thread",
                "user": "U456",
                "ts": "1234567891.123456",
                "thread_ts": "1234567890.123456",
            },
        ]
        mock_client.conversations_history.return_value = {"messages": mock_messages}
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.get_channel_history("C123")

        assert len(result) == 2
        assert "thread_ts" in result[1]


class TestSendPrepDm:
    """Tests for send_prep_dm method."""

    @pytest.mark.asyncio
    async def test_sends_dm_with_blocks(self, mock_web_client):
        """Should send DM with Block Kit blocks."""
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_web_client.return_value = mock_client

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}},
        ]
        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.send_prep_dm("U123", blocks, "Hello fallback")

        assert result == {"success": True, "ts": "1234567890.123456"}
        mock_client.chat_postMessage.assert_called_once_with(
            channel="U123",
            blocks=blocks,
            text="Hello fallback",
        )

    @pytest.mark.asyncio
    async def test_blocks_passed_correctly(self, mock_web_client):
        """Should pass complex Block Kit blocks correctly."""
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_web_client.return_value = mock_client

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Meeting Prep"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Open Items:*\n- Item 1\n- Item 2"},
            },
        ]
        adapter = SlackAdapter(bot_token="xoxb-test")
        await adapter.send_prep_dm("U123", blocks, "Meeting Prep")

        call_kwargs = mock_client.chat_postMessage.call_args[1]
        assert call_kwargs["blocks"] == blocks

    @pytest.mark.asyncio
    async def test_text_fallback_used_for_notification(self, mock_web_client):
        """Should include text fallback for notification preview."""
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        await adapter.send_prep_dm("U123", [], "Important meeting prep")

        call_kwargs = mock_client.chat_postMessage.call_args[1]
        assert call_kwargs["text"] == "Important meeting prep"

    @pytest.mark.asyncio
    async def test_returns_error_on_api_failure(self, mock_web_client):
        """Should return error dict on API failure."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value = "user_not_found"
        error = SlackApiError("User not found", response=mock_response)
        mock_client.chat_postMessage.side_effect = error
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.send_prep_dm("U_INVALID", [], "Test")

        assert result == {"success": False, "error": "user_not_found"}

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, mock_web_client):
        """Should handle rate limiting error."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value = "ratelimited"
        error = SlackApiError("Rate limited", response=mock_response)
        mock_client.chat_postMessage.side_effect = error
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.send_prep_dm("U123", [], "Test")

        assert result == {"success": False, "error": "ratelimited"}

    @pytest.mark.asyncio
    async def test_handles_unknown_error(self, mock_web_client):
        """Should return unknown_error when no error code available."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value = None
        error = SlackApiError("Unknown", response=mock_response)
        mock_client.chat_postMessage.side_effect = error
        mock_web_client.return_value = mock_client

        adapter = SlackAdapter(bot_token="xoxb-test")
        result = await adapter.send_prep_dm("U123", [], "Test")

        assert result["success"] is False
