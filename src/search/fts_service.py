"""Full-text search service for cross-meeting intelligence.

Provides FTS5 query execution with structured filter parsing,
highlighted snippets, and BM25 relevance ranking.
"""

import logging
import re

from pydantic import BaseModel, Field

from src.db.turso import TursoClient

logger = logging.getLogger(__name__)


class ParsedQuery(BaseModel):
    """Parsed search query with keywords and structured filters."""

    keywords: str = Field(default="", description="Free text for FTS MATCH")
    filters: dict[str, str] = Field(
        default_factory=dict,
        description="Structured filters like type:action",
    )


class SearchResult(BaseModel):
    """Single search result with snippet and relevance."""

    id: str = Field(description="Item ID (UUID or integer)")
    source: str = Field(description="Source type: 'transcript' or 'raid_item'")
    meeting_id: str = Field(description="Meeting UUID")
    snippet: str = Field(description="Highlighted context snippet")
    relevance: float = Field(description="BM25 relevance score")
    item_type: str | None = Field(
        default=None, description="For RAID items: action, decision, risk, issue"
    )
    speaker: str | None = Field(
        default=None, description="For transcripts: speaker name"
    )


class SearchResponse(BaseModel):
    """Combined search response with results from both sources."""

    query: str = Field(description="Original search query")
    total_results: int = Field(description="Total number of results")
    raid_items: list[SearchResult] = Field(
        default_factory=list,
        description="Results from RAID items",
    )
    transcripts: list[SearchResult] = Field(
        default_factory=list,
        description="Results from transcripts",
    )


def parse_search_query(query: str) -> ParsedQuery:
    """Parse search query into structured filters and keywords.

    Extracts filter syntax like 'type:action owner:john' and
    separates from free-text keywords.

    Args:
        query: Raw search query string

    Returns:
        ParsedQuery with keywords and filters separated

    Example:
        >>> parse_search_query("type:action owner:john api bug")
        ParsedQuery(keywords="api bug", filters={"type": "action", "owner": "john"})
    """
    filter_pattern = r"(\w+):(\S+)"
    filters = dict(re.findall(filter_pattern, query))
    keywords = re.sub(filter_pattern, "", query).strip()
    # Normalize multiple spaces
    keywords = re.sub(r"\s+", " ", keywords)
    return ParsedQuery(keywords=keywords, filters=filters)


