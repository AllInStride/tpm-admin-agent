---
phase: 02-transcript-ingestion
plan: 02
subsystem: api
tags: [webvtt, srt, parser, transcript, speaker-diarization]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Utterance model from src/models/meeting.py
provides:
  - TranscriptParser service for VTT/SRT parsing
  - ParsedTranscript dataclass with utterances, speakers, duration
  - Speaker extraction from VTT voice tags
affects: [02-03-upload-endpoint, 03-extraction]

# Tech tracking
tech-stack:
  added: [webvtt-py]
  patterns: [service-layer-pattern, format-agnostic-parsing]

key-files:
  created:
    - src/services/__init__.py
    - src/services/transcript_parser.py
    - tests/test_transcript_parser.py
  modified: []

key-decisions:
  - "Used webvtt.from_buffer() for unified VTT/SRT parsing instead of separate methods"
  - "webvtt-py truncates timestamps to integer seconds - accepted as library limitation"

patterns-established:
  - "Service layer pattern: parsing logic in src/services/, not in API handlers"
  - "Format parameter uses file extension with dot (e.g., '.vtt') for consistency with Path.suffix"

# Metrics
duration: 5min
completed: 2026-01-18
---

# Phase 2 Plan 2: Transcript Parser Summary

**TranscriptParser service with VTT/SRT support using webvtt-py, extracts speaker names from voice tags**

## Performance

- **Duration:** 4 min 33 sec
- **Started:** 2026-01-18T05:26:58Z
- **Completed:** 2026-01-18T05:31:31Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- TranscriptParser class parses both VTT and SRT formats
- Speaker names extracted from VTT voice tags (defaults to "Unknown Speaker" for SRT)
- ParsedTranscript dataclass provides utterances, speakers list, and duration
- Comprehensive test coverage with 19 unit tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Add webvtt-py dependency and create services module** - `f6f4cfe` (chore)
2. **Task 2: Create TranscriptParser service** - `c0f873c` (feat)
3. **Task 3: Add parser unit tests** - `e57d95b` (test)

## Files Created/Modified

- `src/services/__init__.py` - Module marker for services package
- `src/services/transcript_parser.py` - TranscriptParser class and ParsedTranscript dataclass
- `tests/test_transcript_parser.py` - 19 unit tests covering all parser functionality

## Decisions Made

1. **Used webvtt.from_buffer() for unified parsing** - The plan suggested `from_srt(StringIO())` but `from_srt()` expects a file path. `from_buffer()` accepts a StringIO and a format parameter, providing a cleaner unified approach for both VTT and SRT.

2. **Accepted integer-second timestamps** - webvtt-py's `start_in_seconds` and `end_in_seconds` properties return integers, truncating milliseconds. This is a library limitation. The raw `start` and `end` string properties retain full precision if needed later.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed SRT parsing method**
- **Found during:** Task 2 (TranscriptParser creation)
- **Issue:** Plan specified `webvtt.from_srt(StringIO(content))` but `from_srt()` expects a file path, not StringIO
- **Fix:** Used `webvtt.from_buffer(StringIO(content), format='srt')` which accepts both format types
- **Files modified:** src/services/transcript_parser.py
- **Verification:** Both VTT and SRT parsing tests pass
- **Committed in:** c0f873c (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix - code would not run without this change. No scope creep.

## Issues Encountered

None - plan executed smoothly after fixing the SRT parsing method.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TranscriptParser ready for use in upload endpoint (02-03)
- Service follows established patterns (service layer, dependency injection compatible)
- Comprehensive tests ensure reliability

---
*Phase: 02-transcript-ingestion*
*Completed: 2026-01-18*
