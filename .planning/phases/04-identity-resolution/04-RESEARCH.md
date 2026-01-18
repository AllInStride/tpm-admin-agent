# Phase 4: Identity Resolution - Research

**Researched:** 2026-01-18
**Domain:** Entity resolution, name matching, multi-source identity verification
**Confidence:** HIGH

## Summary

Identity resolution for this phase combines fuzzy string matching with LLM-assisted inference and multi-source verification. The established approach uses RapidFuzz for algorithmic matching (particularly Jaro-Winkler for person names) combined with LLM inference for ambiguous cases. Multi-source verification (roster + Slack + Calendar) boosts confidence when sources agree, with single-source matches capped at 85%.

The existing codebase already uses Anthropic's structured outputs with Pydantic models, which integrates naturally with LLM-assisted name matching. The Participant model already has `confidence` and `transcript_name` fields designed for this purpose. The key additions are: (1) roster loading from Google Sheets via MCP, (2) fuzzy matching service, (3) learned mappings persistence, and (4) human review workflow.

**Primary recommendation:** Use RapidFuzz with Jaro-Winkler similarity for initial fuzzy matching, LLM inference for low-confidence cases requiring context understanding (e.g., "JSmith" to "John Smith"), and persist learned mappings in SQLite for future resolution.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rapidfuzz | 3.14.x | Fuzzy string matching | MIT licensed, 5-100x faster than alternatives, C++ backend |
| anthropic | existing | LLM-assisted inference | Already in project for RAID extraction |
| pydantic | existing | Schema validation | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mcp-google-sheets | latest | Google Sheets access | Reading roster spreadsheets |
| @modelcontextprotocol/server-slack | latest | Slack workspace access | Cross-referencing channel membership |
| google-calendar-mcp | latest | Calendar access | Cross-referencing meeting attendees |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rapidfuzz | thefuzz | thefuzz depends on rapidfuzz anyway; use rapidfuzz directly |
| Jaro-Winkler | Levenshtein | Jaro-Winkler designed specifically for person names |
| LLM inference | Pure fuzzy matching | LLM handles context like "Johnny" -> "John Smith" better |

**Installation:**
```bash
pip install rapidfuzz
# MCP servers configured via claude_desktop_config.json
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── identity/
│   ├── __init__.py
│   ├── resolver.py         # IdentityResolver orchestrator
│   ├── fuzzy_matcher.py    # RapidFuzz-based matching
│   ├── llm_matcher.py      # LLM-assisted inference
│   ├── schemas.py          # Resolution request/response models
│   └── confidence.py       # Multi-source confidence calculation
├── adapters/
│   ├── roster_adapter.py   # Google Sheets roster interface
│   ├── slack_adapter.py    # Slack membership interface
│   └── calendar_adapter.py # Calendar attendee interface
├── repositories/
│   └── mapping_repo.py     # Learned mappings persistence
```

### Pattern 1: Multi-Stage Resolution Pipeline
**What:** Resolve names through progressively more expensive methods
**When to use:** Always - balance speed and accuracy

```python
# Source: Architecture pattern from context decisions
class IdentityResolver:
    async def resolve(self, transcript_name: str, roster: list[RosterEntry]) -> ResolutionResult:
        # Stage 1: Exact match (O(n))
        if exact := self._exact_match(transcript_name, roster):
            return ResolutionResult(person=exact, confidence=1.0, source="exact")

        # Stage 2: Learned mapping lookup (O(1) with index)
        if learned := await self._learned_mapping(transcript_name):
            return ResolutionResult(person=learned, confidence=0.95, source="learned")

        # Stage 3: Fuzzy match (O(n))
        fuzzy_result = self._fuzzy_match(transcript_name, roster)
        if fuzzy_result.confidence >= 0.85:
            return fuzzy_result

        # Stage 4: LLM inference for ambiguous cases
        return await self._llm_inference(transcript_name, roster, fuzzy_result)
```

