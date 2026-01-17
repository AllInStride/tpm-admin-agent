# Architecture Patterns

**Domain:** Meeting Intelligence / TPM Automation Agent
**Researched:** 2026-01-17
**Confidence:** HIGH (patterns well-established, verified across multiple sources)

## Recommended Architecture

The TPM Admin Agent follows a **layered event-driven architecture** with clear separation between:
1. **Ingestion Layer** - Receives data from external systems via adapters
2. **Event Core** - Central event bus with typed events, event sourcing for audit
3. **Agent Layer** - Multi-agent processing (note-taker, task-assigner, summarizer)
4. **Projection Layer** - Read models for hierarchy rollups and reporting
5. **Integration Layer** - Outbound adapters for external systems

```
+-------------------+     +-------------------+     +-------------------+
|   ZOOM ADAPTER    |     |  GOOGLE ADAPTER   |     |  SLACK ADAPTER    |
|  (Transcript Auth)|     |  (Calendar/Meet)  |     |  (Notifications)  |
+--------+----------+     +--------+----------+     +--------+----------+
         |                         |                         |
         v                         v                         v
+------------------------------------------------------------------------+
|                         EVENT BUS (Typed Events)                        |
|  MeetingStarted | TranscriptReceived | ActionItemExtracted | ...        |
+--------+-------------------+-------------------+-------------------+----+
         |                   |                   |                   |
         v                   v                   v                   v
+--------+----------+ +------+--------+ +--------+--------+ +--------+---+
|  EVENT STORE      | | NOTE-TAKER    | | TASK-ASSIGNER   | | SUMMARIZER |
|  (Append-only)    | | AGENT         | | AGENT           | | AGENT      |
+--------+----------+ +------+--------+ +--------+--------+ +--------+---+
         |                   |                   |                   |
         v                   v                   v                   v
+------------------------------------------------------------------------+
|                    CANONICAL DATA MODEL                                 |
|  Meeting | ActionItem | Decision | Risk | Issue | Participant           |
+------------------------------------------------------------------------+
         |
         v
+--------+----------+     +-------------------+     +-------------------+
|  ROLLUP ENGINE    |     | SMARTSHEET ADAPTER|     |  REPORTING API    |
|  (IC->Dir->VP)    |     | (Task Sync)       |     |  (Dashboard)      |
+-------------------+     +-------------------+     +-------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Build Phase |
|-----------|---------------|-------------------|-------------|
| **Zoom Adapter** | Transcript authority. Fetches recordings, handles webhooks, normalizes transcript format | Event Bus (emits TranscriptReceived) | Phase 1 |
| **Google Adapter** | Calendar integration, meeting metadata, participant info | Event Bus (emits MeetingScheduled) | Phase 2 |
| **Slack Adapter** | Outbound notifications, action item reminders | Event Bus (subscribes to ActionItemAssigned) | Phase 2 |
| **Smartsheet Adapter** | Bidirectional task sync, status updates | Event Bus, Canonical Model | Phase 2-3 |
| **Event Bus** | Routes typed events between components, ensures delivery | All components | Phase 1 |
| **Event Store** | Append-only storage for all events, replay capability | Event Bus | Phase 1 |
| **Note-Taker Agent** | Extracts structured notes from transcripts | Event Bus (TranscriptReceived -> NotesExtracted) | Phase 1 |
| **Task-Assigner Agent** | Identifies action items, assigns owners | Event Bus (NotesExtracted -> ActionItemExtracted) | Phase 1 |
| **Summarizer Agent** | Generates meeting summaries, identifies decisions | Event Bus (MeetingEnded -> SummaryGenerated) | Phase 2 |
| **Canonical Model** | Unified data model for all domain objects | All agents, all adapters | Phase 1 |
| **Rollup Engine** | Hierarchy aggregation (IC -> Director -> VP views) | Canonical Model, Reporting API | Phase 3 |
| **Reporting API** | Dashboard data, executive views | Frontend, Rollup Engine | Phase 3 |

### Data Flow

**Batch Processing Flow (v1):**
```
1. Zoom webhook fires (recording.completed)
2. Zoom Adapter fetches transcript via API
3. Zoom Adapter normalizes to canonical Meeting + Transcript
4. Event Bus receives TranscriptReceived event
5. Event Store persists event (append-only)
6. Note-Taker Agent processes transcript
7. Note-Taker emits NotesExtracted event
8. Task-Assigner processes notes
9. Task-Assigner emits ActionItemExtracted events
10. Smartsheet Adapter syncs action items
11. Slack Adapter notifies assignees
```

**Streaming Flow (v2 - Future):**
```
1. Zoom RTMS WebSocket connection established
2. Real-time transcript chunks arrive
3. Event Bus receives TranscriptChunkReceived events
4. Note-Taker Agent processes incrementally
5. ActionItems streamed as detected
6. Near real-time notifications
```

## Patterns to Follow

### Pattern 1: Adapter Pattern (Ports and Adapters / Hexagonal)

**What:** Isolate external system dependencies behind adapter interfaces. Each adapter translates between external API and canonical internal model.

**Why:** Prevents vendor lock-in. Allows testing core logic without external dependencies. Enables swapping integrations (e.g., Zoom -> Teams) without core changes.

**Example:**
```python
# Port (interface)
class TranscriptSource(Protocol):
    async def fetch_transcript(self, meeting_id: str) -> Transcript:
        ...

    async def handle_webhook(self, payload: dict) -> Event:
        ...

