"""Project-specific output configuration.

Contains settings for per-project output destinations and
template preferences.
"""

from pydantic import BaseModel, ConfigDict, Field


class ProjectOutputConfig(BaseModel):
    """Per-project output configuration.

    Defines where to route meeting minutes and RAID items,
    which adapters to use, and template preferences.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: str | None = Field(
        default=None, description="Optional project identifier"
    )
    minutes_destination: str | None = Field(
        default=None, description="Google Drive folder ID for minutes"
    )
    raid_destination: str | None = Field(
        default=None, description="Google Sheets spreadsheet ID for RAID items"
    )
    raid_sheet_name: str = Field(
        default="RAID", description="Worksheet name within spreadsheet"
    )
    template_name: str = Field(
        default="default_minutes", description="Template name for rendering"
    )
    enabled_targets: list[str] = Field(
        default_factory=lambda: ["drive", "sheets"],
        description="Which output adapters to use",
    )

    # Smartsheet settings
    smartsheet_sheet_id: int | None = Field(
        default=None, description="Smartsheet sheet ID for RAID items"
    )
    smartsheet_folder_id: int | None = Field(
        default=None, description="Folder ID for auto-creating sheets"
    )
    auto_create_sheet: bool = Field(
        default=True, description="Auto-create sheet if missing"
    )

    # Notification settings
    notify_owners: bool = Field(
        default=True, description="Send Slack DMs to action item owners"
    )
    fallback_email: str | None = Field(
        default=None, description="Fallback email for unresolved owners"
    )

    @classmethod
    def default(cls) -> "ProjectOutputConfig":
        """Create a default config with no destinations.

        Returns:
            ProjectOutputConfig safe for dry-run mode
        """
        return cls(
            minutes_destination=None,
            raid_destination=None,
        )
