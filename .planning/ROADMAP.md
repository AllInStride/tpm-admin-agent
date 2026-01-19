# Roadmap: TPM Admin Agent

## Overview

This roadmap delivers a Meeting-to-Execution Agent that converts Zoom transcripts into tracked RAID artifacts (Risks, Actions, Issues, Decisions) automatically routed to Smartsheet. The journey progresses from foundational infrastructure through transcript processing, extraction, identity resolution, and integration, culminating in cross-meeting intelligence and communication automation. Each phase builds on the previous, delivering verifiable capabilities that reduce TPM administrative overhead.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation** - Event infrastructure, canonical models, project scaffolding
- [x] **Phase 2: Transcript Ingestion** - Upload and parse Zoom transcripts with speaker identification
- [x] **Phase 3: RAID Extraction** - Extract action items, decisions, risks, issues with confidence scores
- [x] **Phase 4: Identity Resolution** - Match transcript names to project roster and external systems
- [ ] **Phase 5: Output Generation** - Generate meeting minutes and establish adapter pattern
- [ ] **Phase 6: System Integration** - Write artifacts to Smartsheet and notify owners
- [ ] **Phase 7: Cross-Meeting Intelligence** - Search past meetings and track open items
- [ ] **Phase 8: Meeting Prep** - Surface context and open items before meetings
- [ ] **Phase 9: Communication Automation** - Generate status updates, escalations, exec talking points

## Phase Details

### Phase 1: Foundation
**Goal**: Establish the architectural foundation so all subsequent phases have reliable infrastructure
**Depends on**: Nothing (first phase)
**Requirements**: None (infrastructure only)
**Success Criteria** (what must be TRUE):
  1. Event bus routes typed events between components
  2. Canonical data models (Meeting, ActionItem, Decision, Risk, Issue, Participant) are defined and validated
  3. Event store persists all events with append-only guarantees
  4. FastAPI application starts and responds to health checks
  5. Test harness runs and validates event flow
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding with uv, FastAPI, and health endpoints
- [x] 01-02-PLAN.md — Canonical data models (Meeting, Participant, ActionItem, Decision, Risk, Issue)
- [x] 01-03-PLAN.md — Event bus and event store infrastructure

### Phase 2: Transcript Ingestion
**Goal**: User can upload a Zoom transcript and system parses it into structured meeting data
**Depends on**: Phase 1
**Requirements**: ING-01, ING-02, ING-03
**Success Criteria** (what must be TRUE):
  1. User can upload a VTT or SRT transcript file via API endpoint
  2. System parses transcript into timestamped utterances
  3. System identifies distinct speakers from transcript
  4. Parsed transcript persists as Meeting event in event store
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Upload endpoint with file validation (Wave 1)
- [x] 02-02-PLAN.md — VTT/SRT parser with speaker diarization (Wave 1)
- [x] 02-03-PLAN.md — Meeting event emission and persistence (Wave 2)

### Phase 3: RAID Extraction
**Goal**: System extracts RAID artifacts (Risks, Actions, Issues, Decisions) from parsed transcripts using LLM
**Depends on**: Phase 2
**Requirements**: EXT-01, EXT-02, EXT-03, EXT-04, EXT-05
**Success Criteria** (what must be TRUE):
  1. System extracts action items with owner mention, due date (if stated), and description
  2. System extracts decisions with context and rationale
  3. System extracts risks with severity level
  4. System extracts issues with status
  5. Each extraction includes a confidence score
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — LLM infrastructure, extraction schemas, date normalizer (Wave 1)
- [x] 03-02-PLAN.md — Extraction prompts with confidence rubrics (Wave 1)
- [x] 03-03-PLAN.md — RAIDExtractor service with domain model conversion (Wave 2)
- [x] 03-04-PLAN.md — Extraction API endpoint with event emission (Wave 3)

### Phase 4: Identity Resolution
**Goal**: System resolves names mentioned in transcripts to actual people in project roster
**Depends on**: Phase 3
**Requirements**: IDN-01, IDN-02, IDN-03, IDN-04
**Success Criteria** (what must be TRUE):
  1. System matches names against project roster spreadsheet
  2. System cross-references Slack channel membership for resolution
  3. System cross-references Google Calendar attendees for resolution
  4. System flags low-confidence matches for human review (threshold: <85%)
**Plans**: 4 plans

Plans:
- [x] 04-01-PLAN.md — Identity schemas, fuzzy matcher, confidence calculator (Wave 1)
- [x] 04-02-PLAN.md — IdentityResolver orchestrator, learned mappings, LLM matcher (Wave 2)
- [x] 04-03-PLAN.md — Roster adapter and identity API endpoints (Wave 3)
- [x] 04-04-PLAN.md — Slack and Calendar adapters for multi-source verification (Wave 3)

