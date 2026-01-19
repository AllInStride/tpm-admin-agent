# Phase 5: Output Generation - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate meeting minutes from extracted RAID artifacts using customizable templates. Establish adapter pattern for target systems. User selects destination per project. Adapters handle Google Sheets and Google Drive for v1; Smartsheet integration is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Minutes Format
- Full RAID breakdown: separate sections for Decisions, Actions, Risks, Issues (D-A-R-I order)
- Extracted items only, but include metadata link to source quotes
- Attendees listed as Names + roles: "John Smith (PM)"
- Full metadata header: date, time, duration, attendees, project, meeting series
- Output formats: Markdown + HTML for v1 (PDF, Google Doc deferred)
- Low-confidence items marked with visual indicator in output
- Action items without due date show "TBD" placeholder and flag assignee/TPM to provide
- Decisions include: decision + rationale + alternatives considered
- Risks/Issues include: description, severity, owner, mitigation plan (if mentioned)
- Auto-generated "Next Steps" summary section (top 3-5 actions)
- No timestamps in output (clean view)

### Template Customization
- Per-project templates (each project can have its own)
- Templates stored in Google Drive as editable docs
- Simple placeholder syntax: {{meeting_date}}, {{attendees}}, {{action_items}}
- Fall back to system default if project has no custom template
- Preview optional: can preview before sending, but also one-click send
- Full edit capability: generate → edit in UI → send
- Persist edits: edited version becomes official record

### Target System Selection
- Per-project default (project config specifies targets)
- v1 targets: Google Sheets, Google Drive (Smartsheet is Phase 6)
- Configurable routing:
  - Minutes → Google Drive
  - RAID items → Google Sheets (for tracking)
  - Project plan updates → Smartsheet (Phase 6)

### Adapter Behavior
- Failure handling: queue for later, process async
- Alert user when retries exhausted (Slack notification)
- Retry queue duration: configurable (Claude decides default)
- Invalid credentials: queue items and alert user to fix auth
- Upsert by internal UUID (stored as hidden column in target)
- Batch writes for performance (fewer API calls)
- Dry-run mode for testing ("simulate" flag)
- Full audit log: what was written, when, where, by whom
- Audit logs: local logs for now, external service later

### Claude's Discretion
- Default retry queue duration
- Exact placeholder variable names
- Audit log format and retention
- Batch size for write operations
- HTML template styling

</decisions>

<specifics>
## Specific Ideas

- D-A-R-I section order (Decisions first = strategic, then Actions = tactical)
- Source quotes available as metadata links, not inline text
- "TBD" due dates trigger follow-up workflow (flag assignee or escalate to TPM)
- Three-destination pattern: Drive for docs, Sheets for tracking, Smartsheet for project plan

</specifics>

<deferred>
## Deferred Ideas

- PDF and Google Doc export formats — future enhancement
- Per-meeting-type templates (standup vs steering vs review)
- Jinja-style template conditionals and loops
- External logging service integration (Datadog, etc.)

</deferred>

---

*Phase: 05-output-generation*
*Context gathered: 2026-01-18*
