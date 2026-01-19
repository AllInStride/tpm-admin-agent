"""Duplicate detection service for RAID items.

Uses RapidFuzz to find potentially duplicate items based on
description similarity across meetings.
"""

import logging

from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from src.db.turso import TursoClient

logger = logging.getLogger(__name__)


class DuplicateMatch(BaseModel):
    """A potential duplicate match."""

    item_id: str = Field(description="ID of the matching item")
    description: str = Field(description="Description of the matching item")
    meeting_id: str = Field(description="Meeting ID where item was found")
    similarity: float = Field(ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    meeting_title: str | None = Field(
        default=None, description="Title of the source meeting"
    )


class DuplicateCheckResult(BaseModel):
    """Result of a duplicate check."""

    new_description: str = Field(description="Description being checked")
    potential_duplicates: list[DuplicateMatch] = Field(
        default_factory=list, description="List of potential duplicate matches"
    )
    has_duplicates: bool = Field(
        description="True if any matches found above threshold"
    )


class DuplicateDetector:
    """Detects potential duplicate RAID items using RapidFuzz.

    Uses token_set_ratio for flexible matching that handles
    word order differences.
    """

    def __init__(self, db_client: TursoClient, threshold: float = 0.85):
        """Initialize duplicate detector.

        Args:
            db_client: TursoClient for database operations
            threshold: Minimum similarity score (0.0-1.0) to consider a match
        """
        self._db = db_client
        self._threshold = threshold

    async def find_duplicates(
        self,
        description: str,
        item_type: str | None = None,
        limit: int = 5,
        exclude_item_id: str | None = None,
    ) -> DuplicateCheckResult:
        """Find potential duplicates of a description.

        Args:
            description: Description to check for duplicates
            item_type: Optional type filter (action, risk, issue, decision)
            limit: Maximum number of matches to return
            exclude_item_id: Optional item ID to exclude from results
                (for checking an existing item's duplicates)

        Returns:
            DuplicateCheckResult with potential matches
        """
        # Load existing items
        existing_items = await self._load_existing_items(item_type)

        if not existing_items:
            return DuplicateCheckResult(
                new_description=description,
                potential_duplicates=[],
                has_duplicates=False,
            )

        # Get rejections if we have an item_id
        rejected_ids: set[str] = set()
        if exclude_item_id:
            rejected_ids = await self.get_rejections(exclude_item_id)

        # Filter out rejected items and the item itself
        filtered_items = [
            item
            for item in existing_items
            if item["id"] != exclude_item_id and item["id"] not in rejected_ids
        ]

        if not filtered_items:
            return DuplicateCheckResult(
                new_description=description,
                potential_duplicates=[],
                has_duplicates=False,
            )

        # Build choices list for rapidfuzz
        choices = [item["description"] for item in filtered_items]

        # Use token_set_ratio for flexible matching (handles word order)
        # Score cutoff is threshold * 100 (rapidfuzz uses 0-100 scale)
        results = process.extract(
            description,
            choices,
            scorer=fuzz.token_set_ratio,
            limit=limit,
            score_cutoff=self._threshold * 100,
        )

        # Map results back to items
        potential_duplicates = []
        for matched_text, score, idx in results:
            item = filtered_items[idx]
            # Get meeting title
            meeting_title = await self._get_meeting_title(item["meeting_id"])
            potential_duplicates.append(
                DuplicateMatch(
                    item_id=item["id"],
                    description=item["description"],
                    meeting_id=item["meeting_id"],
                    similarity=score / 100.0,  # Normalize to 0.0-1.0
                    meeting_title=meeting_title,
                )
            )

        return DuplicateCheckResult(
            new_description=description,
            potential_duplicates=potential_duplicates,
            has_duplicates=len(potential_duplicates) > 0,
        )

    async def record_rejection(self, item_id: str, duplicate_id: str) -> None:
        """Record a rejection of a duplicate suggestion.

        Stores the rejection so we don't re-prompt the user.

        Args:
            item_id: ID of the item being compared
            duplicate_id: ID of the item that was rejected as duplicate
        """
        # Ensure table exists
        await self._ensure_rejections_table()

        await self._db.execute(
            """
            INSERT OR IGNORE INTO duplicate_rejections
                (item_id, rejected_duplicate_id)
            VALUES (?, ?)
            """,
            [item_id, duplicate_id],
        )
        logger.debug(f"Recorded rejection: {item_id} not duplicate of {duplicate_id}")

    async def get_rejections(self, item_id: str) -> set[str]:
        """Get set of duplicate IDs that were rejected for an item.

        Args:
            item_id: ID of the item

        Returns:
            Set of duplicate item IDs that were rejected
        """
        # Ensure table exists
        await self._ensure_rejections_table()

        result = await self._db.execute(
            """
            SELECT rejected_duplicate_id
            FROM duplicate_rejections
            WHERE item_id = ?
            """,
            [item_id],
        )
        return {row[0] for row in result.rows}

    async def _load_existing_items(self, item_type: str | None = None) -> list[dict]:
        """Load existing RAID items from projection.

        Args:
            item_type: Optional filter by item type

        Returns:
            List of item dicts with id, description, meeting_id
        """
        if item_type:
            result = await self._db.execute(
                """
                SELECT id, description, meeting_id
                FROM raid_items_projection
                WHERE item_type = ?
                """,
                [item_type],
            )
        else:
            result = await self._db.execute(
                """
                SELECT id, description, meeting_id
                FROM raid_items_projection
                """
            )

        return [
            {
                "id": row[0],
                "description": row[1],
                "meeting_id": row[2],
            }
            for row in result.rows
        ]

    async def _get_meeting_title(self, meeting_id: str) -> str | None:
        """Get meeting title from projection.

        Args:
            meeting_id: Meeting UUID

        Returns:
            Meeting title or None if not found
        """
        result = await self._db.execute(
            """
            SELECT title
            FROM meetings_projection
            WHERE id = ?
            """,
            [meeting_id],
        )
        if result.rows:
            return result.rows[0][0]
        return None

    async def _ensure_rejections_table(self) -> None:
        """Create duplicate_rejections table if it doesn't exist."""
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS duplicate_rejections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                rejected_duplicate_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_id, rejected_duplicate_id)
            )
            """
        )
