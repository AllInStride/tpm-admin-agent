# Phase 9: Communication Automation - Research

**Researched:** 2026-01-19
**Domain:** LLM-driven communication artifacts, status updates, escalation emails, exec talking points
**Confidence:** HIGH

## Summary

Phase 9 generates communication artifacts for different audiences. The existing codebase provides all necessary infrastructure: `LLMClient` for text generation with structured outputs, `OpenItemsRepository` for querying RAID items, `FTSService` for searching meeting content, `MinutesRenderer` with Jinja2 templating, and `SlackAdapter` for delivery.

The core challenge is **prompt engineering** for four distinct output types: exec status updates (half-page summaries with RAG indicators), team status updates (detailed action item lists), escalation emails (Problem-Impact-Ask format), and exec talking points (narrative with Q&A). Each requires different tone, structure, and data aggregation.

The standard approach is:
1. **Data aggregation service** that queries existing repositories for the time period and project scope
2. **LLM generation** using structured output prompts following the existing extraction pattern
3. **Template rendering** for final formatting (plain text + markdown per CONTEXT.md)
4. **Delivery adapters** (existing Slack/email infrastructure)

**Primary recommendation:** Create a `CommunicationService` that orchestrates data gathering and LLM generation, with separate generators for each artifact type. Use the existing `LLMClient` with structured output schemas to ensure consistent formatting. Templates handle final presentation layer.

## Standard Stack

The established libraries/tools for this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.76+ | LLM text generation | Already in codebase, structured outputs for reliable formatting |
| Jinja2 | 3.1.6+ | Template rendering | Already in codebase via MinutesRenderer, supports plain text and markdown |
| pydantic | 2.12.5+ | Output schemas | Already in codebase, structured output validation |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 25.5.0+ | Audit logging | Track generation requests and outputs |
| tenacity | 9.0.0+ | Retry logic | LLM call reliability |
| slack-sdk | 3.35.0+ | Delivery | Slack DM notifications (existing) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Structured outputs | Free-form generation | Structured outputs guarantee schema compliance; free-form risks format drift |
| Jinja2 templates | LLM-generated formatting | Templates ensure consistent structure; LLM formatting is unpredictable |
| Single prompt | Multi-shot prompting | Single prompt simpler; multi-shot only if quality insufficient |

**Installation:**
No new dependencies required. All libraries already in project.

## Architecture Patterns

### Recommended Project Structure

```
src/
|-- communication/               # NEW: Communication automation module
|   |-- __init__.py
|   |-- schemas.py              # Output schemas for all artifact types
|   |-- prompts.py              # LLM prompts for generation
|   |-- data_aggregator.py      # Gathers data for time period/project
|   |-- generators/
|   |   |-- __init__.py
|   |   |-- exec_status.py      # COM-01: Exec status generator
|   |   |-- team_status.py      # COM-02: Team status generator
|   |   |-- escalation.py       # COM-03: Escalation email generator
|   |   |-- talking_points.py   # COM-04: Talking points generator
|   |-- service.py              # CommunicationService orchestrator
|   |-- templates/              # Jinja2 output templates
|       |-- exec_status.md.j2
|       |-- exec_status.txt.j2
|       |-- team_status.md.j2
|       |-- team_status.txt.j2
|       |-- escalation_email.txt.j2
|       |-- talking_points.md.j2
|-- api/
|   |-- communication.py        # NEW: API endpoints
```

### Pattern 1: Data Aggregation Before Generation

**What:** Gather all relevant data before calling LLM. The LLM synthesizes, not retrieves.

**When to use:** Always. LLMs generate better content when given complete context.

