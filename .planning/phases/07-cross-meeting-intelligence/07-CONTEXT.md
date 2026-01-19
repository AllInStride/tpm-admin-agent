# Phase 7: Cross-Meeting Intelligence - Context

**Gathered:** 2026-01-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable users to search across meeting history and track items that span multiple meetings. Full-text search across transcripts and RAID items, open item dashboard, and item history showing meeting linkage. Real-time alerts and scheduled reports are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Search Interface
- Search both transcripts and RAID items
- Simple keyword search by default, structured filter syntax available (e.g., type:action owner:john)
- Results grouped by type (transcripts separate from RAID items)

### Open Item Tracking
- "Open" = not closed AND has upcoming/past due date
- Dashboard view AND API endpoint for open items
- User can toggle between groupings: due date, owner, project
- Track all RAID types (actions, risks, issues, decisions)
- Visual highlight for overdue items (color/badge)
- Show summary counts by category (overdue, upcoming, etc.)
- Inline close action from dashboard

### Item History Display
- Vertical timeline showing meeting mentions
- Each entry shows what changed (new, updated, mentioned)
- Duplicates across meetings: prompt user to decide (merge/link/other)
- Navigation: links to both transcript and minutes

### Data Retention
- Search all historical meetings (no time limit)
- Manual archive capability (user decides what to archive)
- Archived meetings still searchable by default
- No storage limits — handle scale at infrastructure level

### Claude's Discretion
- Search result snippet format and highlighting
- Filter options for open items dashboard
- Search index implementation (SQLite FTS vs. dedicated search)
- Duplicate detection algorithm

</decisions>

<specifics>
## Specific Ideas

- Dashboard should feel like a TPM command center — see everything at a glance
- Timeline view lets TPMs trace an item's journey across meetings
- User choice on duplicate handling respects that TPMs know their context better than the system

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-cross-meeting-intelligence*
*Context gathered: 2026-01-19*
