# Product Requirements Document: TPM Admin Agent v1

**Document Version:** 1.0
**Date:** 2025-01-17
**Author:** Gabriel Guenette
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Goals & Success Metrics](#goals--success-metrics)
4. [User Personas](#user-personas)
5. [Solution Overview](#solution-overview)
6. [Functional Requirements](#functional-requirements)
7. [Technical Architecture](#technical-architecture)
8. [Non-Functional Requirements](#non-functional-requirements)
9. [Dependencies & Constraints](#dependencies--constraints)
10. [Release Phases](#release-phases)
11. [Out of Scope](#out-of-scope)
12. [Open Questions & Risks](#open-questions--risks)
13. [Appendices](#appendices)

---

## Executive Summary

The TPM Admin Agent is an AI-powered system that automatically extracts action items, decisions, risks, and issues from Zoom meeting transcripts and routes them to systems of record. It eliminates the manual reconstruction work that TPMs perform after every meeting, converting meeting talk into tracked execution artifacts automatically.

**Core Value Proposition:** TPMs spend 3-5 hours daily on meeting reconstruction. This system reduces that to minutes, shifting TPM time from clerical work to strategic orchestration.

**v1 Scope:** Meeting → Execution Agent with RAID extraction, identity resolution, system integration, cross-meeting intelligence, meeting prep, and communication automation.

**Target Users:** Technical Program Managers, starting with single-user validation and architected for team/org-wide expansion.

---

## Problem Statement

### Current State

Technical Program Managers attend 10-15 meetings daily. After each meeting, they must:

1. Review the Zoom transcript or recording
2. Manually extract action items, decisions, risks, and issues
3. Identify who owns each item (often ambiguous in transcripts)
4. Enter items into tracking systems (Smartsheet, Google Sheets, Jira)
5. Notify owners of their assignments
6. Reformat the same information for different audiences (exec summaries, team updates)

**Time Impact:** ~20 minutes per meeting × 10-15 meetings = 3-5 hours daily on reconstruction.

### Why Existing Tools Don't Solve This

| Tool | What It Does | What It Doesn't Do |
|------|--------------|-------------------|
| Zoom AI Companion | Transcribes and summarizes | Doesn't extract structured RAID items, resolve identity, or route to systems |
| Otter.ai / Fireflies | Transcription + basic action items | Generic extraction, no project context, no identity resolution |
| Fellow / Notion AI | Meeting notes templates | Manual entry, no automated extraction or routing |

**Gap:** No tool combines AI extraction + identity resolution + system routing + cross-meeting intelligence in a way that fits TPM workflows.

### Impact of Not Solving

- Action items fall through cracks due to manual transcription errors
- Decisions get relitigated because they weren't properly logged
- TPMs spend strategic capacity on clerical work
- Institutional knowledge stays in people's heads, not queryable systems

---

## Goals & Success Metrics

### Primary Goals

1. **Automate RAID extraction** from meeting transcripts with high accuracy
2. **Resolve identity** from transcript names to actual people
3. **Route artifacts** to TPM's systems of record automatically
4. **Enable cross-meeting intelligence** — search, tracking, prep
5. **Generate communication artifacts** for different audiences

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Time from meeting end to items in system | < 5 minutes | Timestamp comparison |
| Action item extraction recall | > 90% | Manual audit of sample meetings |
| Action item extraction precision | > 80% | False positive rate in sample |
| Owner auto-resolution rate | > 85% | % resolved without human intervention |
| User cleanup time per meeting | < 2 minutes | User time tracking |
| User satisfaction | > 4/5 | Post-meeting survey |

### Non-Goals for v1

- Real-time context surfacing during meetings
- Automated Zoom webhook ingestion
- Email/Slack message ingestion
- Multi-tenant deployment

---

## User Personas

### Primary: IC Technical Program Manager

**Profile:**
- Manages 3-8 concurrent projects
- Attends 10-15 meetings daily
- Uses Smartsheet/Google Sheets for tracking, Slack for communication
- Technically proficient but not a developer
- Values efficiency and hates repetitive work

**Pain Points:**
- Spends hours daily on meeting reconstruction
- Loses action items due to manual errors
- Can't remember which meeting a decision was made in
- Reformats same information for different audiences

**Success Criteria:**
- "I finish a meeting, upload the transcript, and the action items appear in my sheet within minutes"
- "I can search 'what did we decide about X' and get an answer"
- "Before a meeting, I know what's still open from last time"

### Secondary: TPM Director (Future)

**Profile:**
- Manages team of 5-10 TPMs
- Needs visibility across programs
- Identifies cross-project risks and dependencies

**Needs (v2+):**
- Aggregated view across TPM portfolios
- Cross-project pattern detection
- Resource/capacity visibility

### Tertiary: VP of TPM (Future)

**Profile:**
- Executive oversight of TPM org
- Portfolio-level health metrics
- Strategic risk identification

**Needs (Future):**
- BU-level rollups
- Predictive health scoring
- Executive dashboards

---

## Solution Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TPM Admin Agent                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Ingest   │───▶│ Extract  │───▶│ Resolve  │───▶│ Output   │  │
│  │ Layer    │    │ Layer    │    │ Layer    │    │ Layer    │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Event Bus                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Event Store                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │ Google  │          │ Smart-  │          │  Slack  │
   │ Sheets  │          │ sheet   │          │         │
   └─────────┘          └─────────┘          └─────────┘
```

### Core Workflow

1. **Ingest**: User uploads Zoom transcript (VTT/SRT format)
2. **Parse**: System extracts timestamped utterances with speaker identification
3. **Extract**: AI identifies action items, decisions, risks, issues with confidence scores
4. **Resolve**: System matches transcript names to actual people via roster + Slack + Calendar
5. **Review**: Low-confidence items flagged for human verification
6. **Output**: Meeting minutes generated from template
7. **Route**: Artifacts written to target system (Google Sheets/Smartsheet/Jira)
8. **Notify**: Owners pinged via Slack with their assignments

### Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| Adapter Pattern | All external systems behind interfaces; swap without core changes |
| Canonical Data Model | Internal models (Meeting, ActionItem, Decision, Risk, Issue) that export to any format |
| Event-Driven | All processing flows through typed events; enables replay and audit |
| Human-in-the-Loop | Confidence thresholds determine auto vs. manual review |
| Privacy-First | Audit logging, data boundaries, consent model |

---

## Functional Requirements

### FR1: Transcript Ingestion

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| ING-01 | User can upload Zoom transcript file | Upload endpoint accepts VTT, SRT, TXT files up to 10MB; returns upload confirmation with transcript ID | P0 |
| ING-02 | System parses VTT/SRT transcript formats | Parser extracts: timestamp, speaker label, utterance text; handles malformed input gracefully | P0 |
| ING-03 | System identifies speakers (diarization) | Distinct speakers extracted from transcript labels; speaker turns mapped to utterances | P0 |

**User Story:** As a TPM, I want to upload my Zoom transcript so the system can process it automatically.

### FR2: RAID Extraction

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| EXT-01 | System extracts action items with owner, due date, description | Each action item includes: description, owner mention (raw name), due date (if stated, else null), source quote | P0 |
| EXT-02 | System extracts decisions with context and rationale | Each decision includes: what was decided, alternatives considered (if discussed), rationale, participants | P0 |
| EXT-03 | System extracts risks with severity level | Each risk includes: description, severity (high/medium/low), potential impact, mitigation (if discussed) | P0 |
| EXT-04 | System extracts issues with status | Each issue includes: description, status (open/blocked/resolved), owner (if assigned), blockers | P0 |
| EXT-05 | System provides confidence score for each extraction | Confidence score 0-100% on every extracted item; items below threshold flagged for review | P0 |

**User Story:** As a TPM, I want the system to extract action items, decisions, risks, and issues from my meeting so I don't have to do it manually.

**Extraction Examples:**

| Transcript Text | Extraction Type | Extracted Data |
|-----------------|-----------------|----------------|
| "John will send the API specs by Friday" | Action Item | Owner: John, Due: Friday, Description: Send API specs |
| "We decided to go with Option B because it's less risky" | Decision | Decision: Go with Option B, Rationale: Less risky |
| "If the vendor delays past March, we're in trouble" | Risk | Description: Vendor delay, Severity: High, Impact: Schedule |
| "We can't proceed until we get staging access" | Issue | Description: No staging access, Status: Blocked |

### FR3: Identity Resolution

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| IDN-01 | System matches names to project roster spreadsheet | Fuzzy matching handles variations (John → John Smith); roster loaded from Google Sheets | P0 |
| IDN-02 | System cross-references Slack channel membership | Slack API queried for project channel members; used as secondary resolution source | P1 |
| IDN-03 | System cross-references Google Calendar attendees | Calendar API queried for meeting attendees; used as tertiary resolution source | P1 |
| IDN-04 | System flags low-confidence matches for human review | Matches below 85% confidence presented to user with options; user selection stored for learning | P0 |

**User Story:** As a TPM, I want "John" in the transcript to be correctly identified as John Smith from Engineering so action items route to the right person.

**Resolution Logic:**
```
1. Extract name mention from transcript ("John")
2. Query project roster for matches
   - Exact match → 95% confidence
   - Fuzzy match (nickname, partial) → 70-90% confidence
3. Cross-reference Slack channel membership
   - Present in channel → +10% confidence
4. Cross-reference Calendar attendees
   - In meeting invite → +10% confidence
5. If confidence ≥ 85% → Auto-resolve
6. If confidence < 85% → Flag for human review
```

### FR4: Output Generation

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| OUT-01 | System generates meeting minutes from template | Template configurable per project; includes: attendees, discussion, decisions, action items, risks, issues | P0 |
| OUT-02 | User can select target system (Google Sheets, Smartsheet, Jira) | Selection UI with dropdown; selection persisted per project; default configurable | P0 |
| OUT-03 | System creates rows/items in selected target for artifacts | Action items, risks, issues created as rows/tickets with all fields populated; link back to source meeting | P0 |
| OUT-04 | System notifies owners of assigned items | Slack notification to owner with: item description, due date, meeting link; configurable notification preferences | P1 |
| OUT-05 | Architecture uses adapter pattern for integrations | Integration interface defines: create, update, delete, query; adapters implement for each target system | P0 |

**User Story:** As a TPM, I want extracted items to automatically appear in my Smartsheet so I don't have to copy-paste.

### FR5: Cross-Meeting Intelligence

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| XMT-01 | User can search across past meeting content | Full-text search across all meetings; results show meeting, date, relevant excerpt, link | P1 |
| XMT-02 | System tracks open items across multiple meetings | Open items dashboard shows: all open, overdue, by owner; item history shows which meetings referenced it | P1 |

**User Story:** As a TPM, I want to search "what did we decide about authentication" and get the answer without remembering which meeting it was.

### FR6: Meeting Prep

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| PRP-01 | System surfaces open items from previous meetings | For recurring meetings, show open items from sessions with overlapping attendees | P1 |
| PRP-02 | System surfaces relevant context from docs/Slack | Query Google Docs and Slack for content related to meeting title/agenda; surface top 5 relevant items | P2 |
| PRP-03 | System delivers prep summary 10 minutes before meeting | Scheduled job queries Calendar; sends prep via Slack/email at configured lead time | P1 |

**User Story:** As a TPM, I want to receive a summary of open items 10 minutes before my recurring standup so I walk in prepared.

### FR7: Communication Automation

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| COM-01 | System drafts status updates for exec audience | Summary format: progress, decisions needed, blockers, asks; bullet points, no jargon | P1 |
| COM-02 | System drafts status updates for team detail | Detailed format: full action item list, assignments, dependencies, next steps | P1 |
| COM-03 | System generates escalation emails | Format: facts (what), impact (why it matters), ask (what you need); professional tone | P2 |
| COM-04 | System generates exec talking points | Format: key messages, anticipated Q&A, risks to highlight, wins to mention | P2 |

**User Story:** As a TPM, I want to generate an exec-ready status update from my meeting data so I don't spend 30 minutes reformatting.

---

## Technical Architecture

### Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Framework | FastAPI 0.128+ | Async-first, Pydantic-native, production-ready |
| Language | Python 3.12+ | LLM ecosystem, team familiarity |
| AI/LLM | Claude Sonnet 4.5 via Anthropic SDK | Structured outputs, high accuracy on extraction tasks |
| Agent Framework | LangGraph 1.0.6 | Production-ready multi-agent orchestration |
| Task Queue | Dramatiq | 10x faster than RQ, simpler than Celery |
| Database | Turso/libSQL | Matches existing stack, edge-ready, built-in vector search |
| Event Store | Append-only table in Turso | Event sourcing for audit and replay |

### Canonical Data Models

```python
class Meeting:
    id: UUID
    transcript_id: str
    title: str
    date: datetime
    attendees: list[Participant]
    utterances: list[Utterance]

class ActionItem:
    id: UUID
    meeting_id: UUID
    description: str
    owner_mention: str  # Raw name from transcript
    owner_resolved: Participant | None
    due_date: date | None
    status: Status
    confidence: float
    source_quote: str

class Decision:
    id: UUID
    meeting_id: UUID
    description: str
    rationale: str
    alternatives: list[str]
    participants: list[Participant]
    confidence: float
    source_quote: str

class Risk:
    id: UUID
    meeting_id: UUID
    description: str
    severity: Severity  # high, medium, low
    impact: str
    mitigation: str | None
    confidence: float
    source_quote: str

class Issue:
    id: UUID
    meeting_id: UUID
    description: str
    status: IssueStatus  # open, blocked, resolved
    owner_resolved: Participant | None
    blockers: list[str]
    confidence: float
    source_quote: str

class Participant:
    id: UUID
    name: str
    email: str
    slack_id: str | None
    source: str  # roster, slack, calendar
```

### Integration Adapters

```python
class TargetSystemAdapter(Protocol):
    def create_action_item(self, item: ActionItem) -> str: ...
    def create_risk(self, risk: Risk) -> str: ...
    def create_issue(self, issue: Issue) -> str: ...
    def update_item(self, id: str, updates: dict) -> None: ...
    def query_items(self, filters: dict) -> list: ...

class GoogleSheetsAdapter(TargetSystemAdapter): ...
class SmartsheetAdapter(TargetSystemAdapter): ...
class JiraAdapter(TargetSystemAdapter): ...
```

### Event Types

```python
# Ingestion events
TranscriptUploaded(transcript_id, filename, size)
TranscriptParsed(transcript_id, meeting_id, utterance_count, speaker_count)

# Extraction events
ExtractionStarted(meeting_id)
ActionItemExtracted(meeting_id, item_id, confidence)
DecisionExtracted(meeting_id, decision_id, confidence)
RiskExtracted(meeting_id, risk_id, confidence)
IssueExtracted(meeting_id, issue_id, confidence)
ExtractionCompleted(meeting_id, item_counts)

# Resolution events
IdentityResolutionStarted(meeting_id)
IdentityResolved(item_id, participant_id, confidence, source)
IdentityFlaggedForReview(item_id, candidates)
IdentityManuallyResolved(item_id, participant_id, user_id)

# Output events
MeetingMinutesGenerated(meeting_id, minutes_id)
ItemRoutedToTarget(item_id, target_system, external_id)
OwnerNotified(item_id, participant_id, channel)
```

---

## Non-Functional Requirements

### Performance

| Requirement | Target |
|-------------|--------|
| Transcript upload | < 2 seconds for 10MB file |
| Extraction processing | < 60 seconds for 1-hour meeting transcript |
| Identity resolution | < 10 seconds per meeting |
| Search query response | < 500ms |
| Meeting prep generation | < 30 seconds |

### Reliability

| Requirement | Target |
|-------------|--------|
| System uptime | 99.5% |
| Data durability | No data loss (event sourcing enables replay) |
| Error handling | Graceful degradation; partial results > complete failure |

### Security

| Requirement | Implementation |
|-------------|----------------|
| Authentication | OAuth 2.0 via Google Workspace |
| Authorization | User can only access own meetings/projects |
| Data encryption | TLS in transit, encrypted at rest |
| Audit logging | All actions logged with user, timestamp, details |
| PII handling | Transcript content treated as sensitive; retention policies enforced |

### Scalability

| Requirement | Target |
|-------------|--------|
| Concurrent users (v1) | 1 (single user validation) |
| Meetings per user | 500+ stored |
| Transcript size | Up to 10MB (~3 hour meeting) |

---

## Dependencies & Constraints

### External Dependencies

| Dependency | Purpose | Risk Level |
|------------|---------|------------|
| Zoom | Transcript source | Low — user provides file |
| Google Workspace | Calendar, Docs, Sheets | Medium — API rate limits |
| Slack | Channel membership, notifications | Medium — API rate limits |
| Smartsheet | Target system | Medium — API complexity |
| Anthropic Claude | LLM extraction | Low — mature API |

### Constraints

| Constraint | Rationale |
|------------|-----------|
| Manual transcript upload (v1) | Webhook automation requires Zoom marketplace approval (4-6 weeks) |
| Single user (v1) | Validate concept before multi-tenant complexity |
| Google Sheets as default target | Fastest to implement; Smartsheet/Jira via adapter pattern |
| English language only (v1) | LLM extraction accuracy varies by language |

### Assumptions

- User has Zoom Pro or higher (AI transcription enabled)
- User has Google Workspace account
- User has Slack workspace access
- User maintains project roster in Google Sheets

---

## Release Phases

### Phase 1: Foundation
**Goal:** Establish architectural foundation
**Deliverables:** Event bus, canonical models, event store, FastAPI skeleton
**Duration:** 1 sprint

### Phase 2: Transcript Ingestion
**Goal:** User can upload and parse transcripts
**Deliverables:** Upload endpoint, VTT/SRT parser, speaker diarization
**Requirements:** ING-01, ING-02, ING-03
**Duration:** 1 sprint

### Phase 3: RAID Extraction
**Goal:** Extract action items, decisions, risks, issues
**Deliverables:** LangGraph extraction agent, structured output prompts, confidence scoring
**Requirements:** EXT-01, EXT-02, EXT-03, EXT-04, EXT-05
**Duration:** 2 sprints

### Phase 4: Identity Resolution
**Goal:** Match names to people
**Deliverables:** Roster adapter, Slack/Calendar integration, human-in-the-loop UI
**Requirements:** IDN-01, IDN-02, IDN-03, IDN-04
**Duration:** 1.5 sprints

### Phase 5: Output Generation
**Goal:** Generate meeting minutes and establish adapters
**Deliverables:** Template engine, target selection UI, Google Sheets adapter
**Requirements:** OUT-01, OUT-02, OUT-05
**Duration:** 1.5 sprints

### Phase 6: System Integration
**Goal:** Route artifacts and notify owners
**Deliverables:** Smartsheet adapter, artifact routing, Slack notifications
**Requirements:** OUT-03, OUT-04
**Duration:** 1.5 sprints

### Phase 7: Cross-Meeting Intelligence
**Goal:** Search and track across meetings
**Deliverables:** Full-text search, open item tracking, item history
**Requirements:** XMT-01, XMT-02
**Duration:** 1.5 sprints

### Phase 8: Meeting Prep
**Goal:** Surface context before meetings
**Deliverables:** Open item surfacing, context retrieval, scheduled delivery
**Requirements:** PRP-01, PRP-02, PRP-03
**Duration:** 1.5 sprints

### Phase 9: Communication Automation
**Goal:** Generate communication artifacts
**Deliverables:** Exec/team status generators, escalation emails, talking points
**Requirements:** COM-01, COM-02, COM-03, COM-04
**Duration:** 1.5 sprints

**Total v1:** ~13 sprints (6-7 months at 2-week sprints)

---

## Out of Scope

### Explicitly Excluded from v1

| Feature | Reason |
|---------|--------|
| Transcription | Zoom provides; commodity feature |
| Recording bots | Complex, not differentiated |
| Video storage | Storage cost, not core value |
| Webhook automation | Requires Zoom marketplace approval |
| Real-time context surfacing | Phase B architecture; v2 feature |
| Email/Slack ingest | Different input modality; v2 feature |
| Voice-to-identity learning | Requires speaker diarization ML; future |
| Multi-tenant deployment | Single user validation first |
| Director/VP rollup views | Requires v1 foundation |

### Deferred to v2

| Feature | Description |
|---------|-------------|
| Webhook automation | Zoom triggers processing automatically |
| Proactive nudging | Alerts for approaching due dates, parked decisions |
| Pattern detection | Cross-project risk and dependency patterns |
| Stakeholder signal tracking | Sentiment and engagement monitoring |
| Decision amnesia prevention | Surface past decisions when topics recur |

---

## Open Questions & Risks

### Open Questions

| Question | Impact | Owner | Target Date |
|----------|--------|-------|-------------|
| Smartsheet API specifics for RAID structure | Phase 6 design | Dev Team | Before Phase 5 |
| Meeting minutes template format | Phase 5 design | Gabe | Before Phase 5 |
| Confidence threshold calibration | Extraction accuracy | Dev Team | During Phase 3 |
| Notification preferences UX | Phase 6 design | Gabe | Before Phase 6 |

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM extraction accuracy below target | Medium | High | Iterative prompt engineering; human-in-the-loop fallback |
| Identity resolution false positives | Medium | High | Conservative confidence thresholds; mandatory review for new names |
| API rate limiting (Slack, Google) | Medium | Medium | Caching, batching, backoff strategies |
| Scope creep from v2 features | High | Medium | Strict phase boundaries; parking lot for ideas |
| Single point of failure on LLM provider | Low | High | Adapter pattern allows provider swap |

---

## Appendices

### A. Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Product Narrative | `docs/PRODUCT_NARRATIVE.md` | Story-driven product overview |
| Feature List | `docs/FEATURE_LIST.md` | Detailed feature descriptions |
| Project Context | `.planning/PROJECT.md` | Core value, constraints, decisions |
| Requirements | `.planning/REQUIREMENTS.md` | Requirement IDs and traceability |
| Roadmap | `.planning/ROADMAP.md` | Phase details and success criteria |
| Stack Research | `.planning/research/STACK.md` | Technology recommendations |
| Architecture Research | `.planning/research/ARCHITECTURE.md` | System design patterns |
| Feature Research | `.planning/research/FEATURES.md` | Competitive analysis |
| Pitfalls Research | `.planning/research/PITFALLS.md` | Common mistakes to avoid |

### B. Glossary

| Term | Definition |
|------|------------|
| RAID | Risks, Actions, Issues, Decisions — core artifacts extracted from meetings |
| Diarization | Identifying who spoke which utterances in a transcript |
| Canonical Model | Internal data structure that can be exported to multiple formats |
| Adapter Pattern | Design pattern where external systems are accessed through standardized interfaces |
| Event Sourcing | Storing all changes as a sequence of events, enabling replay and audit |
| Human-in-the-Loop | System flags uncertain items for human review rather than guessing |

### C. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-17 | Gabriel Guenette | Initial draft |

---

*Document generated with assistance from Claude Code*
