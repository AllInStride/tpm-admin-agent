# Domain Pitfalls: TPM Admin Agent

**Domain:** Meeting Intelligence + Multi-Agent Automation + Enterprise Deployment
**Researched:** 2026-01-17
**Confidence:** HIGH (verified against multiple authoritative sources)

---

## Critical Pitfalls

Mistakes that cause rewrites, compliance failures, or project cancellation.

---

### Pitfall 1: Silent Agent Failures

**What goes wrong:** AI agents report success when they've actually failed. A Salesforce production incident in 2025 involved an agent that skipped a required workflow step, reported completion, and the failure only surfaced days later through customer escalation.

**Why it happens:** Agents make non-deterministic decisions. Unlike traditional software with predetermined paths, agents choose between multiple valid approaches. Without explicit success verification, the system can't distinguish "task completed" from "task attempted."

**Consequences:**
- Action items extracted but never routed to Smartsheet
- Identity resolution fails silently (wrong person assigned)
- Days/weeks pass before users notice missing data
- Trust erosion makes the tool unusable

**Prevention:**
1. **Verification loops**: Every agent action must verify its outcome, not just report completion
2. **Observable outputs**: Each step produces verifiable artifacts (not just logs)
3. **Reconciliation jobs**: Periodic checks that transcript count = extraction count = routing count
4. **User feedback channels**: Easy way for users to report "this meeting wasn't processed"

**Detection (early warning signs):**
- "Processing complete" messages without corresponding Smartsheet updates
- Growing delta between meetings attended and items created
- Users asking "did you catch the action item about X?"

**Phase mapping:** Address in Phase 1 (core agent framework). Build verification-first from day one.

---

### Pitfall 2: Consent Compliance Violations

**What goes wrong:** Recording meetings without proper consent violates state wiretapping laws. California, Florida, Pennsylvania, Illinois, and 7 other states require ALL parties to consent. Enterprise deployment across states multiplies exposure.

**Why it happens:**
- Assuming "joining the meeting = consent to AI processing"
- Relying on platform's recording notification as sufficient
- Not tracking which participants are in two-party consent states
- GDPR requires explicit informed consent for specific purposes; blanket "join meeting" consent is insufficient

**Consequences:**
- Criminal penalties (not just civil) in some states
- GDPR fines up to 4% global revenue or EUR 35M
- Employment law violations (NLRA protections for recording labor discussions)
- Project shutdown by legal/compliance

**Prevention:**
1. **Default to two-party consent**: Always notify all participants explicitly
2. **Consent tracking**: Log who consented, when, to what scope
3. **Opt-out mechanism**: Participants can exclude themselves from AI processing
4. **Geographic awareness**: Know participant locations when cross-state/cross-border
5. **Audit trail**: Document consent for compliance review

**Detection (early warning signs):**
- Legal/compliance asking questions about consent flow
- Users in California/Florida expressing surprise at being recorded
- No consent records in audit logs

**Phase mapping:** Must be MVP (Phase 1). Cannot ship without consent handling.

---

### Pitfall 3: Identity Resolution False Positives

**What goes wrong:** "John" in the transcript gets resolved to wrong John in the org. Action item assigned to John Smith (Sales) when it was John Chen (Engineering). Worse: confidential items routed to wrong person.

**Why it happens:**
- Common names create ambiguity
- Context clues insufficient (no department/role context in transcript)
- Nicknames, pronunciation variations, ASR errors
- Over-confident matching without verification threshold

**Consequences:**
- Confidential information leaked to wrong employees
- Tasks assigned to wrong people, never completed
- Trust destruction ("the bot always gets my name wrong")
- Potential compliance violation if sensitive data misrouted

**Prevention:**
1. **Confidence thresholds**: Don't auto-assign below 85% confidence
2. **Human-in-the-loop for ambiguity**: Flag uncertain matches for user confirmation
3. **Context enrichment**: Use meeting attendee list, calendar context, org hierarchy
4. **Feedback loops**: Users correct mistakes, system learns
5. **Privacy firewall**: Confidential/HR-tagged meetings require explicit confirmation

**Detection (early warning signs):**
- Users reporting "wrong John" incidents
- Action items with no follow-through (assigned to confused recipient)
- Growing number of manual corrections

**Phase mapping:** Phase 2 (identity resolution). Build with human-in-the-loop from start; don't ship fully automated.

---

### Pitfall 4: Multi-Agent Coordination Collapse

**What goes wrong:** Research shows multi-agent systems with 10+ tools suffer 2-6x efficiency penalty vs. single agents. Agents duplicate work, leave gaps, or spawn excessive sub-agents.

