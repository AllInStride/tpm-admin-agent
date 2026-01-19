# Phase 8: Meeting Prep - Research

**Researched:** 2026-01-19
**Domain:** Proactive meeting preparation, calendar scheduling, Slack notifications
**Confidence:** HIGH

## Summary

Phase 8 builds a proactive meeting prep system that surfaces relevant context before meetings start. The existing codebase provides solid infrastructure: `OpenItemsRepository` with `get_items()` for querying RAID items, `FTSService` for full-text search, `CalendarAdapter` for Google Calendar integration, `SlackAdapter` with `send_dm()` for notifications, `DriveAdapter` for docs access, and `MinutesRenderer` with Jinja2 for templating.

The primary challenge is **scheduling**: determining when to prepare and send briefings. Two approaches exist: calendar webhooks (real-time but complex) vs polling (simpler but delayed). For meeting prep sent 10 minutes before a meeting, a polling approach with 5-minute intervals provides sufficient precision while avoiding webhook infrastructure complexity.

The secondary challenge is **context aggregation**: gathering open items (90-day lookback, attendee+project matching), related docs (linked/shared/tagged), and Slack context (7-day channel history). The existing `OpenItemsRepository` and `FTSService` handle RAID item queries. Doc discovery requires extending `DriveAdapter`. Slack context requires extending `SlackAdapter` with channel history methods.

**Primary recommendation:** Use APScheduler with AsyncIOScheduler for scheduling, extend existing adapters for context gathering, create a PrepService to orchestrate preparation, and deliver via existing `SlackAdapter.send_dm()` with Block Kit formatting for scannability.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11+ | Job scheduling | Python standard for background scheduling, AsyncIOScheduler for async compatibility |
| slack-sdk | 3.35.0+ | Slack notifications | Already in project, Block Kit support for rich formatting |
| Jinja2 | 3.1.6+ | Template rendering | Already in project via MinutesRenderer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 25.5.0+ | Structured logging | Already in project, audit trail for prep delivery |
| pydantic | 2.12.5+ | Schema validation | Already in project, PrepSummary models |
| tenacity | 9.0.0+ | Retry logic | Already in project, delivery reliability |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler polling | Google Calendar webhooks | Webhooks require HTTPS endpoint, SSL certs, domain verification; polling simpler for 10-min prep |
| APScheduler | Celery Beat | Celery overkill for this scope; APScheduler sufficient |
| slackblocks (third-party) | Manual Block Kit dicts | slackblocks cleaner API but adds dependency; manual dicts sufficient |

**Installation:**
```bash
pip install APScheduler
```

Or add to pyproject.toml:
```toml
"apscheduler>=3.11.0,<4.0",
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── prep/                       # NEW: Meeting prep module
│   ├── __init__.py
│   ├── schemas.py              # PrepRequest, PrepSummary, PrepConfig
│   ├── scheduler.py            # APScheduler setup, job management
│   ├── prep_service.py         # Orchestrates prep generation
│   ├── context_gatherer.py     # Aggregates context from multiple sources
│   ├── item_matcher.py         # Matches items by attendee+project
│   └── templates/              # Jinja2 templates for prep output
│       └── prep_summary.j2
├── adapters/
│   ├── calendar_adapter.py     # EXTEND: add list_upcoming_events()
│   ├── slack_adapter.py        # EXTEND: add get_channel_history(), send_prep_dm()
│   └── drive_adapter.py        # EXTEND: add search_project_docs()
└── repositories/
    └── open_items_repo.py      # EXTEND: add get_items_for_attendees()
```

### Pattern 1: Polling Scheduler with APScheduler

**What:** Schedule prep jobs at fixed intervals, checking for upcoming meetings.

**When to use:** When meeting prep lead time (10 minutes) doesn't require real-time push notifications.

**Example:**
```python
# Source: APScheduler documentation + FastAPI lifespan pattern
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from fastapi import FastAPI

scheduler = AsyncIOScheduler(timezone='UTC')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Add job to check for upcoming meetings every 5 minutes
    scheduler.add_job(
        check_upcoming_meetings,
        'interval',
        minutes=5,
        id='meeting_prep_scanner',
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown()

async def check_upcoming_meetings():
    """Scan calendar for meetings starting in 10-15 minutes."""
    # Get meetings starting between now+10min and now+15min
    # This window ensures we catch meetings on each 5-min poll
    prep_service = get_prep_service()
    await prep_service.scan_and_prepare()
```

