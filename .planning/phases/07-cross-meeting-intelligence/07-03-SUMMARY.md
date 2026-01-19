---
phase: 07
plan: 03
subsystem: search
tags: [fts5, rapidfuzz, api, search, dashboard]

dependency-graph:
  requires: ["07-01", "07-02"]
  provides: ["fts-service", "duplicate-detection", "search-api"]
  affects: ["08-orchestration"]

tech-stack:
  added: []
  patterns: ["FTS5-query-builder", "rapidfuzz-token-set-ratio", "fastapi-dependency-injection"]

key-files:
  created:
    - src/search/fts_service.py
    - src/search/duplicate_detector.py
    - src/api/search.py
    - tests/search/test_fts_service.py
    - tests/search/test_duplicate_detector.py
    - tests/search/test_search_api.py
  modified:
    - src/search/__init__.py
    - src/api/router.py
    - src/main.py

decisions:
  - id: "07-03-01"
    decision: "Empty keywords returns empty results"
    rationale: "FTS5 MATCH requires keywords; filters alone cannot drive search"
  - id: "07-03-02"
    decision: "BM25 scores converted to absolute values"
    rationale: "bm25() returns negative values; abs() provides intuitive relevance"
  - id: "07-03-03"
    decision: "Duplicate rejections stored in separate table"
    rationale: "Avoids re-prompting users; persists across sessions"

metrics:
  duration: 8 min
  completed: 2026-01-19
---

# Phase 7 Plan 3: Search Service and API Summary

FTS5 search service with query parsing, RapidFuzz duplicate detection, and complete API endpoints for cross-meeting intelligence.

## What Was Built

### Task 1: FTS Service and Query Parsing

Created FTS5 query service for searching across RAID items and transcripts.

**src/search/fts_service.py:**
- `ParsedQuery`: Dataclass for keywords + structured filters
- `SearchResult`: Result with snippet, relevance, source type
- `SearchResponse`: Combined results from both sources
- `parse_search_query()`: Extracts `type:action owner:john` syntax
- `FTSService`: Executes FTS5 MATCH queries with BM25 ranking
- `_escape_fts_query()`: Handles special characters in queries

**Key patterns:**
- Filter syntax: `type:action owner:john deadline` extracts filters, leaves keywords
- BM25 ranking: `ORDER BY bm25(fts_table)` for relevance sorting
- Snippets: `snippet(fts, column, '<mark>', '</mark>', '...', 32)`

### Task 2: Duplicate Detector

Created RapidFuzz-based duplicate detection for RAID items.

**src/search/duplicate_detector.py:**
- `DuplicateMatch`: Match with similarity score and meeting context
- `DuplicateCheckResult`: Check result with has_duplicates flag
- `DuplicateDetector`: Main service class
  - `find_duplicates()`: Uses `token_set_ratio` for flexible matching
  - `record_rejection()`: Stores rejection in `duplicate_rejections` table
  - `get_rejections()`: Returns set of rejected duplicate IDs

**Key patterns:**
- `fuzz.token_set_ratio`: Handles word order differences ("API docs" = "docs API")
- Threshold 0.85: Default similarity threshold (configurable)
- Rejection persistence: `CREATE TABLE duplicate_rejections` with unique constraint

### Task 3: Search API Endpoints

Created complete API for search, dashboard, and item management.

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | /search | FTS5 search with filter syntax |
| GET | /search/open-items | Dashboard with filters and grouping |
| GET | /search/open-items/summary | Counts (overdue, today, week) |
| POST | /search/items/{id}/close | Update item status |
| GET | /search/items/{id}/history | Timeline across meetings |
| POST | /search/items/check-duplicates | Find similar items |
| POST | /search/items/{id}/reject-duplicate | Record rejection |

**Service initialization (main.py):**
```python
app.state.fts_service = FTSService(db)
app.state.duplicate_detector = DuplicateDetector(db)
app.state.open_items_repo = OpenItemsRepository(db)
```

## Decisions Made

### Empty Keywords Returns Empty Results

FTS5 MATCH requires keywords to execute. When a query contains only filters like `type:action` with no keywords, we return empty results rather than returning all items of that type.

**Rationale:** Consistent behavior; use `/search/open-items?item_type=action` for filtered listing.

### BM25 Scores Converted to Absolute Values

`bm25()` returns negative values (more negative = more relevant). We convert to positive in the response with `abs(score)`.

**Rationale:** Intuitive for API consumers; higher score = more relevant.

### Duplicate Rejections Stored Separately

Created `duplicate_rejections` table rather than embedding in RAID items.

**Schema:**
```sql
CREATE TABLE duplicate_rejections (
    id INTEGER PRIMARY KEY,
    item_id TEXT NOT NULL,
    rejected_duplicate_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(item_id, rejected_duplicate_id)
)
```

**Rationale:** Separation of concerns; doesn't bloat projection table; query-optimized.

## Deviations from Plan

None - plan executed exactly as written.

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_fts_service.py | 16 | Query parsing, search, filters, edge cases |
| test_duplicate_detector.py | 13 | Similarity, thresholds, rejections |
| test_search_api.py | 17 | All endpoints, error cases |
| **Total** | **46** | All plan requirements covered |

**Full suite:** 513 tests passing (46 new)

## Files Changed

```
src/search/fts_service.py          [NEW] 200 lines - FTS5 search service
src/search/duplicate_detector.py   [NEW] 230 lines - RapidFuzz detector
src/api/search.py                  [NEW] 200 lines - API endpoints
src/search/__init__.py             [MOD] Added exports
src/api/router.py                  [MOD] Include search_router
src/main.py                        [MOD] Service initialization
tests/search/test_fts_service.py   [NEW] 300 lines
tests/search/test_duplicate_detector.py [NEW] 250 lines
tests/search/test_search_api.py    [NEW] 280 lines
```

## API Examples

**Search with filters:**
```bash
curl "http://localhost:8000/search?q=type:action%20owner:alice%20deadline"
```

**Dashboard grouped by owner:**
```bash
curl "http://localhost:8000/search/open-items?group_by=owner&overdue_only=true"
```

**Check for duplicates:**
```bash
curl -X POST "http://localhost:8000/search/items/check-duplicates" \
  -H "Content-Type: application/json" \
  -d '{"description": "Review API documentation", "item_type": "action"}'
```

## Next Phase Readiness

Phase 7 complete. Ready for Phase 8 (Orchestration Layer).

**Available capabilities:**
- Full-text search across transcripts and RAID items
- Open items dashboard with grouping and filtering
- Item history timeline with meeting context
- Duplicate detection with rejection persistence
- All endpoints documented in OpenAPI schema

**Integration points for Phase 8:**
- `FTSService.search()` for query execution
- `DuplicateDetector.find_duplicates()` for new item checks
- `OpenItemsRepository` for dashboard queries