**Why it happens:**
- Context fragmentation when compute split across agents
- Vague task descriptions lead to duplicated or missed work
- Coordination complexity grows faster than linear with agent count
- Early Anthropic research found agents spawning 50 sub-agents for simple queries

**Consequences:**
- Exponential cost growth (each retry = API cost)
- Cascading failures across agent chain
- Debugging becomes impossible
- Project abandoned due to unreliability

**Prevention:**
1. **Start single-agent**: Prove reliability before adding coordination complexity
2. **45% accuracy threshold**: Research shows multi-agent only helps when single-agent < 45% baseline accuracy
3. **Explicit task decomposition**: Detailed task descriptions prevent overlap
4. **Cost guardrails**: Hard limits on retries, sub-agent spawns, API calls per task
5. **Narrow scope per agent**: Domain-specific agents outperform general-purpose

**Detection (early warning signs):**
- API costs 10x projections
- Same meeting processed multiple times
- Agents stuck in retry loops
- Processing time growing non-linearly

**Phase mapping:** Phase 1 architecture decision. Start with single-agent orchestrator; add specialized agents only when proven necessary.

---

### Pitfall 5: Action Item Extraction Hallucination

**What goes wrong:** LLM extracts action items that weren't actually discussed, or attributes them to wrong people. JSON schema validation ensures format, but not factual accuracy.

**Why it happens:**
- LLMs "fill in blanks" based on statistical patterns when context is ambiguous
- Reflective statements ("we should've started earlier") misinterpreted as commitments
- Overlapping speech creates garbled transcripts
- 68% of remote meetings have 12+ seconds of simultaneous speech per minute

**Consequences:**
- False action items create busy work
- Missed action items let real commitments slip
- Users stop trusting extracted data
- "Garbage in, garbage out" to Smartsheet

**Prevention:**
1. **Confidence scores on every extraction**: Route low-confidence to human review
2. **Grounding requirement**: Action item must have extractable quote from transcript
3. **Commitment language detection**: Train on actual commitment patterns vs. speculation
4. **Validation UI**: Users approve before routing (at least during initial rollout)
5. **Feedback loops**: Track which items users delete/modify

**Detection (early warning signs):**
- Users deleting >20% of extracted items
- Action items with no assignee or vague descriptions
- Items that don't map to any transcript segment

**Phase mapping:** Phase 2 (extraction pipeline). Build with validation UI; don't auto-route until accuracy proven.

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or degraded user experience.

---

### Pitfall 6: Speaker Diarization Errors Cascade

**What goes wrong:** Best-in-class diarization (Pyannote 3.1) has 11-19% error rate on standard benchmarks. Overlapping speech accuracy drops further. When "Speaker 1" and "Speaker 2" are misassigned, identity resolution and action item attribution both fail.

**Why it happens:**
- Overlapping speech remains hardest problem (70% accuracy on overlaps)
- Short utterances harder to attribute than long ones
- Remote meetings with varying audio quality
- ASR and diarization have conflicting optimization objectives

**Consequences:**
- Identity resolution working on garbage input
- Action items attributed to wrong speakers
- Compound errors: 15% diarization error * 10% identity error = significant misattribution

**Prevention:**
1. **Don't over-rely on speaker labels**: Use content + context, not just "Speaker 2 said"
2. **Attendee list grounding**: Cross-reference with known meeting participants
3. **Aggregate confidence**: Track diarization confidence, propagate to downstream
4. **Handle gracefully**: "Someone in the meeting said..." better than wrong attribution

**Detection (early warning signs):**
- Action items consistently attributed to meeting organizer (default fallback)
- Same person identified as multiple speakers in single meeting
- Transcripts showing impossible speaker transitions

**Phase mapping:** Phase 1 (transcript processing). Set expectations; don't promise perfect attribution.

---

### Pitfall 7: Smartsheet Rate Limiting

**What goes wrong:** Smartsheet API limits: 300 requests/minute, file attachments count 10x. Batch processing multiple meetings hits limits, causing failures or delays.

**Why it happens:**
- Not using bulk operations (10 single-row updates vs. 1 bulk update)
- No exponential backoff on 429 errors
- File attachments (meeting recordings) consume quota fast
- Peak processing times (end of day) create spikes

**Consequences:**
- Action items queued indefinitely
- Users see stale Smartsheet data
- Failed updates with no retry = lost data

**Prevention:**
1. **Bulk operations**: Update 10 rows in single request, not 10 requests
2. **Exponential backoff**: Implement proper retry with increasing delays
3. **Queue with rate limiting**: Internal queue that respects Smartsheet limits
4. **Off-peak processing**: Schedule batch operations during low-activity hours
5. **Smartsheet SDK**: Use official SDK which handles rate limiting automatically

