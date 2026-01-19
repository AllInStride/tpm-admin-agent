# Phase 7: Cross-Meeting Intelligence - Research

**Researched:** 2026-01-19
**Domain:** Full-text search, read projections, item tracking
**Confidence:** HIGH

## Summary

Phase 7 requires building search and tracking capabilities across meeting history. The primary challenge is that the current system uses an **event store** (append-only) which is optimized for writes but not for queries like "find all open items" or "search all transcripts for keyword X". This requires building **read projections** - materialized views derived from events that are optimized for query patterns.

The standard approach is:
1. **SQLite FTS5** for full-text search on transcripts and RAID item descriptions
2. **Read projection tables** to materialize searchable state from events
3. **RapidFuzz** (already in deps) for duplicate detection across meetings
4. **Dashboard API endpoints** returning aggregated open items with grouping/filtering

**Primary recommendation:** Build FTS5-backed read projections that materialize from the event store, with triggers to keep them synchronized. Use external content tables to avoid data duplication.

## Standard Stack

The established libraries/tools for this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLite FTS5 | Built-in | Full-text search | Native to libSQL/Turso, no additional deps |
| libsql-client | 0.3.1+ | Database access | Already in use, supports FTS5 |
| rapidfuzz | 3.14.0+ | Duplicate detection | Already in deps, 10x faster than fuzzywuzzy |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dateparser | 1.2.2+ | Date parsing for filters | Already in deps, for "due this week" filters |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FTS5 | Elasticsearch/Meilisearch | More powerful but adds operational complexity |
| FTS5 | PostgreSQL FTS | Would require database migration |
| rapidfuzz | sentence-transformers | Semantic similarity but heavier, requires GPU |

**Installation:**
No new dependencies required - all needed libraries already in pyproject.toml.

## Architecture Patterns

### Recommended Project Structure

```
src/
├── search/
│   ├── __init__.py
│   ├── schemas.py           # SearchQuery, SearchResult, OpenItemFilter
│   ├── projections.py       # ReadProjection classes
│   ├── fts_service.py       # FTS5 query builder and executor
│   └── duplicate_detector.py # RapidFuzz-based duplicate detection
├── repositories/
│   ├── meeting_repo.py      # Meeting read projections
│   ├── raid_item_repo.py    # RAID item read projections
│   └── open_items_repo.py   # Open items aggregation queries
└── api/
    └── search.py            # Search endpoints
```

### Pattern 1: Read Projections from Event Store

**What:** Materialize queryable state from append-only events into denormalized read tables.

**When to use:** When events are the source of truth but queries need different data shapes.

**Example:**
```python
# Source: Event-Driven Architecture patterns
class RaidItemProjection:
    """Projects RAID item events into searchable read model."""

    async def handle(self, event: Event) -> None:
        """Route event to appropriate handler."""
        if isinstance(event, ActionItemExtracted):
            await self._handle_action_item(event)
        elif isinstance(event, IssueExtracted):
            await self._handle_issue(event)
        # ... other RAID types

    async def _handle_action_item(self, event: ActionItemExtracted) -> None:
        """Insert/update action item in read projection."""
        await self.db.execute("""
            INSERT INTO raid_items_projection
            (id, meeting_id, item_type, description, owner, due_date, status, created_at)
            VALUES (?, ?, 'action', ?, ?, ?, 'pending', ?)
            ON CONFLICT(id) DO UPDATE SET
                description = excluded.description,
                owner = excluded.owner,
                due_date = excluded.due_date
        """, [str(event.action_item_id), str(event.meeting_id),
              event.description, event.assignee_name,
              event.due_date, event.timestamp])
```

### Pattern 2: External Content FTS5 Tables

**What:** FTS5 indexes that reference content stored elsewhere, avoiding duplication.

**When to use:** When you have existing tables and want to add full-text search.