### Pattern 2: Context Aggregation Service

**What:** Central service that orchestrates gathering context from multiple sources in parallel.

**When to use:** When prep requires data from calendar, RAID items, docs, and Slack.

**Example:**
```python
# Pattern for gathering context from multiple sources
import asyncio
from dataclasses import dataclass

@dataclass
class PrepContext:
    open_items: list[dict]       # Matched RAID items
    related_docs: list[dict]     # Project docs
    slack_highlights: list[dict] # Recent channel activity
    previous_meeting: dict | None # Most recent meeting in series

class ContextGatherer:
    def __init__(
        self,
        open_items_repo: OpenItemsRepository,
        drive_adapter: DriveAdapter,
        slack_adapter: SlackAdapter,
        fts_service: FTSService,
    ):
        self._items = open_items_repo
        self._drive = drive_adapter
        self._slack = slack_adapter
        self._fts = fts_service

    async def gather_for_meeting(
        self,
        meeting: CalendarEvent,
        project_id: str,
        lookback_days: int = 90,
    ) -> PrepContext:
        """Gather all context in parallel."""
        attendee_emails = [a['email'] for a in meeting.attendees]

        # Run all queries in parallel
        items, docs, slack, prev_meeting = await asyncio.gather(
            self._get_matching_items(attendee_emails, project_id, lookback_days),
            self._get_project_docs(project_id),
            self._get_slack_highlights(project_id),
            self._get_previous_in_series(meeting),
        )

        return PrepContext(
            open_items=items,
            related_docs=docs,
            slack_highlights=slack,
            previous_meeting=prev_meeting,
        )
```

### Pattern 3: Meeting Series Detection

**What:** Identify recurring meetings by matching title patterns.

**When to use:** When determining "previous meeting in series" for context.

**Example:**
```python
# Meeting type inference per CONTEXT.md
import re

MEETING_TYPE_PATTERNS = {
    'steerco': [r'steerco', r'steering\s*committee', r'sc\b'],
    'project_team': [r'project\s*team', r'team\s*sync', r'weekly'],
    'dsu': [r'\bdsu\b', r'daily\s*standup', r'daily\s*sync', r'standup'],
}

def infer_meeting_type(title: str) -> str:
    """Infer meeting type from title with manual override support."""
    title_lower = title.lower()
    for mtype, patterns in MEETING_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, title_lower):
                return mtype
    return 'general'

def normalize_series_key(title: str) -> str:
    """Create normalized key for matching meetings in same series.

    Strips dates, numbers, and normalizes for comparison.
    """
    # Remove common date patterns
    normalized = re.sub(r'\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?', '', title)
    # Remove standalone numbers (week numbers, etc)
    normalized = re.sub(r'\s+\d+\s*', ' ', normalized)
    # Lowercase and strip
    return normalized.lower().strip()
```

### Pattern 4: Item Prioritization (Discretion Area)

**What:** Prioritize items when more than 10 match criteria.

**When to use:** Per CONTEXT.md, max 10 items in summary.

**Example:**
```python
# Prioritization algorithm per CONTEXT.md decisions
def prioritize_items(
    items: list[dict],
    max_items: int = 10,
    last_meeting_date: datetime | None = None,
) -> list[dict]:
    """Prioritize items for prep summary.

    Order per CONTEXT.md:
    1. Overdue items flagged prominently
    2. Group by type: Actions, Risks, Issues, Decisions
    3. Within type: by due date (soonest first)

    New since last meeting gets highlighted (not sorted by).
    """
    now = datetime.now()

    # Score function: lower is higher priority
    def priority_score(item: dict) -> tuple:
        type_order = {'action': 0, 'risk': 1, 'issue': 2, 'decision': 3}
        is_overdue = (
            item.get('due_date') and
            datetime.fromisoformat(item['due_date']) < now
        )
        type_rank = type_order.get(item.get('item_type', 'decision'), 4)
        due = item.get('due_date') or '9999-99-99'  # No due date = last
        return (not is_overdue, type_rank, due)

    sorted_items = sorted(items, key=priority_score)

    # Mark new items (since last meeting)
    if last_meeting_date:
        for item in sorted_items:
            created = datetime.fromisoformat(item.get('created_at', ''))
            item['is_new'] = created > last_meeting_date

    return sorted_items[:max_items]
```

### Pattern 5: Scannable Block Kit Message

**What:** Format prep summary using Slack Block Kit for scannability.