**Detection (early warning signs):**
- 429 errors in logs
- Growing queue of pending Smartsheet updates
- Users reporting "items show up hours later"

**Phase mapping:** Phase 3 (Smartsheet routing). Use SDK from start; add monitoring for quota consumption.

---

### Pitfall 8: Meeting Bot Platform Fragmentation

**What goes wrong:** Each platform (Zoom, Teams, Meet) has different APIs, consent flows, and limitations. Zoom lacks real-time audio API, Teams requires Microsoft 365 infrastructure alignment, Meet has no direct recording API.

**Why it happens:**
- Each platform optimized for different use cases
- Enterprise SSO, waiting rooms, password protection add complexity
- Platform updates break integrations
- OAuth scope configurations easy to misconfigure

**Consequences:**
- Bot fails to join certain meeting types
- Inconsistent experience across platforms
- Brittle integrations require constant maintenance
- Users lose trust when "it worked last week"

**Prevention:**
1. **Abstract platform layer**: Don't build platform-specific logic into core
2. **Start single-platform**: Prove value on one platform before multi-platform
3. **Consider Recall.ai**: Third-party abstraction handles platform complexity
4. **Explicit platform support**: Clear documentation of what's supported
5. **Graceful degradation**: If bot can't join, notify user with reason

**Detection (early warning signs):**
- Platform-specific bugs in issue tracker
- "Works on Zoom but not Teams" reports
- Post-platform-update failures

**Phase mapping:** Phase 1 decision: single platform vs. abstraction layer. Don't build multi-platform from scratch.

---

### Pitfall 9: Audit Trail Gaps

**What goes wrong:** SEC Rule 204-2 requires retention of AI-generated outputs, prompts, model versions. EU AI Act treats compliance AI as "high-risk" requiring explainability. Missing audit trails = non-compliant.

**Why it happens:**
- Treating AI like regular software (log exceptions, not decisions)
- Not versioning prompts/models
- Logs retained but not queryable
- Focus on functionality over compliance

**Consequences:**
- Failed compliance audits
- Unable to explain "why did the AI decide X?"
- Regulatory penalties (EU AI Act: up to 7% global revenue)
- Forced to rebuild with compliance baked in

**Prevention:**
1. **Log everything**: Input, output, model version, prompt version, timestamp
2. **Immutable storage**: Tamper-proof audit trail (append-only)
3. **Explainability**: Each decision must be traceable to specific inputs
4. **Retention policy**: Define hot/warm/cold tiers aligned with regulations
5. **Quarterly audits**: Review audit trail completeness regularly

**Detection (early warning signs):**
- Compliance team asking for data you can't produce
- "Why did it do that?" questions without answers
- Model/prompt changes with no version tracking

**Phase mapping:** Phase 1 (infrastructure). Build audit trail into architecture; don't retrofit.

---

### Pitfall 10: The Demo-to-Production Gap

**What goes wrong:** 95% of agentic AI projects fail to generate measurable business value. Beautiful demos that can't handle "spiking traffic, shifting APIs, and compliance audits."

**Why it happens:**
- Optimizing for demo scenarios, not edge cases
- Manual intervention masked as automation
- Not testing with real messy data
- Stakeholders impressed by demo, surprised by production

**Consequences:**
- Launch delays as edge cases surface
- Stakeholder confidence loss
- Project cancellation ("we were promised X")
- Sunk cost with no ROI

**Prevention:**
1. **Test with real data early**: Use actual (anonymized) meeting transcripts
2. **Measure on hard cases**: Overlapping speech, accents, technical jargon
3. **Define production criteria**: What reliability level = "production ready"?
4. **Staged rollout**: 1 user > 10 users > team > org
5. **Honest demos**: Show failure modes, not just happy path

**Detection (early warning signs):**
- Works great in demos, fails on real meetings
- Manual cleanup required after every test
- No quantified accuracy metrics

**Phase mapping:** Every phase. Build evaluation framework in Phase 1; use throughout.

---

## Minor Pitfalls

Annoyances that degrade UX but are recoverable.

---

### Pitfall 11: Transcript Quality Variance

**What goes wrong:** ASR accuracy varies wildly based on audio quality, accents, technical jargon. A 5% word error rate can break syntactic links between agent and action.

**Prevention:**
- Audio quality checks before processing
- Domain-specific vocabulary training
- Confidence-based routing (low confidence = human review)

**Phase mapping:** Phase 1 (transcript processing). Accept variance; design for graceful handling.

---

### Pitfall 12: Timezone Confusion

