# Phase 3: RAID Extraction - Research

**Researched:** 2026-01-18
**Domain:** LLM-based structured data extraction from meeting transcripts
**Confidence:** HIGH

## Summary

Phase 3 requires extracting RAID artifacts (Risks, Actions, Issues, Decisions) from parsed meeting transcripts using LLM-based extraction. The existing codebase has domain models (ActionItem, Decision, Risk, Issue) with confidence scores and all event types (ActionItemExtracted, DecisionExtracted, etc.) already defined. Phase 2 provides ParsedTranscript with utterances and speakers.

The standard approach for LLM structured extraction in Python 2025 uses either (1) Anthropic's native structured outputs (beta) with Pydantic via `client.beta.messages.parse()`, or (2) the Instructor library which provides retries, validation, and works with multiple providers. Given this project uses FastAPI + Pydantic v2 and needs confidence scores, the Anthropic native approach is recommended for its simplicity and tight Pydantic integration.

Key considerations: prompt engineering for RAID extraction requires explicit instructions with examples, confidence score calibration needs verbalized confidence from the LLM, and relative date parsing (e.g., "next Friday") requires the dateparser library.

**Primary recommendation:** Use Anthropic SDK structured outputs with Pydantic models for extraction. Define extraction-specific Pydantic models that include confidence scores as required fields. Use dateparser library for normalizing due dates.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | ^0.76.0 | LLM API client | Official SDK, native Pydantic support |
| dateparser | ^1.2.2 | Natural language date parsing | 200+ language locales, handles relative dates |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| instructor | ^1.7.5 | Structured extraction with retries | If switching LLM providers or needing advanced retry logic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Anthropic native | Instructor library | Instructor adds retry logic but adds dependency; native is simpler for single-provider |
| dateparser | python-dateutil | dateutil handles fewer natural language formats; dateparser better for "next week" style |

**Installation:**
```bash
uv add anthropic dateparser
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── services/
│   ├── transcript_parser.py    # Existing from Phase 2
│   ├── raid_extractor.py       # NEW: Orchestrates RAID extraction
│   └── llm_client.py           # NEW: Anthropic client wrapper
├── extraction/                  # NEW: Extraction-specific code
│   ├── __init__.py
│   ├── prompts.py              # System prompts for each RAID type
│   ├── schemas.py              # Pydantic models for LLM output
│   └── date_normalizer.py      # dateparser wrapper
└── models/                      # Existing domain models
```

### Pattern 1: Extraction Service with Dependency Injection
**What:** RAIDExtractor service that receives LLM client via constructor
**When to use:** Enables testing with mock LLM responses
**Example:**
```python
# Source: Project architecture pattern
class RAIDExtractor:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    async def extract_all(
        self,
        transcript: ParsedTranscript,
        meeting_id: UUID
    ) -> ExtractionResult:
        """Extract all RAID items from transcript."""
        # Concatenate utterances for LLM input
        text = self._format_transcript(transcript)

        # Extract each type
        actions = await self._extract_actions(text, meeting_id)
        decisions = await self._extract_decisions(text, meeting_id)
        risks = await self._extract_risks(text, meeting_id)
        issues = await self._extract_issues(text, meeting_id)

        return ExtractionResult(
            action_items=actions,
            decisions=decisions,
            risks=risks,
            issues=issues
        )
```

### Pattern 2: Pydantic Models for LLM Output Schema
**What:** Separate Pydantic models for LLM extraction vs. domain storage
**When to use:** LLM output schema differs from storage schema (e.g., raw date strings vs. date objects)
**Example:**
```python
# Source: Anthropic structured outputs documentation
from pydantic import BaseModel, Field

class ExtractedActionItem(BaseModel):
    """Schema for LLM extraction output."""
    description: str = Field(description="What needs to be done")
    assignee_name: str | None = Field(
        default=None,
        description="Name of person assigned, exactly as mentioned"
    )
    due_date_raw: str | None = Field(
        default=None,
        description="Due date as mentioned (e.g., 'next Friday', 'end of month')"
    )
    source_quote: str = Field(
        description="Exact quote from transcript supporting this action item"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence this is a real action item (0.0-1.0)"
    )

class ExtractionResponse(BaseModel):
    """Container for multiple extracted items."""
    items: list[ExtractedActionItem]
```

