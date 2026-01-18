# Requirements: TPM Admin Agent

**Defined:** 2025-01-17
**Core Value:** Convert meeting talk into tracked execution artifacts automatically — so TPMs shift from clerical work to strategic orchestration.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Ingestion

- [x] **ING-01**: User can upload Zoom transcript file
- [x] **ING-02**: System parses VTT/SRT transcript formats
- [x] **ING-03**: System identifies speakers (diarization)

### Extraction

- [x] **EXT-01**: System extracts action items with owner, due date, description
- [x] **EXT-02**: System extracts decisions with context and rationale
- [x] **EXT-03**: System extracts risks with severity level
- [x] **EXT-04**: System extracts issues with status
- [x] **EXT-05**: System provides confidence score for each extraction

### Identity Resolution

- [x] **IDN-01**: System matches names to project roster spreadsheet
- [x] **IDN-02**: System cross-references Slack channel membership
- [x] **IDN-03**: System cross-references Google Calendar attendees
- [x] **IDN-04**: System flags low-confidence matches for human review

### Output

- [ ] **OUT-01**: System generates meeting minutes from template
- [ ] **OUT-02**: User can select target system (Google Sheets, Smartsheet, Jira)
- [ ] **OUT-03**: System creates rows/items in selected target for action items, risks, issues
- [ ] **OUT-04**: System notifies owners of assigned items
- [ ] **OUT-05**: Architecture uses adapter pattern for integrations

### Cross-Meeting Intelligence

- [ ] **XMT-01**: User can search across past meeting content
- [ ] **XMT-02**: System tracks open items across multiple meetings

### Meeting Prep

- [ ] **PRP-01**: System surfaces open items from previous meetings before meeting starts
- [ ] **PRP-02**: System surfaces relevant context from docs/Slack related to meeting agenda
- [ ] **PRP-03**: System delivers prep summary 10 minutes before meeting

### Communication Automation

- [ ] **COM-01**: System drafts status updates formatted for exec audience
- [ ] **COM-02**: System drafts status updates formatted for team detail
- [ ] **COM-03**: System generates escalation emails with facts, impact, and ask
- [ ] **COM-04**: System generates exec talking points for reviews

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Automation

- **AUT-01**: Zoom webhook triggers processing automatically (no manual upload)
- **AUT-02**: Voice-to-identity learning improves over time

### Real-Time Intelligence

- **RTI-01**: System surfaces context cards during live meetings
- **RTI-02**: System shows running action item list during meeting

### Proactive Intelligence

- **PRO-01**: System alerts on action items approaching due date
- **PRO-02**: System alerts on parked decisions not revisited
- **PRO-03**: System alerts on risks logged without mitigation
- **PRO-04**: System detects patterns across projects
- **PRO-05**: System tracks stakeholder signals (sentiment, silence, escalation language)
- **PRO-06**: System tracks capacity/load across assignees
- **PRO-07**: System prevents decision amnesia by surfacing past decisions

### Extended Ingest

- **EXI-01**: System processes email threads for extraction
- **EXI-02**: System processes Slack conversations for extraction

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Transcription | Zoom provides; commodity feature |
| Recording bots | Complex, not differentiated |
| Video storage | Storage cost, not core value |
| Calendar/scheduling | Adjacent domain |
| CRM features | Not TPM workflow |
| Sentiment analysis | Low signal-to-noise for TPM use case |
| Timeline intelligence | Future, not v2 |
| Relationship mapping | Future, not v2 |
| Predictive health scoring | Future, not v2 |
| Handoff/onboarding generation | Future, not v2 |
| TPM Director/VP Agents | Future, requires v1 foundation |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ING-01 | Phase 2 | Complete |
| ING-02 | Phase 2 | Complete |
| ING-03 | Phase 2 | Complete |
| EXT-01 | Phase 3 | Complete |
| EXT-02 | Phase 3 | Complete |
| EXT-03 | Phase 3 | Complete |
| EXT-04 | Phase 3 | Complete |
| EXT-05 | Phase 3 | Complete |
| IDN-01 | Phase 4 | Complete |
| IDN-02 | Phase 4 | Complete |
| IDN-03 | Phase 4 | Complete |
| IDN-04 | Phase 4 | Complete |
| OUT-01 | Phase 5 | Pending |
| OUT-02 | Phase 5 | Pending |
| OUT-03 | Phase 6 | Pending |
| OUT-04 | Phase 6 | Pending |
| OUT-05 | Phase 5 | Pending |
| XMT-01 | Phase 7 | Pending |
| XMT-02 | Phase 7 | Pending |
| PRP-01 | Phase 8 | Pending |
| PRP-02 | Phase 8 | Pending |
| PRP-03 | Phase 8 | Pending |
| COM-01 | Phase 9 | Pending |
| COM-02 | Phase 9 | Pending |
| COM-03 | Phase 9 | Pending |
| COM-04 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2025-01-17*
*Last updated: 2025-01-17 after roadmap creation*