**What goes wrong:** Meeting at "3pm" - but which timezone? Deadlines extracted as "by Friday" need absolute dates.

**Prevention:**
- Always store in UTC, display in user timezone
- Extract relative dates ("Friday") using meeting timestamp as anchor
- Validate extracted dates are reasonable (not past, not 5 years away)

**Phase mapping:** Phase 2 (extraction). Simple but easy to overlook.

---

### Pitfall 13: Notification Fatigue

**What goes wrong:** Every extraction triggers notifications. Users disable notifications. Important items get missed.

**Prevention:**
- Batch notifications (daily digest vs. real-time)
- User-controlled notification preferences
- Only notify on high-confidence, user-relevant items

**Phase mapping:** Phase 3 (routing). Design notification strategy before building.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Transcript ingestion | Diarization errors cascade | Use attendee list grounding, don't over-rely on speaker labels |
| AI extraction | Hallucinated action items | Confidence scores + validation UI + grounding requirement |
| Identity resolution | False positive assignment | Human-in-the-loop for ambiguous matches |
| Smartsheet routing | Rate limiting failures | Use SDK with built-in handling, implement queue |
| Multi-agent orchestration | Coordination collapse | Start single-agent, add complexity only when proven necessary |
| Enterprise deployment | Consent/compliance gaps | Two-party consent default, audit trail from day one |
| Scale rollout | Demo-to-production gap | Test with real data, staged rollout, honest metrics |

---

## Sources

**AI/Agent Failures:**
- [MIT's State of AI in Business 2025](https://www.ninetwothree.co/blog/ai-fails)
- [RAND Corporation AI Project Failures](https://www.techfunnel.com/information-technology/why-ai-fails-2025-lessons/)
- [Galileo AI Agent Reliability](https://galileo.ai/blog/ai-agent-architecture)
- [VentureBeat: "More Agents" Research](https://venturebeat.com/orchestration/research-shows-more-agents-isnt-a-reliable-path-to-better-enterprise-ai/)
- [Google Cloud: Lessons on Agents and Trust](https://cloud.google.com/transform/ai-grew-up-and-got-a-job-lessons-from-2025-on-agents-and-trust)

**Speaker Diarization:**
- [Pyannote Diarization Benchmarks](https://brasstranscripts.com/blog/speaker-diarization-models-comparison)
- [UMEVO Transcription Accuracy Comparison](https://www.umevo.ai/blogs/ume-all-posts/ai-transcription-accuracy-a-2025-comparison-of-top-services)

**Action Item Extraction:**
- [MeetStream: NLP Extraction Challenges](https://blog.meetstream.ai/extracting-action-items-and-tasks-using-nlp/)
- [Common Pitfalls in AI Meeting Summaries](https://www.alibaba.com/product-insights/why-is-my-ai-meeting-summary-missing-key-action-items-common-pitfalls-and-fixes.html)

**Identity Resolution:**
- [Introduction to Entity Resolution](https://towardsdatascience.com/an-introduction-to-entity-resolution-needs-and-challenges-97fba052dde5/)
- [Identity vs Entity Resolution in Enterprise](https://www.getcensus.com/research-blog-listing/mastering-data-management-identity-vs.-entity-resolution-in-b2b-tech-and-retail)

**Consent & Compliance:**
- [Call Recording Laws by State](https://www.avoma.com/blog/call-recording-laws)
- [GDPR and AI Meeting Assistants](https://www.sembly.ai/blog/gdpr-and-ai-rules-risks-tools-that-comply/)
- [AI Meeting Assistant Security Guide](https://fellow.ai/blog/ai-meeting-assistant-security-and-privacy/)
- [Enterprise AI Compliance 2025](https://www.liminal.ai/blog/enterprise-ai-governance-guide)

**Smartsheet API:**
- [Smartsheet Rate Limiting Documentation](https://developers.smartsheet.com/api/resource_management/getting-started/throttling-and-rate-limiting)
- [Smartsheet API Best Practices](https://www.smartsheet.com/content-center/best-practices/tips-tricks/api-best-practices)

**Meeting Bot Integration:**
- [Meeting Bot API Comparison 2025](https://skribby.io/blog/best-meeting-bot-apis-(2025)-zoom-microsoft-teams-google-meet)
- [Zoom Recording Methods](https://www.nylas.com/blog/how-to-record-a-zoom-meeting/)

**LLM Structured Output:**
- [Structured Output Reliability Guide](https://www.cognitivetoday.com/2025/10/structured-output-ai-reliability/)
- [Simon Willison: LLM Schema Extraction](https://simonwillison.net/2025/Feb/28/llm-schemas/)