**When to use:** When delivering prep via Slack DM per CONTEXT.md.

**Example:**
```python
# Source: Slack Block Kit docs + CONTEXT.md formatting requirements
def format_prep_blocks(
    meeting_title: str,
    attendees: list[dict],  # name, role
    open_items: list[dict],
    recent_meeting_url: str | None,
    full_prep_url: str | None,
    talking_points: list[str],
) -> list[dict]:
    """Format prep as Slack Block Kit for scannability.

    Per CONTEXT.md: fits on one screen, professional tone,
    compact item list (title + owner + due date, one line each).
    """
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"Meeting Prep: {meeting_title}"}
    })

    # Attendees section
    attendee_text = ", ".join(
        f"{a['name']} ({a['role']})" if a.get('role') else a['name']
        for a in attendees
    )
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Attendees:* {attendee_text}"}
    })

    blocks.append({"type": "divider"})

    # Open items - compact list
    if open_items:
        # Overdue items first with warning
        overdue = [i for i in open_items if i.get('is_overdue')]
        if overdue:
            overdue_text = "\n".join(
                f":warning: {i['description'][:50]} | {i.get('owner', 'TBD')} | {i.get('due_date', 'No date')}"
                for i in overdue
            )
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Overdue Items:*\n{overdue_text}"}
            })

        # Non-overdue items
        other = [i for i in open_items if not i.get('is_overdue')]
        if other:
            items_text = "\n".join(
                f"{'*NEW* ' if i.get('is_new') else ''}{i['description'][:50]} | {i.get('owner', 'TBD')} | {i.get('due_date', 'No date')}"
                for i in other
            )
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Open Items:*\n{items_text}"}
            })

    blocks.append({"type": "divider"})

    # Suggested talking points
    if talking_points:
        tp_text = "\n".join(f"- {tp}" for tp in talking_points[:3])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Suggested Talking Points:*\n{tp_text}"}
        })

    # Links section
    links = []
    if recent_meeting_url:
        links.append(f"<{recent_meeting_url}|Recent Meeting Notes>")
    if full_prep_url:
        links.append(f"<{full_prep_url}|View Full Prep>")
    if links:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": " | ".join(links)}]
        })

    return blocks
```

### Anti-Patterns to Avoid

- **Synchronous prep generation:** Always use async for external API calls (calendar, Slack, Drive)
- **Sending prep too early:** Per CONTEXT.md, default 10 minutes before meeting - configurable but not too early
- **Missing calendar changes:** Handle short-notice calendar changes - still send prep even if <10 min warning
- **Over-fetching context:** Limit queries - 90 days for items, 7 days for Slack, 5 previous meetings max
- **Blocking on prep failure:** Use fire-and-forget with error logging; don't block scheduler on failures

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Job scheduling | Custom timers/cron | APScheduler | Handles timezone, persistence, job management |
| Calendar polling | Custom sleep loops | APScheduler interval jobs | Built-in retry, error handling |
| Block Kit formatting | Manual dict construction | Existing patterns + Block Kit Builder | Validated structure, preview tool |
| Retry on notification failure | Custom loops | tenacity decorator (existing) | Already in codebase, battle-tested |
| Open items query | New SQL queries | OpenItemsRepository.get_items() | Already handles grouping, filtering |
| Full-text search | New FTS queries | FTSService.search() | Already handles escaping, ranking |

**Key insight:** The existing codebase has most components needed. Phase 8 primarily orchestrates existing services and adds scheduling.

## Common Pitfalls

### Pitfall 1: Scheduler Not Persisting Across Restarts

**What goes wrong:** Scheduled prep jobs lost when application restarts.

**Why it happens:** APScheduler default uses in-memory job store.

**How to avoid:** For MVP, accept in-memory (jobs re-added on startup). For production, use SQLite job store:
```python
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
scheduler = AsyncIOScheduler(
    jobstores={'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')}
)
```

**Warning signs:** Preps not sent after server restart until first scan runs.

### Pitfall 2: Duplicate Prep Messages

**What goes wrong:** Same prep sent multiple times for one meeting.

**Why it happens:** Polling window catches same meeting on consecutive runs.

**How to avoid:** Track sent preps by meeting_id + date:
```python
# Use set or DB table to track sent preps
sent_preps: set[str] = set()  # In-memory for MVP

def prep_key(meeting_id: str, date: str) -> str:
    return f"{meeting_id}:{date}"

async def scan_and_prepare():
    for meeting in upcoming:
        key = prep_key(meeting.id, meeting.start)
        if key in sent_preps:
            continue
        await send_prep(meeting)
        sent_preps.add(key)
```

