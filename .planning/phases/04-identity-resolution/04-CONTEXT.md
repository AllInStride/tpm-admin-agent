# Phase 4: Identity Resolution - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve names mentioned in transcripts to actual people in project roster. Match against roster spreadsheet, Slack channel membership, and Google Calendar attendees. Flag low-confidence matches (<85%) for human review. Include all Calendar attendees (not just speakers).

</domain>

<decisions>
## Implementation Decisions

### Name Matching Logic
- AI-assisted matching using LLM to infer likely matches (e.g., "JSmith" → "John Smith")
- 85% confidence threshold for auto-accepting matches (conservative)
- Unmatched names block processing until human provides mapping
- Persist learned mappings: when user corrects "Johnny" → "John Smith", remember for next time
- Include full attendee list from Google Calendar (not just transcript speakers)
- Email address is the unique identifier across all systems
- Present partial matches as top match with confidence score (e.g., "John Smith (87%)")

### External Participants
- Auto-add to roster when found in Calendar but not in project roster
- Mark as "external" for PM review
- PM confirms if person should be on project team

### Data Source Priority
- Roster is canonical truth — never overridden by other sources
- Slack and Calendar used for verification (boost confidence when sources agree)
- Cannot exceed 85% confidence without verification from second source
- Single-source matches (roster only) proceed but capped at 85%

### Human Review UX
- Review appears inline in extraction results (not separate queue)
- Human-readable "Review needed" summary with context in API response
- Correction endpoint: POST with item ID + correct person → updates item and learns mapping
- Unreviewed items block downstream processing (can't push to Smartsheet until all owners confirmed)
- Inline confirmation when user confirms match ("Confirmed: John Smith")
- Reject triggers searchable roster list to pick correct person
- Unreviewed items expire after 7 days → marked as "unresolved"
- Daily summary notification: "You have X items pending review"

### Roster Format
- Google Sheet (MCP access available)
- Required columns: Name, Email, Slack handle, Role
- Optional column: Aliases (comma-separated nicknames like "Bob, Bobby, Robert")
- Per-project rosters (each meeting references specific project roster)
- Meeting specifies roster via explicit parameter when uploading transcript
- Live sync — always read from Google Sheet, changes apply immediately
- Best effort on malformed data — use what's available, warn about missing
- Provide Google Sheet template with correct columns and example data

### Claude's Discretion
- Exact LLM prompts for name matching
- Fuzzy matching algorithm details
- How to structure learned mappings storage
- Daily summary delivery mechanism (email, Slack, or API-driven)

</decisions>

<specifics>
## Specific Ideas

- V1 uses Google Calendar for attendee list; Zoom API/participant report is future enhancement
- Blocking on unresolved owners ensures data quality before Smartsheet sync
- 7-day expiry prevents review queue from growing indefinitely

</specifics>

<deferred>
## Deferred Ideas

- Zoom API integration for participant list (more accurate than Calendar)
- Zoom meeting report CSV upload as manual alternative
- Calendar-based automatic roster selection (match meeting to project without explicit parameter)

</deferred>

---

*Phase: 04-identity-resolution*
*Context gathered: 2026-01-18*