**Example:**
```sql
-- Source: SQLite FTS5 official documentation
-- Create content table first
CREATE TABLE transcripts (
    id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL,
    speaker TEXT,
    text TEXT NOT NULL,
    start_time REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create FTS5 external content table
CREATE VIRTUAL TABLE transcripts_fts USING fts5(
    speaker,
    text,
    content='transcripts',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER transcripts_ai AFTER INSERT ON transcripts BEGIN
    INSERT INTO transcripts_fts(rowid, speaker, text)
    VALUES (new.rowid, new.speaker, new.text);
END;

CREATE TRIGGER transcripts_ad AFTER DELETE ON transcripts BEGIN
    INSERT INTO transcripts_fts(transcripts_fts, rowid, speaker, text)
    VALUES('delete', old.rowid, old.speaker, old.text);
END;
```

### Pattern 3: Structured Filter Syntax Parsing

**What:** Parse user queries like "type:action owner:john overdue" into SQL filters.

**When to use:** When providing power-user search syntax.

**Example:**
```python
# Simple parser for structured filters
import re
from dataclasses import dataclass

@dataclass
class ParsedQuery:
    keywords: str           # Free text for FTS
    filters: dict[str, str] # Structured filters

def parse_search_query(query: str) -> ParsedQuery:
    """Parse 'type:action owner:john api bug' into structured query."""
    filter_pattern = r'(\w+):(\S+)'
    filters = dict(re.findall(filter_pattern, query))
    keywords = re.sub(filter_pattern, '', query).strip()
    return ParsedQuery(keywords=keywords, filters=filters)
```

### Anti-Patterns to Avoid

- **Querying event store directly for dashboards:** Event stores are optimized for append/replay, not ad-hoc queries. Always use read projections.
- **Synchronous projection updates:** Process events asynchronously to avoid blocking writes.
- **Storing FTS content twice:** Use external content tables to reference existing data.
- **Hand-rolling FTS query escaping:** FTS5 has specific quoting rules; use parameterized queries.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full-text search | LIKE queries with wildcards | FTS5 MATCH | 10-100x faster, proper tokenization, ranking |
| String similarity | Levenshtein from scratch | RapidFuzz | C++ implementation, handles edge cases |
| Result highlighting | String manipulation | FTS5 highlight() | Handles overlapping matches correctly |
| Relevance ranking | Simple match count | FTS5 bm25() | Proper TF-IDF ranking algorithm |
| Query parsing | Regex soup | Simple state machine | Handles quotes and escapes properly |

**Key insight:** SQLite FTS5 provides a complete search engine - highlighting, snippets, ranking, boolean queries, prefix matching - all built-in. Using LIKE queries would be slower and miss features.

## Common Pitfalls

### Pitfall 1: FTS5 Virtual Table Insert Failures with libsql_client

**What goes wrong:** GitHub issue #1811 reports that batch operations with FTS5 tables can fail with "thread panicked at src/statement.rs" errors.

**Why it happens:** libsql_client's batch API may have issues with FTS5 virtual table operations.

**How to avoid:** Use individual `execute()` calls for FTS5 inserts instead of `execute_batch()`. Wrap in try/except and log failures.

**Warning signs:** Thread panic errors, silent insert failures with no rowcount.

### Pitfall 2: External Content Table Sync Issues

**What goes wrong:** FTS index gets out of sync with source table.

**Why it happens:** Triggers not created, or app bypasses triggers with direct SQL.

**How to avoid:**
1. Always create INSERT/UPDATE/DELETE triggers
2. If sync issues suspected, run: `INSERT INTO fts_table(fts_table) VALUES('rebuild');`
3. Add integrity check on startup: `INSERT INTO fts_table(fts_table) VALUES('integrity-check');`

**Warning signs:** Search returning stale results, queries returning deleted items.

### Pitfall 3: Open Item Definition Drift

**What goes wrong:** "Open" items definition varies across the codebase.

**Why it happens:** Multiple places implement "is open" logic differently.

**How to avoid:** Centralize the definition in a single function:
```python
def is_item_open(item: RaidItem) -> bool:
    """Single source of truth for 'open' definition."""
    if item.status in ('completed', 'cancelled', 'closed', 'resolved'):
        return False
    # Open = not closed AND (has due date OR no due date)
    return True
```

