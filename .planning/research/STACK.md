# Technology Stack: TPM Admin Agent

**Project:** Meeting Intelligence / TPM Automation
**Researched:** 2026-01-17
**Overall Confidence:** HIGH

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Python** | 3.12+ | Runtime | LangGraph 1.0 requires Python 3.10+. Python 3.12 offers best balance of stability and performance. Avoid 3.8/3.9 (EOL). | HIGH |
| **FastAPI** | 0.128.0 | API Framework | Async-first, Pydantic-native validation, automatic OpenAPI docs. Industry standard for Python APIs in 2025. Dropped Python 3.8 support. | HIGH |
| **Pydantic** | 2.12+ | Data Validation | Rust-powered validation core. Native integration with FastAPI and Anthropic SDK structured outputs. Essential for meeting data schemas. | HIGH |

### AI/LLM Layer

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **LangGraph** | 1.0.6 | Multi-Agent Orchestration | Production-ready as of Oct 2025. Graph-based workflows with durable state, human-in-the-loop, built-in persistence. Used by Uber, LinkedIn, Klarna. Superior to CrewAI (prototype-grade) and AutoGen (conversational-focused). | HIGH |
| **Anthropic SDK** | 0.76+ | Claude API | Native structured outputs via `client.beta.messages.parse()` with Pydantic models. Critical for reliable action item extraction. Requires beta header `structured-outputs-2025-11-13`. | HIGH |
| **Claude Sonnet 4.5** | - | Primary LLM | Best cost/performance ratio for structured extraction. Supports structured outputs. Use Opus 4.1 only for complex reasoning if needed. | HIGH |

**Why LangGraph over alternatives:**

| Framework | Verdict | Reason |
|-----------|---------|--------|
| **LangGraph** | USE | Graph-based state machines, production-proven, durable execution, excellent for multi-step workflows with conditional logic |
| CrewAI | AVOID | Role-based design is elegant but "suited for demos and prototypes" per 2025 benchmarks. Scaling/observability gaps. |
| AutoGen | AVOID | Conversational/brainstorming focus. Async model better for human interaction, not batch processing. |

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Turso/libSQL** | Latest | Primary Database | SQLite-compatible, async Python SDK, embedded vector search for LLMs, scales globally. Matches your existing Momentum stack. Production-ready. | HIGH |
| **SQLAlchemy** | 2.0+ | ORM | Async support, works with libSQL via `sqlalchemy-libsql` dialect. Type-safe queries. | MEDIUM |

**Alternative considered:** PostgreSQL is heavier than needed for single-TPM to team-scale. Turso's SQLite compatibility means local dev is trivial, production is managed.

### Task Queue / Event Processing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Dramatiq** | Latest | Background Tasks | 10x faster than RQ in benchmarks. Modern async design. Simpler API than Celery with production-grade reliability. | HIGH |
| **Redis** | 7.0+ | Message Broker | Dramatiq backend. Also useful for caching Zoom auth tokens and rate limiting. | HIGH |

**Why Dramatiq over alternatives:**

| Option | Verdict | Reason |
|--------|---------|--------|
| **Dramatiq** | USE | Best balance: modern, fast, production-ready, simpler than Celery |
| Celery | CONSIDER | Enterprise-grade, complex workflows. Overkill for this scope. Use if need RabbitMQ or canvas workflows. |
| ARQ | AVOID | Async-native but "struggles" in benchmarks, no multi-worker support out of box |
| FastAPI BackgroundTasks | AVOID | Only for minor tasks. No persistence, no retry, no scaling. |

### HTTP Client

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **httpx** | 0.28.1 | Async HTTP | Zoom API, Smartsheet API calls. Native async/await, HTTP/2 support, connection pooling. The standard for async Python. | HIGH |