# Adapter (implementation)
class ZoomTranscriptAdapter(TranscriptSource):
    def __init__(self, zoom_client: ZoomAPIClient):
        self.client = zoom_client

    async def fetch_transcript(self, meeting_id: str) -> Transcript:
        raw = await self.client.get_recording_transcript(meeting_id)
        return self._normalize_to_canonical(raw)

    def _normalize_to_canonical(self, raw: dict) -> Transcript:
        # Transform Zoom-specific format to canonical Transcript
        return Transcript(
            meeting_id=raw["meeting_id"],
            segments=[
                TranscriptSegment(
                    speaker=s["speaker_name"],
                    text=s["text"],
                    start_time=s["start_time"],
                    end_time=s["end_time"]
                )
                for s in raw["segments"]
            ]
        )
```

**Source:** [Hexagonal Architecture - AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/hexagonal-architecture.html), [Adapter Service Pattern](https://medium.com/@jescrich_57703/harnessing-the-adapter-pattern-in-microservice-architectures-for-vendor-agnosticism-debc21d2fe21)

### Pattern 2: Event Sourcing with CQRS

**What:** Store all state changes as immutable events. Separate write model (events) from read models (projections). Replay events to reconstruct state.

**Why:** Full audit trail for compliance. Enables replay for debugging and recovery. Supports multiple read models optimized for different queries. Perfect for hierarchy rollups.

**Example:**
```python
# Event definitions (typed)
@dataclass
class ActionItemExtracted(Event):
    meeting_id: str
    action_item_id: str
    description: str
    assignee: str
    due_date: Optional[datetime]
    extracted_at: datetime
    source_segment_ids: List[str]  # Trace back to transcript

@dataclass
class ActionItemStatusChanged(Event):
    action_item_id: str
    old_status: str
    new_status: str
    changed_by: str
    changed_at: datetime

# Event Store (append-only)
class EventStore:
    async def append(self, event: Event) -> None:
        await self.db.execute(
            "INSERT INTO events (event_type, event_data, created_at) VALUES (?, ?, ?)",
            event.__class__.__name__,
            event.to_json(),
            datetime.utcnow()
        )

    async def replay(self, from_position: int = 0) -> AsyncIterator[Event]:
        async for row in self.db.fetch_all("SELECT * FROM events WHERE id > ? ORDER BY id", from_position):
            yield Event.from_json(row["event_data"])

# Read Model Projection
class ActionItemProjection:
    async def handle(self, event: Event) -> None:
        if isinstance(event, ActionItemExtracted):
            await self.db.execute(
                "INSERT INTO action_items_view (...) VALUES (...)",
                ...
            )
        elif isinstance(event, ActionItemStatusChanged):
            await self.db.execute(
                "UPDATE action_items_view SET status = ? WHERE id = ?",
                event.new_status, event.action_item_id
            )
```

**Source:** [Event Sourcing - Microsoft](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing), [CQRS Pattern - Microsoft](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)

### Pattern 3: Multi-Agent Orchestration (Orchestrator-Worker)

**What:** Central orchestrator coordinates specialized worker agents. Each agent has a single responsibility. Orchestrator manages workflow, handles failures, tracks progress.

**Why:** Clear separation of concerns. Agents can be developed/tested independently. Easy to add new agent types. Supports both sequential and parallel processing.

**Example:**
```python
class MeetingProcessingOrchestrator:
    def __init__(self, agents: Dict[str, Agent]):
        self.note_taker = agents["note_taker"]
        self.task_assigner = agents["task_assigner"]
        self.summarizer = agents["summarizer"]

    async def process_transcript(self, transcript: Transcript) -> ProcessingResult:
        # Sequential: notes must come before task extraction
        notes = await self.note_taker.extract_notes(transcript)

        # Parallel: task extraction and summarization can run concurrently
        action_items, summary = await asyncio.gather(
            self.task_assigner.extract_action_items(notes),
            self.summarizer.generate_summary(transcript, notes)
        )

        return ProcessingResult(
            notes=notes,
            action_items=action_items,
            summary=summary
        )