**Example:**
```python
# src/communication/data_aggregator.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StatusData:
    """Aggregated data for status generation."""

    project_name: str
    time_period: tuple[datetime, datetime]

    # Progress
    completed_items: list[dict]      # Items closed in period
    new_items: list[dict]            # Items created in period
    open_items: list[dict]           # Currently open

    # RAID summary
    decisions: list[dict]            # Key decisions made
    risks: list[dict]                # Active risks
    issues: list[dict]               # Open issues
    blockers: list[dict]             # Items blocking progress

    # Meetings
    meetings_held: list[dict]        # Meetings in period

    # Metrics
    item_velocity: int               # Items closed vs opened
    overdue_count: int               # Items past due date


class DataAggregator:
    """Aggregates data from repositories for communication artifacts."""

    def __init__(
        self,
        open_items_repo: OpenItemsRepository,
        fts_service: FTSService,
        projection_repo: ProjectionRepository,
    ):
        self._items = open_items_repo
        self._fts = fts_service
        self._projections = projection_repo

    async def gather_for_status(
        self,
        project_id: str,
        since: datetime,
        until: datetime | None = None,
    ) -> StatusData:
        """Gather all data needed for status generation.

        Args:
            project_id: Project scope
            since: Start of period (e.g., last status update)
            until: End of period (default: now)

        Returns:
            StatusData with all relevant items aggregated
        """
        until = until or datetime.now()

        # Query in parallel
        completed, new, open_items, meetings = await asyncio.gather(
            self._get_completed_items(project_id, since, until),
            self._get_new_items(project_id, since, until),
            self._get_open_items(project_id),
            self._get_meetings(project_id, since, until),
        )

        # Derive blockers, risks, issues from open items
        blockers = [i for i in open_items if self._is_blocker(i)]
        risks = [i for i in open_items if i['item_type'] == 'risk']
        issues = [i for i in open_items if i['item_type'] == 'issue']
        decisions = [i for i in new if i['item_type'] == 'decision']

        return StatusData(
            project_name=project_id,  # Lookup actual name
            time_period=(since, until),
            completed_items=completed,
            new_items=new,
            open_items=open_items,
            decisions=decisions,
            risks=risks,
            issues=issues,
            blockers=blockers,
            meetings_held=meetings,
            item_velocity=len(completed) - len(new),
            overdue_count=len([i for i in open_items if i.get('is_overdue')]),
        )
```

### Pattern 2: Structured Output Generation

**What:** Define Pydantic schemas for LLM output, use `LLMClient.extract()` for generation.

**When to use:** Always. Ensures consistent, parseable output.

**Example:**
```python
# src/communication/schemas.py
from pydantic import BaseModel, Field

class ExecStatusOutput(BaseModel):
    """LLM-generated exec status content."""

    overall_rag: str = Field(
        description="Overall status: GREEN, AMBER, or RED"
    )
    scope_rag: str = Field(
        description="Scope status: GREEN, AMBER, or RED"
    )
    schedule_rag: str = Field(
        description="Schedule status: GREEN, AMBER, or RED"
    )
    risk_rag: str = Field(
        description="Risk status: GREEN, AMBER, or RED"
    )

    summary: str = Field(
        description="2-3 sentence executive summary"
    )

    key_progress: list[str] = Field(
        description="3-5 key progress highlights (team references, not names)"
    )

    key_decisions: list[str] = Field(
        description="Key decisions made this period"
    )

    blockers: list[dict] = Field(
        description="Blockers with explicit ask from exec"
    )

    risks: list[str] = Field(
        description="Active risks requiring awareness"
    )

    next_period: list[str] = Field(
        description="3-5 items expected next period"
    )


class EscalationOutput(BaseModel):
    """LLM-generated escalation email content."""

    subject: str = Field(
        description="Email subject line (clear, specific)"
    )

    problem: str = Field(
        description="Clear statement of the problem (2-3 sentences)"
    )

    impact: str = Field(
        description="Business/project impact if not resolved"
    )

    deadline: str = Field(
        description="When decision is needed (specific date)"
    )

    options: list[dict] = Field(
        description="2-3 options with pros/cons"
    )

    recommendation: str | None = Field(
        default=None,
        description="Recommended option if appropriate"
    )

    context_summary: str | None = Field(
        default=None,
        description="Brief history if relevant (1-2 sentences)"
    )
```

### Pattern 3: Prompt Template with Context

**What:** Prompts follow "context first, instructions after" pattern established in extraction prompts.