### Pattern 3: Quote Extraction for Confidence
**What:** Require source_quote in schema, use it to verify extraction quality
**When to use:** Always - provides audit trail and helps calibrate confidence
**Example:**
```python
# Source: Anthropic long context prompting guide
system_prompt = """You are extracting action items from a meeting transcript.

For each action item found:
1. First, identify the EXACT quote from the transcript
2. Then extract the structured data
3. Assess confidence based on how explicit the commitment was

Confidence guidelines:
- 0.9-1.0: Explicit commitment with clear owner ("I will", "John, can you")
- 0.7-0.9: Implied commitment or clear task ("We need to", followed by name)
- 0.5-0.7: Possible task mentioned but owner unclear
- Below 0.5: Don't extract, too uncertain

Return ONLY items with confidence >= 0.5"""
```

### Anti-Patterns to Avoid
- **Extracting without source quotes:** Makes it impossible to verify extraction quality or debug issues
- **Using domain models directly for LLM output:** Domain models have UUIDs, timestamps; LLM shouldn't generate these
- **Single extraction call for all RAID types:** Separate prompts per type yield better results than one mega-prompt
- **Hardcoding confidence thresholds:** Make thresholds configurable for tuning

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date parsing | Regex for "next week" | dateparser library | Handles 200+ locales, relative dates, edge cases |
| JSON from LLM | String parsing + json.loads | Anthropic structured outputs | Constrained decoding guarantees valid schema |
| Retry on validation failure | Custom retry loops | Instructor or manual retry with error feedback | Proven retry with validation error in prompt |
| Meeting date context | Hardcode "today" | Pass meeting date to dateparser's PREFER_DATES_FROM | Dates relative to meeting, not extraction time |

**Key insight:** LLM structured extraction is a solved problem in 2025. The challenge is prompt engineering for RAID-specific patterns, not building extraction infrastructure.

## Common Pitfalls

### Pitfall 1: Confidence Score Miscalibration
**What goes wrong:** LLM assigns 0.95 confidence to weak signals, or 0.5 to obvious commitments
**Why it happens:** Without explicit guidance, LLMs default to high confidence
**How to avoid:**
- Provide explicit confidence rubric in prompt (see Pattern 3)
- Include few-shot examples with labeled confidence scores
- Consider post-hoc calibration based on extraction quality metrics
**Warning signs:** All extractions cluster at 0.8-0.9 regardless of clarity

### Pitfall 2: Relative Date Without Context
**What goes wrong:** "Next Friday" extracted as date, but which Friday?
**Why it happens:** dateparser uses current date by default, not meeting date
**How to avoid:**
```python
from dateparser import parse
from dateparser.search import search_dates

# Set meeting date as reference point
settings = {
    'RELATIVE_BASE': meeting_date,  # datetime of the meeting
    'PREFER_DATES_FROM': 'future'   # "Friday" means next Friday, not last
}
parsed = parse(raw_date, settings=settings)
```
**Warning signs:** Due dates in the past, or inconsistent relative to meeting date

### Pitfall 3: Lost in the Middle
**What goes wrong:** RAID items from middle of long transcripts are missed
**Why it happens:** LLM attention is strongest at start/end of context
**How to avoid:**
- Put extraction instructions at END of prompt (after transcript)
- For very long transcripts (>50k tokens), consider chunking with overlap
- Use quote extraction to force attention to specific passages
**Warning signs:** Extractions cluster at transcript start/end

### Pitfall 4: Over-Extraction
**What goes wrong:** Discussions about action items extracted as action items themselves
**Why it happens:** Phrases like "we should" or "someone needs to" trigger false positives
**How to avoid:**
- Require explicit owner assignment for high confidence
- Prompt to distinguish "discussion of task" from "commitment to task"
- Review extractions with confidence < 0.7 carefully
**Warning signs:** High volume of low-confidence extractions

### Pitfall 5: Token Limit Exceeded
**What goes wrong:** API error on long transcripts
**Why it happens:** Claude's context is 200k tokens, but 1-hour meeting = ~20k words = ~25k tokens
**How to avoid:**
- Calculate token estimate: `len(text) / 4` as rough estimate
- For transcripts > 150k tokens, chunk with speaker-boundary overlap
- Most meetings (< 2 hours) fit in single context
**Warning signs:** API errors on long meetings, truncated extractions

## Code Examples

Verified patterns from official sources:

### Anthropic Structured Output with Pydantic
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from anthropic import Anthropic
from pydantic import BaseModel, Field

