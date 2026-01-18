"""Turso/libSQL database client wrapper."""

import logging
from typing import Any

from libsql_client import Client, ResultSet, create_client

from src.config import settings

logger = logging.getLogger(__name__)


class TursoClient:
    """Wrapper for Turso/libSQL async client.

    Supports both cloud Turso (with auth token) and local SQLite files.
    """

    def __init__(
        self,
        url: str | None = None,
        auth_token: str | None = None,
    ):
        """Initialize client with connection parameters.

        Args:
            url: Database URL. Defaults to settings or local file.
            auth_token: Auth token for Turso cloud. Defaults to settings.
        """
        self.url = url or settings.turso_database_url or "file:local.db"
        self.auth_token = auth_token or settings.turso_auth_token
        self._client: Client | None = None

    async def connect(self) -> None:
        """Establish database connection."""
        if self._client is not None:
            return

        if self.auth_token and self.url.startswith("libsql://"):
            # Cloud Turso
            self._client = create_client(
                url=self.url,
                auth_token=self.auth_token,
            )
        else:
            # Local file database
            self._client = create_client(url=self.url)

        logger.info(f"Connected to database: {self.url}")

    async def execute(
        self,
        sql: str,
        params: list[Any] | None = None,
    ) -> ResultSet:
        """Execute a SQL statement.

        Args:
            sql: SQL query with ? placeholders
            params: Query parameters

        Returns:
            ResultSet with rows and metadata
        """
        if not self._client:
            msg = "Not connected. Call connect() first."
            raise RuntimeError(msg)
        return await self._client.execute(sql, params or [])

    async def execute_batch(self, statements: list[str]) -> None:
        """Execute multiple SQL statements in a batch.

        Args:
            statements: List of SQL statements
        """
        if not self._client:
            msg = "Not connected. Call connect() first."
            raise RuntimeError(msg)
        await self._client.batch(statements)

    async def close(self) -> None:
        """Close the database connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Database connection closed")

    async def is_healthy(self) -> bool:
        """Check if database connection is healthy."""
        try:
            if not self._client:
                return False
            result = await self._client.execute("SELECT 1")
            return len(result.rows) == 1
        except Exception:
            return False


# Global client instance (initialized in app lifespan)
db_client: TursoClient | None = None


async def get_db() -> TursoClient:
    """Get the database client instance.

    Used as FastAPI dependency.
    """
    if db_client is None:
        msg = "Database not initialized"
        raise RuntimeError(msg)
    return db_client