**When to use:** Always. Avoids "lost in the middle" problem with long context.

**Example:**
```python
# src/communication/prompts.py

EXEC_STATUS_PROMPT = """You are an expert TPM writing a status update for executive leadership.

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

TONE:
- Direct and confident
- Facts over opinions
- No hedging language ("somewhat", "fairly")

IMPORTANT:
- Do not invent information not present in the data
- If data is insufficient for a section, note "No updates this period"
- Blockers must have a clear ASK - what do you need from the exec?
"""

ESCALATION_PROMPT = """You are an expert TPM writing an escalation email to request a decision.

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

IMPORTANT:
- Always include options for the recipient
- Never bury the ask - it should be immediately clear
- Keep history section brief (only include if truly relevant)
"""
```

### Pattern 4: Template-Based Final Formatting

**What:** LLM generates structured content, templates handle final presentation.

**When to use:** Always. Separates content from presentation, enables format switching.

**Example:**
```jinja2
{# templates/exec_status.md.j2 #}
# Status Update: {{ project_name }}

**Period:** {{ period_start | dateformat }} - {{ period_end | dateformat }}
**Overall Status:** {{ overall_rag | rag_badge }}

## RAG Breakdown

| Dimension | Status |
|-----------|--------|
| Scope | {{ scope_rag | rag_badge }} |
| Schedule | {{ schedule_rag | rag_badge }} |
| Risk | {{ risk_rag | rag_badge }} |

## Summary

{{ summary }}

## Key Progress

{% for item in key_progress %}
- {{ item }}
{% endfor %}

{% if key_decisions %}
## Decisions Made

{% for decision in key_decisions %}
- {{ decision }}
{% endfor %}
{% endif %}

{% if blockers %}
## Blockers (Action Required)

{% for blocker in blockers %}
### {{ blocker.title }}

{{ blocker.problem }}

**Ask:** {{ blocker.ask }}

{% endfor %}
{% endif %}

{% if risks %}
## Active Risks

{% for risk in risks %}
- {{ risk }}
{% endfor %}
{% endif %}

## Next Period

{% for item in next_period %}
- {{ item }}
{% endfor %}

---
*Generated: {{ generated_at | dateformat }}*
*Source meetings: {{ source_meetings | join(', ') }}*
```

### Pattern 5: Audience-Aware Generators

**What:** Separate generator classes for each audience type, sharing common infrastructure.

**When to use:** When output requirements differ significantly (exec vs team vs escalation).

**Example:**
```python
# src/communication/generators/base.py
from abc import ABC, abstractmethod

class BaseGenerator(ABC):
    """Base class for communication artifact generators."""

    def __init__(
        self,
        llm_client: LLMClient,
        template_dir: str = "src/communication/templates",
    ):
        self._llm = llm_client
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @abstractmethod
    async def generate(self, data: StatusData, **kwargs) -> GeneratedArtifact:
        """Generate the communication artifact."""
        pass

    def _render_template(
        self,
        template_name: str,
        context: dict,
    ) -> tuple[str, str]:
        """Render both markdown and plain text versions.

        Returns:
            Tuple of (markdown, plain_text)
        """
        md_template = self._env.get_template(f"{template_name}.md.j2")
        txt_template = self._env.get_template(f"{template_name}.txt.j2")

        return (
            md_template.render(context),
            txt_template.render(context),
        )


# src/communication/generators/exec_status.py
class ExecStatusGenerator(BaseGenerator):
    """Generates executive status updates per COM-01."""

    async def generate(
        self,
        data: StatusData,
        *,
        include_lookahead: bool = True,
    ) -> GeneratedArtifact:
        """Generate exec status update.

        Args:
            data: Aggregated status data
            include_lookahead: Whether to include next period section

        Returns:
            GeneratedArtifact with markdown and plain text
        """
        # Format data for prompt
        prompt = EXEC_STATUS_PROMPT.format(
            project_name=data.project_name,
            period_start=data.time_period[0].strftime('%Y-%m-%d'),
            period_end=data.time_period[1].strftime('%Y-%m-%d'),
            completed_items=self._format_items(data.completed_items),
            completed_count=len(data.completed_items),
            # ... more formatting
        )

        # Generate structured content via LLM
        output = await self._llm.extract(prompt, ExecStatusOutput)

        # Render templates
        context = output.model_dump()
        context['project_name'] = data.project_name
        context['period_start'] = data.time_period[0]
        context['period_end'] = data.time_period[1]
        context['generated_at'] = datetime.now()
        context['source_meetings'] = [m['title'] for m in data.meetings_held]

        markdown, plain_text = self._render_template('exec_status', context)

        return GeneratedArtifact(
            artifact_type='exec_status',
            markdown=markdown,
            plain_text=plain_text,
            metadata={'rag_overall': output.overall_rag},
        )
```

