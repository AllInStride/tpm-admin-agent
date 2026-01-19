"""Notification service for RAID item owner notifications.

Sends Slack DMs to action item owners when they are assigned tasks
from meeting extraction, with full audit trail.
"""

from datetime import UTC, datetime

import structlog

from src.adapters.slack_adapter import SlackAdapter
from src.integration.schemas import NotificationRecord, NotificationResult
from src.output.schemas import ActionItemData

logger = structlog.get_logger()


class NotificationService:
    """Service for sending and auditing RAID item notifications.

    Looks up users by email, sends Slack DMs, and maintains an
    audit log of all notification attempts.
    """

    def __init__(self, slack_adapter: SlackAdapter):
        """Initialize with Slack adapter.

        Args:
            slack_adapter: Configured SlackAdapter for sending DMs
        """
        self._slack = slack_adapter
        self._audit_log: list[NotificationRecord] = []

    async def notify_owner(
        self,
        owner_email: str,
        item: ActionItemData,
        smartsheet_url: str | None = None,
    ) -> NotificationResult:
        """Notify owner of new action item assignment.

        Looks up user by email, sends DM, records in audit log.

        Args:
            owner_email: Email address of the item owner
            item: Action item data to notify about
            smartsheet_url: Optional link to Smartsheet row

        Returns:
            NotificationResult with success status and details
        """
        # Lookup user by email
        user = await self._slack.lookup_user_by_email(owner_email)
        if not user:
            result = NotificationResult(
                success=False,
                recipient_email=owner_email,
                error="user_not_found",
            )
            self._record_audit(owner_email, item, smartsheet_url, result)
            return result

        # Format and send message
        message = self._format_message(item, smartsheet_url)
        dm_result = await self._slack.send_dm(user["id"], message)

        result = NotificationResult(
            success=dm_result.get("success", False),
            recipient_email=owner_email,
            recipient_slack_id=user["id"],
            message_ts=dm_result.get("ts"),
            error=dm_result.get("error"),
        )
        self._record_audit(owner_email, item, smartsheet_url, result)
        return result

    def _format_message(
        self,
        item: ActionItemData,
        smartsheet_url: str | None,
    ) -> str:
        """Format notification message per CONTEXT.md spec.

        Plain text with mrkdwn: title, due date, Smartsheet link.

        Args:
            item: Action item to format
            smartsheet_url: Optional Smartsheet link

        Returns:
            Formatted message string with mrkdwn
        """
        parts = [
            "*New action item assigned to you:*",
            f"> {item.description}",
        ]
        if item.due_date:
            parts.append(f"*Due:* {item.due_date}")
        if smartsheet_url:
            parts.append(f"<{smartsheet_url}|View in Smartsheet>")
        return "\n".join(parts)

    def _record_audit(
        self,
        email: str,
        item: ActionItemData,
        url: str | None,
        result: NotificationResult,
    ) -> None:
        """Record notification in audit log.

        Args:
            email: Recipient email
            item: Action item that was notified
            url: Smartsheet URL if available
            result: Result of notification attempt
        """
        record = NotificationRecord(
            recipient_email=email,
            item_description=item.description,
            item_type="Action",
            smartsheet_url=url,
            sent_at=datetime.now(UTC),
            success=result.success,
            error=result.error,
        )
        self._audit_log.append(record)
        logger.info(
            "notification recorded",
            email=email,
            success=result.success,
        )

    def get_audit_log(self) -> list[NotificationRecord]:
        """Return copy of audit log.

        Returns:
            Copy of the audit log list
        """
        return list(self._audit_log)

    def clear_audit_log(self) -> None:
        """Clear audit log."""
        self._audit_log.clear()
