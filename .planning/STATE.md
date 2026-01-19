# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2025-01-17)

**Core value:** Convert meeting talk into tracked execution artifacts automatically — so TPMs shift from clerical work to strategic orchestration.
**Current focus:** Phase 6 In Progress - System Integration

## Current Position

Phase: 6 of 9 (System Integration)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-01-19 - Completed 06-02-PLAN.md

Progress: [========..] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 15
- Average duration: 4.2 min
- Total execution time: 63 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3/3 | 11 min | 3.7 min |
| 03 | 4/4 | 14 min | 3.5 min |
| 04 | 4/4 | 19 min | 4.8 min |
| 05 | 3/3 | 12 min | 4.0 min |
| 06 | 1/3 | 7 min | 7.0 min |

**Recent Trend:**
- Last 5 plans: 05-01 (5 min), 05-02 (3 min), 05-03 (4 min), 06-02 (7 min)
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
| 05-01 | Role enum formatted as titlecase | Participant roles: host -> Host in attendee strings |
| 05-01 | Autoescape for HTML templates only | Markdown templates unescaped for valid output |
| 05-01 | Low confidence threshold at 0.7 | Matches extraction confidence threshold |
| 05-01 | Next steps limited to 5 items | Per CONTEXT.md "top 3-5 actions" guidance |
| 05-02 | OutputAdapter as runtime_checkable Protocol | Structural subtyping without inheritance |
| 05-02 | asyncio.to_thread for sync SDK calls | Non-blocking I/O without async SDK |
| 05-02 | DriveAdapter falls back to Sheets creds | Reuse existing service account |
| 05-02 | SheetsAdapter auto-creates worksheet | Better UX, ready to use |
| 05-03 | In-memory RetryQueue for MVP | SQLite persistence deferred per CONTEXT.md |
| 05-03 | Tenacity retry: 5 attempts, 4-60s backoff | Handle transient Google API failures |
| 05-03 | OutputRouter coordinates adapters | Single orchestration point for output pipeline |
| 05-03 | Minutes filename: {date}-{title-slug}.md | Sortable by date, human-readable |
| 06-02 | lookup_user_by_email returns full user dict | Enables downstream code to access user ID without re-querying |
| 06-02 | verify_member delegates to lookup_user_by_email | Single code path for user lookup, DRY |
| 06-02 | Audit log in-memory with copy-on-read | Simple MVP, prevents external mutation |

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Phase 6 In Progress

Phase 6: System Integration in progress.

**Plan 06-02 complete:**
- SlackAdapter extended with send_dm and lookup_user_by_email
- NotificationService with notify_owner and audit trail
- Message format: mrkdwn with title, due date, Smartsheet link
- NotificationResult and NotificationRecord schemas
- 31 new tests passing (17 slack + 14 notification)

**Test coverage:** 355 tests passing

## Session Continuity

Last session: 2026-01-19
Stopped at: Completed 06-02-PLAN.md
Resume file: None