### Anti-Patterns to Avoid

- **LLM for data retrieval:** Don't ask LLM to find items. Use repositories, give LLM results to synthesize.
- **Free-form output:** Don't let LLM decide structure. Use structured outputs for consistency.
- **Single generator for all:** Don't create one generator handling all types. Keep separate for maintainability.
- **Names in exec updates:** Per CONTEXT.md, reference teams not individuals in exec status.
- **Missing explicit ask:** Escalations must have clear ask. Validate output includes one.
- **RAG without criteria:** Don't let LLM hallucinate RAG status. Provide explicit criteria in prompt.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text generation | Custom ML models | LLMClient with Anthropic | Already works, structured outputs |
| Template rendering | String formatting | Jinja2 (existing MinutesRenderer) | Filters, inheritance, escaping |
| Data queries | New SQL queries | OpenItemsRepository methods | Already handles filtering, grouping |
| Meeting search | New FTS queries | FTSService.search() | Already handles escaping, ranking |
| Delivery | Custom email/Slack | Existing adapters | SlackAdapter, email via integration |
| Retry logic | Custom loops | tenacity (existing) | Battle-tested, already in codebase |

**Key insight:** Phase 9 is primarily orchestration and prompting. The hard infrastructure work is done in Phases 1-8.

## Common Pitfalls

### Pitfall 1: LLM Inventing Data

**What goes wrong:** LLM adds items, dates, or names not in the source data.

**Why it happens:** LLMs are generative and try to be helpful.

**How to avoid:**
- Explicit instruction: "Do not invent information not present in the data"
- Provide complete data in prompt (items, dates, names)
- Use structured outputs that map to source data
- Post-generation validation: verify items exist in source

**Warning signs:** Status update contains items not in database.

### Pitfall 2: Inconsistent RAG Indicators

**What goes wrong:** RAG status doesn't match reality (GREEN when should be RED).

**Why it happens:** LLM lacks objective criteria for RAG assignment.

**How to avoid:**
- Define explicit RAG criteria in prompt
- Consider rule-based RAG with LLM override
- Include metrics in prompt (overdue count, blocker count)
- Example: `if overdue > 3 or blockers > 0: suggest AMBER or RED`

**Warning signs:** User manually corrects RAG status frequently.

### Pitfall 3: Vague Escalation Asks

**What goes wrong:** Escalation email doesn't have clear ask, recipient unsure what to do.

**Why it happens:** LLM generates polite but unclear requests.

**How to avoid:**
- Structured output requires `options` and `deadline` fields
- Template puts ask first (not buried at end)
- Validation: reject output without explicit deadline
- Example options format enforced: "Option A: [action] - Pros: X, Cons: Y"

**Warning signs:** Escalation recipients ask "what do you need from me?"

### Pitfall 4: Exec Status Too Long

**What goes wrong:** Exec update becomes multi-page document.

**Why it happens:** LLM tries to be thorough, includes everything.

**How to avoid:**
- Per CONTEXT.md: "half page (5-7 bullet points with context)"
- Limit data in prompt (top 5 items per category)
- Structured output with list length constraints
- Post-generation truncation if needed

**Warning signs:** Execs don't read full update, miss key items.

### Pitfall 5: Team Status Missing Completed Items

