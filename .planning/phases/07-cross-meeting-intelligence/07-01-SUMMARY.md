---
phase: 07-cross-meeting-intelligence
plan: 01
subsystem: search
tags: [fts5, sqlite, projections, cqrs, event-sourcing]

# Dependency graph
requires:
  - phase: 02-event-sourcing
    provides: EventStore, Event types for RAID extraction
  - phase: 03-llm-extraction
    provides: ActionItemExtracted, DecisionExtracted, RiskExtracted, IssueExtracted events
provides:
  - ProjectionRepository with FTS5 indexes for full-text search
  - MeetingProjection, RaidItemProjection, TranscriptProjection schemas
  - ProjectionBuilder for materializing events into searchable projections
  - Event bus integration for automatic projection updates
affects: [07-02-open-items, 07-03-search-api, 08-dashboards]

# Tech tracking
tech-stack:
  added: []  # No new deps - FTS5 is built into SQLite/libSQL
  patterns: [cqrs-projections, external-content-fts5, event-driven-materialization]

key-files:
  created:
    - src/search/schemas.py
    - src/search/projections.py
    - src/repositories/projection_repo.py
    - tests/repositories/test_projection_repo.py
    - tests/test_projections.py
    - tests/test_projection_integration.py
  modified:
    - src/search/__init__.py
    - src/main.py

key-decisions:
  - "Individual execute() calls for FTS5 (not batch) per RESEARCH.md Pitfall 1"
  - "External content FTS5 tables to avoid data duplication"
  - "Triggers for automatic FTS5 sync on INSERT/DELETE/UPDATE"
  - "Porter unicode61 tokenizer for search relevance"
  - "Subscribe projection builder to each event type (no wildcard support in EventBus)"
  - "Convert datetime to ISO string in projection builder for Pydantic validation"

patterns-established:
  - "ProjectionRepository pattern: initialize() creates tables/indexes, individual methods for CRUD"
  - "ProjectionBuilder pattern: handle_event() routes to type-specific handlers, rebuild_all() for recovery"
  - "Event bus subscription in main.py lifespan for projection updates"

# Metrics
duration: 10min
completed: 2026-01-19
---

# Phase 7 Plan 01: Read Projections Summary

**FTS5-backed read projections that materialize from events, with automatic event bus integration for real-time search**

## Performance

- **Duration:** 10 min
- **Started:** 2026-01-19T16:48:14Z
- **Completed:** 2026-01-19T16:57:46Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- ProjectionRepository with meetings, RAID items, and transcripts projection tables
- FTS5 virtual tables with triggers for automatic sync
- ProjectionBuilder materializes all RAID extraction events
- Event bus integration for automatic projection updates on publish
- Full-text search on RAID items and transcripts with BM25 ranking
- rebuild_all() for reconstructing projections from event store

## Task Commits

Each task was committed atomically:

1. **Task 1: Projection schemas and repository** - `fbf4000` (feat)
2. **Task 2: Projection builder from events** - `2f849c7` (feat)
3. **Task 3: Wire projections into event bus** - `2d7aef4` (feat)

## Files Created/Modified

- `src/search/schemas.py` - MeetingProjection, RaidItemProjection, TranscriptProjection Pydantic models
- `src/search/projections.py` - ProjectionBuilder class for event materialization
- `src/repositories/projection_repo.py` - Database operations with FTS5 indexes and triggers
- `src/search/__init__.py` - Module exports for schemas and ProjectionBuilder
- `src/main.py` - Lifespan wiring for projection repo and event bus subscriptions
- `tests/repositories/test_projection_repo.py` - 16 repository tests
- `tests/test_projections.py` - 9 projection builder tests
- `tests/test_projection_integration.py` - 6 end-to-end integration tests

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Individual execute() for FTS5 | libsql_client batch operations can fail with FTS5 per RESEARCH.md |
| External content FTS5 tables | Avoid data duplication, reference existing projection tables |
| Porter unicode61 tokenizer | Good balance of stemming and unicode support |
| Triggers for FTS sync | Automatic sync without application code |
| datetime to string conversion | Pydantic validation requires string for date fields |
| Per-type event subscriptions | EventBus doesn't support wildcard; subscribe to each type explicitly |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Convert datetime to string in projection builder**
- **Found during:** Task 3 integration testing
- **Issue:** MeetingCreated event's meeting_date was datetime object, Pydantic expected string
- **Fix:** Added _to_string() helper to convert datetime to ISO string
- **Files modified:** src/search/projections.py
- **Verification:** Integration tests pass
- **Committed in:** 2d7aef4 (part of Task 3)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was essential for correct operation. No scope creep.

## Issues Encountered

None - all three tasks executed smoothly after the datetime bug fix.

## User Setup Required

None - no external service configuration required. FTS5 is built into SQLite/libSQL.

## Next Phase Readiness

- Projection infrastructure ready for open items dashboard queries
- FTS5 search available for search API endpoints
- Event bus automatically updates projections on RAID extraction
- 31 new tests passing, 467 total tests passing

---
*Phase: 07-cross-meeting-intelligence*
*Completed: 2026-01-19*