```

**Source:** [Multi-Agent Patterns - Confluent](https://www.confluent.io/blog/event-driven-multi-agent-systems/), [Multi-Agent Architecture - Ampcome](https://www.ampcome.com/post/multi-agent-system-architecture-for-enterprises)

### Pattern 4: Canonical Data Model

**What:** Single, authoritative data model shared across all components. All adapters translate to/from this model. All agents operate on this model.

**Why:** Eliminates translation errors between components. Single source of truth for domain concepts. Enables adapter swapping without downstream changes.

**Example:**
```python
# Canonical domain models
@dataclass
class Meeting:
    id: str
    title: str
    scheduled_start: datetime
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    participants: List[Participant]
    hierarchy_path: HierarchyPath  # IC -> Manager -> Director -> VP
    source: str  # "zoom", "teams", "meet"

@dataclass
class ActionItem:
    id: str
    meeting_id: str
    description: str
    assignee: Participant
    due_date: Optional[datetime]
    status: ActionItemStatus
    source_segment: Optional[TranscriptSegment]  # Provenance

@dataclass
class HierarchyPath:
    """Enables rollup views: IC -> Director -> VP"""
    ic_id: str
    manager_id: Optional[str]
    director_id: Optional[str]
    vp_id: Optional[str]
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct External API Calls

**What:** Calling external APIs (Zoom, Slack, Smartsheet) directly from business logic.

**Why bad:** Tight coupling. Testing requires mocking external services. API changes break business logic. Cannot swap providers.

**Instead:** Always go through adapters. Business logic only knows canonical model.

### Anti-Pattern 2: Synchronous Agent Chains

**What:** Agent A directly calls Agent B, which calls Agent C. Deep call stacks.

**Why bad:** Brittle. Single failure breaks entire chain. Hard to retry partial failures. Cannot scale agents independently.

**Instead:** Event-driven communication. Agents emit events, subscribe to events. Orchestrator coordinates when sequencing matters.

### Anti-Pattern 3: Storing Only Current State

**What:** Updating records in place. Losing history of changes.

**Why bad:** No audit trail. Cannot debug "how did we get here?" Cannot replay to recover from bugs. Cannot build new projections from historical data.

**Instead:** Event sourcing. Append-only event store. Derive current state from event replay.

### Anti-Pattern 4: Tight Coupling to LLM Provider

**What:** OpenAI-specific code scattered throughout agents.

**Why bad:** Model costs change. New models emerge. Testing requires API calls.

**Instead:** Abstract LLM behind interface. Inject provider. Enable local/mock models for testing.

```python
# Bad
class TaskAssignerAgent:
    async def extract(self, notes: Notes) -> List[ActionItem]:
        response = await openai.chat.completions.create(...)  # Tight coupling

# Good
class TaskAssignerAgent:
    def __init__(self, llm: LLMProvider):  # Injected
        self.llm = llm

    async def extract(self, notes: Notes) -> List[ActionItem]:
        response = await self.llm.complete(prompt)  # Abstract
```

### Anti-Pattern 5: Real-Time Complexity Before Batch Works

**What:** Building streaming architecture before batch processing is proven.

**Why bad:** Streaming adds significant complexity (stateful processing, backpressure, out-of-order events). Debugging is harder. Most value comes from batch first.

**Instead:** Start with batch (webhook-triggered processing). Prove value. Add streaming only when latency requirements demand it.

## Scalability Considerations

| Concern | At 10 meetings/day | At 100 meetings/day | At 1000 meetings/day |
|---------|-------------------|--------------------|--------------------|
| **Transcript Processing** | Single worker, sequential | Celery workers, parallel | Kafka + multiple workers |
| **Event Store** | SQLite/Turso single table | PostgreSQL with partitioning | TimescaleDB or EventStoreDB |
| **Agent Processing** | Async in-process | Celery task queue | Dedicated agent services |
| **Rollup Computation** | On-demand queries | Materialized views, hourly refresh | Streaming aggregation |
| **LLM Calls** | Direct API calls | Rate-limited queue | Batch API with retries |