### Phase 5: Output Generation
**Goal**: System generates meeting minutes and establishes extensible integration architecture
**Depends on**: Phase 4
**Requirements**: OUT-01, OUT-02, OUT-05
**Success Criteria** (what must be TRUE):
  1. System generates meeting minutes from customizable template
  2. User can select target system (Google Sheets, Smartsheet, Jira) for output
  3. Integration architecture uses adapter pattern for target systems
**Plans**: 3 plans

Plans:
- [ ] 05-01-PLAN.md — Output schemas, Jinja2 renderer, default templates (Wave 1)
- [ ] 05-02-PLAN.md — OutputAdapter protocol, SheetsAdapter, DriveAdapter (Wave 2)
- [ ] 05-03-PLAN.md — OutputRouter, retry queue, output API endpoint (Wave 3)

### Phase 6: System Integration
**Goal**: Extracted artifacts flow to Smartsheet and owners receive notifications
**Depends on**: Phase 5
**Requirements**: OUT-03, OUT-04
**Success Criteria** (what must be TRUE):
  1. System creates rows in Smartsheet for action items, risks, and issues
  2. System handles Smartsheet rate limiting gracefully
  3. System notifies owners of assigned items via Slack
  4. Notification includes item description, due date, and link to source meeting
**Plans**: TBD

Plans:
- [ ] 06-01: Smartsheet adapter with rate limiting
- [ ] 06-02: Artifact routing and row creation
- [ ] 06-03: Slack notification adapter

### Phase 7: Cross-Meeting Intelligence
**Goal**: User can search and track items across multiple meetings
**Depends on**: Phase 6
**Requirements**: XMT-01, XMT-02
**Success Criteria** (what must be TRUE):
  1. User can search across past meeting content (full-text search)
  2. System tracks open items across multiple meetings and surfaces them
  3. User can view item history showing which meetings referenced it
**Plans**: TBD

Plans:
- [ ] 07-01: Full-text search index
- [ ] 07-02: Open item tracking and rollup
- [ ] 07-03: Item history and meeting linkage

### Phase 8: Meeting Prep
**Goal**: System proactively surfaces relevant context before meetings start
**Depends on**: Phase 7
**Requirements**: PRP-01, PRP-02, PRP-03
**Success Criteria** (what must be TRUE):
  1. System surfaces open items from previous meetings with same attendees
  2. System surfaces relevant context from docs/Slack related to meeting agenda
  3. System delivers prep summary 10 minutes before meeting start time
**Plans**: TBD

Plans:
- [ ] 08-01: Open item surfacing by attendee overlap
- [ ] 08-02: Context retrieval from docs and Slack
- [ ] 08-03: Scheduled prep delivery

### Phase 9: Communication Automation
**Goal**: System generates communication artifacts for different audiences
**Depends on**: Phase 8
**Requirements**: COM-01, COM-02, COM-03, COM-04
**Success Criteria** (what must be TRUE):
  1. System drafts status updates formatted for executive audience (summary, key decisions, blockers)
  2. System drafts status updates formatted for team detail (full action item list, assignments)
  3. System generates escalation emails with facts, impact, and explicit ask
  4. System generates exec talking points for reviews

**Plans**: TBD

Plans:
- [ ] 09-01: Exec status update generator
- [ ] 09-02: Team status update generator
- [ ] 09-03: Escalation email generator
- [ ] 09-04: Exec talking points generator

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> ... -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-01-18 |
| 2. Transcript Ingestion | 3/3 | Complete | 2026-01-18 |
| 3. RAID Extraction | 4/4 | Complete | 2026-01-18 |
| 4. Identity Resolution | 4/4 | Complete | 2026-01-18 |
| 5. Output Generation | 0/3 | Planned | - |
| 6. System Integration | 0/3 | Not started | - |
| 7. Cross-Meeting Intelligence | 0/3 | Not started | - |
| 8. Meeting Prep | 0/3 | Not started | - |
| 9. Communication Automation | 0/4 | Not started | - |

---
*Roadmap created: 2025-01-17*
*Phase 1 planned: 2025-01-17*
*Phase 2 planned: 2025-01-17*
*Phase 3 planned: 2026-01-18*
*Phase 4 planned: 2026-01-18*
*Phase 5 planned: 2026-01-18*
*Total plans: 30*
*Total v1 requirements: 26 (100% coverage)*