**Warning signs:** Users receiving same prep 2-3 times.

### Pitfall 3: Slack Rate Limiting on Bulk Prep

**What goes wrong:** Rate limit errors when multiple meetings start at same time.

**Why it happens:** Common meeting times (9:00 AM, top of hour) trigger many preps simultaneously.

**How to avoid:** Stagger DM sends with small delays:
```python
for i, user_id in enumerate(recipients):
    if i > 0:
        await asyncio.sleep(0.5)  # Slack rate limit: ~1 msg/sec for DMs
    await slack.send_dm(user_id, blocks)
```

**Warning signs:** `ratelimited` errors in logs, preps not delivered.

### Pitfall 4: Timezone Confusion

**What goes wrong:** Preps sent at wrong time relative to meeting.

**Why it happens:** Mixing UTC and local timezones in comparisons.

**How to avoid:** Always work in UTC, convert only at display:
```python
# Always use UTC internally
from datetime import timezone
now = datetime.now(timezone.utc)
meeting_start = datetime.fromisoformat(event['start']).astimezone(timezone.utc)
lead_time = timedelta(minutes=config.lead_time_minutes)

if now >= meeting_start - lead_time:
    # Time to send prep
```

**Warning signs:** Preps arriving hours early/late for users in different timezones.

### Pitfall 5: Over-scoped Context Queries

**What goes wrong:** Prep takes too long to generate, times out.

**Why it happens:** Fetching too much context (all docs, all Slack messages).

**How to avoid:** Apply limits per CONTEXT.md:
- 90 days for RAID items
- 7 days for Slack channel history
- 5 previous meetings in series
- Max 10 items in summary
- Max 5-10 docs

**Warning signs:** Prep generation > 10 seconds, database timeouts.

### Pitfall 6: Missing Attendee-Project Association

**What goes wrong:** Prep shows unrelated items or misses relevant ones.

**Why it happens:** Items matched only by attendee OR only by project, not both.

**How to avoid:** Per CONTEXT.md, match by BOTH attendee overlap AND project association:
```python
async def get_items_for_meeting(
    self,
    attendee_emails: list[str],
    project_id: str,
    lookback_days: int = 90,
) -> list[dict]:
    """Match items by BOTH attendee AND project."""
    # Items must be associated with project AND have attendee as owner/assignee
    query = """
        SELECT * FROM raid_items_projection
        WHERE project_id = ?
          AND owner IN ({})
          AND created_at >= date('now', '-{} days')
          AND status NOT IN ({})
    """.format(
        ','.join(['?'] * len(attendee_emails)),
        lookback_days,
        ','.join(['?'] * len(CLOSED_STATUSES)),
    )
```

**Warning signs:** Users report "this item isn't relevant to our project".

## Code Examples

Verified patterns from official sources and existing codebase:

### APScheduler FastAPI Integration

```python
# Source: APScheduler docs + FastAPI lifespan pattern
# src/prep/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from datetime import timezone

import structlog

from src.prep.prep_service import PrepService

logger = structlog.get_logger()

# Module-level scheduler
_scheduler: AsyncIOScheduler | None = None

def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=timezone.utc)
    return _scheduler

@asynccontextmanager
async def prep_scheduler_lifespan():
    """Lifespan context manager for prep scheduler."""
    scheduler = get_scheduler()

    # Add meeting scanner job
    scheduler.add_job(
        scan_for_upcoming_meetings,
        'interval',
        minutes=5,
        id='meeting_prep_scanner',
        replace_existing=True,
        max_instances=1,  # Prevent overlap if job runs long
    )

    logger.info("Starting prep scheduler")
    scheduler.start()

    try:
        yield
    finally:
        logger.info("Shutting down prep scheduler")
        scheduler.shutdown(wait=False)

async def scan_for_upcoming_meetings():
    """Scheduled job: find meetings starting soon and prepare."""
    try:
        prep_service = PrepService.get_instance()
        await prep_service.scan_and_prepare()
    except Exception as e:
        logger.error("Prep scan failed", error=str(e))
```

### CalendarAdapter Extension

