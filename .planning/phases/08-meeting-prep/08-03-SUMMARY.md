---
phase: 08-meeting-prep
plan: 03
subsystem: prep
tags: [apscheduler, slack-block-kit, fastapi, scheduling, async]

# Dependency graph
requires:
  - phase: 08-01
    provides: PrepConfig, CalendarEvent, ItemMatcher, prioritize_items, generate_talking_points
  - phase: 08-02
    provides: ContextGatherer, PrepContext, SlackAdapter extensions
provides:
  - format_prep_blocks for scannable Block Kit messages
  - format_prep_text for plain text fallback
  - PrepService for orchestrating prep generation and delivery
  - APScheduler integration with 5-minute scan interval
  - API endpoints for manual prep triggers and status
affects: [09-agent-ux]

# Tech tracking
tech-stack:
  added:
    - apscheduler>=3.11.0,<4.0
  patterns:
    - Singleton PrepService with class-level instance
    - AsyncExitStack for composable lifespan contexts
    - Scheduled background jobs with APScheduler
    - Block Kit formatting for Slack messages

key-files:
  created:
    - src/prep/formatter.py
    - src/prep/prep_service.py
    - src/prep/scheduler.py
    - src/api/prep.py
    - tests/prep/test_formatter.py
    - tests/prep/test_prep_service.py
    - tests/prep/test_scheduler.py
    - tests/api/test_prep_api.py
  modified:
    - pyproject.toml
    - src/api/router.py
    - src/main.py
    - src/prep/__init__.py
    - uv.lock

key-decisions:
  - "PrepService singleton pattern for scheduler access"
  - "5-minute scan interval with 10-15 min lookahead window"
  - "Duplicate prevention via _sent_preps set tracking event_id:date"
  - "Block Kit message with overdue section, open items, talking points, links"
  - "AsyncExitStack for composable scheduler lifespan"
  - "DISABLE_PREP_SCHEDULER env var for test isolation"

patterns-established:
  - "format_prep_blocks creates scannable Slack message with sections"
  - "PrepService.scan_and_prepare orchestrates calendar scan and prep delivery"
  - "prep_scheduler_lifespan for APScheduler FastAPI integration"

# Metrics
duration: 8min
completed: 2026-01-19
---

# Phase 08 Plan 03: PrepService, Scheduler, and API Summary

**PrepService with Block Kit formatter, APScheduler for 5-minute periodic scanning, and API endpoints for manual triggers and status**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-19T18:47:01Z
- **Completed:** 2026-01-19T18:55:18Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Created Block Kit formatter with scannable message layout (header, attendees, overdue items, open items, talking points, links)
- Built PrepService to orchestrate context gathering, prioritization, and Slack delivery
- Implemented duplicate prevention via _sent_preps tracking (event_id:date keys)
- Added APScheduler integration with 5-minute scan interval and 10-15 min lookahead window
- Created API endpoints: POST /prep/trigger, POST /prep/scan, GET /prep/config, GET /prep/status
- Integrated PrepService initialization and scheduler lifespan into main.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Block Kit formatter and PrepService** - `f956933` (feat)
2. **Task 2: APScheduler, API endpoints, and app integration** - `fb965a9` (feat)

## Files Created/Modified

- `src/prep/formatter.py` - format_prep_blocks and format_prep_text functions
- `src/prep/prep_service.py` - PrepService class with scan_and_prepare and prepare_for_meeting
- `src/prep/scheduler.py` - APScheduler setup with prep_scheduler_lifespan
- `src/api/prep.py` - REST endpoints for prep management
- `src/api/router.py` - Added prep_router inclusion
- `src/main.py` - PrepService initialization and scheduler lifespan integration
- `src/prep/__init__.py` - Module exports for new classes and functions
- `pyproject.toml` - Added apscheduler dependency
- `tests/prep/test_formatter.py` - 22 tests for Block Kit formatting
- `tests/prep/test_prep_service.py` - 18 tests for PrepService
- `tests/prep/test_scheduler.py` - 12 tests for scheduler
- `tests/api/test_prep_api.py` - 14 tests for API endpoints

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| PrepService singleton pattern | Scheduler needs access to service instance via get_instance() |
| 5-minute scan interval | Per RESEARCH.md - sufficient for 10-min lead time precision |
| Duplicate tracking via set | In-memory for MVP; simple and effective |
| Block Kit sections pattern | Per CONTEXT.md - scannable, fits one screen |
| AsyncExitStack for lifespan | Composable lifespans without nesting |
| DISABLE_PREP_SCHEDULER env | Test isolation without scheduler interference |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Meeting prep system complete and operational
- PrepService ready to scan calendar and send prep summaries
- API endpoints available for manual triggers and monitoring
- All 663 tests passing

**Ready for:** Phase 9 (Agent UX) or production deployment with appropriate credentials

---
*Phase: 08-meeting-prep*
*Completed: 2026-01-19*