### Pattern 2: Multi-Source Confidence Boosting
**What:** Boost confidence when multiple sources agree on match
**When to use:** When initial match is below auto-accept threshold

```python
# Source: CONTEXT.md decision - cannot exceed 85% without second source verification
def calculate_confidence(
    fuzzy_score: float,
    roster_match: bool,
    slack_match: bool,
    calendar_match: bool
) -> float:
    base = fuzzy_score

    # Single-source cap
    if not (slack_match or calendar_match):
        return min(base, 0.85)

    # Multi-source boost
    sources_agreeing = sum([roster_match, slack_match, calendar_match])
    if sources_agreeing >= 2:
        boost = 0.05 * (sources_agreeing - 1)
        return min(base + boost, 1.0)

    return base
```

### Pattern 3: Human Review Inline Response
**What:** Include review items in extraction response, not separate queue
**When to use:** When confidence < 85% threshold

```python
# Source: CONTEXT.md decision - review appears inline in extraction results
class ExtractionResponse(BaseModel):
    action_items: list[ActionItem]
    decisions: list[Decision]
    # ... other RAID items

    # Human review section
    pending_reviews: list[IdentityReview] = Field(
        default_factory=list,
        description="Items requiring human confirmation before downstream sync"
    )
    review_summary: str | None = Field(
        default=None,
        description="Human-readable summary: 'X items need owner confirmation'"
    )
```

### Anti-Patterns to Avoid
- **Calling LLM for every name:** Use fuzzy matching first; LLM only for ambiguous cases
- **Ignoring learned mappings:** Always check persisted corrections before re-matching
- **Trusting single source at 100%:** Cap single-source matches at 85% per CONTEXT.md
- **Blocking on external API failures:** Gracefully degrade if Slack/Calendar unavailable

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom edit distance | rapidfuzz | C++ optimized, handles edge cases |
| Name normalization | Custom rules | rapidfuzz.utils.default_process | Handles Unicode, whitespace, case |
| Best match from list | Loop + comparison | rapidfuzz.process.extractOne | Optimized for bulk matching |
| Jaro-Winkler distance | Implement algorithm | rapidfuzz.distance.JaroWinkler | Battle-tested, prefix-weighted |

**Key insight:** Name matching has decades of research; libraries encode edge cases you'll discover painfully if hand-rolling.

## Common Pitfalls

### Pitfall 1: Preprocessing Mismatch
**What goes wrong:** RapidFuzz 3.x doesn't preprocess by default; comparison fails
**Why it happens:** Version change from 2.x behavior
**How to avoid:** Always use `processor=rapidfuzz.utils.default_process` or preprocess manually
**Warning signs:** Identical names scoring <100%

### Pitfall 2: Confidence Score Calibration
**What goes wrong:** Jaro-Winkler returns 0-1, but fuzz functions return 0-100
**Why it happens:** Different modules use different scales
**How to avoid:** Use consistent scorer; prefer `JaroWinkler.normalized_similarity()` for 0-1 scale
**Warning signs:** Thresholds not behaving as expected

### Pitfall 3: First Name / Last Name Order
**What goes wrong:** "John Smith" doesn't match "Smith, John"
**Why it happens:** Simple ratio penalizes word order
**How to avoid:** Use `token_sort_ratio` or `token_set_ratio` for name matching
**Warning signs:** Low scores for clearly matching names

### Pitfall 4: Nickname/Alias Complexity
**What goes wrong:** "Bob" doesn't match "Robert" with pure fuzzy matching
**Why it happens:** Fuzzy matching is string similarity, not semantic
**How to avoid:** Store known aliases in roster; use LLM for inference
**Warning signs:** Common nicknames failing to resolve

### Pitfall 5: MCP Server Authentication Complexity
**What goes wrong:** OAuth flows fail in automated contexts
**Why it happens:** Interactive OAuth not suited for server environments
**How to avoid:** Use service account authentication for Google Sheets/Calendar
**Warning signs:** Auth prompts in production, token expiry issues

