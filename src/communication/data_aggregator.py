"""Data aggregator for communication artifact generation.

Gathers data from repositories for a given time period and project,
providing all context needed for LLM synthesis.
"""

import asyncio
from datetime import datetime

import structlog

from src.communication.schemas import StatusData
from src.repositories.open_items_repo import OpenItemsRepository
from src.repositories.projection_repo import ProjectionRepository
from src.search.open_items import CLOSED_STATUSES

logger = structlog.get_logger()


class DataAggregator:
    """Aggregates data from repositories for communication artifacts.

    Gathers completed items, new items, open items, and meetings
    for a given time period to provide complete context for
    status generation.
    """

    def __init__(
        self,
        open_items_repo: OpenItemsRepository,
        projection_repo: ProjectionRepository,
    ):
        """Initialize aggregator with repository dependencies.

        Args:
            open_items_repo: Repository for open items queries
            projection_repo: Repository for projection table access
        """
        self._open_items = open_items_repo
        self._projections = projection_repo
        # Build closed statuses SQL fragment
        self._closed_statuses_sql = ", ".join(f"'{s}'" for s in CLOSED_STATUSES)

    async def gather_for_status(
        self,
        project_id: str,
        since: datetime,
        until: datetime | None = None,
    ) -> StatusData:
        """Gather all data needed for status generation.

        Args:
            project_id: Project scope (currently used as project_name)
            since: Start of period (e.g., last status update)
            until: End of period (default: now)

        Returns:
            StatusData with all relevant items aggregated
        """
        until = until or datetime.now()

        logger.info(
            "gathering status data",
            project_id=project_id,
            since=since.isoformat(),
            until=until.isoformat(),
        )

        # Query in parallel
        completed, new, open_items, meetings = await asyncio.gather(
            self._get_completed_items(since, until),
            self._get_new_items(since, until),
            self._get_open_items(),
            self._get_meetings(since, until),
        )

        # Derive categorized items
        blockers = [i for i in open_items if self._is_blocker(i, until)]
        risks = [i for i in open_items if i.get("item_type") == "risk"]
        issues = [i for i in open_items if i.get("item_type") == "issue"]
        decisions = [i for i in new if i.get("item_type") == "decision"]

        # Calculate metrics
        velocity = len(completed) - len(new)
        overdue_count = sum(1 for i in open_items if self._is_overdue(i, until))

        logger.info(
            "status data gathered",
            project_id=project_id,
            completed=len(completed),
            new=len(new),
            open=len(open_items),
            blockers=len(blockers),
            overdue=overdue_count,
        )

        return StatusData(
            project_id=project_id,
            time_period=(since, until),
            completed_items=completed,
            new_items=new,
            open_items=open_items,
            decisions=decisions,
            risks=risks,
            issues=issues,
            blockers=blockers,
            meetings_held=meetings,
            item_velocity=velocity,
            overdue_count=overdue_count,
        )

    async def _get_completed_items(
        self,
        since: datetime,
        until: datetime,
    ) -> list[dict]:
        """Get items completed (status changed to closed) in the period.

        Items are considered completed if:
        - status is in CLOSED_STATUSES
        - status was updated within the period (approximated by created_at for now)

        Note: Ideally we'd track status change timestamps, but for MVP
        we use items that exist with closed status as a proxy.
        """
        db = self._projections._db
        result = await db.execute(
            f"""
            SELECT id, meeting_id, item_type, description, owner,
                   due_date, status, confidence, created_at
            FROM raid_items_projection
            WHERE status IN ({self._closed_statuses_sql})
            ORDER BY created_at DESC
            """,
        )

        return [
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

    async def _get_new_items(
        self,
        since: datetime,
        until: datetime,
    ) -> list[dict]:
        """Get items created within the period."""
        db = self._projections._db
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")
        until_str = until.strftime("%Y-%m-%d %H:%M:%S")

        result = await db.execute(
            """
            SELECT id, meeting_id, item_type, description, owner,
                   due_date, status, confidence, created_at
            FROM raid_items_projection
            WHERE datetime(created_at) >= datetime(?)
              AND datetime(created_at) <= datetime(?)
            ORDER BY created_at DESC
            """,
            [since_str, until_str],
        )

        return [
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

    async def _get_open_items(self) -> list[dict]:
        """Get all currently open items."""
        db = self._projections._db
        result = await db.execute(
            f"""
            SELECT id, meeting_id, item_type, description, owner,
                   due_date, status, confidence, created_at
            FROM raid_items_projection
            WHERE status NOT IN ({self._closed_statuses_sql})
            ORDER BY
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                due_date ASC
            """,
        )

        return [
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

    async def _get_meetings(
        self,
        since: datetime,
        until: datetime,
    ) -> list[dict]:
        """Get meetings held within the period."""
        db = self._projections._db
        since_str = since.strftime("%Y-%m-%d")
        until_str = until.strftime("%Y-%m-%d")

        result = await db.execute(
            """
            SELECT id, title, date, participant_count, created_at
            FROM meetings_projection
            WHERE date(date) >= date(?)
              AND date(date) <= date(?)
            ORDER BY date DESC
            """,
            [since_str, until_str],
        )

        return [
            {
                "id": row[0],
                "title": row[1],
                "date": row[2],
                "participant_count": row[3],
                "created_at": row[4],
            }
            for row in result.rows
        ]

    def _is_blocker(self, item: dict, reference_date: datetime) -> bool:
        """Determine if an item is a blocker.

        An item is considered a blocker if:
        - It's overdue (due_date < reference_date)
        - OR it has "block" in description (flagged as blocking)
        """
        if self._is_overdue(item, reference_date):
            return True

        description = (item.get("description") or "").lower()
        return "block" in description or "blocked" in description

    def _is_overdue(self, item: dict, reference_date: datetime) -> bool:
        """Check if an item is overdue."""
        due_date_str = item.get("due_date")
        if not due_date_str:
            return False

        try:
            # Parse various date formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    due_date = datetime.strptime(due_date_str, fmt)
                    return due_date.date() < reference_date.date()
                except ValueError:
                    continue
            return False
        except Exception:
            return False