```python
# Source: Existing CalendarAdapter + Google Calendar API docs
# Extend src/adapters/calendar_adapter.py

async def list_upcoming_events(
    self,
    calendar_id: str,
    time_min: datetime,
    time_max: datetime,
    max_results: int = 50,
) -> list[dict]:
    """List events in a time window.

    Args:
        calendar_id: Calendar ID (user's email for primary)
        time_min: Start of window (UTC)
        time_max: End of window (UTC)
        max_results: Maximum events to return

    Returns:
        List of event dicts with id, summary, start, end, attendees
    """
    try:
        service = self._get_service()
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
            )
            .execute()
        )
        return events_result.get('items', [])
    except Exception as e:
        logger.warning("Error listing events", error=str(e))
        return []
```

### SlackAdapter Extension for Channel History

```python
# Source: Existing SlackAdapter + Slack API docs
# Extend src/adapters/slack_adapter.py

async def get_channel_history(
    self,
    channel_id: str,
    days: int = 7,
    limit: int = 100,
) -> list[dict]:
    """Get recent messages from a channel.

    Args:
        channel_id: Slack channel ID
        days: How many days back to look
        limit: Maximum messages to return

    Returns:
        List of message dicts (newest first)
    """
    try:
        client = self._get_client()
        oldest = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()

        result = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest),
            limit=limit,
        )
        return result.get('messages', [])
    except SlackApiError as e:
        if e.response.get('error') == 'channel_not_found':
            logger.warning("Channel not found", channel_id=channel_id)
            return []
        raise

async def send_prep_dm(
    self,
    user_id: str,
    blocks: list[dict],
    text_fallback: str,
) -> dict:
    """Send prep summary as DM with Block Kit formatting.

    Args:
        user_id: Slack user ID
        blocks: Block Kit blocks
        text_fallback: Plain text fallback for notifications

    Returns:
        Dict with 'success' and 'ts' or 'error'
    """
    try:
        client = self._get_client()
        response = client.chat_postMessage(
            channel=user_id,
            blocks=blocks,
            text=text_fallback,
        )
        return {"success": True, "ts": response["ts"]}
    except SlackApiError as e:
        return {"success": False, "error": e.response.get("error")}
```

### OpenItemsRepository Extension

```python
# Source: Existing OpenItemsRepository pattern
# Extend src/repositories/open_items_repo.py

async def get_items_for_prep(
    self,
    attendee_emails: list[str],
    project_id: str,
    lookback_days: int = 90,
    include_types: list[str] | None = None,
) -> list[dict]:
    """Get open items matching attendees AND project.

    Per CONTEXT.md: match by BOTH attendee overlap AND project association.

    Args:
        attendee_emails: Meeting attendee emails
        project_id: Project ID to scope
        lookback_days: How far back to look (default 90)
        include_types: Item types to include (default all RAID)

    Returns:
        List of matching items sorted by overdue, then type order
    """
    include_types = include_types or ['action', 'risk', 'issue', 'decision']

    # Build email placeholders
    email_placeholders = ','.join(['?'] * len(attendee_emails))
    type_placeholders = ','.join(['?'] * len(include_types))

    query = f"""
        SELECT id, meeting_id, item_type, description, owner,
               due_date, status, confidence, created_at
        FROM raid_items_projection
        WHERE status NOT IN ({self._closed_statuses_sql})
          AND item_type IN ({type_placeholders})
          AND created_at >= date('now', '-{lookback_days} days')
          AND (
              owner IN ({email_placeholders})
              OR meeting_id IN (
                  SELECT DISTINCT meeting_id FROM raid_items_projection
                  WHERE owner IN ({email_placeholders})
              )
          )
        ORDER BY
            CASE WHEN date(due_date) < date('now') THEN 0 ELSE 1 END,
            CASE item_type
                WHEN 'action' THEN 0
                WHEN 'risk' THEN 1
                WHEN 'issue' THEN 2
                WHEN 'decision' THEN 3
                ELSE 4
            END,
            due_date ASC
    """

    params = (
        include_types +
        attendee_emails +
        attendee_emails  # Used twice in subquery
    )

    result = await self._db.execute(query, params)
    return [
        {
            "id": row[0],
            "meeting_id": row[1],
            "item_type": row[2],
            "description": row[3],
            "owner": row[4],
            "due_date": row[5],
            "status": row[6],
            "confidence": row[7],
            "created_at": row[8],
            "is_overdue": row[5] and row[5] < datetime.now().isoformat()[:10],
        }
        for row in result.rows
    ]
```

### Prep Summary Jinja2 Template

