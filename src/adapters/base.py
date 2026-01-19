"""Base types for output adapters.

This module defines the OutputAdapter protocol and WriteResult model
used by adapters that write data to external systems (Sheets, Drive, etc.).
"""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class WriteResult(BaseModel):
    """Result of a write operation to an external system.

    Captures success/failure status along with metadata about
    the write operation (external IDs, URLs, timing).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    success: bool = Field(description="Whether the write succeeded")
    dry_run: bool = Field(default=False, description="True if this was a dry run")
    item_count: int = Field(default=0, description="Number of items written")
    external_id: str | None = Field(
        default=None, description="External ID (Sheet ID, file ID, etc.)"
    )
    url: str | None = Field(default=None, description="Web view link if available")
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    duration_ms: int | None = Field(
        default=None, description="Operation duration in milliseconds"
    )


@runtime_checkable
class OutputAdapter(Protocol):
    """Protocol for adapters that write data to external systems.

    Adapters implement this protocol for structural subtyping -
    they don't need to inherit, just implement the methods.
    """

    async def write(
        self, data: dict, destination: str, *, dry_run: bool = False
    ) -> WriteResult:
        """Write data to an external destination.

        Args:
            data: Data to write (adapter-specific format)
            destination: Where to write (sheet ID, folder ID, etc.)
            dry_run: If True, validate but don't actually write

        Returns:
            WriteResult with operation outcome
        """
        ...

    async def health_check(self) -> bool:
        """Check if adapter is properly configured and can connect.

        Returns:
            True if adapter is healthy, False otherwise
        """
        ...