**What goes wrong:** Team doesn't see what was accomplished, only what's still open.

**Why it happens:** Focus on "what needs to be done" over "what was done."

**How to avoid:**
- Per CONTEXT.md: "Include completed items section to celebrate wins"
- Query completed items explicitly in data aggregation
- Template has dedicated "Completed This Period" section first
- Highlight "shipped", "closed", "done" items prominently

**Warning signs:** Team morale low despite progress; wins not visible.

### Pitfall 6: Talking Points Without Q&A

**What goes wrong:** Exec unprepared for obvious questions in review.

**Why it happens:** Generator focuses on narrative, forgets defensive prep.

**How to avoid:**
- Per CONTEXT.md: "key bullet points + anticipated Q&A section"
- Structured output requires `anticipated_questions` field
- Prompt explicitly asks for risk/concern, resource, and other questions
- Template dedicates section to Q&A

**Warning signs:** Exec asks "what if they ask about X?" after receiving talking points.

## Code Examples

Verified patterns from existing codebase and official sources:

### CommunicationService Orchestrator

```python
# src/communication/service.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import structlog

from src.communication.data_aggregator import DataAggregator, StatusData
from src.communication.generators.exec_status import ExecStatusGenerator
from src.communication.generators.team_status import TeamStatusGenerator
from src.communication.generators.escalation import EscalationGenerator
from src.communication.generators.talking_points import TalkingPointsGenerator
from src.communication.schemas import GeneratedArtifact, EscalationRequest
from src.services.llm_client import LLMClient

logger = structlog.get_logger()

ArtifactType = Literal['exec_status', 'team_status', 'escalation', 'talking_points']


@dataclass
class GenerationResult:
    """Result of artifact generation."""

    artifact_type: ArtifactType
    artifact: GeneratedArtifact
    data_used: StatusData | None
    generated_at: datetime


class CommunicationService:
    """Orchestrates communication artifact generation.

    Entry point for all communication automation features.
    Handles data gathering, generation, and audit logging.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        data_aggregator: DataAggregator,
    ):
        self._llm = llm_client
        self._aggregator = data_aggregator

        # Initialize generators
        self._exec_status = ExecStatusGenerator(llm_client)
        self._team_status = TeamStatusGenerator(llm_client)
        self._escalation = EscalationGenerator(llm_client)
        self._talking_points = TalkingPointsGenerator(llm_client)

    async def generate_exec_status(
        self,
        project_id: str,
        since: datetime,
        until: datetime | None = None,
    ) -> GenerationResult:
        """Generate executive status update (COM-01).

        Args:
            project_id: Project to report on
            since: Start of reporting period
            until: End of period (default: now)

        Returns:
            GenerationResult with markdown and plain text
        """
        logger.info(
            "generating exec status",
            project_id=project_id,
            since=since.isoformat(),
        )

        # Gather data
        data = await self._aggregator.gather_for_status(
            project_id=project_id,
            since=since,
            until=until,
        )

        # Generate artifact
        artifact = await self._exec_status.generate(data)

        logger.info(
            "exec status generated",
            project_id=project_id,
            rag=artifact.metadata.get('rag_overall'),
        )

        return GenerationResult(
            artifact_type='exec_status',
            artifact=artifact,
            data_used=data,
            generated_at=datetime.now(),
        )

    async def generate_team_status(
        self,
        project_id: str,
        since: datetime,
        until: datetime | None = None,
    ) -> GenerationResult:
        """Generate team status update (COM-02).

        Args:
            project_id: Project to report on
            since: Start of reporting period
            until: End of period (default: now)

        Returns:
            GenerationResult with detailed team status
        """
        data = await self._aggregator.gather_for_status(
            project_id=project_id,
            since=since,
            until=until,
        )

        artifact = await self._team_status.generate(data)

        return GenerationResult(
            artifact_type='team_status',
            artifact=artifact,
            data_used=data,
            generated_at=datetime.now(),
        )

    async def generate_escalation(
        self,
        request: EscalationRequest,
    ) -> GenerationResult:
        """Generate escalation email (COM-03).

        Args:
            request: EscalationRequest with problem details and options

        Returns:
            GenerationResult with Problem-Impact-Ask formatted email
        """
        artifact = await self._escalation.generate(request)

        return GenerationResult(
            artifact_type='escalation',
            artifact=artifact,
            data_used=None,  # Escalations use request data, not aggregated
            generated_at=datetime.now(),
        )

    async def generate_talking_points(
        self,
        project_id: str,
        meeting_type: str,
        since: datetime | None = None,
    ) -> GenerationResult:
        """Generate exec talking points (COM-04).

        Args:
            project_id: Project for the review
            meeting_type: Type of meeting (e.g., 'steerco', 'exec_review')
            since: Period to cover (default: since last similar meeting)

        Returns:
            GenerationResult with bullet points and Q&A
        """
        # If no since, find last similar meeting
        if since is None:
            since = await self._aggregator.find_last_meeting_date(
                project_id=project_id,
                meeting_type=meeting_type,
            )

        data = await self._aggregator.gather_for_status(
            project_id=project_id,
            since=since,
        )

        artifact = await self._talking_points.generate(
            data,
            meeting_type=meeting_type,
        )

        return GenerationResult(
            artifact_type='talking_points',
            artifact=artifact,
            data_used=data,
            generated_at=datetime.now(),
        )
```

