"""Repository for projection tables and FTS5 indexes.

Provides database operations for read projections used by
cross-meeting intelligence features.
"""

import logging

from src.db.turso import TursoClient
from src.search.schemas import (
    MeetingProjection,
    RaidItemProjection,
    TranscriptProjection,
)

logger = logging.getLogger(__name__)


class ProjectionRepository:
    """Repository for managing projection tables with FTS5 search indexes.

    Handles CRUD operations for meetings, RAID items, and transcript
    projections. Uses FTS5 external content tables for full-text search.
    """

    def __init__(self, db_client: TursoClient):
        """Initialize repository with database client.

        Args:
            db_client: TursoClient instance for database operations
        """
        self._db = db_client

    async def initialize(self) -> None:
        """Create projection tables and FTS5 indexes if they don't exist.

        Note: Uses individual execute() calls instead of execute_batch()
        for FTS5 operations per RESEARCH.md Pitfall 1.
        """
        # Meetings projection table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS meetings_projection (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                date TEXT,
                participant_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # RAID items projection table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS raid_items_projection (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                description TEXT NOT NULL,
                owner TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                confidence REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add rowid alias for FTS5 external content table
        # SQLite requires explicit rowid for external content tables
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_items_meeting
            ON raid_items_projection(meeting_id)
        """)

        # Transcripts projection table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS transcripts_projection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id TEXT NOT NULL,
                speaker TEXT,
                text TEXT NOT NULL,
                start_time REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_meeting
            ON transcripts_projection(meeting_id)
        """)

        # FTS5 for RAID items (external content)
        await self._db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS raid_items_fts USING fts5(
                description,
                owner,
                content='raid_items_projection',
                content_rowid='rowid',
                tokenize='porter unicode61'
            )
        """)

        # FTS5 for transcripts (external content)
        await self._db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS transcripts_fts USING fts5(
                speaker,
                text,
                content='transcripts_projection',
                content_rowid='id',
                tokenize='porter unicode61'
            )
        """)

        # Triggers for RAID items FTS sync
        await self._db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS raid_items_ai
            AFTER INSERT ON raid_items_projection
            BEGIN
                INSERT INTO raid_items_fts(rowid, description, owner)
                VALUES (new.rowid, new.description, new.owner);
            END
            """
        )

        await self._db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS raid_items_ad
            AFTER DELETE ON raid_items_projection
            BEGIN
                INSERT INTO raid_items_fts(raid_items_fts, rowid, description, owner)
                VALUES('delete', old.rowid, old.description, old.owner);
            END
            """
        )

        await self._db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS raid_items_au
            AFTER UPDATE ON raid_items_projection
            BEGIN
                INSERT INTO raid_items_fts(raid_items_fts, rowid, description, owner)
                VALUES('delete', old.rowid, old.description, old.owner);
                INSERT INTO raid_items_fts(rowid, description, owner)
                VALUES (new.rowid, new.description, new.owner);
            END
            """
        )

        # Triggers for transcripts FTS sync
        await self._db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS transcripts_ai
            AFTER INSERT ON transcripts_projection
            BEGIN
                INSERT INTO transcripts_fts(rowid, speaker, text)
                VALUES (new.id, new.speaker, new.text);
            END
            """
        )

        await self._db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS transcripts_ad
            AFTER DELETE ON transcripts_projection
            BEGIN
                INSERT INTO transcripts_fts(transcripts_fts, rowid, speaker, text)
                VALUES('delete', old.id, old.speaker, old.text);
            END
            """
        )

        logger.info("Projection tables and FTS5 indexes initialized")

    async def upsert_meeting(self, projection: MeetingProjection) -> None:
        """Insert or update a meeting projection.

        Args:
            projection: Meeting projection data
        """
        await self._db.execute(
            """
            INSERT INTO meetings_projection (id, title, date, participant_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                date = excluded.date,
                participant_count = excluded.participant_count
            """,
            [
                projection.id,
                projection.title,
                projection.date,
                projection.participant_count,
            ],
        )
        logger.debug(f"Upserted meeting projection: {projection.id}")

    async def upsert_raid_item(self, projection: RaidItemProjection) -> None:
        """Insert or update a RAID item projection.

        Args:
            projection: RAID item projection data
        """
        await self._db.execute(
            """
            INSERT INTO raid_items_projection
                (id, meeting_id, item_type, description,
                 owner, due_date, status, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                meeting_id = excluded.meeting_id,
                item_type = excluded.item_type,
                description = excluded.description,
                owner = excluded.owner,
                due_date = excluded.due_date,
                status = excluded.status,
                confidence = excluded.confidence
            """,
            [
                projection.id,
                projection.meeting_id,
                projection.item_type,
                projection.description,
                projection.owner,
                projection.due_date,
                projection.status,
                projection.confidence,
            ],
        )
        logger.debug(f"Upserted RAID item projection: {projection.id}")

    async def insert_transcript_utterance(
        self, projection: TranscriptProjection
    ) -> None:
        """Insert a transcript utterance projection.

        Args:
            projection: Transcript utterance projection data
        """
        await self._db.execute(
            """
            INSERT INTO transcripts_projection (meeting_id, speaker, text, start_time)
            VALUES (?, ?, ?, ?)
            """,
            [
                projection.meeting_id,
                projection.speaker,
                projection.text,
                projection.start_time,
            ],
        )
        logger.debug(
            f"Inserted transcript utterance for meeting: {projection.meeting_id}"
        )

    async def update_item_status(self, item_id: str, status: str) -> bool:
        """Update the status of a RAID item.

        Args:
            item_id: RAID item ID
            status: New status value

        Returns:
            True if item was updated, False if not found
        """
        result = await self._db.execute(
            """
            UPDATE raid_items_projection
            SET status = ?
            WHERE id = ?
            """,
            [status, item_id],
        )
        updated = result.rows_affected > 0
        if updated:
            logger.debug(f"Updated RAID item {item_id} status to {status}")
        return updated

    async def get_meeting(self, meeting_id: str) -> MeetingProjection | None:
        """Get a meeting projection by ID.

        Args:
            meeting_id: Meeting UUID

        Returns:
            MeetingProjection if found, None otherwise
        """
        result = await self._db.execute(
            """
            SELECT id, title, date, participant_count, created_at
            FROM meetings_projection
            WHERE id = ?
            """,
            [meeting_id],
        )
        if result.rows:
            row = result.rows[0]
            return MeetingProjection(
                id=row[0],
                title=row[1],
                date=row[2],
                participant_count=row[3],
                created_at=row[4],
            )
        return None

    async def get_raid_item(self, item_id: str) -> RaidItemProjection | None:
        """Get a RAID item projection by ID.

        Args:
            item_id: RAID item UUID

        Returns:
            RaidItemProjection if found, None otherwise
        """
        result = await self._db.execute(
            """
            SELECT id, meeting_id, item_type, description, owner,
                   due_date, status, confidence, created_at
            FROM raid_items_projection
            WHERE id = ?
            """,
            [item_id],
        )
        if result.rows:
            row = result.rows[0]
            return RaidItemProjection(
                id=row[0],
                meeting_id=row[1],
                item_type=row[2],
                description=row[3],
                owner=row[4],
                due_date=row[5],
                status=row[6],
                confidence=row[7],
                created_at=row[8],
            )
        return None

    async def clear_all_projections(self) -> None:
        """Clear all projection tables.

        Used during rebuild operations.
        """
        await self._db.execute("DELETE FROM transcripts_projection")
        await self._db.execute("DELETE FROM raid_items_projection")
        await self._db.execute("DELETE FROM meetings_projection")
        logger.info("Cleared all projection tables")

    async def rebuild_fts_indexes(self) -> None:
        """Rebuild FTS5 indexes from content tables.

        Call after bulk operations or suspected sync issues.
        """
        await self._db.execute(
            "INSERT INTO raid_items_fts(raid_items_fts) VALUES('rebuild')"
        )
        await self._db.execute(
            "INSERT INTO transcripts_fts(transcripts_fts) VALUES('rebuild')"
        )
        logger.info("Rebuilt FTS5 indexes")

    async def search_raid_items(
        self, query: str, limit: int = 50
    ) -> list[RaidItemProjection]:
        """Search RAID items using full-text search.

        Args:
            query: Search query (FTS5 match syntax)
            limit: Maximum results

        Returns:
            List of matching RAID item projections
        """
        result = await self._db.execute(
            """
            SELECT r.id, r.meeting_id, r.item_type, r.description, r.owner,
                   r.due_date, r.status, r.confidence, r.created_at
            FROM raid_items_projection r
            JOIN raid_items_fts f ON r.rowid = f.rowid
            WHERE raid_items_fts MATCH ?
            ORDER BY bm25(raid_items_fts)
            LIMIT ?
            """,
            [query, limit],
        )
        return [
            RaidItemProjection(
                id=row[0],
                meeting_id=row[1],
                item_type=row[2],
                description=row[3],
                owner=row[4],
                due_date=row[5],
                status=row[6],
                confidence=row[7],
                created_at=row[8],
            )
            for row in result.rows
        ]

    async def search_transcripts(
        self, query: str, limit: int = 50
    ) -> list[TranscriptProjection]:
        """Search transcript utterances using full-text search.

        Args:
            query: Search query (FTS5 match syntax)
            limit: Maximum results

        Returns:
            List of matching transcript projections
        """
        result = await self._db.execute(
            """
            SELECT t.id, t.meeting_id, t.speaker, t.text, t.start_time, t.created_at
            FROM transcripts_projection t
            JOIN transcripts_fts f ON t.id = f.rowid
            WHERE transcripts_fts MATCH ?
            ORDER BY bm25(transcripts_fts)
            LIMIT ?
            """,
            [query, limit],
        )
        return [
            TranscriptProjection(
                id=row[0],
                meeting_id=row[1],
                speaker=row[2],
                text=row[3],
                start_time=row[4],
                created_at=row[5],
            )
            for row in result.rows
        ]
