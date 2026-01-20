# TPM Admin Agent

## What This Is

An agentic platform that removes administrative overhead from TPMs by automating meeting intelligence, action tracking, and operational communication. Starting with a Meeting → Execution Agent that extracts action items, decisions, risks, and issues from Zoom transcripts and routes them to systems of record. Built for one TPM initially, architected to scale to teams, directors, and VP-level aggregation.

## Core Value

Convert meeting talk into tracked execution artifacts automatically — so TPMs shift from clerical work to strategic orchestration.

## Requirements

### Validated

**v1.0 — Meeting → Execution Agent (shipped 2026-01-19):**
- ✓ Ingest Zoom meeting transcripts (manual upload) — v1.0
- ✓ Extract action items with owner, due date, description — v1.0
- ✓ Extract decisions with context and rationale — v1.0
- ✓ Extract risks with severity level — v1.0
- ✓ Extract issues with status — v1.0
- ✓ Resolve identity from names in transcript to project roster — v1.0
- ✓ Generate meeting minutes from template — v1.0
- ✓ Write extracted artifacts to Smartsheet — v1.0
- ✓ Notify owners of assigned action items — v1.0
- ✓ Search across past meeting content — v1.0
- ✓ Track open items across multiple meetings — v1.0
- ✓ Surface context before meetings start — v1.0
- ✓ Draft status updates for different audiences — v1.0
- ✓ Generate escalation emails with facts and ask — v1.0
- ✓ Generate exec talking points — v1.0

### Active

**v1.1 — Production Hardening (planned):**
- [ ] Zoom webhook triggers processing automatically
- [ ] Voice-to-identity learning improves over time
- [ ] Proactive nudging: action items approaching due date
- [ ] Proactive nudging: parked decisions not revisited

**v2 — Expanded Intelligence (future):**
- [ ] Real-time context surfacing during meetings
- [ ] Pattern detection across projects
- [ ] Stakeholder signal tracking
- [ ] Capacity/load balancing
- [ ] Decision amnesia prevention

### Out of Scope

- Timeline intelligence (critical path, cascade analysis) — future, not v2
- Relationship/influence mapping — future
- Knowledge graph / full audit trail — future
- Personal effectiveness analysis — future
- Handoff/onboarding document generation — future
- Predictive health scoring — future
- Dependency orchestration across teams — future
- Email/Slack ingest — v2 or later
- Voice-to-identity matching over time — future enhancement

## Context

**The Problem:**
TPMs spend ~20 minutes after each meeting reconstructing what matters — transcribing minutes, extracting action items, risks, decisions, and routing them to the right systems. With 10-15 meetings/day, this is brutal. Zoom AI transcribes but doesn't understand project context, ownership, or systems of record.

**The Vision:**
Operationalize GenAI into repeatable "work completion" loops. The TPM orchestrates agents that handle the clerical work across meeting intelligence, status reporting, risk tracking, and stakeholder communication. Institutional memory becomes queryable. Action capture becomes reliable. Decision hygiene improves.

**Agent Hierarchy (future expansion):**
| Level | Agent | Scope |
|-------|-------|-------|
| IC TPM | TPM Assistant Agent | Individual meetings, projects |
| Director | TPM Director Agent | Consolidates across programs/teams |
| VP | VP TPM Agent | Executive view across BUs, depts |

**Identity Resolution Sources:**
- Project roster spreadsheet (primary for v1)
- Slack channel membership
- Google Calendar meeting attendees
- Voice matching over time (future)

**Integration Landscape:**
- Meeting source: Zoom (transcript, recording)
- Knowledge sources: Google Docs, Slack, Smartsheet, Jira, Google Calendar
- Export targets: Smartsheet (v1), Jira (future), Slack, Google Docs
- Identity: Okta/Ping → Google Workspace → Slack

## Constraints

- **Target system (v1)**: Smartsheet — focus on one integration done well before expanding
- **Ingest method (v1)**: Manual transcript upload — automation comes later
- **User scope (v1)**: Single TPM (Gabe) — prove value before team rollout
- **Architecture**: Must support multi-tenant, hierarchical aggregation from day one
- **Privacy**: Clear data boundaries, audit logging, consent model for enterprise deployment

## Canonical Data Model

Objects that flow through the system:

| Object | Source | Purpose |
|--------|--------|---------|
| Meeting | Transcript + recording | Source of truth for decisions + commitments |
| Action Item | Extracted + accepted | Converts talk into execution |
| Decision | Extracted + confirmed | Prevents decision drift |
| Risk | Detected + logged | Enables proactive mitigation |
| Issue | Detected + logged | Tracks blockers |
| Dependency | Inferred + mapped | Program-level orchestration (future) |
| Artifact | Docs/tickets | Deliverable traceability (future) |
| Message | Email/Slack | Context + intent + signals (v2) |

## Architectural Principles

- **Adapter pattern everywhere**: Every external system behind a clean interface; swap implementations without touching core logic
- **Canonical internal models**: Rich data structures that lose fidelity gracefully when exporting to constrained systems
- **Event-driven core**: All processing flows through typed events; enables replay, audit, and future expansion
- **Zoom as transcript authority**: System adds intelligence, doesn't duplicate storage
- **Multi-agent scaffolding**: Specialized agents (note-taker, task-assigner, summarizer) composed together
- **Hierarchy-aware data**: Ownership and grouping metadata from day one for future rollup views

## Success Metrics

- Time from meeting end to action items in Smartsheet: < 5 minutes
- Action item extraction accuracy: > 90% recall, > 80% precision
- Owner resolution rate: > 85% automatically matched
- User intervention required: < 2 minutes of cleanup per meeting

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Smartsheet as v1 target | Focus on one integration done well; Smartsheet is current system of record | ✓ Good — shipped with SmartsheetAdapter |
| Manual transcript upload for v1 | Reduces complexity; automation is a separate concern | ✓ Good — POST /meetings/{id} endpoint |
| Multi-agent architecture | Clean separation of concerns; agents testable independently | ✓ Good — adapters, services, repositories |
| Canonical data model from day one | Enables future aggregation, rollups, and system swaps | ✓ Good — Meeting, ActionItem, Decision, Risk, Issue |
| Phase A (batch) before Phase B (real-time) | Different architectural beasts; learn from batch before streaming | ✓ Good — batch complete, real-time is v2 |
| Event-driven core | All processing flows through typed events | ✓ Good — EventBus, EventStore, projections |
| FTS5 for search | SQLite full-text search for cross-meeting queries | ✓ Good — fast, no external dependencies |
| APScheduler for prep | Lightweight scheduler for meeting prep automation | ✓ Good — 5-min scan interval works |

## Current State

**v1.0 shipped:** 2026-01-19
**Codebase:** 12,435 LOC Python, 769 tests
**Tech stack:** FastAPI, Turso (libSQL), Claude API, APScheduler
**APIs:** 9 routers, 25+ endpoints

---
*Last updated: 2026-01-19 after v1.0 milestone*
