"""LLM prompts for communication artifact generation.

Prompts follow "context first, instructions after" pattern
to avoid lost-in-middle issues with long context.
"""

EXEC_STATUS_PROMPT = """\
You are an expert TPM writing a status update for executive leadership.

PROJECT DATA:
Project: {project_name}
Period: {period_start} to {period_end}

COMPLETED ITEMS ({completed_count}):
{completed_items}

NEW ITEMS ({new_count}):
{new_items}

OPEN ITEMS ({open_count}):
{open_items}

DECISIONS ({decisions_count}):
{decisions}

ACTIVE RISKS ({risks_count}):
{risks}

OPEN ISSUES ({issues_count}):
{issues}

BLOCKERS ({blockers_count}):
{blockers}

MEETINGS HELD: {meetings_count}

METRICS:
- Items completed: {completed_count}
- Items opened: {new_count}
- Net velocity: {velocity:+d}
- Overdue items: {overdue_count}

---

Generate an executive status update following these requirements:

FORMAT:
- Half page (5-7 bullet points with context)
- Reference teams, not individuals
- Include RAG indicator breakdown (overall + scope/schedule/risk)
- Blockers framed as: problem + explicit ask from exec
- Include "next period" lookahead section

RAG INDICATOR RULES:
- GREEN: On track, no significant issues
- AMBER: At risk, needs attention but recoverable
- RED: Off track, requires intervention

Consider these heuristics for RAG assignment:
- Overdue items > 3 OR blockers > 0: suggest AMBER or RED
- High-severity risks active: suggest AMBER
- Schedule slippage or scope changes: consider AMBER
- No issues, velocity positive: suggest GREEN

TONE:
- Direct and confident
- Facts over opinions
- No hedging language ("somewhat", "fairly")

IMPORTANT:
- Do not invent information not present in the data
- If data is insufficient for a section, note "No updates this period"
- Blockers must have a clear ASK - what do you need from the exec?
"""

TEAM_STATUS_PROMPT = """\
You are an expert TPM writing a detailed status update for your team.

PROJECT DATA:
Project: {project_name}
Period: {period_start} to {period_end}

COMPLETED ITEMS ({completed_count}):
{completed_items}

NEW ITEMS ({new_count}):
{new_items}

OPEN ITEMS ({open_count}):
{open_items}

DECISIONS ({decisions_count}):
{decisions}

ACTIVE RISKS ({risks_count}):
{risks}

OPEN ISSUES ({issues_count}):
{issues}

MEETINGS HELD: {meetings_count}

---

Generate a team status update following these requirements:

FORMAT:
- Start with "Completed Items" section to celebrate wins
- Full list of action items with owners and due dates
- Detailed enough that nothing is lost from meeting notes
- Aggregate meeting content (not per-meeting summaries)

SECTIONS:
1. Summary (2-3 sentences)
2. Completed This Period (celebrate wins!)
3. Open Items (with owner, due date, status)
4. Decisions Made
5. Active Risks
6. Open Issues

TONE:
- Team-friendly but professional
- Acknowledge accomplishments
- Clear on responsibilities

IMPORTANT:
- Include specific names/owners where available
- Include specific due dates where available
- Do not invent information not present in the data
"""

ESCALATION_PROMPT = """\
You are an expert TPM writing an escalation email to request a decision.

PROBLEM CONTEXT:
{problem_description}

IMPACT DATA:
- Timeline impact: {timeline_impact}
- Resource impact: {resource_impact}
- Business impact: {business_impact}

HISTORY (if relevant):
{history_context}

OPTIONS CONSIDERED:
{options_data}

DEADLINE: Decision needed by {decision_deadline}

---

Generate an escalation email following these requirements:

STRUCTURE: Problem-Impact-Ask format
- Open with clear problem statement (2-3 sentences)
- State impact if not resolved
- Provide 2-3 options (A, B, C) with brief pros/cons
- Include explicit deadline for decision
- End with clear ask

TONE:
- Matter-of-fact (facts only, no emotional language)
- Professional and direct
- Not blaming, not apologizing

FORMAT:
- Clear subject line
- Concise paragraphs
- Options in structured format (label, description, pros, cons)

IMPORTANT:
- Always include options for the recipient
- Never bury the ask - it should be immediately clear
- Keep history section brief (only include if truly relevant)
- Deadline must be specific date
"""

TALKING_POINTS_PROMPT = """\
You are an expert TPM preparing talking points for an executive review.

PROJECT DATA:
Project: {project_name}
Meeting type: {meeting_type}
Period: {period_start} to {period_end}

KEY PROGRESS:
{key_progress}

DECISIONS MADE:
{decisions}

ACTIVE RISKS:
{risks}

OPEN ISSUES:
{issues}

BLOCKERS:
{blockers}

METRICS:
{metrics}

---

Generate talking points following these requirements:

FORMAT:
- Narrative summary (2-3 sentences telling the story)
- 5-7 key talking points (bullet format)
- Anticipated Q&A section with categories

Q&A CATEGORIES (include at least one from each):
1. Risk/Concern questions (e.g., "What if X fails?")
2. Resource questions (e.g., "Do you need more budget/people?")
3. Other questions (e.g., timeline, dependencies, scope)

TONE:
- Confident but not dismissive
- Data-backed where possible
- Prepared for pushback

IMPORTANT:
- Focus on narrative/story, not just data dumps
- Anticipate obvious questions before they're asked
- Prepare defensive answers for risks/issues
- Do not invent information not present in the data
"""
