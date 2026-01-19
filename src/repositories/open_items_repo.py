"""Repository for open items dashboard queries.

Provides efficient queries for open items across meetings,
avoiding N+1 query issues with aggregation queries.
"""

import json
import logging
from datetime import datetime

from src.db.turso import TursoClient
from src.search.open_items import (
    CLOSED_STATUSES,
    GroupedOpenItems,
    ItemHistory,
    ItemHistoryEntry,
    OpenItemFilter,
    OpenItemSummary,
    classify_change,
)

logger = logging.getLogger(__name__)


class OpenItemsRepository:
    """Repository for open items dashboard queries.

    Queries raid_items_projection table for dashboard aggregations,
    filtering, and grouping. Uses efficient SQL aggregations to
    avoid N+1 query patterns.
    """

    def __init__(self, db_client: TursoClient):
        """Initialize repository with database client.

        Args:
            db_client: TursoClient instance for database operations
        """
        self._db = db_client
        # Build the closed statuses list for SQL IN clause
        self._closed_statuses_sql = ", ".join(f"'{s}'" for s in CLOSED_STATUSES)

    async def get_summary(self) -> OpenItemSummary:
        """Get summary counts of open items.

        Returns summary in a single query to avoid N+1 issues.

        Returns:
            OpenItemSummary with counts by category
        """
        # Get main counts in single query
        counts_result = await self._db.execute(
            f"""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN date(due_date) < date('now') THEN 1 END) as overdue,
                COUNT(CASE WHEN date(due_date) = date('now') THEN 1 END) as due_today,
                COUNT(CASE WHEN date(due_date) > date('now')
                    AND date(due_date) <= date('now', '+7 days')
                    THEN 1 END) as due_this_week
            FROM raid_items_projection
            WHERE status NOT IN ({self._closed_statuses_sql})
            """
        )

        # Get counts by type
        type_result = await self._db.execute(f"""
            SELECT item_type, COUNT(*) as count
            FROM raid_items_projection
            WHERE status NOT IN ({self._closed_statuses_sql})
            GROUP BY item_type
        """)

        # Parse results
        row = counts_result.rows[0] if counts_result.rows else (0, 0, 0, 0)
        by_type = {r[0]: r[1] for r in type_result.rows}

        return OpenItemSummary(
            total=row[0] or 0,
            overdue=row[1] or 0,
            due_today=row[2] or 0,
            due_this_week=row[3] or 0,
            by_type=by_type,
        )

    async def get_items(
        self,
        filter: OpenItemFilter | None = None,
        group_by: str = "due_date",
    ) -> GroupedOpenItems:
        """Get open items with filtering and grouping.

        Args:
            filter: Optional filter criteria
            group_by: Grouping key: 'due_date', 'owner', or 'item_type'

        Returns:
            GroupedOpenItems with summary and filtered items
        """
        filter = filter or OpenItemFilter()

        # Build WHERE clause
        where_clauses = [f"status NOT IN ({self._closed_statuses_sql})"]
        params: list = []

        if filter.item_type:
            where_clauses.append("item_type = ?")
            params.append(filter.item_type)

        if filter.owner:
            where_clauses.append("owner = ?")
            params.append(filter.owner)

        if filter.meeting_id:
            where_clauses.append("meeting_id = ?")
            params.append(filter.meeting_id)

        if filter.overdue_only:
            where_clauses.append("date(due_date) < date('now')")

        if filter.due_within_days is not None:
            where_clauses.append(
                f"date(due_date) <= date('now', '+{filter.due_within_days} days')"
            )

        where_sql = " AND ".join(where_clauses)

        # Determine ORDER BY based on group_by
        if group_by == "owner":
            order_sql = "ORDER BY owner, due_date"
        elif group_by == "item_type":
            order_sql = "ORDER BY item_type, due_date"
        else:  # due_date is default
            order_sql = (
                "ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC"
            )

        # Execute query
        query = f"""
            SELECT id, meeting_id, item_type, description, owner,
                   due_date, status, confidence, created_at
            FROM raid_items_projection
            WHERE {where_sql}
            {order_sql}
        """

        result = await self._db.execute(query, params)

        # Convert rows to dicts
        items = [
            {
                "id": row[0],
                "meeting_id": row[1],
                "item_type": row[2],
                "description": row[3],
                "owner": row[4],
                "due_date": row[5],
                "status": row[6],
                "confidence": row[7],
                "created_at": row[8],
            }
            for row in result.rows
        ]

        # Get summary
        summary = await self.get_summary()

        return GroupedOpenItems(
            summary=summary,
            items=items,
            group_by=group_by,
        )

    async def close_item(self, item_id: str, new_status: str = "completed") -> bool:
        """Update item status to close it.

        Args:
            item_id: RAID item ID
            new_status: New status (default: 'completed')

        Returns:
            True if item was updated, False if not found
        """
        result = await self._db.execute(
            """
            UPDATE raid_items_projection
            SET status = ?
            WHERE id = ?
            """,
            [new_status, item_id],
        )
        updated = result.rows_affected > 0
        if updated:
            logger.debug(f"Closed item {item_id} with status {new_status}")
        return updated

    async def get_item_history(self, item_id: str) -> ItemHistory | None:
        """Get history of an item across meetings.

        Args:
            item_id: RAID item ID

        Returns:
            ItemHistory with chronological entries, or None if item not found
        """
        # First get the current item
        item_result = await self._db.execute(
            """
            SELECT id, item_type, description, status
            FROM raid_items_projection
            WHERE id = ?
            """,
            [item_id],
        )

        if not item_result.rows:
            return None

        item_row = item_result.rows[0]

        # Query events related to this item
        events_result = await self._db.execute(
            """
            SELECT e.timestamp, e.event_type, e.event_data, e.aggregate_id
            FROM events e
            WHERE e.aggregate_id = ?
               OR e.event_data LIKE ?
            ORDER BY e.timestamp ASC
            """,
            [item_id, f'%"{item_id}"%'],
        )

        # Build history entries with meeting context
        entries = []
        for row in events_result.rows:
            timestamp_str = row[0]
            event_type = row[1]
            event_data_str = row[2]
            # row[3] is aggregate_id, kept in query for debugging

            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.now()

            # Try to get meeting context from event_data
            meeting_id = None
            meeting_title = None
            meeting_date = None

            if event_data_str:
                try:
                    event_data = json.loads(event_data_str)
                    meeting_id = event_data.get("meeting_id")
                except (json.JSONDecodeError, TypeError):
                    pass

            # If we have a meeting_id, look up the meeting
            if meeting_id:
                meeting_result = await self._db.execute(
                    """
                    SELECT title, date
                    FROM meetings_projection
                    WHERE id = ?
                    """,
                    [meeting_id],
                )
                if meeting_result.rows:
                    meeting_title = meeting_result.rows[0][0]
                    meeting_date = meeting_result.rows[0][1]

            entries.append(
                ItemHistoryEntry(
                    timestamp=timestamp,
                    event_type=event_type,
                    change_type=classify_change(event_type),
                    meeting_id=meeting_id,
                    meeting_title=meeting_title,
                    meeting_date=meeting_date,
                )
            )

        return ItemHistory(
            item_id=item_row[0],
            item_type=item_row[1],
            description=item_row[2],
            current_status=item_row[3],
            entries=entries,
        )