### Pitfall 6: Review Expiry Without Notification
**What goes wrong:** Items expire after 7 days without user awareness
**Why it happens:** No reminder mechanism implemented
**How to avoid:** Implement daily summary notification per CONTEXT.md
**Warning signs:** Growing count of "unresolved" items

## Code Examples

Verified patterns from official sources:

### Basic Fuzzy Matching with RapidFuzz
```python
# Source: RapidFuzz documentation
from rapidfuzz import fuzz, process
from rapidfuzz.distance import JaroWinkler
from rapidfuzz import utils

def find_best_match(query: str, choices: list[str], threshold: float = 0.85):
    """Find best matching name from roster choices."""
    # Use token_sort_ratio for name order independence
    result = process.extractOne(
        query,
        choices,
        scorer=fuzz.token_sort_ratio,
        processor=utils.default_process,
        score_cutoff=threshold * 100  # fuzz uses 0-100 scale
    )
    if result:
        match, score, index = result
        return match, score / 100  # Normalize to 0-1
    return None, 0.0

# For person names specifically, Jaro-Winkler often works better
def jaro_winkler_match(query: str, choices: list[str], threshold: float = 0.85):
    """Find best match using Jaro-Winkler (optimized for person names)."""
    result = process.extractOne(
        query,
        choices,
        scorer=JaroWinkler.normalized_similarity,
        processor=utils.default_process,
        score_cutoff=threshold
    )
    if result:
        match, score, index = result
        return match, score
    return None, 0.0
```

### Roster Entry Schema
```python
# Source: CONTEXT.md roster format decision
from pydantic import BaseModel, EmailStr, Field

class RosterEntry(BaseModel):
    """Person in project roster from Google Sheets."""
    name: str = Field(description="Full name")
    email: EmailStr = Field(description="Email - unique identifier")
    slack_handle: str | None = Field(default=None, description="Slack @handle")
    role: str | None = Field(default=None, description="Role on project")
    aliases: list[str] = Field(
        default_factory=list,
        description="Known nicknames/variations (from Aliases column)"
    )

    @classmethod
    def from_sheet_row(cls, row: dict) -> "RosterEntry":
        """Parse from Google Sheets row."""
        aliases = []
        if alias_str := row.get("Aliases", ""):
            aliases = [a.strip() for a in alias_str.split(",") if a.strip()]
        return cls(
            name=row["Name"],
            email=row["Email"],
            slack_handle=row.get("Slack handle"),
            role=row.get("Role"),
            aliases=aliases,
        )
```

### Resolution Result Schema
```python
# Source: Derived from CONTEXT.md decisions
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID

class ResolutionSource(str, Enum):
    EXACT = "exact"
    LEARNED = "learned"
    FUZZY = "fuzzy"
    LLM = "llm"
    CALENDAR = "calendar"
    SLACK = "slack"

class ResolutionResult(BaseModel):
    """Result of name resolution attempt."""
    transcript_name: str = Field(description="Original name from transcript")
    resolved_email: str | None = Field(default=None, description="Matched person's email")
    resolved_name: str | None = Field(default=None, description="Canonical name")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence")
    source: ResolutionSource = Field(description="How match was determined")
    alternatives: list[tuple[str, float]] = Field(
        default_factory=list,
        description="Other possible matches with scores"
    )
    requires_review: bool = Field(description="True if confidence < 85%")

    @property
    def is_resolved(self) -> bool:
        return self.resolved_email is not None and self.confidence >= 0.85
```

### Learned Mapping Persistence
```python
# Source: Derived from CONTEXT.md decision to persist learned mappings
# Schema for SQLite storage

CREATE_MAPPINGS_TABLE = """
CREATE TABLE IF NOT EXISTS learned_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    transcript_name TEXT NOT NULL,
    resolved_email TEXT NOT NULL,
    resolved_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    UNIQUE(project_id, transcript_name)
);

CREATE INDEX IF NOT EXISTS idx_mapping_lookup
ON learned_mappings(project_id, transcript_name);
"""
```