### Escalation Generator with Options

```python
# src/communication/generators/escalation.py
from src.communication.generators.base import BaseGenerator
from src.communication.prompts import ESCALATION_PROMPT
from src.communication.schemas import EscalationOutput, EscalationRequest, GeneratedArtifact


class EscalationGenerator(BaseGenerator):
    """Generates escalation emails per COM-03.

    Per CONTEXT.md:
    - Problem-Impact-Ask format
    - Explicit deadline
    - Always include options (A, B, or C)
    - Matter-of-fact tone
    """

    async def generate(
        self,
        request: EscalationRequest,
    ) -> GeneratedArtifact:
        """Generate escalation email.

        Args:
            request: EscalationRequest with problem and options

        Returns:
            GeneratedArtifact with email content
        """
        # Format options for prompt
        options_text = self._format_options(request.options)

        # Build prompt
        prompt = ESCALATION_PROMPT.format(
            problem_description=request.problem_description,
            timeline_impact=request.timeline_impact or "Not specified",
            resource_impact=request.resource_impact or "Not specified",
            business_impact=request.business_impact or "Not specified",
            history_context=request.history_context or "No prior history",
            options_data=options_text,
            decision_deadline=request.decision_deadline.strftime('%Y-%m-%d'),
        )

        # Generate via LLM
        output = await self._llm.extract(prompt, EscalationOutput)

        # Validate output has required elements
        if not output.options or len(output.options) < 2:
            raise ValueError("Escalation must have at least 2 options")
        if not output.deadline:
            raise ValueError("Escalation must have explicit deadline")

        # Render template
        context = output.model_dump()
        context['recipient'] = request.recipient
        context['generated_at'] = datetime.now()

        markdown, plain_text = self._render_template('escalation_email', context)

        return GeneratedArtifact(
            artifact_type='escalation',
            markdown=markdown,
            plain_text=plain_text,
            metadata={
                'subject': output.subject,
                'deadline': output.deadline,
                'option_count': len(output.options),
            },
        )

    def _format_options(self, options: list[dict]) -> str:
        """Format options for prompt context."""
        lines = []
        for i, opt in enumerate(options, 1):
            label = chr(64 + i)  # A, B, C
            lines.append(f"Option {label}: {opt['description']}")
            if opt.get('pros'):
                lines.append(f"  Pros: {opt['pros']}")
            if opt.get('cons'):
                lines.append(f"  Cons: {opt['cons']}")
        return "\n".join(lines)
```

### Talking Points with Q&A

