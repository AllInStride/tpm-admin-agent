"""Slack workspace adapter for identity verification and messaging.

Uses Slack Web API to verify that users exist in a workspace,
enabling multi-source identity corroboration. Also supports channel
history retrieval and Block Kit formatted messaging for meeting prep.
"""

import os
from datetime import UTC, datetime, timedelta

import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = structlog.get_logger()


class SlackAdapter:
    """Adapter for Slack workspace member verification.

    Uses Slack Web API to verify that an email exists in the workspace
    and optionally in specific channels.
    """

    def __init__(self, bot_token: str | None = None):
        """Initialize with bot token.

        Args:
            bot_token: Slack bot token (xoxb-...).
                      Falls back to SLACK_BOT_TOKEN env var.
        """
        self._token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
        self._client: WebClient | None = None

    def _get_client(self) -> WebClient:
        """Get or create Slack client."""
        if self._client is None:
            if not self._token:
                raise ValueError(
                    "No Slack token. Set SLACK_BOT_TOKEN env var "
                    "or pass bot_token to constructor."
                )
            self._client = WebClient(token=self._token)
        return self._client

    async def lookup_user_by_email(self, email: str) -> dict | None:
        """Look up Slack user by email address.

        Args:
            email: Email address to look up

        Returns:
            User dict with 'id', 'name', 'profile' or None if not found
        """
        try:
            client = self._get_client()
            result = client.users_lookupByEmail(email=email)
            return result.get("user")
        except SlackApiError as e:
            if e.response.get("error") == "users_not_found":
                return None
            logger.warning(
                "Slack API error looking up user",
                email=email,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.warning(
                "Error looking up Slack user",
                email=email,
                error=str(e),
            )
            return None

    async def verify_member(self, email: str) -> bool:
        """Check if email exists as Slack workspace member.

        Args:
            email: Email address to verify

        Returns:
            True if member exists in workspace
        """
        user = await self.lookup_user_by_email(email)
        return user is not None

    async def send_dm(
        self,
        user_id: str,
        message: str,
    ) -> dict:
        """Send direct message to a Slack user.

        Args:
            user_id: Slack user ID (not email)
            message: Message text (supports mrkdwn formatting)

        Returns:
            Dict with 'success' and 'ts' (timestamp) or 'error'
        """
        try:
            client = self._get_client()
            response = client.chat_postMessage(
                channel=user_id,  # DM channel opened automatically
                text=message,
            )
            return {"success": True, "ts": response["ts"]}
        except SlackApiError as e:
            error = e.response.get("error", "unknown_error")
            logger.warning(
                "Failed to send Slack DM",
                user_id=user_id,
                error=error,
            )
            return {"success": False, "error": error}

    async def get_channel_members(self, channel_id: str) -> set[str]:
        """Get email addresses of channel members.

        Args:
            channel_id: Slack channel ID

        Returns:
            Set of email addresses in channel
        """
        try:
            client = self._get_client()
            # Get member IDs
            members_result = client.conversations_members(channel=channel_id)
            member_ids = members_result.get("members", [])

            # Get email for each member
            emails: set[str] = set()
            for member_id in member_ids:
                try:
                    user_result = client.users_info(user=member_id)
                    user = user_result.get("user", {})
                    profile = user.get("profile", {})
                    if email := profile.get("email"):
                        emails.add(email.lower())
                except SlackApiError:
                    continue
            return emails
        except Exception as e:
            logger.warning(
                "Error getting channel members",
                channel_id=channel_id,
                error=str(e),
            )
            return set()

    async def get_channel_history(
        self,
        channel_id: str,
        days: int = 7,
        limit: int = 100,
    ) -> list[dict]:
        """Get recent messages from a channel.

        Args:
            channel_id: Slack channel ID
            days: How many days back to look (default 7)
            limit: Maximum messages to return (default 100)

        Returns:
            List of message dicts (newest first) with text, user, ts,
            and thread_ts if the message is a reply.
        """
        try:
            client = self._get_client()
            oldest = (datetime.now(UTC) - timedelta(days=days)).timestamp()

            result = client.conversations_history(
                channel=channel_id,
                oldest=str(oldest),
                limit=limit,
            )
            return result.get("messages", [])
        except SlackApiError as e:
            if e.response.get("error") == "channel_not_found":
                logger.warning(
                    "Channel not found for history",
                    channel_id=channel_id,
                )
                return []
            logger.warning(
                "Slack API error getting channel history",
                channel_id=channel_id,
                error=str(e),
            )
            return []
        except Exception as e:
            logger.warning(
                "Error getting channel history",
                channel_id=channel_id,
                error=str(e),
            )
            return []

    async def send_prep_dm(
        self,
        user_id: str,
        blocks: list[dict],
        text_fallback: str,
    ) -> dict:
        """Send prep summary as DM with Block Kit formatting.

        Args:
            user_id: Slack user ID
            blocks: Block Kit blocks for rich formatting
            text_fallback: Plain text fallback for notifications

        Returns:
            Dict with 'success' and 'ts' (timestamp) or 'error'
        """
        try:
            client = self._get_client()
            response = client.chat_postMessage(
                channel=user_id,  # DM channel opened automatically
                blocks=blocks,
                text=text_fallback,
            )
            return {"success": True, "ts": response["ts"]}
        except SlackApiError as e:
            error = e.response.get("error", "unknown_error")
            logger.warning(
                "Failed to send Slack prep DM",
                user_id=user_id,
                error=error,
            )
            return {"success": False, "error": error}
