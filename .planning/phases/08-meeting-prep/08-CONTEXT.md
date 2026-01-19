# Phase 8: Meeting Prep - Context

**Gathered:** 2026-01-19
**Status:** Ready for planning

<domain>
## Phase Boundary

System proactively surfaces relevant context before meetings start. Includes open items from previous meetings with same attendees (PRP-01), relevant context from docs/Slack related to meeting agenda (PRP-02), and delivers prep summary 10 minutes before meeting start time (PRP-03).

</domain>

<decisions>
## Implementation Decisions

### Open item surfacing
- Match items by BOTH attendee overlap AND project association
- Look back 90 days for related open items
- Overdue items flagged prominently at top with visual indicator
- Group items by type (Actions, then Risks, then Issues, then Decisions)
- Include all RAID types (actions, decisions, risks, issues)
- Maximum 10 items in summary
- No distinction between user-owned vs. others' items

### Context retrieval
- Search Docs + Slack for meeting context
- Context scoped to project only, focusing on previous meetings in series
- Meeting types (SteerCo, Project Team, DSU) inferred from title with manual override
- Reference last 5 meetings in the series
- Slack: last 7 days from project channel
- Docs identified by: linked in previous meetings, shared with attendees, OR tagged to project
- Include brief summary for docs (title, link, 1-2 sentence summary)
- Prioritize recently updated docs (last 7 days ranked higher)

### Prep delivery timing
- Delivery via Slack DM or email (user configurable)
- Lead time configurable (default 10 minutes)
- Send prep even if calendar changes with short notice

### Summary format
- Scannable (fits on one screen without scrolling)
- Always include 2-3 suggested talking points
- Open items as compact list: title + owner + due date, one line each
- Link to most recent meeting notes
- Professional/formal tone
- Include "View full prep" link for detailed version
- Highlight items that are new since last meeting in series
- Include attendee names with their project roles

### Claude's Discretion
- Prioritization logic when >10 items
- Best triggering mechanism (calendar poll vs webhook)
- Overall structure of prep summary
- Number of docs/resources to include based on relevance
- Slack summary approach (threads vs highlights)

</decisions>

<specifics>
## Specific Ideas

- Meeting types matter: SteerCo, Project Team, DSU should be identifiable
- Focus on meeting series context rather than broad keyword search
- "What's new since last time" is valuable for recurring meetings

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-meeting-prep*
*Context gathered: 2026-01-19*
