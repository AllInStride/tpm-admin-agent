"""Repository for persisting learned name mappings.

Stores user-corrected name -> email mappings per project.
Uses SQLite (via TursoClient) for persistence.
"""

from src.db.turso import TursoClient


class MappingRepository:
    """Repository for persisting learned name mappings.

    Stores user-corrected name -> email mappings per project.
    Uses SQLite (via TursoClient) for persistence.
    """

    def __init__(self, db_client: TursoClient):
        """Initialize repository with database client.

        Args:
            db_client: TursoClient instance for database operations
        """
        self._db = db_client

    async def initialize(self) -> None:
        """Create mappings table if not exists."""
        await self._db.execute_batch(
            [
                """
            CREATE TABLE IF NOT EXISTS learned_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                transcript_name TEXT NOT NULL,
                resolved_email TEXT NOT NULL,
                resolved_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                UNIQUE(project_id, transcript_name)
            )
            """,
                """
            CREATE INDEX IF NOT EXISTS idx_mapping_lookup
            ON learned_mappings(project_id, transcript_name)
            """,
            ]
        )

    async def get_mapping(
        self,
        project_id: str,
        transcript_name: str,
    ) -> tuple[str, str] | None:
        """Get learned mapping for a transcript name.

        Args:
            project_id: Project identifier
            transcript_name: Name as it appeared in transcript

        Returns:
            Tuple of (resolved_email, resolved_name) or None if not found
        """
        result = await self._db.execute(
            """
            SELECT resolved_email, resolved_name
            FROM learned_mappings
            WHERE project_id = ? AND transcript_name = ?
            """,
            [project_id, transcript_name],
        )
        if result.rows:
            row = result.rows[0]
            return (row[0], row[1])
        return None

    async def save_mapping(
        self,
        project_id: str,
        transcript_name: str,
        resolved_email: str,
        resolved_name: str,
        created_by: str | None = None,
    ) -> None:
        """Save a learned mapping (upsert).

        If a mapping already exists for this project_id + transcript_name,
        it will be replaced with the new values.

        Args:
            project_id: Project identifier
            transcript_name: Name as it appeared in transcript
            resolved_email: Correct email address
            resolved_name: Canonical name
            created_by: Optional user who created this mapping
        """
        await self._db.execute(
            """
            INSERT INTO learned_mappings
                (project_id, transcript_name, resolved_email, resolved_name, created_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(project_id, transcript_name)
            DO UPDATE SET
                resolved_email = excluded.resolved_email,
                resolved_name = excluded.resolved_name,
                created_by = excluded.created_by,
                created_at = CURRENT_TIMESTAMP
            """,
            [project_id, transcript_name, resolved_email, resolved_name, created_by],
        )

    async def delete_mapping(
        self,
        project_id: str,
        transcript_name: str,
    ) -> bool:
        """Delete a mapping.

        Args:
            project_id: Project identifier
            transcript_name: Name as it appeared in transcript

        Returns:
            True if a mapping was deleted, False if not found
        """
        result = await self._db.execute(
            """
            DELETE FROM learned_mappings
            WHERE project_id = ? AND transcript_name = ?
            """,
            [project_id, transcript_name],
        )
        return result.rows_affected > 0

    async def get_all_mappings(
        self,
        project_id: str,
    ) -> list[dict]:
        """Get all mappings for a project.

        Args:
            project_id: Project identifier

        Returns:
            List of mapping dictionaries with transcript_name, resolved_email,
            resolved_name, created_at, and created_by fields
        """
        result = await self._db.execute(
            """
            SELECT transcript_name, resolved_email, resolved_name,
                   created_at, created_by
            FROM learned_mappings
            WHERE project_id = ?
            ORDER BY transcript_name
            """,
            [project_id],
        )
        return [
            {
                "transcript_name": row[0],
                "resolved_email": row[1],
                "resolved_name": row[2],
                "created_at": row[3],
                "created_by": row[4],
            }
            for row in result.rows
        ]
