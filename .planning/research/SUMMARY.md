# Project Research Summary

**Project:** TPM Admin Agent
**Domain:** Meeting Intelligence / Multi-Agent Automation
**Researched:** 2026-01-17
**Confidence:** HIGH

## Executive Summary

The TPM Admin Agent is a meeting intelligence system that extracts RAID artifacts (Risks, Actions, Issues, Decisions) from Zoom transcripts and routes them to Smartsheet. This is a well-understood problem domain with established patterns, but most existing tools focus on generic summarization rather than structured TPM workflows. The differentiation is clear: deep RAID extraction with TPM-specific templates and Smartsheet integration. No competitor does this combination.

The recommended approach is a layered event-driven architecture with adapter pattern for integrations. Start with batch processing (webhook-triggered) rather than real-time streaming. Use LangGraph for multi-agent orchestration with Claude Sonnet 4.5 for structured extraction. Begin with a single-agent orchestrator; add specialized agents only when proven necessary. The stack aligns with your existing Momentum project (FastAPI, Turso, Python 3.12+), reducing ramp-up time.

The critical risks are: (1) silent agent failures that erode user trust, (2) consent compliance violations across states/countries, (3) identity resolution false positives assigning action items to the wrong person, and (4) hallucinated action items that create noise. All four require human-in-the-loop patterns during initial deployment. Build verification loops from day one, not as an afterthought.

## Key Findings

### Recommended Stack

The stack prioritizes async-first design, production-proven libraries, and alignment with your existing projects. Python 3.12+ with FastAPI provides the foundation. LangGraph 1.0 (GA as of Oct 2025) handles multi-agent orchestration with durable state and human-in-the-loop support. Anthropic's structured outputs with Pydantic ensure reliable extraction.

**Core technologies:**
- **Python 3.12+ / FastAPI 0.128**: Async-first API framework with native Pydantic validation
- **LangGraph 1.0**: Production-ready multi-agent orchestration (used by Uber, LinkedIn, Klarna)
- **Anthropic SDK + Claude Sonnet 4.5**: Structured outputs via `client.beta.messages.parse()` for reliable extraction
- **Turso/libSQL**: SQLite-compatible database matching your existing stack, with embedded vector search
- **Dramatiq + Redis**: Task queue 10x faster than RQ, simpler than Celery
- **httpx**: Async HTTP client for Zoom/Smartsheet API calls
- **structlog + OpenTelemetry**: Observability-native logging with distributed tracing

**Avoid:** CrewAI (prototype-grade), AutoGen (conversational focus), Celery (overkill), requests (sync-only), Loguru (no OTel integration).

### Expected Features

