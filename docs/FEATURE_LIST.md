# TPM Admin Agent — Feature List

Complete inventory of features across all release horizons.

---

## v1 Features

Core meeting intelligence and execution routing. The minimum viable product that proves the concept and delivers immediate value.

### Ingestion

| ID | Feature | Description |
|----|---------|-------------|
| ING-01 | Upload Zoom transcript | User uploads a Zoom meeting transcript file (VTT, SRT, or TXT format) through a simple interface. No automation yet — manual trigger ensures user control during validation phase. |
| ING-02 | Parse transcript formats | System parses standard transcript formats (VTT with timestamps, SRT with speaker labels, plain text). Extracts utterances, timestamps, and speaker identifiers into canonical internal structure. |
| ING-03 | Speaker diarization | System identifies who said what by parsing speaker labels from transcript. Maps speaker turns to enable attribution of action items, decisions, and other artifacts to specific participants. |

### Extraction

| ID | Feature | Description |
|----|---------|-------------|
| EXT-01 | Action item extraction | AI extracts action items from meeting dialogue. Captures: task description, assigned owner (name as spoken), due date (explicit or inferred), and source quote from transcript. Handles both explicit assignments ("John will do X by Friday") and implicit commitments ("I'll follow up on that"). |
| EXT-02 | Decision extraction | AI identifies decisions made during the meeting. Captures: what was decided, alternatives considered (if discussed), rationale, and participants involved. Prevents "decision drift" by creating auditable record. |
| EXT-03 | Risk detection | AI identifies risks surfaced in discussion. Captures: risk description, severity level (high/medium/low), potential impact, and any mitigation discussed. Flags risks that need tracking even if not explicitly called out as such. |
| EXT-04 | Issue tracking | AI identifies blockers and issues raised. Captures: issue description, current status, owner (if assigned), and dependencies. Distinguishes between risks (potential problems) and issues (current problems). |
| EXT-05 | Confidence scoring | Every extraction includes a confidence score (0-100%). Low-confidence items are flagged for human review. Enables users to trust high-confidence extractions while focusing attention on ambiguous ones. Threshold configurable per user. |

### Identity Resolution

| ID | Feature | Description |
|----|---------|-------------|
| IDN-01 | Roster spreadsheet lookup | Primary identity source. User provides project roster spreadsheet with names, emails, roles. System matches names spoken in transcript to roster entries using fuzzy matching (handles "John" → "John Smith", nicknames, etc.). |
| IDN-02 | Slack channel cross-reference | Secondary identity source. System queries Slack channel membership for the project. Helps disambiguate common names ("Which John?") by checking who's actually on the project team. |
| IDN-03 | Calendar attendee cross-reference | Tertiary identity source. System checks Google Calendar invite for the meeting. If "Sarah" is mentioned and only one Sarah was invited, confidence increases. Reduces false positives on common names. |
| IDN-04 | Human review fallback | When identity confidence falls below threshold, system flags for human review rather than guessing. User sees: "John mentioned — did you mean John Smith (Engineering) or John Davis (Product)?" Prevents routing sensitive items to wrong people. |

### Output

| ID | Feature | Description |
|----|---------|-------------|
| OUT-01 | Template-based meeting minutes | System generates meeting minutes following user's template structure. Includes: attendees, agenda items discussed, key discussion points, decisions made, action items, risks/issues, and next steps. Template is configurable per user or per project. |
| OUT-02 | Configurable target system | User selects where extracted artifacts are routed: Google Sheets (default, fastest setup), Smartsheet, or Jira. Selection can be per-project or global default. Adapter pattern ensures adding new targets doesn't require core changes. |
| OUT-03 | Automatic item creation | System creates rows/items in the selected target system. Action items become tasks with owner, due date, status. Risks become risk register entries. Issues become issue tracker items. Maintains link back to source meeting. |
| OUT-04 | Owner notifications | When action items are assigned, system notifies the owner via their preferred channel (email, Slack). Notification includes: task description, due date, source meeting, and link to full context. Reduces "I didn't know I had that" syndrome. |
| OUT-05 | Adapter pattern architecture | All external integrations go through adapter interfaces. Core system works with canonical models; adapters translate to/from external system formats. Enables swapping Smartsheet for Jira without touching extraction logic. Future-proofs for new integrations. |