### External Integrations

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **smartsheet-python-sdk** | 3.6.0+ | Smartsheet Output | Official SDK. Sync-only, but wrap in `asyncio.to_thread()` for async contexts. | HIGH |
| **Zoom OAuth + Webhooks** | API 2.0 | Meeting Transcripts | Server-to-Server OAuth for transcript access. Subscribe to `recording.transcript_completed` webhook. | HIGH |
| **Google APIs (google-api-python-client)** | Latest | Calendar/Docs | Meeting correlation, roster lookup. Use service account for server-side. | MEDIUM |

### Identity Resolution

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Splink** | Latest | Fuzzy Name Matching | Probabilistic record linkage. Links "John" in transcript to "John Smith" in roster. No training data required. Scales to millions. UK Ministry of Justice production use. | MEDIUM |
| **rapidfuzz** | Latest | String Similarity | Levenshtein, Jaro-Winkler for name matching. Fallback/complement to Splink. | HIGH |

**Note:** For initial MVP, simple fuzzy matching (rapidfuzz) may suffice. Splink adds sophistication for ambiguous cases (multiple Johns, nicknames).

### Observability

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **structlog** | Latest | Structured Logging | Better OpenTelemetry integration than Loguru. Processor pipeline for trace context injection. Production-grade JSON output. | HIGH |
| **OpenTelemetry** | Latest | Distributed Tracing | Trace LLM calls through agent workflows. Correlate logs with traces. | MEDIUM |
| **LangSmith** | - | LLM Observability | LangGraph native. Visualize agent execution, trace reasoning, debug workflows. Free tier available. | HIGH |

**Why structlog over Loguru:**
Loguru has no first-party OpenTelemetry integration. Structlog has native support and cleaner processor pipeline for trace context. Both work, but structlog is more observability-native.

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **pytest** | 8.0+ | Test Framework | Industry standard. | HIGH |
| **pytest-asyncio** | 1.3.0 | Async Testing | Required for FastAPI/httpx async tests. Major 1.0 release in 2025 with simplified API. | HIGH |
| **pytest-httpx** | Latest | HTTP Mocking | Mock httpx calls to Zoom/Smartsheet APIs. | HIGH |
| **Respx** | Latest | Alternative HTTP Mock | If pytest-httpx insufficient. | MEDIUM |

---

## Architecture Decisions

### Why Event-Driven + Adapter Pattern

Your stated architecture (event-driven, adapter pattern) is correct for this domain:

1. **Zoom transcripts arrive asynchronously** - Webhook-triggered processing
2. **Multiple output targets** - Smartsheet today, Notion/Jira tomorrow. Adapters isolate integration logic.
3. **Processing is inherently multi-step** - Ingest -> Extract -> Resolve -> Output. LangGraph state machines model this cleanly.

### Agent Boundaries

Based on multi-agent research, recommended agent structure:

| Agent | Responsibility | Why Separate |
|-------|---------------|--------------|
| **Ingestion Agent** | Receive webhook, fetch transcript, normalize | Decoupled from processing for reliability |
| **Extraction Agent** | Action items, decisions, risks, issues | LLM-intensive, benefits from structured outputs |
| **Resolution Agent** | Map names to roster identities | Requires roster context, can be cached |
| **Output Agent** | Write to Smartsheet | Integration-specific, adapter pattern |

LangGraph orchestrates these as nodes in a state machine. Not separate processes, but separate concerns.

---

## Installation

```bash
# Core
pip install fastapi uvicorn pydantic

# AI/LLM
pip install langgraph anthropic

# Database
pip install libsql-client sqlalchemy-libsql

# Task Queue
pip install dramatiq[redis] redis

# HTTP/Integrations
pip install httpx smartsheet-python-sdk google-api-python-client

# Identity Resolution
pip install rapidfuzz splink

# Observability
pip install structlog opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi

# Testing
pip install pytest pytest-asyncio pytest-httpx
```

### Development Dependencies

```bash
pip install ruff mypy pre-commit
```

---

## What NOT to Use