**Warning signs:** Dashboard counts don't match API counts, items appearing/disappearing unexpectedly.

### Pitfall 4: Duplicate Detection False Positives

**What goes wrong:** System flags non-duplicates as duplicates, or misses actual duplicates.

**Why it happens:** Threshold set too low (false positives) or too high (misses).

**How to avoid:**
1. Use token_set_ratio for flexibility with word order
2. Start with 85% threshold, tune based on user feedback
3. Always surface to user for decision (per CONTEXT.md)
4. Store rejection decisions to avoid re-prompting

**Warning signs:** Users repeatedly dismissing duplicate prompts, or discovering unlinked duplicates manually.

### Pitfall 5: N+1 Queries in Dashboard

**What goes wrong:** Dashboard loads slowly as item count grows.

**Why it happens:** Fetching items then making separate queries for each item's history.

**How to avoid:** Use aggregation queries:
```sql
SELECT
    item_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE due_date < DATE('now')) as overdue,
    COUNT(*) FILTER (WHERE due_date BETWEEN DATE('now') AND DATE('now', '+7 days')) as due_this_week
FROM raid_items_projection
WHERE status NOT IN ('completed', 'cancelled', 'closed', 'resolved')
GROUP BY item_type
```

**Warning signs:** Dashboard API latency grows linearly with data volume.

## Code Examples

Verified patterns from official sources:

### FTS5 Search with Highlighting

```sql
-- Source: SQLite FTS5 official documentation
-- Search with relevance ranking and highlighting
SELECT
    meeting_id,
    highlight(transcripts_fts, 1, '<mark>', '</mark>') as highlighted_text,
    bm25(transcripts_fts) as relevance
FROM transcripts_fts
WHERE transcripts_fts MATCH 'api AND (bug OR issue)'
ORDER BY bm25(transcripts_fts)
LIMIT 50;
```

### FTS5 Snippet Extraction

```sql
-- Source: SQLite FTS5 official documentation
-- Extract contextual snippets
SELECT
    meeting_id,
    snippet(raid_items_fts, 0, '<b>', '</b>', '...', 32) as context
FROM raid_items_fts
WHERE raid_items_fts MATCH 'deadline'
ORDER BY rank;
```

### RapidFuzz Duplicate Detection

```python
# Source: RapidFuzz GitHub documentation
from rapidfuzz import fuzz, process

def find_potential_duplicates(
    new_description: str,
    existing_items: list[dict],
    threshold: float = 0.85
) -> list[dict]:
    """Find items that might be duplicates of the new item."""
    choices = [item['description'] for item in existing_items]

    # Use token_set_ratio for flexibility with word order
    results = process.extract(
        new_description,
        choices,
        scorer=fuzz.token_set_ratio,
        limit=5,
        score_cutoff=threshold * 100  # rapidfuzz uses 0-100
    )

    return [
        {
            'item': existing_items[idx],
            'similarity': score / 100,
            'matched_text': match
        }
        for match, score, idx in results
    ]
```

### Open Items Query with Grouping

```python
# Pattern for dashboard API
async def get_open_items_summary(
    db: TursoClient,
    group_by: str = 'due_date'
) -> dict:
    """Get summary of open items for dashboard."""

    # Get counts by category
    counts_query = """
        SELECT
            item_type,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE due_date < DATE('now')) as overdue,
            COUNT(*) FILTER (WHERE due_date = DATE('now')) as due_today,
            COUNT(*) FILTER (WHERE due_date > DATE('now')
                AND due_date <= DATE('now', '+7 days')) as due_this_week
        FROM raid_items_projection
        WHERE status NOT IN ('completed', 'cancelled', 'closed', 'resolved')
        GROUP BY item_type
    """

    counts = await db.execute(counts_query)

    # Get actual items based on grouping
    if group_by == 'due_date':
        items_query = """
            SELECT * FROM raid_items_projection
            WHERE status NOT IN ('completed', 'cancelled', 'closed', 'resolved')
            ORDER BY
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                due_date ASC
        """
    elif group_by == 'owner':
        items_query = """
            SELECT * FROM raid_items_projection
            WHERE status NOT IN ('completed', 'cancelled', 'closed', 'resolved')
            ORDER BY owner, due_date
        """
    # ... other groupings

    items = await db.execute(items_query)

    return {
        'summary': [dict(row) for row in counts.rows],
        'items': [dict(row) for row in items.rows]
    }
```