class ExtractedActions(BaseModel):
    items: list[ExtractedActionItem]

client = Anthropic()

response = client.beta.messages.parse(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["structured-outputs-2025-11-13"],
    messages=[
        {"role": "user", "content": f"{system_prompt}\n\nTranscript:\n{transcript_text}"}
    ],
    output_format=ExtractedActions,
)

actions = response.parsed_output  # Type: ExtractedActions
```

### Date Normalization with Meeting Context
```python
# Source: https://dateparser.readthedocs.io/
from datetime import datetime
from dateparser import parse

def normalize_due_date(
    raw_date: str | None,
    meeting_date: datetime
) -> datetime | None:
    """Convert natural language date to datetime, relative to meeting date."""
    if not raw_date:
        return None

    settings = {
        'RELATIVE_BASE': meeting_date,
        'PREFER_DATES_FROM': 'future',
        'RETURN_AS_TIMEZONE_AWARE': False,
    }

    parsed = parse(raw_date, settings=settings)
    return parsed
```

### Converting Extraction to Domain Model
```python
# Source: Project pattern
from uuid import uuid4
from src.models import ActionItem, ActionItemStatus

def to_domain_model(
    extracted: ExtractedActionItem,
    meeting_id: UUID,
    meeting_date: datetime
) -> ActionItem:
    """Convert LLM extraction output to domain model."""
    return ActionItem(
        id=uuid4(),
        meeting_id=meeting_id,
        description=extracted.description,
        assignee_name=extracted.assignee_name,
        due_date=normalize_due_date(extracted.due_date_raw, meeting_date),
        source_quote=extracted.source_quote,
        confidence=extracted.confidence,
        status=ActionItemStatus.PENDING,
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON mode prompting | Structured outputs (constrained decoding) | Nov 2025 | Guarantees valid schema, no parsing errors |
| Custom retry loops | Instructor library / native SDK retries | 2024 | Built-in validation + retry with error feedback |
| Fine-tuning for extraction | Prompt engineering + structured output | 2024-2025 | Much lower cost and faster iteration |
| Single mega-prompt | Type-specific prompts | 2025 | Better recall and precision per extraction type |

**Deprecated/outdated:**
- JSON mode without schema validation: Replaced by structured outputs
- Using completion API for extraction: Use messages API with structured outputs
- Manual JSON parsing from LLM output: Pydantic validation now built into SDK

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal chunk size for very long transcripts**
   - What we know: Claude handles 200k tokens, most 2-hour meetings fit
   - What's unclear: Optimal overlap strategy if chunking needed
   - Recommendation: Start without chunking, add if extraction quality degrades on long meetings

2. **Confidence score calibration approach**
   - What we know: Verbalized confidence + explicit rubric helps
   - What's unclear: Whether to add post-hoc calibration step
   - Recommendation: Start with rubric in prompt, measure quality, add calibration if needed

3. **Model selection (Sonnet vs Haiku)**
   - What we know: Sonnet 4.5 supports structured outputs, Haiku 4.5 coming soon
   - What's unclear: Quality/cost tradeoff for RAID extraction
   - Recommendation: Start with Sonnet for quality, test Haiku when available for cost optimization

## Sources

### Primary (HIGH confidence)
- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - API usage, Pydantic integration, beta headers
- [Anthropic Long Context Prompting](https://www.anthropic.com/news/prompting-long-context) - Quote extraction, few-shot examples
- [dateparser documentation](https://dateparser.readthedocs.io/) - Relative date handling, settings

### Secondary (MEDIUM confidence)
- [Instructor Library Documentation](https://python.useinstructor.com/) - Alternative approach, verified with official source
- [Pydantic LLM Guide](https://pydantic.dev/articles/llm-intro) - Schema patterns for LLM output
- [AWS Meeting Summarization Blog](https://aws.amazon.com/blogs/machine-learning/meeting-summarization-and-action-item-extraction-with-amazon-nova/) - RAID extraction prompts

### Tertiary (LOW confidence)
- [LLM Confidence Calibration Research](https://arxiv.org/html/2503.15850v1) - Academic survey, needs validation in practice

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Anthropic documentation, verified SDK features
- Architecture: HIGH - Based on existing codebase patterns + official examples
- Pitfalls: MEDIUM - Combination of official docs and practitioner experience

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - stable domain, structured outputs in public beta)