### Cross-Meeting Intelligence

| ID | Feature | Description |
|----|---------|-------------|
| XMT-01 | Search past meetings | User can query across all processed meetings. Natural language search: "What did we decide about the API redesign?" or "Show me all action items assigned to Sarah." Returns relevant excerpts with meeting source and date. |
| XMT-02 | Open item tracking | System maintains a running list of open items across meetings. Shows: items created, items completed, items overdue, items discussed but not resolved. Enables continuity across recurring meetings ("Last time we said X — did that happen?"). |

### Meeting Prep

| ID | Feature | Description |
|----|---------|-------------|
| PRP-01 | Previous meeting open items | Before a recurring meeting, system compiles: open action items from previous meetings with same attendees, unresolved issues, decisions that need follow-up. User sees what's still hanging before walking in. |
| PRP-02 | Relevant context surfacing | System queries connected sources (Google Docs, Slack) for content related to meeting agenda or attendees. Surfaces: recent doc updates, Slack threads on relevant topics, related decisions from other meetings. User walks in informed. |
| PRP-03 | Timed prep delivery | System delivers prep summary 10 minutes before meeting start (configurable). Arrives via email or Slack. User doesn't need to remember to check — context arrives automatically at the right moment. |

### Communication Automation

| ID | Feature | Description |
|----|---------|-------------|
| COM-01 | Exec status update draft | System generates status update formatted for executive audience: high-level progress, key risks, blockers needing escalation, asks. Bullet points, no jargon, focused on decisions needed. User reviews and sends. |
| COM-02 | Team status update draft | System generates detailed status update for team: task-level progress, technical details, dependencies, next steps. More granular than exec version. Same source data, different lens. |
| COM-03 | Escalation email generation | When a risk or issue needs escalation, system drafts the email: facts (what happened), impact (why it matters), ask (what you need). Professional tone, no emotion. User reviews before sending. |
| COM-04 | Exec talking points | Before an exec review, system generates talking points: key messages, anticipated questions with suggested answers, risks to highlight, wins to mention. User walks in prepared, not scrambling. |

---

## v2 Candidates

Features planned for the second release. Builds on v1 foundation to add proactive intelligence and automation.

| Feature | Description |
|---------|-------------|
| **Webhook automation** | Zoom automatically triggers processing when transcript is ready. No manual upload required. Uses Zoom Server-to-Server OAuth and `recording.transcript_completed` webhook. Requires Zoom marketplace app approval (4-6 week process). |
| **Real-time context surfacing** | Phase B architecture. System runs parallel to live Zoom meeting and surfaces context cards as topics arise: "Here's the PRD for that feature" / "Last meeting you decided X." Requires Zoom RTMS (Real-Time Media Stream) integration. |
| **Proactive nudging** | System monitors timelines and sends alerts: action items approaching due date with no update, decisions that were "parked" N meetings ago and never revisited, risks logged but with no mitigation plan. Reduces things falling through cracks. |
| **Pattern detection** | AI analyzes across all projects to identify patterns: "Three of your projects have dependencies on Platform team and they're all slipping" / "This risk pattern appeared in Project X last quarter — here's how it played out." Cross-project intelligence. |
| **Stakeholder signal tracking** | AI monitors email and Slack for signals: sentiment shifts in threads, stakeholders going quiet (often a leading indicator), escalation language appearing. Early warning system for relationship issues. |
| **Capacity/load balancing** | System tracks action item distribution across team members. Alerts when someone is overloaded: "John has 14 open items across 4 projects, Maria has 3." Suggests reassignment when appropriate. |
| **Decision amnesia prevention** | When a topic is being discussed that was previously decided, system surfaces the past decision: "You're discussing X again — you decided Y on [date], here's the rationale." Prevents relitigating settled issues. |
| **Email/Slack ingest** | Expand input sources beyond meetings. Process email threads and Slack conversations to extract action items, decisions, risks. Same extraction logic, different input adapter. |
| **Voice-to-identity learning** | System learns to associate voices with identities over time. After processing multiple meetings, can identify speakers even without explicit labels in transcript. Improves diarization accuracy. |

