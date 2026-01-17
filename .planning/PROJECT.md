# TPM Admin Agent

## What This Is

An agentic platform that removes administrative overhead from TPMs by automating meeting intelligence, action tracking, and operational communication. Starting with a Meeting → Execution Agent that extracts action items, decisions, risks, and issues from Zoom transcripts and routes them to systems of record. Built for one TPM initially, architected to scale to teams, directors, and VP-level aggregation.

## Core Value

Convert meeting talk into tracked execution artifacts automatically — so TPMs shift from clerical work to strategic orchestration.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**v1 — Meeting → Execution Agent:**
- [ ] Ingest Zoom meeting transcripts (manual upload initially)
- [ ] Extract action items with owner, due date, description
- [ ] Extract decisions with context and rationale
- [ ] Extract risks with severity and mitigation notes
- [ ] Extract issues with owner and status
- [ ] Resolve identity from names in transcript to project roster
- [ ] Generate meeting minutes from template
- [ ] Write extracted artifacts to Smartsheet
- [ ] Notify owners of assigned action items

**v2 — Expanded Intelligence:**
- [ ] Real-time context surfacing during meetings (Phase B)
- [ ] Proactive nudging: action items approaching due date
- [ ] Proactive nudging: parked decisions not revisited
- [ ] Proactive nudging: risks logged but not mitigated
- [ ] Meeting prep: surface context before meetings start
- [ ] Pattern detection across projects (common dependencies, recurring slips)
- [ ] Stakeholder signal tracking: sentiment shifts, silence detection, escalation language
- [ ] Capacity/load balancing: action item distribution across assignees
- [ ] Decision amnesia prevention: surface past decisions when topics recur
- [ ] Communication automation: draft status updates for different audiences
- [ ] Communication automation: generate escalation emails with facts and ask
- [ ] Communication automation: exec talking points

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
| Smartsheet as v1 target | Focus on one integration done well; Smartsheet is current system of record | — Pending |
| Manual transcript upload for v1 | Reduces complexity; automation is a separate concern | — Pending |
| Multi-agent architecture | Clean separation of concerns; agents testable independently | — Pending |
| Canonical data model from day one | Enables future aggregation, rollups, and system swaps | — Pending |
| Phase A (batch) before Phase B (real-time) | Different architectural beasts; learn from batch before streaming | — Pending |

---
*Last updated: 2025-01-17 after initialization*