### Item History Timeline Query

```python
# Pattern for item history across meetings
async def get_item_history(
    db: TursoClient,
    item_id: str
) -> list[dict]:
    """Get history of an item across meetings."""

    # Query event store for all events related to this item
    query = """
        SELECT
            e.timestamp,
            e.event_type,
            e.event_data,
            m.title as meeting_title,
            m.date as meeting_date
        FROM events e
        LEFT JOIN meetings_projection m ON e.event_data LIKE '%' || m.id || '%'
        WHERE e.aggregate_id = ?
           OR e.event_data LIKE ?
        ORDER BY e.timestamp ASC
    """

    result = await db.execute(query, [item_id, f'%{item_id}%'])

    return [
        {
            'timestamp': row[0],
            'event_type': row[1],
            'change_type': _classify_change(row[1]),  # 'new', 'updated', 'mentioned'
            'meeting_title': row[3],
            'meeting_date': row[4]
        }
        for row in result.rows
    ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LIKE queries | FTS5 MATCH | SQLite 3.9+ (2015) | 100x faster, proper tokenization |
| FuzzyWuzzy | RapidFuzz | 2020 | 10x performance, MIT license |
| Single read model | CQRS projections | N/A (pattern evolution) | Better query performance |
| Polling for updates | Event-driven projections | N/A | Real-time consistency |

**Deprecated/outdated:**
- **FTS3/FTS4:** Use FTS5 instead - better performance, more features
- **FuzzyWuzzy:** Use RapidFuzz - same API, faster, MIT licensed
- **LIKE '%term%' for search:** Use FTS5 - proper indexing and ranking

## Open Questions

Things that couldn't be fully resolved:

1. **libsql_client FTS5 batch insert behavior**
   - What we know: GitHub issue #1811 reports problems with TypeScript client
   - What's unclear: Whether Python client has same issues
   - Recommendation: Test FTS5 inserts early in implementation, use individual execute() calls if batch fails

2. **FTS5 tokenizer configuration for meeting content**
   - What we know: Porter stemmer good for general text, trigram for fuzzy matching
   - What's unclear: Best tokenizer for meeting transcripts with names/acronyms
   - Recommendation: Start with `porter unicode61`, tune if name/acronym search is poor

3. **Projection rebuild strategy**
   - What we know: Can rebuild from events, but takes time
   - What's unclear: How to handle rebuilds without downtime
   - Recommendation: Add `rebuild` admin endpoint, run during off-hours initially

## Sources

### Primary (HIGH confidence)
- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html) - Query syntax, external content tables, auxiliary functions
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) - String matching API, performance characteristics

### Secondary (MEDIUM confidence)
- [Turso libSQL Documentation](https://docs.turso.tech/libsql) - FTS5 extension support confirmed
- [Breadcrumbs Collector - Event Sourcing Projections](https://breadcrumbscollector.tech/implementing-event-sourcing-in-python-part-4-efficient-read-model-with-projections/) - Projection patterns for Python
- [Event-Driven.io Projections Guide](https://event-driven.io/en/projections_and_read_models_in_event_driven_architecture/) - CQRS/ES projection architecture

### Tertiary (LOW confidence)
- [GitHub Issue #1811](https://github.com/tursodatabase/libsql/issues/1811) - FTS5 batch insert issues (TypeScript, may not apply to Python)
- WebSearch results for dashboard patterns - General guidance, not verified implementations

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - FTS5 is native SQLite/libSQL, RapidFuzz already in deps
- Architecture: HIGH - CQRS projections are well-documented pattern
- Pitfalls: MEDIUM - FTS5/libsql_client interaction needs testing

**Research date:** 2026-01-19
**Valid until:** 2026-02-19 (30 days - stable technologies)
