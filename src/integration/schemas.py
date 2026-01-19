"""Integration-specific schemas for external system connections.

Defines models for Smartsheet configuration, write results,
column definitions for RAID item tracking, and notification schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.adapters.base import WriteResult


class SmartsheetConfig(BaseModel):
    """Configuration for Smartsheet integration.

    Specifies where to write RAID items - either an existing sheet
    or folder for auto-creation.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    sheet_id: int | None = Field(
        default=None, description="Existing sheet ID to write to"
    )
    folder_id: int | None = Field(
        default=None, description="Folder ID for auto-creating sheets"
    )
    auto_create: bool = Field(
        default=True, description="Create sheet automatically if missing"
    )


class SmartsheetWriteResult(WriteResult):
    """Result of a Smartsheet write operation.

    Extends WriteResult with Smartsheet-specific fields for
    tracking row IDs and sheet URLs.
    """

    row_ids: list[int] = Field(default_factory=list, description="IDs of created rows")
    sheet_url: str | None = Field(default=None, description="URL to view the sheet")


class RaidRowData(BaseModel):
    """Data for a single RAID item row in Smartsheet.

    Maps RAID item fields to Smartsheet columns with appropriate
    types and formatting.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    type: str = Field(description="RAID type: Action, Risk, Issue, Decision")
    title: str = Field(description="Item title/description")
    owner: str = Field(default="", description="Assigned owner email or name")
    status: str = Field(default="Open", description="Current status")
    due_date: str | None = Field(
        default=None, description="Due date in YYYY-MM-DD format"
    )
    source_meeting: str = Field(
        default="", description="Link to meeting minutes or meeting title"
    )
    created_date: str | None = Field(
        default=None, description="Created date in YYYY-MM-DD format"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence score"
    )
    item_hash: str = Field(default="", description="Unique hash for deduplication")


# Column definitions for RAID sheet per CONTEXT.md
# Type, Title, Owner, Status, Due Date, Source Meeting, Created Date, Confidence
RAID_COLUMNS = [
    {
        "title": "Type",
        "type": "PICKLIST",
        "options": ["Action", "Risk", "Issue", "Decision"],
    },
    {
        "title": "Title",
        "type": "TEXT_NUMBER",
        "primary": True,  # Primary column required by Smartsheet
    },
    {
        "title": "Owner",
        "type": "CONTACT_LIST",
    },
    {
        "title": "Status",
        "type": "PICKLIST",
        "options": [
            "Open",
            "In Progress",
            "Done",
            "Identified",
            "Mitigated",
            "Closed",
            "Investigating",
            "Resolved",
            "Documented",
        ],
    },
    {
        "title": "Due Date",
        "type": "DATE",
    },
    {
        "title": "Source Meeting",
        "type": "TEXT_NUMBER",
    },
    {
        "title": "Created Date",
        "type": "DATE",
    },
    {
        "title": "Confidence",
        "type": "TEXT_NUMBER",
    },
    {
        "title": "Item Hash",
        "type": "TEXT_NUMBER",
    },
]


class NotificationResult(BaseModel):
    """Result of a notification attempt."""

    model_config = ConfigDict(str_strip_whitespace=True)

    success: bool = Field(description="Whether notification was sent successfully")
    recipient_email: str = Field(description="Email address of the recipient")
    recipient_slack_id: str | None = Field(
        default=None, description="Slack user ID if found"
    )
    message_ts: str | None = Field(default=None, description="Slack message timestamp")
    error: str | None = Field(default=None, description="Error message if failed")


class NotificationRecord(BaseModel):
    """Audit record for a sent notification."""

    model_config = ConfigDict(str_strip_whitespace=True)

    recipient_email: str = Field(description="Email address of the recipient")
    item_description: str = Field(description="Description of the notified item")
    item_type: str = Field(description="RAID item type")
    smartsheet_url: str | None = Field(
        default=None, description="Link to Smartsheet row"
    )
    sent_at: datetime = Field(description="When notification was sent")
    success: bool = Field(description="Whether notification succeeded")
    error: str | None = Field(default=None, description="Error if notification failed")