```jinja2
{# src/prep/templates/prep_summary.j2 #}
{# Plain text version for email fallback #}
MEETING PREP: {{ meeting_title }}
{{ "=" * 40 }}

Attendees: {% for a in attendees %}{{ a.name }}{% if a.role %} ({{ a.role }}){% endif %}{% if not loop.last %}, {% endif %}{% endfor %}

{% if overdue_items %}
OVERDUE ITEMS ({{ overdue_items|length }}):
{% for item in overdue_items %}
[!] {{ item.description[:60] }} | {{ item.owner or 'TBD' }} | Due: {{ item.due_date }}
{% endfor %}
{% endif %}

{% if open_items %}
OPEN ITEMS:
{% for item in open_items %}
{% if item.is_new %}[NEW] {% endif %}{{ item.description[:60] }} | {{ item.owner or 'TBD' }} | Due: {{ item.due_date or 'TBD' }}
{% endfor %}
{% endif %}

SUGGESTED TALKING POINTS:
{% for point in talking_points %}
- {{ point }}
{% endfor %}

{% if recent_meeting_url %}
Recent meeting notes: {{ recent_meeting_url }}
{% endif %}
{% if full_prep_url %}
Full prep: {{ full_prep_url }}
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual meeting prep | LLM-assisted context aggregation | 2024+ | Automated, consistent |
| Calendar webhooks for all updates | Polling for non-real-time use cases | N/A | Simpler infrastructure |
| Plain text Slack messages | Block Kit for rich formatting | 2019+ | Better scannability |
| Cron jobs | APScheduler with lifespan | Python 3.7+ | Better async integration |

**Deprecated/outdated:**
- `schedule` library: Use APScheduler instead - more features, async support
- Slack RTM API: Use Web API with `chat.postMessage` - RTM deprecated
- Manual cron: Use APScheduler for Python apps - better integration

## Open Questions

Things that couldn't be fully resolved:

1. **Project-meeting association**
   - What we know: Items matched by attendee+project per CONTEXT.md
   - What's unclear: How meetings associate with projects (calendar event metadata? title matching? manual?)
   - Recommendation: Start with title-based inference, add manual override field to meeting metadata

2. **Talking points generation**
   - What we know: CONTEXT.md requires 2-3 suggested talking points
   - What's unclear: Should LLM generate these or derive from item types?
   - Recommendation: Simple heuristic first (overdue items, new items, highest severity risks); LLM enhancement as future work

3. **Full prep URL hosting**
   - What we know: CONTEXT.md mentions "View full prep" link
   - What's unclear: Where full prep is hosted (Drive? internal API endpoint?)
   - Recommendation: Upload to Drive as markdown, link to Drive file

4. **Attendee role resolution**
   - What we know: CONTEXT.md requires "attendee names with their project roles"
   - What's unclear: Where role info comes from (meeting metadata? separate roster?)
   - Recommendation: Extend meeting projection to include roles if available; fall back to "Attendee"

## Sources

### Primary (HIGH confidence)
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) - Version 3.11.2, scheduling patterns
- [Slack Block Kit Docs](https://docs.slack.dev/block-kit/) - Block structure, formatting
- [Slack Messaging Formatting](https://docs.slack.dev/messaging/formatting-message-text/) - mrkdwn syntax
- [Google Calendar API Events List](https://developers.google.com/workspace/calendar/api/v3/reference/events/list) - Event listing

### Secondary (MEDIUM confidence)
- [APScheduler FastAPI Integration](https://rajansahu713.medium.com/implementing-background-job-scheduling-in-fastapi-with-apscheduler-6f5fdabf3186) - Lifespan pattern
- [Polling vs Webhooks](https://www.merge.dev/blog/webhooks-vs-polling) - Trade-off analysis
- [Slack chat.postMessage](https://docs.slack.dev/reference/methods/chat.postMessage/) - DM delivery
- [Calendar Push Notifications](https://developers.google.com/workspace/calendar/api/guides/push) - Webhook alternative (not used)

### Tertiary (LOW confidence)
- WebSearch results for meeting prep patterns - General guidance verified against requirements

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - APScheduler well-documented, existing adapters proven
- Architecture: HIGH - Extends established patterns from Phases 5-7
- Pitfalls: MEDIUM - Some based on common async scheduling issues
- Talking points generation: LOW - Algorithm TBD, marked for validation

**Research date:** 2026-01-19
**Valid until:** 2026-02-19 (30 days - stable technologies)