---

## Future Features (Not Prioritized for v2)

Long-term vision features. Will be evaluated after v2 based on user feedback and market needs.

| Feature | Description |
|---------|-------------|
| **Timeline intelligence** | Critical path analysis that updates as things slip. "If X slips 2 days, here's the cascade effect on launch date." Requires integration with project schedules and dependency mapping. |
| **Relationship/influence mapping** | AI maps who actually makes decisions (vs. who's nominally responsible), communication patterns, influence networks. "To unblock X, you need buy-in from Y and Z." Organizational intelligence. |
| **Knowledge graph / audit trail** | Full context chain for any decision or artifact. "Why did we decide X?" returns the meeting, attendees, discussion, alternatives considered, and downstream impacts. Complete institutional memory. |
| **Personal effectiveness analysis** | Analyzes user's time allocation: "You spend 40% of meeting time on Project A which is 10% of your portfolio priority." Identifies meetings that could be async. Suggests optimization. |
| **Handoff/onboarding generation** | Auto-generates project context packages for new team members or exec sponsors. "Here's everything you need to know about Project X in 5 minutes." Reduces onboarding burden. |
| **Predictive health scoring** | ML model predicts project health based on leading indicators: meeting cadence, action item completion rate, decision velocity, risk accumulation. "Projects with this pattern ship on time 80% of the time." |
| **Dependency orchestration** | Cross-team commitment tracking. "Platform team owes you 3 things across 4 projects — here's the consolidated view." External team SLA tracking and alerting. |
| **TPM Director Agent** | Aggregates intelligence across multiple TPMs' projects. Director sees: rolled-up risks, cross-team dependencies, resource conflicts, escalation candidates. Hierarchy-aware views. |
| **VP TPM Agent** | Executive-level aggregation across business units. VP sees: portfolio health, strategic risk themes, resource allocation patterns, org-wide blockers. Configurable grouping (by BU, program, team). |

---

## Out of Scope (Not Building)

Features explicitly excluded from the product vision.

| Feature | Reason |
|---------|--------|
| **Transcription** | Zoom and other meeting platforms provide transcription. This is a commodity feature with no differentiation. Our value is in extraction and intelligence, not capture. |
| **Recording bots** | Building bots that join meetings to record adds complexity and user friction. Zoom native recording is sufficient. Focus engineering effort on intelligence layer. |
| **Video storage** | Storing meeting recordings creates storage cost and compliance burden. Zoom remains the source of truth for recordings. We store extracted artifacts, not raw media. |
| **Calendar/scheduling** | Meeting scheduling is an adjacent domain with strong incumbents (Calendly, etc.). Not core to TPM administrative burden. Integrate with calendars; don't replace them. |
| **CRM features** | Customer relationship management is a different workflow. TPMs manage projects and programs, not sales pipelines. Stay focused on TPM-specific value. |
| **Sentiment analysis** | General sentiment analysis on meeting content has low signal-to-noise ratio. Stakeholder signal tracking (v2) is more targeted — looks for specific escalation patterns, not general "positive/negative" scores. |

---

## Feature Count Summary

| Category | Count |
|----------|-------|
| v1 Features | 22 |
| v2 Candidates | 9 |
| Future Features | 9 |
| Out of Scope | 6 |
| **Total Defined** | **46** |

---

*Last updated: 2025-01-17*
