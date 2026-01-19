"""Integration layer for external system connections.

This module provides orchestration for writing to external systems
like Smartsheet and sending notifications via Slack.
"""

from src.integration.notification_service import NotificationService
from src.integration.schemas import (
    RAID_COLUMNS,
    NotificationRecord,
    NotificationResult,
    RaidRowData,
    SmartsheetConfig,
    SmartsheetWriteResult,
)

__all__ = [
    "NotificationRecord",
    "NotificationResult",
    "NotificationService",
    "RAID_COLUMNS",
    "RaidRowData",
    "SmartsheetConfig",
    "SmartsheetWriteResult",
]