**Must have (table stakes):**
- Zoom transcript ingestion via webhook (don't build recording)
- Action item extraction with ownership attribution
- Speaker identification (who said what)
- Calendar integration for meeting context
- Basic search/retrieval of past meetings

**Should have (differentiators):**
- Decision extraction with traceability (most tools miss this)
- Risk/Issue extraction (TPM-specific, no competitor does well)
- Template-based meeting minutes (org-specific formats)
- Smartsheet integration (your specific workflow requirement)

**Defer (v2+):**
- Multi-meeting intelligence / pattern detection (requires data accumulation)
- Proactive nudges (requires notification infrastructure)
- Conversational query / RAG (requires vector search pipeline)
- Bot-free capture (complex, Zoom transcript ingestion is simpler)
- Real-time streaming (batch covers 90% of value)

### Architecture Approach

A layered event-driven architecture with five tiers: Ingestion Layer (adapters for Zoom, Google, Slack), Event Core (typed event bus with append-only event store), Agent Layer (specialized agents for extraction), Projection Layer (read models for rollups), and Integration Layer (outbound adapters for Smartsheet). Event sourcing provides full audit trail for compliance and enables replay for debugging.

**Major components:**
1. **Zoom Adapter** — Transcript authority; handles webhooks, normalizes to canonical format
2. **Event Bus + Event Store** — Routes typed events, provides append-only audit trail
3. **Note-Taker Agent** — Extracts structured notes from transcript
4. **Task-Assigner Agent** — Identifies action items, assigns owners
5. **Smartsheet Adapter** — Bidirectional task sync with rate limiting

**Key patterns to follow:**
- Adapter pattern (Ports and Adapters) for vendor isolation
- Event sourcing with CQRS for audit trail and multiple read models
- Orchestrator-Worker pattern for multi-agent coordination
- Canonical data model shared across all components

### Critical Pitfalls

1. **Silent Agent Failures** — Agents report success when they've failed. Build verification loops into every action. Reconciliation jobs that check transcript count = extraction count = routing count. Address in Phase 1.

2. **Consent Compliance Violations** — 11 states require two-party consent. GDPR requires explicit informed consent. Default to two-party consent, track who consented, provide opt-out mechanism. Must be MVP.

3. **Identity Resolution False Positives** — "John" resolves to wrong John. Use confidence thresholds (>85%), human-in-the-loop for ambiguous matches, attendee list grounding. Don't ship fully automated.

4. **Action Item Hallucination** — LLM extracts items that weren't discussed. Require grounding (extractable quote from transcript), confidence scores on every extraction, validation UI before auto-routing.

5. **Multi-Agent Coordination Collapse** — Research shows 2-6x efficiency penalty with 10+ tools. Start single-agent. Only add coordination when single-agent < 45% baseline accuracy.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Core Foundation
**Rationale:** Everything depends on events flowing and canonical models. Must prove reliability before adding complexity.
**Delivers:** Basic transcript-to-action-items pipeline with verification
**Addresses:** Transcript ingestion, action item extraction, decision extraction
**Avoids:** Silent failures (verification loops), consent violations (tracking), demo-to-production gap (real data testing)

Components to build:
- Canonical data models (Meeting, ActionItem, Decision, Participant)
- Typed event definitions and event bus (in-memory v1)
- Append-only event store in Turso
- Zoom adapter (webhook handling, transcript fetch)
- Single orchestrator agent with extraction prompts
- Verification/reconciliation framework
- Consent tracking infrastructure

### Phase 2: Integration Loop
**Rationale:** Phase 1 extracts data. Phase 2 makes it actionable in user tools.
**Delivers:** Closed loop with Smartsheet, notifications, calendar context
**Uses:** Smartsheet SDK (handles rate limiting), Google Calendar API
**Implements:** Smartsheet adapter, Slack adapter, identity resolution

Components to build:
- Smartsheet adapter (bidirectional sync with queue)
- Google Calendar adapter (meeting context, participant info)
- Identity resolution with confidence thresholds and human-in-the-loop
- Summarizer agent (meeting summaries, decision extraction)
- Slack adapter (notifications for assigned items)
- Validation UI for extraction review

### Phase 3: Intelligence Layer
**Rationale:** Once data flows and syncs, add hierarchy views and executive reporting.
**Delivers:** TPM-specific dashboards, rollup views (IC -> Director -> VP)
**Uses:** Projection layer, rollup engine
**Implements:** Reporting API, Risk/Issue detection agent

Components to build:
- Hierarchy resolver (map participants to org structure)
- Rollup engine (aggregate by hierarchy level)
- Reporting API (dashboard endpoints)
- Risk/Issue detection agent
- Template output system (org-specific formats)

### Phase 4: Scale and Optimization (Future)
**Rationale:** Only pursue if latency requirements demand it or user base expands significantly.
**Delivers:** Real-time processing, multi-platform support
**Uses:** Kafka/Redis Streams, incremental processing

Components to build:
- Zoom RTMS integration (real-time transcript streaming)
- Streaming event bus upgrade
- Multi-platform abstraction (Teams, Meet)
- Advanced agent specialization

### Phase Ordering Rationale

- **Events first:** The event-driven architecture requires the event bus and store before any processing logic. This foundation enables replay, audit, and debugging.
- **Single-agent before multi:** Research shows multi-agent coordination fails when single-agent would suffice. Prove the orchestrator works before splitting into specialized agents.
- **Batch before streaming:** Batch (webhook-triggered) is simpler, covers 90% of value, and proves the pipeline. Streaming adds stateful complexity that's unnecessary initially.
- **Human-in-the-loop early:** Identity resolution and extraction both need human validation during initial deployment. Build these UIs early, not after users lose trust.
- **Smartsheet in Phase 2:** The extraction pipeline must work before routing makes sense. Rate limiting handling is well-documented with SDK.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Identity Resolution):** Splink vs rapidfuzz decision depends on actual name ambiguity in your meetings. Test with real roster data.
- **Phase 3 (Hierarchy):** Org structure integration depends on available data sources. May need HRIS API research.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Event Sourcing):** Well-documented pattern from Microsoft, AWS. Use append-only table in Turso.
- **Phase 2 (Smartsheet):** Official SDK handles rate limiting. Straightforward CRUD operations.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against PyPI, official docs, 2025 benchmarks. LangGraph 1.0 GA confirmed. |
| Features | HIGH | Multiple authoritative sources (Zapier, competitor docs). Clear table stakes vs differentiators. |
| Architecture | HIGH | Established patterns (event sourcing, hexagonal). Multiple enterprise reference architectures. |
| Pitfalls | HIGH | Verified against MIT, RAND, Google Cloud AI research. Real-world failure cases documented. |

