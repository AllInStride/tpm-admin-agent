# Phase 9: Communication Automation - Context

**Gathered:** 2026-01-19
**Status:** Ready for planning

<domain>
## Phase Boundary

System generates communication artifacts for different audiences. Includes exec status updates (COM-01), team status updates (COM-02), escalation emails (COM-03), and exec talking points (COM-04).

</domain>

<decisions>
## Implementation Decisions

### Exec status updates
- Primary focus: decisions + blockers + progress + risks + highlights (comprehensive)
- Length: half page (5-7 bullet points with context)
- Reference teams, not individuals (no specific names)
- Include RAG indicator with breakdown (overall + scope/schedule/risk)
- Blockers framed as: problem + explicit ask from exec
- Time period: since last update (delta tracking)
- Always include "next period" lookahead section
- Source meetings referenced in footnotes
- Both plain text and markdown formats available

### Team status updates
- Full list of action items with owners and due dates
- Much more detailed than exec version
- Meeting notes aggregated (not per-meeting summaries)
- Include "completed items" section to celebrate wins

### Escalation emails
- Structure: Problem-Impact-Ask format
- Urgency: explicit deadline ("Decision needed by [date]")
- Always include options for recipient (A, B, or C)
- Tone: matter-of-fact (facts only, no emotional language)
- Include history/context only when relevant for decision
- Recipients: user specifies, infer from chain, or use templates (all available)
- Source data: links only (no inline citations or attachments)

### Exec talking points
- Format: key bullet points + anticipated Q&A section
- Focus on narrative/story with supporting data when available
- Comprehensive Q&A coverage (risk/concern + resource + other)

### Claude's Discretion
- Exec status tone (direct/confident vs formal)
- Number of talking points based on content volume
- History context depth for escalations

</decisions>

<specifics>
## Specific Ideas

- Exec status should feel like a "no surprises" update — exec knows what they need to know
- Team status is the detailed record — nothing should be lost
- Escalations are decision requests, not complaints
- Talking points prepare exec to defend/explain the project

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-communication-automation*
*Context gathered: 2026-01-19*
