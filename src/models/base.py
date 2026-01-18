"""Base entity class for all domain models."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class BaseEntity(BaseModel):
    """Base class for all domain entities.

    Provides:
    - Unique ID (UUID)
    - Created/updated timestamps
    - Standard serialization config
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        from_attributes=True,
    )

    id: UUID = Field(default_factory=uuid4, description="Unique entity identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When entity was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When entity was last updated",
    )

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)
