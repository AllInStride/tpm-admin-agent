---
phase: "05"
plan: "03"
subsystem: output-routing
tags: [fastapi, tenacity, retry, orchestration]

dependency-graph:
  requires: ["05-01", "05-02"]
  provides: ["output-routing-pipeline", "output-api-endpoint"]
  affects: ["06-orchestration"]

tech-stack:
  added: []
  patterns: ["retry-with-backoff", "router-orchestration", "dependency-injection"]

key-files:
  created:
    - src/output/config.py
    - src/output/queue.py
    - src/output/router.py
    - src/api/output.py
    - tests/test_output_router.py
    - tests/test_output_api.py
  modified:
    - src/output/__init__.py
    - src/api/router.py

decisions:
  - id: "05-03-01"
    decision: "In-memory RetryQueue for MVP"
    rationale: "SQLite persistence is future work per CONTEXT.md; in-memory sufficient for initial release"
  - id: "05-03-02"
    decision: "Tenacity retry with 5 attempts, exponential backoff 4-60s"
    rationale: "Handles transient Google API failures without overwhelming rate limits"
  - id: "05-03-03"
    decision: "OutputRouter coordinates renderer and adapters"
    rationale: "Single orchestration point for output pipeline"
  - id: "05-03-04"
    decision: "Minutes filename: {date}-{title-slug}.md"
    rationale: "Sortable by date, human-readable, URL-safe"

metrics:
  duration: "4 min"
  completed: "2026-01-19"
---

# Phase 5 Plan 3: Output Routing and API Summary

Output router with tenacity retry, project config, and REST API endpoint for end-to-end meeting output generation.

## What Was Built

### Task 1: Project Output Config and Retry Queue
- **ProjectOutputConfig** - Per-project settings for destinations, templates, enabled targets
- **write_with_retry** - Tenacity decorator with 5 attempts, exponential backoff (4-60s)
- **RetryQueue** - In-memory storage for failed items (SQLite persistence deferred)
- Retriable exceptions: ConnectionError, TimeoutError, gspread.APIError, googleapiclient.HttpError

### Task 2: OutputRouter Orchestration
- **OutputRouter** - Coordinates MinutesRenderer, DriveAdapter, SheetsAdapter
- **route_minutes()** - Generates date-slug filename, uploads to Drive
- **route_raid_items()** - Adds type field to items, writes to Sheets
- **OutputResult** - Aggregates rendered content and all write results
- Audit logging with structlog for all operations
- 8 tests covering router orchestration

### Task 3: Output API Endpoint
- **POST /output** - Accepts meeting data, generates and routes output
- **dry_run** query parameter for validation without writing
- **GET /output/health** - Reports adapter status (ok/degraded/no_adapters)
- Response includes minutes_url, sheets_url, markdown_preview (500 chars)
- 7 tests covering API behavior

## Key Artifacts

| File | Purpose |
|------|---------|
| `src/output/config.py` | ProjectOutputConfig with destination settings |
| `src/output/queue.py` | write_with_retry decorator and RetryQueue class |
| `src/output/router.py` | OutputRouter and OutputResult orchestration |
| `src/api/output.py` | REST endpoint for output generation |

## Commits

| Hash | Description |
|------|-------------|
| 9752337 | feat(05-03): add project output config and retry queue |
| 996ff01 | feat(05-03): add OutputRouter for orchestrating output generation |
| 53c2a76 | feat(05-03): add output generation API endpoint |

## Test Results

```
tests/test_output_router.py - 8 passed
tests/test_output_api.py - 7 passed
Full suite: 334 passed
```

## Deviations from Plan

None - plan executed exactly as written.

## Integration Points

- **Upstream**: Consumes MinutesRenderer (05-01), SheetsAdapter, DriveAdapter (05-02)
- **Downstream**: Ready for orchestration pipeline (Phase 6)

## Next Phase Readiness

Phase 5 (Output Generation) is now complete with:
- MinutesRenderer for template-based rendering
- SheetsAdapter and DriveAdapter for external writes
- OutputRouter for pipeline orchestration
- REST API for external access

Ready for Phase 6 (Orchestration Pipeline).
