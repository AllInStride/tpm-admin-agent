# Phase 6: System Integration - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect extracted RAID artifacts to external systems. Write items to Smartsheet for tracking and notify owners via Slack. This phase focuses on the write/push integration — reading from external systems is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Smartsheet Structure
- One unified RAID sheet per project (all item types together)
- Prompt user to select sheet on first use, save in project settings
- Auto-create sheet with correct columns if missing
- User specifies folder location during initial setup
- Standard TPM columns: Type, Title, Owner, Status, Due Date, Source Meeting, Created Date, Confidence
- Status options vary by type:
  - Actions: Open / In Progress / Done
  - Risks: Identified / Mitigated / Closed
  - Issues: Open / Investigating / Resolved
  - Decisions: Documented
- Link to Drive-hosted meeting minutes in Source Meeting column
- Include confidence score as visible column for transparency
- Store Smartsheet row IDs per item (enables future updates)
- Sort by meeting date (most recent at top)

### Notification Behavior
- DM directly to assigned owner via Slack
- Notify on new assignment + reminder 3 days before due date + when overdue
- Actions only (they have owners and due dates)
- Essential message content: item title, due date, Smartsheet link
- Plain text message with links (no interactive buttons)
- Send immediately as each item is processed
- No muting capability — always notify
- Full audit log of all notifications sent

### Conflict Handling
- Create new row each time, link to detected duplicates
- If owner unresolved: write to Smartsheet, notify project lead as fallback
- Smartsheet write failures: queue for later retry
- Slack notification failures: queue for retry

### Rate Limiting
- Chunk items into batches for Smartsheet API calls
- On rate limit: queue remaining items, notify user of delay
- Show progress indicator during writes ("Writing 5/12 items...")
- No cap on items per meeting — process all

### Claude's Discretion
- Exact batch size for Smartsheet API
- Duplicate detection algorithm
- Retry timing and backoff strategy
- Queue persistence implementation

</decisions>

<specifics>
## Specific Ideas

- Per-project sheet keeps different workstreams isolated
- Confidence column lets TPMs quickly spot items needing human review
- 3-day reminder window gives enough time to act without being annoying
- Project lead fallback ensures no action items fall through the cracks

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-system-integration*
*Context gathered: 2026-01-18*
