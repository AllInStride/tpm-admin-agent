# Feature Landscape: Meeting Intelligence / TPM Automation

**Domain:** Meeting intelligence with TPM workflow automation
**Researched:** 2026-01-17
**Confidence:** HIGH (multiple authoritative sources, current market data)

## Table Stakes

Features users expect. Missing = product feels incomplete or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Real-time transcription | Every competitor offers it. Users won't manually transcribe. | Medium | 90%+ accuracy expected. Poor audio = poor results. Accents/jargon remain challenging. |
| Speaker identification | Unusable without knowing who said what. | Medium | Critical for action item attribution. Multi-speaker calls are the norm. |
| Meeting summary | Manual summarization is the pain point being solved. | Low | AI summarization is commoditized. Differentiator is structure/quality. |
| Action item extraction | Primary value proposition of category. | Medium | 2024 ACL research: real-time extraction 2.3x more accurate than post-hoc. Explicit assignment ("John will do X") works; implicit ("someone should") fails. |
| Calendar integration | Users expect meetings to flow from calendar automatically. | Low | Google Calendar, Outlook are minimum. |
| Platform support (Zoom, Teams, Meet) | Market is split across platforms. Single-platform = dealbreaker for most. | Medium | Zoom dominates but Teams/Meet are enterprise standards. |
| Search/retrieval of past meetings | Meetings aren't one-off events. Users need to find past discussions. | Medium | Full-text search of transcripts is baseline. |
| Sharing/export | Notes trapped in tool = friction. | Low | Export to PDF, share links, copy to clipboard. |
| Basic integrations (Slack, email) | Summary delivery must go where teams already work. | Low | Slack channel summaries, email recaps are expected. |

## Differentiators

Features that set products apart. Not universally expected, but create competitive advantage.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Multi-meeting intelligence** | Surface patterns across meeting history (recurring objections, themes, blockers). tl;dv pioneered this in 2025. | High | Requires vector search or similar. Transforms tool from note-taker to organizational memory. |
| **RAID extraction (Risks, Issues, Decisions)** | Goes beyond action items. Captures decisions for traceability, risks/issues for escalation. | Medium | TPM-specific. No major competitor does this well. Strong differentiator for your use case. |
| **Template-based output** | Generate meeting minutes matching org-specific formats. | Medium | Otter.ai has custom templates. Most tools output generic summaries. |
| **Deep PM/task tool integration** | Push action items directly into Jira, Asana, Linear, Smartsheet. | Medium | Fellow, Fireflies lead here. One-click task creation vs manual copy-paste. |
| **CRM integration** | Auto-populate Salesforce/HubSpot with meeting outcomes. | Medium | Sales-focused tools (Gong, Fireflies) do this. Less relevant for TPM use case. |
| **Proactive nudges** | Remind assignees of overdue action items, surface unaddressed decisions. | High | Emerging in 2025-2026. Most tools are passive (capture only). Active follow-up = differentiation. |
| **Conversational query ("Ask" features)** | Natural language queries across meeting history ("What did we decide about X?"). | High | Fellow's "Ask Copilot", Notion AI have this. Requires robust RAG pipeline. |
| **Bot-free capture** | Record without visible meeting bot. Jamie, Notion AI do this via system audio. | Medium | Privacy-conscious orgs prefer this. Many users find bots intrusive. |
| **Real-time collaboration** | Multiple people annotating/highlighting during meeting. | Medium | Fellow does collaborative agendas. Useful for structured meetings. |
| **Coaching/analytics** | Talk-to-listen ratios, speaking pace, meeting effectiveness metrics. | Medium | Zoom AI Companion, Read.ai offer this. More relevant for sales than TPM. |
| **Workflow automation triggers** | Meeting outcomes trigger downstream workflows (status updates, notifications). | High | Smartsheet's 2025 "Smart Flows" and "Smart Agents" target this. Your Smartsheet routing fits here. |
| **Meeting prep assistance** | AI surfaces relevant context from past meetings before upcoming meeting. | High | Emerging feature. Notion AI searching calendars for prep material. |

## Anti-Features

Features to explicitly NOT build. Common mistakes or scope traps in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Building your own ASR/transcription** | Commoditized. AssemblyAI, Deepgram, Whisper are battle-tested. Rolling your own = months of wasted effort. | Use AssemblyAI or Deepgram API. Focus on what happens after transcription. |
| **Generic summarization** | Every tool does this. Not differentiating. Easy to build, easy to ignore. | Structure extraction (RAID, decisions) over prose summaries. |
| **Real-time recording join bot** | Complex infrastructure (WebRTC, browser automation). Zoom/Teams actively fight bots. Maintenance nightmare. | Ingest transcripts post-meeting or use platform webhooks/APIs. Let Zoom handle recording. |
| **All-in-one meeting scheduler** | Calendar/scheduling is a different product category (Calendly, Cal.com). Scope creep trap. | Integrate with calendars for context, don't replace them. |
| **Video storage/playback** | Storage costs, streaming infrastructure, video processing. Not your core value. | Store transcript/summary. Link to original recording in Zoom/Teams. |
| **Live meeting collaboration UI** | Building a collaborative editor is a product unto itself (think Notion complexity). | Output to existing collaboration tools (Notion, Confluence, Smartsheet). |
| **Full CRM features** | Not your market. Sales tools (Gong, Chorus) own this space. | Light Smartsheet/PM tool integration. Don't become a CRM. |
| **Compliance-as-differentiator** | SOC2, HIPAA are table stakes for enterprise. Not a feature, a requirement. | Get SOC2 eventually, but don't market it as a feature. |
| **Auto-join every meeting** | Privacy concerns. Users get fatigued. "AI listening to everything" is creepy. | Explicit opt-in per meeting or meeting type. User controls what gets captured. |
| **Sentiment analysis emphasis** | Impressive demo, questionable utility. "Meeting was 73% positive" means nothing actionable. | Focus on action items and decisions. Skip the vanity metrics. |

