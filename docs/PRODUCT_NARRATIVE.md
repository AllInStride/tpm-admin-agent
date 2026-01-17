# TPM Admin Agent — Product Narrative

## The Problem We're Solving

A Technical Program Manager walks out of their fourth meeting of the day. In that meeting, twelve action items were assigned, two critical decisions were made, a risk was surfaced about a vendor dependency, and someone flagged an issue with the API integration that's blocking three teams.

None of that is written down anywhere useful yet.

The TPM opens their laptop, pulls up the Zoom recording, and begins the ritual: scrubbing through the transcript, copying action items into a spreadsheet, tagging owners who may or may not respond, reformatting everything for the weekly status update, and hoping they didn't miss the one comment that will blow up next week.

This happens 10-15 times a day. Twenty minutes of reconstruction per meeting. That's 3-5 hours daily spent on clerical work instead of actually driving programs forward.

**Zoom AI transcribes. It doesn't understand.**

It doesn't know your projects, your team roster, your systems of record. It can't tell the difference between "John will handle the API review" (an action item) and "John mentioned the API review last week" (context). It doesn't know that "John" is John Smith from Platform Engineering, not John Davis from Product. It definitely can't route that action item to your Smartsheet and ping John on Slack.

The TPM Admin Agent fixes this.

---

## What the System Does

### The Core Loop: Meeting → Execution

You finish a meeting. You upload the transcript. The system takes over.

**Extraction**: AI reads the transcript and pulls out the signal from the noise:
- **Action Items**: Who committed to what, by when. "Sarah will send the updated requirements by Friday" becomes a tracked task with Sarah as owner, Friday as due date, and the exact quote from the meeting as context.
- **Decisions**: What was decided and why. "We agreed to go with Option B because it reduces the dependency on Platform team" becomes a logged decision with rationale, so three months from now when someone asks "why did we choose Option B?" the answer exists.
- **Risks**: What could go wrong. "If the vendor delays past March 15, we're in trouble" becomes a tracked risk with severity and the context of who raised it.
- **Issues**: What's already wrong. "The API integration is blocked because we don't have access to the staging environment" becomes a tracked issue with status and owner.

Every extraction includes a confidence score. High confidence items flow automatically. Low confidence items get flagged for your review. The system learns your patterns over time.

**Identity Resolution**: The transcript says "John will handle it." But which John? The system checks:
1. Your project roster spreadsheet
2. Who's in the project's Slack channel
3. Who was actually in the meeting (Calendar invite)

If it's confident, it maps "John" to john.smith@company.com. If it's not sure, it asks you: "Did you mean John Smith (Engineering) or John Davis (Product)?" No more action items disappearing because they were assigned to a name that doesn't exist in any system.

**Output**: The system generates meeting minutes from your template — the format you already use, not some generic structure. Then it routes the artifacts:
- Action items → Google Sheets (or Smartsheet, or Jira — your choice)
- Risks → Your risk register
- Issues → Your issue tracker
- Owners get pinged on Slack with their assignments

**Time from meeting end to action items in your system: under 5 minutes.** Not 20 minutes of manual work. Five minutes of automated processing while you're already in your next meeting.

---

### Beyond Single Meetings: Cross-Meeting Intelligence

Individual meetings are the starting point. The real leverage comes from connecting them.

**Search Across Everything**: "What did we decide about the authentication approach?" You don't remember which meeting it was. You don't need to. The system searches across all your meetings and surfaces the decision, who was there, what the alternatives were, and what happened since.

**Open Item Tracking**: That action item from three weeks ago that never got done? The system knows. It tracks items across meetings, shows you what's still open, what's overdue, and what keeps getting pushed. No more items falling through the cracks because they weren't on any dashboard.

**Meeting Prep That Actually Helps**: Ten minutes before your recurring Project Alpha standup, you get a summary:
- Open action items from the last meeting
- Risks that haven't been mitigated
- Decisions that need follow-up
- Relevant updates from Slack and Docs since last time

You walk into the meeting knowing exactly where things stand, not scrambling to remember what happened last week.

---

### Communication Automation: Stop Rewriting the Same Updates

You know the drill. You have the same information, but you need to present it three different ways:
- **Exec summary**: High-level, focused on decisions needed and blockers
- **Team detail**: Full action item list, who's doing what, dependencies
- **Escalation email**: The facts, the impact, the ask — professional and precise