## Suggested Build Order

Based on component dependencies:

### Phase 1: Core Foundation
**Must build first. Everything depends on these.**

1. **Canonical Data Model** - Define Meeting, ActionItem, Decision, Risk, Issue, Participant
2. **Event Types** - Define typed events (MeetingCreated, TranscriptReceived, ActionItemExtracted)
3. **Event Bus** - In-memory for v1, can upgrade to Redis/Kafka later
4. **Event Store** - Append-only table in Turso
5. **Zoom Adapter** - Transcript authority, webhook handling
6. **Note-Taker Agent** - Basic transcript -> notes extraction
7. **Task-Assigner Agent** - Notes -> action items extraction

**Rationale:** You need events flowing before anything else matters. Zoom is your source of truth. Agents provide immediate value.

### Phase 2: Integration Loop
**Closes the loop with users. Provides feedback.**

1. **Slack Adapter** - Notifications for action items
2. **Google Calendar Adapter** - Meeting context, participant hierarchy
3. **Smartsheet Adapter** - Task sync (bidirectional)
4. **Summarizer Agent** - Meeting summaries, decision extraction

**Rationale:** Phase 1 extracts data. Phase 2 makes it actionable. Users start seeing value in their existing tools.

### Phase 3: Intelligence Layer
**Hierarchy views. Executive reporting.**

1. **Hierarchy Resolver** - Map participants to org structure
2. **Rollup Engine** - Aggregate action items, risks, decisions by hierarchy
3. **Reporting API** - Dashboard endpoints
4. **Risk/Issue Detection Agent** - Identify blockers, escalations

**Rationale:** Once data flows and syncs, add the intelligence layer that makes this valuable for TPMs and leadership.

### Phase 4: Real-Time (Future)
**Only if latency requirements demand it.**

1. **Zoom RTMS Integration** - Real-time transcript streaming
2. **Streaming Event Bus** - Kafka or Redis Streams
3. **Incremental Agent Processing** - Process transcript chunks

**Rationale:** Batch covers 90% of value. Streaming is expensive complexity. Only add when proven necessary.

## Technology Recommendations

| Layer | Recommended | Why |
|-------|-------------|-----|
| **Event Bus** | In-memory (v1), Redis Pub/Sub (v2) | Simple to start, scales when needed |
| **Event Store** | Turso (SQLite) | Already in your stack, append-only works fine |
| **Task Queue** | Celery + Redis | Mature, well-documented, async support |
| **Agent Framework** | Custom with asyncio | LangGraph overkill for this, CrewAI too opinionated |
| **LLM Abstraction** | LiteLLM or custom | Provider-agnostic, easy model swapping |
| **Transcript Processing** | LLM-based prompting | Better than traditional NLP for action item extraction |

## Sources

- [Four Design Patterns for Event-Driven Multi-Agent Systems - Confluent](https://www.confluent.io/blog/event-driven-multi-agent-systems/)
- [Event Sourcing Pattern - Microsoft Azure](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [CQRS Pattern - Microsoft Azure](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)
- [Hexagonal Architecture - AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/hexagonal-architecture.html)
- [Adapter Service Pattern for Microservices](https://medium.com/@jescrich_57703/harnessing-the-adapter-pattern-in-microservice-architectures-for-vendor-agnosticism-debc21d2fe21)
- [Zoom Transcript API Tutorial - Recall.ai](https://www.recall.ai/blog/zoom-transcript-api)
- [Action-Item-Driven Summarization - arXiv](https://arxiv.org/abs/2312.17581)
- [Meeting Summarization with Amazon Nova - AWS](https://aws.amazon.com/blogs/machine-learning/meeting-summarization-and-action-item-extraction-with-amazon-nova/)
- [Multi-Agent System Architecture for Enterprises - Ampcome](https://www.ampcome.com/post/multi-agent-system-architecture-for-enterprises)
- [Python Event-Driven Architecture - ToTheNew](https://www.tothenew.com/blog/design-implement-a-event-driven-architecture-in-python/)
- [Batch vs Stream Processing - OpenSourceForU](https://www.opensourceforu.com/2025/10/batch-processing-or-streaming-whats-better/)
- [Hierarchical Rollup Architecture - FasterCapital](https://fastercapital.com/content/Rollup-hierarchy--Organizing-Data-Hierarchically-with-Rollups.html)
