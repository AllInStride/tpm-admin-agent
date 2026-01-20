# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2025-01-17)

**Core value:** Convert meeting talk into tracked execution artifacts automatically — so TPMs shift from clerical work to strategic orchestration.
**Current focus:** Phase 10 (Identity Service Wiring) - In Progress

## Current Position

Phase: 10 of 10 (Identity Service Wiring)
Plan: 1 of 1 in current phase (complete)
Status: Phase complete
Last activity: 2026-01-20 - Completed 10-01-PLAN.md

Progress: [==========================] 100% (29/29 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 29
- Average duration: 5.7 min
- Total execution time: 168 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3/3 | 11 min | 3.7 min |
| 03 | 4/4 | 14 min | 3.5 min |
| 04 | 4/4 | 19 min | 4.8 min |
| 05 | 3/3 | 12 min | 4.0 min |
| 06 | 3/3 | 20 min | 6.7 min |
| 07 | 3/3 | 21 min | 7.0 min |
| 08 | 3/3 | 30 min | 10.0 min |
| 09 | 4/4 | 32 min | 8.0 min |
| 10 | 1/1 | 2 min | 2.0 min |

**Recent Trend:**
- Last 5 plans: 09-02 (13 min), 09-03 (7 min), 09-04 (5 min), 10-01 (2 min)
- Trend: Gap closure plans are fast (wiring-only changes)

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
| 06-01 | BATCH_SIZE=100 for Smartsheet add_rows | Conservative (API max 500) to avoid rate limiting |
| 06-01 | Dynamic column ID fetch per write | Column IDs are sheet-specific; cannot hardcode |
| 06-01 | row.to_bottom=True for new rows | Required per RESEARCH.md for add_rows to work |
| 06-01 | Date format as YYYY-MM-DD strings | Smartsheet DATE columns expect ISO format |
| 06-02 | lookup_user_by_email returns full user dict | Enables downstream code to access user ID without re-querying |
| 06-02 | verify_member delegates to lookup_user_by_email | Single code path for user lookup, DRY |
| 06-02 | Audit log in-memory with copy-on-read | Simple MVP, prevents external mutation |
| 06-03 | TYPE_CHECKING for SmartsheetAdapter import | Prevent circular import between adapters and integration |
| 06-03 | ProjectOutputConfig extended with Smartsheet settings | smartsheet_sheet_id, notify_owners, fallback_email |
| 06-03 | Partial success supported | Smartsheet failure doesn't block notifications |
| 07-01 | FTS5 external content tables | Avoid data duplication for search indexes |
| 07-01 | Triggers for FTS5 sync | Auto-sync on INSERT/UPDATE/DELETE |
| 07-01 | Individual execute() for FTS5 ops | Avoid libsql_client batch issues per RESEARCH.md |
| 07-02 | CLOSED_STATUSES = {completed, cancelled, closed, resolved} | Standard TPM workflow statuses |
| 07-02 | None status is open | Items without status appear in open lists |
| 07-02 | Case-insensitive status check | Avoid casing mismatches |
| 07-02 | Single SQL query for summary counts | Avoid N+1 query pattern |
| 07-02 | Filter builder pattern for dynamic WHERE | Optional filter params handled cleanly |
| 07-02 | ORDER BY for grouping | Dashboard needs sorted items, not aggregated counts |
| 07-03 | Empty keywords returns empty results | FTS5 MATCH requires keywords; filters alone cannot drive search |
| 07-03 | BM25 scores converted to absolute values | bm25() returns negative; abs() provides intuitive relevance |
| 07-03 | Duplicate rejections stored separately | Separation of concerns; doesn't bloat projection table |
| 08-01 | PrepConfig defaults: lead_time=10min, max_items=10, lookback=90days | Per CONTEXT.md requirements |
| 08-01 | CalendarAdapter.list_upcoming_events uses asyncio.to_thread | Non-blocking since google-api-python-client is sync |
| 08-01 | ItemMatcher queries by attendee email OR shared meeting_id | Per CONTEXT.md: match by BOTH attendee AND project association |
| 08-01 | prioritize_items: overdue first, then type order | Per CONTEXT.md: action>risk>issue>decision |
| 08-01 | generate_talking_points: heuristic approach | Per RESEARCH.md: simple heuristic first, LLM enhancement future |
| 08-01 | project_id parameter reserved | Scoping by project_id deferred until project associations exist |
| 08-02 | ContextGatherer uses optional dependencies | Graceful degradation when adapters unavailable |
| 08-02 | Parallel gathering via asyncio.gather | return_exceptions=True isolates source failures |
| 08-02 | normalize_series_key strips dates/numbers | Regex for MM/DD, YYYY-MM-DD, standalone numbers |
| 08-03 | PrepService singleton pattern | Scheduler needs access to service instance via get_instance() |
| 08-03 | 5-minute scan interval with 10-15 min lookahead | Per RESEARCH.md for 10-min lead time precision |
| 08-03 | Duplicate prevention via _sent_preps set | In-memory tracking event_id:date keys |
| 08-03 | AsyncExitStack for composable lifespan | Multiple lifespan contexts without deep nesting |
| 08-03 | DISABLE_PREP_SCHEDULER env var | Test isolation without scheduler interference |
| 09-01 | Blocker detection: overdue OR 'blocked' keyword | Two heuristics catch most blockers without complex logic |
| 09-01 | Velocity = completed - new | Simple metric showing net progress |
| 09-01 | Markdown + plain text template pairs | Flexibility for different delivery channels |
| 09-01 | UTC dates for SQLite consistency in tests | SQLite date('now') returns UTC; must match |
| 09-02 | ExecStatusGenerator limits items to 5 per category | Exec brevity - half-page requirement |
| 09-02 | TeamStatusGenerator uses max_items=100 | Full detail for team without truncation |
| 09-02 | Metadata tracks item counts and RAG indicators | Enable downstream filtering and display |
| 09-03 | EscalationGenerator validates min 2 options | Per CONTEXT.md: always include options A, B, or C |
| 09-03 | EscalationGenerator validates explicit deadline | Per CONTEXT.md: must have "Decision needed by [date]" |
| 09-03 | Options formatted with A/B/C labels | Standard escalation format for clarity |
| 09-03 | TalkingPointsGenerator logs warning for missing Q&A categories | LLM may have valid reason for omission; don't fail |
| 09-03 | Escalation uses plain text for both outputs | Email format doesn't need markdown |
| 09-04 | CommunicationService coordinates all generators with shared LLM client | Single entry point for all communication generation |
| 09-04 | Talking points defaults to 30 days lookback | Reasonable default for project context gathering |
| 09-04 | FastAPI dependency override pattern for tests | Enables clean mocking without import hacks |
| 10-01 | Identity service initialized after search services | Maintains logical grouping in lifespan |
| 10-01 | Slack and calendar adapters optional for IdentityResolver | Multi-source verification already handled in prep_service |

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Phase 10 Progress

Phase 10: Identity Service Wiring complete.

**Plan 10-01 complete:**
- Added _initialize_identity_service function to main.py
- Wired RosterAdapter, FuzzyMatcher, MappingRepository, IdentityResolver into lifespan
- Identity endpoints no longer raise AttributeError for missing state
- All 769 tests passing

**Test coverage:** 769 tests passing

## Session Continuity

Last session: 2026-01-20T06:02:19Z
Stopped at: Completed 10-01-PLAN.md (Phase 10 complete)
Resume file: None
