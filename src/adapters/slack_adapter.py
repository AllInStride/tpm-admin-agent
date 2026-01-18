"""Slack workspace adapter for identity verification.

Uses Slack Web API to verify that users exist in a workspace,
enabling multi-source identity corroboration.
"""

import os

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

    async def verify_member(self, email: str) -> bool:
        """Check if email exists as Slack workspace member.

        Args:
            email: Email address to verify

        Returns:
            True if member exists in workspace
        """
        try:
            client = self._get_client()
            # Use users.lookupByEmail API
            result = client.users_lookupByEmail(email=email)
            return result.get("ok", False)
        except SlackApiError as e:
            if e.response.get("error") == "users_not_found":
                return False
            logger.warning(
                "Slack API error verifying member",
                email=email,
                error=str(e),
            )
            return False
        except Exception as e:
            logger.warning(
                "Error verifying Slack member",
                email=email,
                error=str(e),
            )
            return False

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