| Technology | Why Avoid |
|------------|-----------|
| **CrewAI** | Prototype-grade. Fun for demos, problematic at scale. Lacks production observability. |
| **AutoGen** | Conversational AI focus. Not designed for batch document processing. |
| **Celery** | Overkill complexity for this scope. Use Dramatiq for simpler mental model. |
| **requests** | Sync-only. Blocks event loop. Always use httpx for async. |
| **Loguru** | No native OpenTelemetry integration. Structlog is better for observability. |
| **Flask** | No native async. FastAPI is strictly superior for this use case. |
| **Django** | ORM/admin overhead not needed. FastAPI is leaner. |
| **MongoDB** | Document DB adds complexity. SQLite/Turso handles JSON columns fine. |
| **Langchain (raw)** | Use LangGraph instead. LangChain alone lacks state machine primitives for multi-agent. |

---

## Version Pinning Strategy

Pin major.minor, allow patch updates:

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi>=0.128,<0.130",
    "pydantic>=2.12,<3.0",
    "langgraph>=1.0,<2.0",
    "anthropic>=0.76,<1.0",
    "httpx>=0.28,<0.30",
    "dramatiq[redis]>=1.17,<2.0",
    "structlog>=25.0,<26.0",
    "pytest-asyncio>=1.3,<2.0",
]
```

---

## Confidence Assessment

| Category | Confidence | Notes |
|----------|------------|-------|
| Core Framework (FastAPI, Pydantic) | HIGH | Verified via PyPI, official docs. Industry standard. |
| AI Layer (LangGraph, Anthropic) | HIGH | Verified via official changelogs. LangGraph 1.0 GA in Oct 2025. |
| Task Queue (Dramatiq) | HIGH | Verified via 2025 benchmarks. Clear winner for async workloads. |
| Database (Turso/libSQL) | HIGH | Matches your existing stack. Verified production-ready. |
| Identity Resolution (Splink) | MEDIUM | Solid library, but may need testing against your specific name patterns. |
| Observability (structlog + OTel) | MEDIUM | Standard approach, but integration depth varies by setup. |

---

## Sources

### Multi-Agent Frameworks
- [LangGraph vs AutoGen vs CrewAI Comparison 2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langgraph-vs-autogen-vs-crewai-complete-ai-agent-framework-comparison-architecture-analysis-2025)
- [LangGraph 1.0 GA Announcement](https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available)
- [AI Agent Frameworks Comparison - Langfuse](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)

### FastAPI / Async
- [FastAPI Production Patterns 2025](https://orchestrator.dev/blog/2025-1-30-fastapi-production-patterns/)
- [Async APIs with FastAPI Best Practices](https://shiladityamajumder.medium.com/async-apis-with-fastapi-patterns-pitfalls-best-practices-2d72b2b66f25)
- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/)

### Task Queues
- [Python Task Queue Benchmarks 2025](https://stevenyue.com/blogs/exploring-python-task-queue-libraries-with-load-test)
- [Python Background Tasks Comparison 2025](https://devproportal.com/languages/python/python-background-tasks-celery-rq-dramatiq-comparison-2025/)

### Anthropic/Claude
- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Anthropic SDK Python GitHub](https://github.com/anthropics/anthropic-sdk-python)

### Database
- [Turso/libSQL Documentation](https://docs.turso.tech/libsql)
- [libSQL Python SDK](https://docs.turso.tech/libsql/client-access/python-sdk)

### Identity Resolution
- [Splink Documentation](https://moj-analytical-services.github.io/splink/index.html)
- [Entity Resolution Python Libraries](https://spotintelligence.com/2024/01/22/entity-resolution/)

### Integrations
- [Zoom Cloud Recording API Tutorial](https://www.recall.ai/blog/zoom-transcript-api)
- [Zoom Webhook Documentation](https://developers.zoom.us/docs/api/webhooks/)
- [Smartsheet Python SDK](https://smartsheet-platform.github.io/smartsheet-python-sdk/)

### Observability
- [Python Logging with Structlog](https://last9.io/blog/python-logging-with-structlog/)
- [OpenTelemetry Python Logging](https://oneuptime.com/blog/post/2025-01-06-python-structured-logging-opentelemetry/view)

### Testing
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Pydantic v2.12 Release](https://pydantic.dev/articles/pydantic-v2-12-release)