```python
# src/communication/generators/talking_points.py
from src.communication.generators.base import BaseGenerator
from src.communication.prompts import TALKING_POINTS_PROMPT
from src.communication.schemas import TalkingPointsOutput, GeneratedArtifact
from src.communication.data_aggregator import StatusData


class TalkingPointsGenerator(BaseGenerator):
    """Generates exec talking points per COM-04.

    Per CONTEXT.md:
    - Key bullet points + anticipated Q&A section
    - Focus on narrative/story with supporting data
    - Comprehensive Q&A coverage (risk/concern + resource + other)
    """

    async def generate(
        self,
        data: StatusData,
        *,
        meeting_type: str = "exec_review",
    ) -> GeneratedArtifact:
        """Generate talking points for exec review.

        Args:
            data: Aggregated status data
            meeting_type: Type of meeting for context

        Returns:
            GeneratedArtifact with talking points and Q&A
        """
        # Build prompt with narrative focus
        prompt = TALKING_POINTS_PROMPT.format(
            project_name=data.project_name,
            meeting_type=meeting_type,
            period_start=data.time_period[0].strftime('%Y-%m-%d'),
            period_end=data.time_period[1].strftime('%Y-%m-%d'),
            key_progress=self._format_items(data.completed_items[:5]),
            decisions=self._format_items(data.decisions[:3]),
            risks=self._format_items(data.risks[:5]),
            issues=self._format_items(data.issues[:5]),
            blockers=self._format_items(data.blockers),
            metrics=self._format_metrics(data),
        )

        # Generate via LLM
        output = await self._llm.extract(prompt, TalkingPointsOutput)

        # Validate Q&A coverage
        qa_categories = {q['category'] for q in output.anticipated_qa}
        required = {'risk', 'resource'}
        missing = required - qa_categories
        if missing:
            # Re-prompt or add defaults for missing categories
            pass

        # Render template
        context = output.model_dump()
        context['project_name'] = data.project_name
        context['meeting_type'] = meeting_type
        context['generated_at'] = datetime.now()

        markdown, plain_text = self._render_template('talking_points', context)

        return GeneratedArtifact(
            artifact_type='talking_points',
            markdown=markdown,
            plain_text=plain_text,
            metadata={
                'point_count': len(output.key_points),
                'qa_count': len(output.anticipated_qa),
            },
        )

    def _format_metrics(self, data: StatusData) -> str:
        """Format key metrics for prompt."""
        return f"""
Items completed: {len(data.completed_items)}
Items opened: {len(data.new_items)}
Net velocity: {data.item_velocity:+d}
Currently open: {len(data.open_items)}
Overdue items: {data.overdue_count}
Active risks: {len(data.risks)}
Open issues: {len(data.issues)}
Blockers: {len(data.blockers)}
Meetings held: {len(data.meetings_held)}
"""
```

### API Endpoints