### LLM-Assisted Name Inference Prompt
```python
# Source: Derived from existing prompts.py patterns + entity matching research
NAME_INFERENCE_PROMPT = """You are resolving a person's name from a meeting transcript to a project roster.

TRANSCRIPT NAME: {transcript_name}
MEETING CONTEXT: {context}

PROJECT ROSTER:
{roster_formatted}

TASK: Determine which roster person (if any) the transcript name refers to.

RULES:
1. Consider common nicknames (Bob=Robert, Mike=Michael, etc.)
2. Consider initials (JSmith might be John Smith)
3. Consider typos or transcription errors
4. If no confident match, say "NO_MATCH"

Respond with:
- matched_email: The email of the matched person, or null
- confidence: 0.0-1.0 how certain you are
- reasoning: Brief explanation of your logic

{transcript}
"""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FuzzyWuzzy | RapidFuzz | 2020+ | 5-100x faster, MIT license |
| Pure string matching | Hybrid fuzzy + LLM | 2023+ | Handles semantic similarity |
| Manual alias lists | LLM alias generation | 2024+ | Discovers new variations |
| Single-pass resolution | Multi-stage pipeline | Standard | Balance speed/accuracy |

**Deprecated/outdated:**
- **FuzzyWuzzy:** Superseded by TheFuzz, which depends on RapidFuzz
- **python-Levenshtein:** Use rapidfuzz.distance.Levenshtein instead
- **pyjarowinkler:** Use rapidfuzz.distance.JaroWinkler instead

## Open Questions

Things that couldn't be fully resolved:

1. **MCP Server Availability for This Project**
   - What we know: Multiple MCP servers exist for Google Sheets, Slack, Calendar
   - What's unclear: Which specific MCP servers are already configured in this project
   - Recommendation: Check claude_desktop_config.json; may need to add/configure servers

2. **Google Sheets Authentication Method**
   - What we know: Service account recommended for server environments
   - What's unclear: Whether project has existing GCP credentials
   - Recommendation: Use service account; create if needed

3. **Daily Summary Notification Mechanism**
   - What we know: CONTEXT.md says "email, Slack, or API-driven" is Claude's discretion
   - What's unclear: Which approach best fits existing architecture
   - Recommendation: Start with API-driven (client polls); add push notification later

4. **External Participant Auto-Add Workflow**
   - What we know: Auto-add to roster when in Calendar but not roster, mark as "external"
   - What's unclear: Exact UX for PM confirmation of external participants
   - Recommendation: Treat as special case of human review workflow

## Sources

### Primary (HIGH confidence)
- [RapidFuzz Documentation](https://rapidfuzz.github.io/RapidFuzz/) - API reference, scoring functions
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) - Library details, version 3.14.x
- Project CONTEXT.md - Locked implementation decisions

### Secondary (MEDIUM confidence)
- [MCP Google Sheets (xing5)](https://github.com/xing5/mcp-google-sheets) - Sheets MCP pattern
- [MCP Slack (AVIMBU)](https://github.com/AVIMBU/slack-mcp-server) - Slack MCP pattern
- [Jaro-Winkler Wikipedia](https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance) - Algorithm design for names
- [Entity Matching with LLMs (EDBT 2025)](https://arxiv.org/pdf/2310.11244) - LLM prompting strategies

### Tertiary (LOW confidence)
- Various blog posts on entity resolution patterns - general guidance only
- Multi-source confidence boosting patterns - synthesized from multiple sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - RapidFuzz is clearly the standard; well-documented
- Architecture: HIGH - Patterns derived from CONTEXT.md decisions and existing codebase
- Pitfalls: MEDIUM - Based on documentation + common sense, not production experience

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - stable domain)