**Overall confidence:** HIGH

### Gaps to Address

- **Identity resolution accuracy:** Need to test Splink vs rapidfuzz against your actual meeting transcripts and roster. Research shows Splink is more sophisticated but may be overkill for initial deployment.
- **Org hierarchy data source:** Research assumes org structure is available somewhere. Need to identify actual data source during Phase 3 planning.
- **Consent UI/UX:** Research covers legal requirements but not UX implementation. May need UX research for consent flow design.
- **Zoom webhook reliability:** Research shows Zoom webhooks are standard, but no data on delivery guarantees. Build retry/reconciliation regardless.

## Sources

### Primary (HIGH confidence)
- [LangGraph 1.0 GA Announcement](https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available)
- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Microsoft Event Sourcing Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [AWS Hexagonal Architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/hexagonal-architecture.html)
- [Smartsheet API Rate Limiting](https://developers.smartsheet.com/api/resource_management/getting-started/throttling-and-rate-limiting)
- [Fellow.ai Features](https://fellow.ai/features/action-items)
- [Zoom Webhook Documentation](https://developers.zoom.us/docs/api/webhooks/)

### Secondary (MEDIUM confidence)
- [LangGraph vs AutoGen vs CrewAI Comparison 2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langgraph-vs-autogen-vs-crewai-complete-ai-agent-framework-comparison-architecture-analysis-2025)
- [Python Task Queue Benchmarks 2025](https://stevenyue.com/blogs/exploring-python-task-queue-libraries-with-load-test)
- [Confluent Multi-Agent Patterns](https://www.confluent.io/blog/event-driven-multi-agent-systems/)
- [Call Recording Laws by State](https://www.avoma.com/blog/call-recording-laws)
- [Pyannote Diarization Benchmarks](https://brasstranscripts.com/blog/speaker-diarization-models-comparison)

### Tertiary (LOW confidence)
- [Entity Resolution Python Libraries](https://spotintelligence.com/2024/01/22/entity-resolution/) — Splink recommendation needs validation against your data
- [MIT State of AI 2025](https://www.ninetwothree.co/blog/ai-fails) — 95% failure rate statistic is aggregate, may not apply to focused projects

---
*Research completed: 2026-01-17*
*Ready for roadmap: yes*
