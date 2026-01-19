---
phase: 07-cross-meeting-intelligence
plan: 02
subsystem: database
tags: [sqlite, turso, dashboard, open-items, raid-items, filtering, aggregation]

# Dependency graph
requires:
  - phase: 07-01
    provides: raid_items_projection table and MeetingProjection schema
provides:
  - is_item_open() centralized function for open item definition
  - CLOSED_STATUSES constant for SQL queries
  - OpenItemsRepository with dashboard queries
  - get_summary() aggregation query
  - get_items() with filtering and grouping
  - close_item() status update
  - get_item_history() timeline queries
  - OpenItemFilter, OpenItemSummary, GroupedOpenItems schemas
  - ItemHistoryEntry, ItemHistory schemas for timeline
  - classify_change() event classification helper
affects: [07-03-search-api, dashboard-endpoints, item-tracking]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Single source of truth for open item definition via CLOSED_STATUSES
    - SQL aggregation to avoid N+1 queries
    - Filter builder pattern for dynamic WHERE clauses
    - Grouping by ORDER BY for dashboard display

key-files:
  created:
    - src/search/open_items.py
    - src/repositories/open_items_repo.py
    - tests/test_open_items.py
    - tests/repositories/test_open_items_repo.py
  modified:
    - src/search/__init__.py
    - src/repositories/__init__.py
    - src/search/projections.py (bug fix)

key-decisions:
  - "CLOSED_STATUSES frozenset: completed, cancelled, closed, resolved"
  - "None status considered open (default state)"
  - "Case-insensitive status comparison"
  - "Single SQL query for summary counts (avoid N+1)"
  - "Filter builder pattern for dynamic WHERE clauses"
  - "Group by ORDER BY rather than SQL GROUP BY for item lists"

patterns-established:
  - "Centralized open item definition via is_item_open()"
  - "CLOSED_STATUSES constant imported wherever needed"
  - "classify_change() for event type categorization"

# Metrics
duration: 9min
completed: 2026-01-19
---

# Phase 7 Plan 2: Open Item Tracking Summary

**Centralized is_item_open() function, OpenItemsRepository with aggregation queries, and item history timeline support**

## Performance

- **Duration:** 9 min
- **Started:** 2026-01-19T16:48:28Z
- **Completed:** 2026-01-19T16:57:02Z
- **Tasks:** 3 (Task 3 merged into Tasks 1-2)
- **Files modified:** 6

## Accomplishments

- Single source of truth for "open" item definition with CLOSED_STATUSES constant
- Dashboard summary query runs in single SQL statement (no N+1)
- Filtering by item_type, owner, meeting_id, overdue_only, due_within_days
- Grouping by due_date, owner, item_type for dashboard views
- Item status update via close_item()
- Item history returns chronological event entries with meeting context
- 51 new tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Open item definition and schemas** - `7906e13` (feat)
2. **Task 2: Open items repository** - `68045a7` (feat)
3. **Task 3: Item history queries** - merged into Tasks 1-2 (schemas in Task 1, repo method in Task 2)

## Files Created/Modified

- `src/search/open_items.py` - is_item_open(), CLOSED_STATUSES, classify_change(), filter/summary schemas
- `src/repositories/open_items_repo.py` - OpenItemsRepository with dashboard queries
- `tests/test_open_items.py` - 30 tests for open item logic and schemas
- `tests/repositories/test_open_items_repo.py` - 21 tests for repository queries
- `src/search/__init__.py` - Exports for new schemas and functions
- `src/repositories/__init__.py` - Export for OpenItemsRepository
- `src/search/projections.py` - Bug fix: convert datetime to string for meeting_date

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| CLOSED_STATUSES = {completed, cancelled, closed, resolved} | Standard status set for TPM workflows |
| None status is open | Items without status should appear in open lists |
| Case-insensitive status check | Avoid mismatches from inconsistent casing |
| Single query for get_summary() | COUNT with CASE expressions avoids multiple queries |
| Build WHERE clause dynamically | Filter parameters are optional; dynamic SQL cleaner than many branches |
| ORDER BY for grouping | Dashboard needs sorted items, not aggregated counts |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed meeting_date datetime-to-string conversion in projections.py**

- **Found during:** Task 2 commit (pre-commit hook ran integration test)
- **Issue:** MeetingProjection.date expects string but event data contains datetime object
- **Fix:** Used _to_string() helper to convert datetime to ISO string
- **Files modified:** src/search/projections.py
- **Verification:** test_projection_integration.py passes
- **Committed in:** 68045a7 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was in 07-01 code discovered during 07-02 testing. Essential for correctness.

## Issues Encountered

None - plan executed smoothly after bug fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Open item queries ready for API endpoint exposure
- is_item_open() available for use across codebase
- Dashboard data shape (GroupedOpenItems) ready for frontend
- Item history ready for timeline UI

---
*Phase: 07-cross-meeting-intelligence*
*Completed: 2026-01-19*