The system drafts all of these from the same source data. Same meeting, same action items, different audiences. You review, tweak if needed, and send. You're not spending 30 minutes reformatting the same information for different stakeholders.

Before an exec review, you get talking points: key messages to land, anticipated questions with suggested answers, risks to highlight, wins to mention. You walk in prepared.

---

## The Architecture: Built to Last

This isn't a script that will break next month. It's a platform built with enterprise principles:

**Canonical Data Model**: Everything flows through normalized objects — Meeting, ActionItem, Decision, Risk, Issue, Participant. Messy transcript input becomes clean, structured data that can be rendered into any format.

**Adapter Pattern**: Smartsheet today, Jira tomorrow, whatever comes next. Every external system sits behind a clean interface. Swapping integrations doesn't require rewriting extraction logic.

**Event-Driven Core**: Every action is an event that gets stored. You can replay, audit, debug. When something goes wrong, you can trace exactly what happened.

**Human-in-the-Loop by Design**: AI extracts, humans verify. Confidence thresholds determine what flows automatically vs. what needs review. The system gets better over time, but never makes decisions it shouldn't make alone.

**Privacy-First**: Clear data boundaries. Audit logging. Consent model for enterprise deployment. Meeting content stays secure, with explicit controls over who sees what.

---

## The Hierarchy: IC to VP

This starts with one TPM. But the architecture supports the full hierarchy:

**IC TPM**: Your meetings, your projects, your action items. The core system.

**TPM Director**: Roll up across your team. See which TPMs have overloaded backlogs. Spot cross-project dependencies. Identify risks that appear in multiple programs.

**VP TPM**: Executive view across business units. Portfolio health at a glance. Strategic risk themes. Resource allocation patterns across the org.

Same data, different views. The canonical model supports aggregation from day one.

---

## What This Unlocks

**Institutional memory becomes queryable.** "Why did we make that decision?" has an answer.

**Action capture becomes reliable.** Nothing falls through the cracks because it wasn't written down fast enough.

**Decision hygiene improves.** You stop relitigating settled issues because the decisions are logged with rationale.

**Work can be re-rendered into any format.** Same source, different outputs for different audiences.

**TPM time shifts from clerical to strategic.** You stop being a human middleware between meetings and spreadsheets. You start being the orchestrator who drives programs forward.

---

## The Journey

### v1: Meeting → Execution Agent

The foundation. Upload a transcript, get structured artifacts in your systems.

- Transcript ingestion with speaker identification
- RAID extraction (Risks, Actions, Issues, Decisions)
- Identity resolution across roster, Slack, Calendar
- Template-based meeting minutes
- Google Sheets / Smartsheet / Jira routing
- Owner notifications
- Cross-meeting search and open item tracking
- Meeting prep summaries
- Communication drafts (exec, team, escalation)

**26 requirements. 9 phases. One TPM proving the concept.**

### v2: Proactive Intelligence

The system stops waiting for you to ask and starts telling you what matters.

- Webhook automation (no manual upload)
- Proactive nudging (approaching due dates, parked decisions, unmitigated risks)
- Pattern detection across projects
- Stakeholder signal tracking
- Capacity/load balancing
- Decision amnesia prevention
- Real-time context surfacing during meetings

### Future: The TPM Platform

- Timeline intelligence with cascade analysis
- Relationship and influence mapping
- Full knowledge graph with audit trails
- Predictive health scoring
- Director and VP agents for hierarchy rollups

---

## Success Metrics

How we'll know it's working:

| Metric | Target |
|--------|--------|
| Time from meeting end to action items in system | < 5 minutes |
| Action item extraction accuracy | > 90% recall, > 80% precision |
| Owner resolution rate | > 85% automatically matched |
| User intervention required | < 2 minutes cleanup per meeting |

---

## The Bottom Line

TPMs are drowning in administrative work. Every meeting generates artifacts that need to be extracted, formatted, routed, and tracked. Today, that's manual labor — slow, error-prone, and soul-crushing at scale.

The TPM Admin Agent turns meetings into execution automatically. You stop being a transcription service and start being a strategic driver.

**The meeting ends. The work begins. Automatically.**

---

*TPM Admin Agent — Convert talk into tracked execution.*
