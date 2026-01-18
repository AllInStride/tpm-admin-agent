# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2025-01-17)

**Core value:** Convert meeting talk into tracked execution artifacts automatically — so TPMs shift from clerical work to strategic orchestration.
**Current focus:** Phase 3 - RAID Extraction (in progress)

## Current Position

Phase: 3 of 9 (RAID Extraction)
Plan: 2 of 4 in current phase complete
Status: In progress
Last activity: 2026-01-18 - Completed 03-01-PLAN.md

Progress: [=====.....] 18%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 3.4 min
- Total execution time: 17 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3/3 | 11 min | 3.7 min |
| 03 | 2/4 | 6 min | 3.0 min |

**Recent Trend:**
- Last 5 plans: 02-03 (4 min), 03-02 (3 min), 03-01 (6 min)
- Trend: Stable execution pace

*Updated after each plan completion*

## Accumulated Context

### Decisions

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 02-01 | UTF-8-sig decoding first, Latin-1 fallback | Handle BOM markers and legacy files |
| 02-01 | 10MB file size limit | Sufficient for multi-hour transcripts |
| 02-02 | webvtt.from_buffer() for unified parsing | Cleaner API than separate VTT/SRT methods |
| 02-02 | Accept integer-second timestamps | webvtt-py library limitation |
| 02-03 | Mock EventBus with AsyncMock for tests | Verify event emission without persistence |
| 02-03 | Combined commit for endpoint + tests | Pre-commit hook requires tests to pass |
| 03-02 | Instructions after transcript in prompts | Lost-in-middle mitigation per Anthropic research |
| 03-02 | 3-tier confidence rubric (0.9/0.7/0.5) | Calibrate LLM confidence with explicit examples |
| 03-02 | 0.5 minimum extraction threshold | Below this is too uncertain for TPM workflows |
| 03-02 | Separate prompts per RAID type | Better precision than single mega-prompt |
| 03-01 | dateparser limitations documented | Library parses "Friday" but not "next Friday" |
| 03-01 | Extraction schemas separate from domain | due_date_raw string, no UUIDs/timestamps |
| 03-01 | LLMClient allows None client | Enables testing without API key |

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Phase 3 Progress

Phase 3: RAID Extraction in progress.

- [x] Extraction schemas for LLM output (03-01)
- [x] RAID extraction prompts with confidence rubrics (03-02)
- [ ] RAIDExtractor service with LLM client (03-03)
- [ ] Extraction endpoint and event emission (03-04)

## Session Continuity

Last session: 2026-01-18T21:16:00Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