```python
# src/api/communication.py
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.communication.service import CommunicationService, GenerationResult
from src.communication.schemas import EscalationRequest

router = APIRouter(prefix="/communication", tags=["communication"])


class StatusRequest(BaseModel):
    """Request for status generation."""

    project_id: str = Field(description="Project ID to report on")
    since: datetime = Field(description="Start of reporting period")
    until: datetime | None = Field(default=None, description="End of period")


class TalkingPointsRequest(BaseModel):
    """Request for talking points generation."""

    project_id: str
    meeting_type: str = Field(default="exec_review")
    since: datetime | None = None


class GenerationResponse(BaseModel):
    """Response from generation endpoint."""

    artifact_type: str
    markdown: str
    plain_text: str
    generated_at: datetime
    metadata: dict


@router.post("/exec-status", response_model=GenerationResponse)
async def generate_exec_status(
    request: StatusRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate executive status update (COM-01)."""
    result = await service.generate_exec_status(
        project_id=request.project_id,
        since=request.since,
        until=request.until,
    )
    return _to_response(result)


@router.post("/team-status", response_model=GenerationResponse)
async def generate_team_status(
    request: StatusRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate team status update (COM-02)."""
    result = await service.generate_team_status(
        project_id=request.project_id,
        since=request.since,
        until=request.until,
    )
    return _to_response(result)


@router.post("/escalation", response_model=GenerationResponse)
async def generate_escalation(
    request: EscalationRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate escalation email (COM-03)."""
    result = await service.generate_escalation(request)
    return _to_response(result)


@router.post("/talking-points", response_model=GenerationResponse)
async def generate_talking_points(
    request: TalkingPointsRequest,
    service: Annotated[CommunicationService, Depends(get_communication_service)],
) -> GenerationResponse:
    """Generate exec talking points (COM-04)."""
    result = await service.generate_talking_points(
        project_id=request.project_id,
        meeting_type=request.meeting_type,
        since=request.since,
    )
    return _to_response(result)


def _to_response(result: GenerationResult) -> GenerationResponse:
    """Convert GenerationResult to API response."""
    return GenerationResponse(
        artifact_type=result.artifact_type,
        markdown=result.artifact.markdown,
        plain_text=result.artifact.plain_text,
        generated_at=result.generated_at,
        metadata=result.artifact.metadata,
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual status writing | LLM-assisted generation with RAG | 2024+ | Faster, more consistent |
| Template-only formatting | LLM synthesis + template presentation | 2024+ | Better narrative quality |
| Free-form LLM output | Structured outputs with schemas | Late 2024 | Reliable, parseable |
| Single prompt for all | Audience-specific generators | Best practice | Better fit per audience |

**Deprecated/outdated:**
- Asking LLM to retrieve data (use repositories instead)
- Free-form JSON output (use structured outputs for reliability)
- Single "write a status update" prompt (too vague, inconsistent results)

## Open Questions

Things that couldn't be fully resolved:

1. **Delta tracking for exec status**
   - What we know: CONTEXT.md says "since last update"
   - What's unclear: How to track when last update was sent
   - Recommendation: Store `last_status_sent` timestamp per project in new table, or accept user-provided `since` date

2. **Recipient inference for escalations**
   - What we know: CONTEXT.md says "user specifies, infer from chain, or use templates"
   - What's unclear: What "infer from chain" means (email thread? project hierarchy?)
   - Recommendation: Start with user-specified; add escalation path templates later

3. **RAG indicator calculation**
   - What we know: Need overall + scope/schedule/risk breakdown
   - What's unclear: Whether to use rule-based, LLM-based, or hybrid
   - Recommendation: Hybrid - rules suggest, LLM can override with justification; log for tuning

4. **Meeting footnotes in exec status**
   - What we know: CONTEXT.md says "Source meetings referenced in footnotes"
   - What's unclear: Footnote format in plain text vs markdown
   - Recommendation: Markdown supports `[^1]` footnotes; plain text uses `[1]` style

## Sources

### Primary (HIGH confidence)
- Existing codebase: `LLMClient`, `OpenItemsRepository`, `FTSService`, `MinutesRenderer`
- Existing extraction prompts: `src/extraction/prompts.py` pattern for structured outputs
- Existing schemas: `src/output/schemas.py` for output model patterns

### Secondary (MEDIUM confidence)
- [Project Status Updates Framework](https://winningpresentations.com/project-status-update-framework/) - Executive status structure
- [AI for Work: Executive Briefing](https://www.aiforwork.co/prompt-articles/chatgpt-prompt-executive-assistant-administrative-create-an-executive-briefing-document) - Briefing document format
- [RAG for Structured Data](https://www.ai21.com/knowledge/rag-for-structured-data/) - Using RAG with structured outputs
- [Lindy.ai Escalation Workflows](https://www.lindy.ai/blog/ai-email-assistant) - Escalation automation patterns

### Tertiary (LOW confidence)
- WebSearch results for LLM project management - General patterns verified against existing codebase
- WebSearch results for AI email automation - Enterprise escalation patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing codebase infrastructure
- Architecture: HIGH - Extends proven patterns from Phases 3, 5, 8
- Pitfalls: MEDIUM - Based on LLM generation experience, may need tuning
- Prompts: MEDIUM - Will require iteration based on output quality

**Research date:** 2026-01-19
**Valid until:** 2026-02-19 (30 days - stable patterns, may need prompt tuning)
