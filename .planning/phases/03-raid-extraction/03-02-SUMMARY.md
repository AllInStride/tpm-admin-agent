---
phase: 03-raid-extraction
plan: 02
subsystem: extraction
tags: [llm, prompts, confidence-calibration, raid]

# Dependency graph
requires:
  - phase: 02-transcript-ingestion
    provides: ParsedTranscript with utterances and speakers
provides:
  - Four RAID extraction prompts (action items, decisions, risks, issues)
  - Explicit confidence calibration rubrics for LLM
  - Source quote requirements for audit trail
  - Type-specific extraction guidance
affects: [03-raid-extraction/03-03 (RAIDExtractor will use these prompts)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Instructions after content pattern (lost-in-middle mitigation)"
    - "Confidence rubric pattern (0.9-1.0, 0.7-0.9, 0.5-0.7 thresholds)"
    - "Source quote requirement for verifiable extractions"

key-files:
  created:
    - src/extraction/prompts.py
    - tests/extraction/test_prompts.py
  modified:
    - pyproject.toml (ruff per-file-ignores)

key-decisions:
  - "Put extraction instructions AFTER transcript per lost-in-middle research"
  - "Require source_quote for all extractions (audit trail)"
  - "Use explicit confidence rubric with 3 tiers (0.9-1.0, 0.7-0.9, 0.5-0.7)"
  - "0.5 minimum threshold - do not extract below this"
  - "Separate prompts per RAID type (better precision than mega-prompt)"

patterns-established:
  - "Confidence rubric: explicit examples at each tier"
  - "Type distinctions: risks vs issues, commitments vs discussions"
  - "Prompt structure: context first, instructions after"

# Metrics
duration: 3min
completed: 2026-01-18
---

# Phase 3 Plan 2: RAID Extraction Prompts Summary

**Four LLM system prompts for RAID extraction with explicit confidence calibration, source quote requirements, and type-specific guidance**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-18T21:05:33Z
- **Completed:** 2026-01-18T21:08:56Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Created ACTION_ITEM_PROMPT with assignee/due_date extraction and commitment vs discussion distinction
- Created DECISION_PROMPT with rationale/alternatives extraction and made vs being-discussed distinction
- Created RISK_PROMPT with severity levels and risk vs issue distinction
- Created ISSUE_PROMPT with priority levels and issue vs risk distinction
- All prompts include 3-tier confidence rubric with explicit examples
- All prompts require verbatim source_quote for audit trail
- Prompts structured with transcript first, instructions after (lost-in-middle mitigation)
- 34 structural tests validating prompt requirements

## Task Commits

Each task was committed atomically:

1. **Task 1: Create extraction prompts** - `2397303` (feat)
2. **Task 2: Test prompts exist and contain required elements** - `7d3a7ef` (test)

## Files Created/Modified

- `src/extraction/__init__.py` - Module exports for prompts
- `src/extraction/prompts.py` - Four RAID extraction prompts
- `tests/extraction/__init__.py` - Test module init
- `tests/extraction/test_prompts.py` - 34 structural tests
- `pyproject.toml` - Added ruff per-file-ignore for prompts.py line length

## Decisions Made

1. **Instructions after transcript placement** - Per Anthropic's research on "lost in the middle" problem, extraction instructions are placed after the transcript placeholder to improve attention to content.

2. **Explicit 3-tier confidence rubric** - Each prompt includes concrete examples at 0.9-1.0, 0.7-0.9, and 0.5-0.7 thresholds to calibrate LLM confidence scoring.

3. **0.5 minimum extraction threshold** - Items below 0.5 confidence should not be extracted (too uncertain for TPM workflows).

4. **Type distinction guidance** - Each prompt explicitly distinguishes its type from similar types (risks vs issues, commitments vs discussions) to reduce misclassification.

5. **Ruff line-length exception** - Added per-file-ignore for prompts.py since LLM prompt strings are not subject to code line length constraints.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-commit ruff hook failed on line length in prompt strings. Resolved by adding per-file-ignore in pyproject.toml for prompts.py - prompts are LLM-facing strings where line length is irrelevant.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Four RAID prompts ready for use by RAIDExtractor (Plan 03)
- Prompts designed to work with Anthropic structured outputs
- Confidence rubrics aligned with extraction schema validation thresholds
- Source quote requirement matches domain model field constraints

---
*Phase: 03-raid-extraction*
*Completed: 2026-01-18*