class FTSService:
    """Full-text search service using FTS5.

    Executes FTS5 queries against raid_items_fts and transcripts_fts
    tables with BM25 ranking and snippet highlighting.
    """

    def __init__(self, db_client: TursoClient):
        """Initialize FTS service with database client.

        Args:
            db_client: TursoClient instance for database operations
        """
        self._db = db_client

    async def search(self, query: str, limit: int = 50) -> SearchResponse:
        """Search both RAID items and transcripts.

        Parses structured filters from query, executes FTS5 searches,
        and returns combined results.

        Args:
            query: Search query (may include filters like type:action)
            limit: Maximum results per source

        Returns:
            SearchResponse with results from both sources
        """
        parsed = parse_search_query(query)
        logger.debug(
            f"Parsed query: keywords='{parsed.keywords}', filters={parsed.filters}"
        )

        raid_results: list[SearchResult] = []
        transcript_results: list[SearchResult] = []

        # Only search if we have keywords
        if parsed.keywords:
            raid_results = await self._search_raid_items(parsed, limit)
            transcript_results = await self._search_transcripts(parsed, limit)

        return SearchResponse(
            query=query,
            total_results=len(raid_results) + len(transcript_results),
            raid_items=raid_results,
            transcripts=transcript_results,
        )

    async def _search_raid_items(
        self, parsed: ParsedQuery, limit: int
    ) -> list[SearchResult]:
        """Search RAID items using FTS5.

        Args:
            parsed: Parsed query with keywords and filters
            limit: Maximum results

        Returns:
            List of SearchResult from raid_items_fts
        """
        # Build base query
        # Note: bm25() returns negative values (more negative = more relevant)
        base_query = """
            SELECT
                r.id,
                r.meeting_id,
                r.item_type,
                snippet(raid_items_fts, 0, '<mark>', '</mark>', '...', 32) as snippet,
                bm25(raid_items_fts) as relevance
            FROM raid_items_fts
            JOIN raid_items_projection r ON raid_items_fts.rowid = r.rowid
            WHERE raid_items_fts MATCH ?
        """

        params: list = [self._escape_fts_query(parsed.keywords)]
        filters = []

        # Apply structured filters
        if "type" in parsed.filters:
            filters.append("r.item_type = ?")
            params.append(parsed.filters["type"])

        if "owner" in parsed.filters:
            filters.append("r.owner LIKE ?")
            params.append(f"%{parsed.filters['owner']}%")

        if "status" in parsed.filters:
            filters.append("r.status = ?")
            params.append(parsed.filters["status"])

        # Build full query
        query = base_query
        if filters:
            query += " AND " + " AND ".join(filters)
        query += " ORDER BY bm25(raid_items_fts) LIMIT ?"
        params.append(limit)

        try:
            result = await self._db.execute(query, params)
            return [
                SearchResult(
                    id=str(row[0]),
                    source="raid_item",
                    meeting_id=str(row[1]),
                    item_type=row[2],
                    snippet=row[3] or "",
                    relevance=abs(row[4]) if row[4] else 0.0,
                    speaker=None,
                )
                for row in result.rows
            ]
        except Exception as e:
            logger.error(f"RAID items FTS search failed: {e}")
            return []

    async def _search_transcripts(
        self, parsed: ParsedQuery, limit: int
    ) -> list[SearchResult]:
        """Search transcripts using FTS5.

        Args:
            parsed: Parsed query with keywords and filters
            limit: Maximum results

        Returns:
            List of SearchResult from transcripts_fts
        """
        # Build base query
        # Column 1 is 'text' in transcripts_fts (speaker, text)
        base_query = """
            SELECT
                t.id,
                t.meeting_id,
                t.speaker,
                snippet(transcripts_fts, 1, '<mark>', '</mark>', '...', 32) as snippet,
                bm25(transcripts_fts) as relevance
            FROM transcripts_fts
            JOIN transcripts_projection t ON transcripts_fts.rowid = t.id
            WHERE transcripts_fts MATCH ?
        """

        params: list = [self._escape_fts_query(parsed.keywords)]
        filters = []

        # Apply speaker filter
        if "speaker" in parsed.filters:
            filters.append("t.speaker LIKE ?")
            params.append(f"%{parsed.filters['speaker']}%")

        # Build full query
        query = base_query
        if filters:
            query += " AND " + " AND ".join(filters)
        query += " ORDER BY bm25(transcripts_fts) LIMIT ?"
        params.append(limit)

        try:
            result = await self._db.execute(query, params)
            return [
                SearchResult(
                    id=str(row[0]),
                    source="transcript",
                    meeting_id=str(row[1]),
                    speaker=row[2],
                    snippet=row[3] or "",
                    relevance=abs(row[4]) if row[4] else 0.0,
                    item_type=None,
                )
                for row in result.rows
            ]
        except Exception as e:
            logger.error(f"Transcripts FTS search failed: {e}")
            return []

    def _escape_fts_query(self, query: str) -> str:
        """Escape special characters in FTS5 query.

        FTS5 has special syntax for operators. For simple keyword
        search, we wrap terms in double quotes if they contain
        special characters.

        Args:
            query: Raw query string

        Returns:
            Escaped query safe for FTS5 MATCH
        """
        # FTS5 special characters that need escaping
        special_chars = set('*^"():')

        # If query contains special chars, quote each word
        words = query.split()
        escaped_words = []
        for word in words:
            if any(c in word for c in special_chars):
                # Remove existing quotes and re-quote
                word = word.replace('"', "")
                escaped_words.append(f'"{word}"')
            else:
                escaped_words.append(word)

        return " ".join(escaped_words)