## Feature Dependencies

```
Transcription (input)
    |
    v
Speaker Identification --> Action Item Extraction --> Task Tool Integration
    |                           |
    v                           v
Meeting Summary           Decision Extraction --> Multi-meeting patterns
    |                           |
    v                           v
Search/Retrieval         Risk/Issue Extraction --> Proactive Nudges
                                |
                                v
                         Template Output --> Smartsheet Routing
```

**Critical path for your TPM use case:**
1. Transcription ingestion (Zoom transcript import)
2. Speaker identification (who said what)
3. RAID extraction (action items, decisions, risks, issues)
4. Template-based output (meeting minutes format)
5. Smartsheet integration (artifact routing)
6. Then: proactive nudges, pattern detection, communication drafting

## MVP Recommendation

For MVP, prioritize:

1. **Zoom transcript ingestion** (table stakes, Low complexity)
   - Don't build recording. Ingest Zoom's transcript output.

2. **Action item extraction with ownership** (table stakes, Medium complexity)
   - Who is doing what by when. This is the core value prop.

3. **Decision extraction** (differentiator, Medium complexity)
   - Most tools miss this. Decisions need traceability for TPMs.

4. **Template-based meeting minutes** (differentiator, Medium complexity)
   - Org-specific formats. Not generic summaries.

5. **Smartsheet integration** (differentiator, Medium complexity)
   - Your specific workflow requirement. Route artifacts to right place.

**Defer to post-MVP:**

- Multi-meeting intelligence (requires significant data accumulation)
- Proactive nudges (requires notification infrastructure)
- Risk/issue extraction (start with action items + decisions)
- Bot-free capture (complex, Zoom transcript ingestion is simpler)
- Conversational query (requires RAG infrastructure)
- Meeting prep assistance (nice-to-have, not core)

## Competitive Positioning Matrix

| Capability | Otter | Fireflies | Fathom | Fellow | Zoom AI | Notion AI | Your Agent |
|------------|-------|-----------|--------|--------|---------|-----------|------------|
| Transcription | Yes | Yes | Yes | Yes | Yes | Yes | Via Zoom |
| Action Items | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Decisions | Basic | Basic | Basic | Basic | Basic | Basic | **Deep** |
| Risks/Issues | No | No | No | No | No | No | **Yes** |
| Template Output | Yes | Limited | No | Agenda | No | Limited | **Yes** |
| Smartsheet | No | No | No | No | No | No | **Yes** |
| Multi-meeting | Limited | Limited | No | Limited | No | Yes | Phase 2 |
| TPM Workflows | No | No | No | No | No | No | **Yes** |

**Your differentiation:** RAID extraction + TPM-specific templates + Smartsheet routing. Nobody does this combination.

## Pricing Insights

For context on market expectations:

| Tool | Free Tier | Pro Tier | Enterprise |
|------|-----------|----------|------------|
| Fathom | Generous (unlimited) | $19/mo | Custom |
| Otter | Limited | $16.99/mo | Custom |
| Fireflies | Limited storage | $18/mo | Custom |
| tl;dv | Generous | $18/mo | $59/mo |
| Fellow | Limited | $9/mo | Custom |
| Notion AI | Part of Business ($20/user) | - | - |
| Zoom AI | Included with paid Zoom | - | - |

Users expect free tiers or are used to $15-20/mo pricing. Enterprise is custom.

## Sources

### Primary Sources (HIGH confidence)
- [Zapier - Fathom vs Fireflies comparison](https://zapier.com/blog/fathom-vs-fireflies/)
- [Zoom AI Companion documentation](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0058013)
- [Fellow.ai features](https://fellow.ai/features/action-items)
- [tl;dv features and integrations](https://tldv.io/)
- [Notion AI Meeting Notes](https://www.notion.com/product/ai-meeting-notes)
- [Smartsheet AI features announcement](https://www.smartsheet.com/content-center/news/smartsheet-debuts-intelligent-work-management-unifying-ai-data-and-people)

### Market Analysis (MEDIUM confidence)
- [Index.dev - Otter vs Fireflies vs Fathom comparison](https://www.index.dev/blog/otter-vs-fireflies-vs-fathom-ai-meeting-notes-comparison)
- [WealthTech Today - AI Notetakers buyer's guide](https://wealthtechtoday.com/2025/04/29/best-ai-notetakers-for-financial-advisors-2025-a-strategic-buyers-guide/)
- [Jamie - AI meeting assistants overview](https://www.meetjamie.ai/blog/ai-meeting-assistant)
- [tl;dv - Best AI meeting assistants 2025](https://tldv.io/blog/best-ai-meeting-assistants/)

### Accuracy & Compliance (MEDIUM confidence)
- [Alibaba - AI meeting summary pitfalls](https://www.alibaba.com/product-insights/why-is-my-ai-meeting-summary-missing-key-action-items-common-pitfalls-and-fixes.html)
- [Fellow - AI meeting assistant security](https://fellow.ai/blog/ai-meeting-assistant-security-and-privacy/)
- [Faegre Drinker - Recording consent considerations](https://www.faegredrinker.com/en/insights/publications/2025/2/permission-to-record-considerations-for-ai-meeting-assistants)
- [Harvard AI Assistant Guidelines](https://www.huit.harvard.edu/ai-assistant-guidelines)
