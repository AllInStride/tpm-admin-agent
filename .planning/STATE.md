# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2025-01-17)

**Core value:** Convert meeting talk into tracked execution artifacts automatically — so TPMs shift from clerical work to strategic orchestration.
**Current focus:** Phase 4 Complete - Ready for Phase 5 (Output Generation)

## Current Position

Phase: 4 of 9 (Identity Resolution) - COMPLETE
Plan: 4 of 4 in current phase
Status: Phase verified and complete
Last activity: 2026-01-18 - Phase 4 verification passed

Progress: [=====.....] 44%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 4.0 min
- Total execution time: 44 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3/3 | 11 min | 3.7 min |
| 03 | 4/4 | 14 min | 3.5 min |
| 04 | 4/4 | 19 min | 4.8 min |

**Recent Trend:**
- Last 5 plans: 04-01 (4 min), 04-02 (5 min), 04-03 (4 min), 04-04 (6 min)
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
| 03-03 | Sequential extraction (not parallel) | Avoid LLM rate limits |
| 03-03 | Error isolation per extraction type | Failed extraction returns [], doesn't stop others |
| 03-03 | Confidence filtering uses >= threshold | Inclusive comparison at boundary |
| 03-04 | Extraction accepts transcript in request body | MVP approach; later will fetch from event store |
| 03-04 | Confidence threshold via query param | Per-request customization without changing service |
| 03-04 | Event emission order: items then summary | MeetingProcessed emitted after all item events |
| 04-01 | token_sort_ratio for name order independence | John Smith = Smith, John with high score |
| 04-01 | Single-source matches capped at 85% | Per CONTEXT.md - need verification for higher |
| 04-01 | Multi-source boost: +5% per additional source | Calendar/Slack verification increases confidence |
| 04-02 | 4-stage pipeline: exact -> learned -> fuzzy -> LLM | Cheapest operations first; LLM only for ambiguous cases |
| 04-02 | Learned mappings confidence 0.95 | User-verified but might be outdated; not quite 1.0 |
| 04-02 | LLM matches capped at 85% | Single-source cap; LLM inference needs verification |
| 04-02 | Temp file SQLite for tests (not in-memory) | libsql_client has issues with in-memory batch operations |
| 04-03 | RosterAdapter uses service account auth | gspread with GOOGLE_SHEETS_CREDENTIALS env var |
| 04-03 | load_roster skips malformed rows | Best effort - logs warning, continues with valid entries |
| 04-03 | Review summary shows first 5 items | Truncation with "...and N more" for large review counts |
| 04-03 | GET /pending returns empty for MVP | Reviews handled inline; queue-based workflow future |
| 04-04 | Use users.lookupByEmail API for Slack | Direct email lookup is O(1), no need to enumerate users |
| 04-04 | CalendarAdapter falls back to Sheets credentials | Reuse existing service account; same scopes often apply |
| 04-04 | Verification adapters are optional | System works without Slack/Calendar; caps at 85% |

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Phase 4 Complete

Phase 4: Identity Resolution complete.

**Plan 04-01 complete:**
- RapidFuzz installed for fuzzy matching
- FuzzyMatcher with Jaro-Winkler token_sort_ratio
- Multi-source confidence calculator
- RosterEntry and ResolutionResult schemas
- 20 new tests passing

**Plan 04-02 complete:**
- MappingRepository for learned mappings persistence
- LLMMatcher for ambiguous name inference
- IdentityResolver 4-stage pipeline (exact -> learned -> fuzzy -> LLM)
- src/repositories/ module created
- 20 new tests passing

**Plan 04-03 complete:**
- RosterAdapter for Google Sheets roster loading
- gspread and google-auth dependencies added
- Identity API endpoints: resolve, confirm, pending
- Human-readable review summary generation
- 29 new tests passing (17 adapter + 12 API)

**Plan 04-04 complete:**
- SlackAdapter for workspace member verification
- CalendarAdapter for meeting attendee verification
- Multi-source verification in IdentityResolver
- slack-sdk and google-api-python-client dependencies
- 32 new tests passing (10 Slack + 13 Calendar + 9 multi-source)

**Test coverage:** 275 tests passing

## Session Continuity

Last session: 2026-01-18
Stopped at: Phase 4 verified complete
Resume file: None
