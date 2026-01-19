# Phase 6: System Integration - Research

**Researched:** 2026-01-19
**Domain:** Smartsheet API + Slack Notifications
**Confidence:** HIGH

## Summary

Phase 6 integrates the TPM Admin Agent with Smartsheet for RAID item tracking and extends Slack integration for owner notifications. The existing codebase has a solid foundation with adapter patterns from Phase 5 (SheetsAdapter, DriveAdapter, SlackAdapter) that inform the architecture.

The Smartsheet Python SDK (v3.7.1) provides a mature, well-documented interface for sheet creation and row management. The SDK includes built-in retry logic for rate limiting. Slack notifications extend the existing SlackAdapter with `chat.postMessage` for DMs, using the already-implemented `users.lookupByEmail` pattern for user resolution.

**Primary recommendation:** Add `smartsheet-python-sdk` dependency and create SmartsheetAdapter following the established OutputAdapter protocol. Extend SlackAdapter with notification methods. Use the existing `write_with_retry` decorator for resilience.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| smartsheet-python-sdk | 3.7.1 | Smartsheet API integration | Official SDK, built-in retry, well-documented |
| slack-sdk | 3.35.0+ | Slack DM notifications | Already in project, `chat.postMessage` for DMs |
| tenacity | 9.0.0+ | Retry logic | Already in project, used by `write_with_retry` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 25.5.0+ | Structured logging | Already in project, audit trail for notifications |
| pydantic | 2.12.5+ | Schema validation | Already in project, config and result models |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| smartsheet-python-sdk | simple-smartsheet | Cleaner API but less official, fewer features |
| slack-sdk | httpx direct | Already have slack-sdk, no need to add complexity |

**Installation:**
```bash
pip install smartsheet-python-sdk
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── adapters/
│   ├── smartsheet_adapter.py  # NEW: SmartsheetAdapter
│   └── slack_adapter.py       # EXTEND: add notification methods
├── integration/               # NEW: orchestration layer
│   ├── __init__.py
│   ├── smartsheet_writer.py   # Batching, dedup, column mapping
│   ├── notification_service.py # DM sending, audit logging
│   └── schemas.py             # Integration-specific models
└── output/
    ├── router.py              # EXTEND: add smartsheet/notification routing
    └── config.py              # EXTEND: add smartsheet config
```

### Pattern 1: Adapter Protocol Compliance
**What:** New adapters follow existing OutputAdapter protocol
**When to use:** Any new external system integration
**Example:**
```python
# Source: Existing src/adapters/base.py pattern
class SmartsheetAdapter:
    """Adapter for writing RAID items to Smartsheet.

    Follows established adapter pattern with lazy client initialization,
    asyncio.to_thread for sync SDK calls, and WriteResult return type.
    """

    def __init__(self, access_token: str | None = None):
        self._token = access_token or os.environ.get("SMARTSHEET_ACCESS_TOKEN")
        self._client: smartsheet.Smartsheet | None = None

    def _get_client(self) -> smartsheet.Smartsheet:
        if self._client is None:
            if not self._token:
                raise ValueError("No Smartsheet token configured")
            self._client = smartsheet.Smartsheet(access_token=self._token)
        return self._client

    async def write_raid_items(
        self,
        sheet_id: int,
        items: list[dict],
        *,
        dry_run: bool = False,
    ) -> WriteResult:
        if dry_run:
            return WriteResult(success=True, dry_run=True, item_count=len(items))
        return await asyncio.to_thread(self._write_sync, sheet_id, items)
```

### Pattern 2: Batch Operations with Chunking
**What:** Chunk items into API-safe batches
**When to use:** Smartsheet add_rows (max 500 per call)
**Example:**
```python
# Source: Smartsheet API docs - 500 row limit per add_rows call
SMARTSHEET_BATCH_SIZE = 100  # Conservative batch size for safety

def _write_sync(self, sheet_id: int, items: list[dict]) -> WriteResult:
    client = self._get_client()
    sheet = client.Sheets.get_sheet(sheet_id)
    column_map = {col.title: col.id for col in sheet.columns}

    total_written = 0
    for chunk in _chunked(items, SMARTSHEET_BATCH_SIZE):
        rows = [self._item_to_row(item, column_map) for item in chunk]
        response = client.Sheets.add_rows(sheet_id, rows)
        total_written += len(response.data)

    return WriteResult(
        success=True,
        item_count=total_written,
        external_id=str(sheet_id),
        url=f"https://app.smartsheet.com/sheets/{sheet_id}",
    )
```

### Pattern 3: Notification Service with Audit Trail
**What:** Dedicated service for sending and logging notifications
**When to use:** All Slack DM operations
**Example:**
```python
# Source: Slack API docs + existing SlackAdapter pattern
class NotificationService:
    def __init__(self, slack_adapter: SlackAdapter):
        self._slack = slack_adapter
        self._audit_log: list[NotificationRecord] = []

    async def notify_owner(
        self,
        owner_email: str,
        item: ActionItemData,
        smartsheet_url: str,
    ) -> NotificationResult:
        # Look up Slack user by email
        user = await self._slack.lookup_user_by_email(owner_email)
        if not user:
            return NotificationResult(success=False, reason="user_not_found")

        message = self._format_message(item, smartsheet_url)
        result = await self._slack.send_dm(user["id"], message)

        # Audit log
        self._audit_log.append(NotificationRecord(
            owner_email=owner_email,
            item_description=item.description,
            sent_at=datetime.now(UTC),
            success=result.success,
        ))
        return result
```

### Anti-Patterns to Avoid
- **Single-row API calls:** Always batch rows to avoid rate limiting
- **Blocking sync calls:** Use `asyncio.to_thread()` for SDK calls (SDK is sync)
- **Hardcoded column IDs:** Fetch column map dynamically; column IDs are sheet-specific
- **Direct DM without lookup:** Always verify user exists via `users.lookupByEmail` first

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Smartsheet auth | Custom token handling | SDK's env var support | SDK reads SMARTSHEET_ACCESS_TOKEN automatically |
| Rate limit handling | Custom backoff | SDK's built-in retry | SDK has `request_with_retry()` and backoff calculation |
| Retry logic | Custom retry loops | tenacity decorator | Already in project as `write_with_retry` |
| User lookup | Manual Slack user enumeration | `users.lookupByEmail` | O(1) lookup vs O(n) list iteration |
| DM channel creation | Manual `conversations.open` | Pass user ID to `chat.postMessage` | API opens DM automatically |

**Key insight:** Both Smartsheet SDK and Slack SDK handle their own rate limiting. The existing `write_with_retry` decorator adds an additional layer for transient failures.

## Common Pitfalls

### Pitfall 1: Column ID vs Column Title Confusion
**What goes wrong:** Using column titles in row cells instead of column IDs
**Why it happens:** Column titles are human-readable but API requires integer IDs
**How to avoid:** Fetch sheet columns once, build title-to-ID map, cache for session
**Warning signs:** API errors about invalid column references

### Pitfall 2: Smartsheet Row Location Not Specified
**What goes wrong:** Rows silently fail to add or add at wrong position
**Why it happens:** `add_rows` requires location specifier (`to_top`, `to_bottom`, etc.)
**How to avoid:** Always set `row.to_bottom = True` for new items
**Warning signs:** Empty response from add_rows, items not appearing in sheet

### Pitfall 3: Slack DM to Non-Existent User
**What goes wrong:** `channel_not_found` error when DMing
**Why it happens:** User ID doesn't exist or user is deactivated
**How to avoid:** Pre-verify user with `users.lookupByEmail`, handle `users_not_found`
**Warning signs:** `channel_not_found` or `user_not_found` errors

### Pitfall 4: Date Format Mismatch in Smartsheet
**What goes wrong:** Dates appear as text strings instead of date values
**Why it happens:** Smartsheet DATE columns expect ISO format (YYYY-MM-DD)
**How to avoid:** Format all dates as ISO strings, set `strict: False` for leniency
**Warning signs:** Dates not sortable, no calendar date picker in cells

### Pitfall 5: Duplicate Row Creation
**What goes wrong:** Same item added multiple times on retries
**Why it happens:** Retry after timeout when row was actually created
**How to avoid:** Use unique identifier column (meeting_id + item hash), check before insert
**Warning signs:** Duplicate entries in RAID sheet after processing failures

### Pitfall 6: Queue Persistence Loss
**What goes wrong:** Queued items lost on application restart
**Why it happens:** In-memory RetryQueue from Phase 5 doesn't persist
**How to avoid:** Per CONTEXT.md, continue with in-memory for MVP; SQLite future work
**Warning signs:** Items "disappear" after restart (expected for MVP)

## Code Examples

Verified patterns from official sources:

### Smartsheet: Create Sheet with Columns
```python
# Source: Smartsheet API docs + SDK documentation
import smartsheet

client = smartsheet.Smartsheet()  # Uses SMARTSHEET_ACCESS_TOKEN env var

# Define columns for RAID sheet
columns = [
    {"title": "Type", "type": "PICKLIST", "options": ["Action", "Risk", "Issue", "Decision"]},
    {"title": "Title", "type": "TEXT_NUMBER", "primary": True},
    {"title": "Owner", "type": "CONTACT_LIST"},
    {"title": "Status", "type": "PICKLIST", "options": ["Open", "In Progress", "Done", "Closed"]},
    {"title": "Due Date", "type": "DATE"},
    {"title": "Source Meeting", "type": "TEXT_NUMBER"},
    {"title": "Created Date", "type": "DATE"},
    {"title": "Confidence", "type": "TEXT_NUMBER"},
]

sheet_spec = client.models.Sheet({
    "name": "Project RAID Log",
    "columns": [client.models.Column(col) for col in columns],
})

# Create in specific folder
response = client.Folders.create_sheet_in_folder(folder_id, sheet_spec)
sheet_id = response.result.id
```

### Smartsheet: Add Rows with Column Mapping
```python
# Source: Smartsheet Python SDK docs + community examples
def add_raid_items(client, sheet_id: int, items: list[dict]) -> int:
    # Get column map
    sheet = client.Sheets.get_sheet(sheet_id)
    col_map = {col.title: col.id for col in sheet.columns}

    rows_to_add = []
    for item in items:
        row = client.models.Row()
        row.to_bottom = True
        row.cells.append({"column_id": col_map["Type"], "value": item["type"]})
        row.cells.append({"column_id": col_map["Title"], "value": item["description"]})
        row.cells.append({"column_id": col_map["Owner"], "value": item.get("owner", "")})
        row.cells.append({"column_id": col_map["Status"], "value": item.get("status", "Open")})
        if item.get("due_date"):
            row.cells.append({"column_id": col_map["Due Date"], "value": item["due_date"]})
        row.cells.append({"column_id": col_map["Source Meeting"], "value": item.get("source_meeting", "")})
        row.cells.append({"column_id": col_map["Confidence"], "value": str(item.get("confidence", 1.0))})
        rows_to_add.append(row)

    # Batch add (respects 500 row limit)
    response = client.Sheets.add_rows(sheet_id, rows_to_add)
    return len(response.data)
```

### Slack: Send DM to User by Email
```python
# Source: Slack API docs + existing SlackAdapter pattern
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

def send_dm_by_email(email: str, message: str) -> dict:
    # Step 1: Look up user by email
    try:
        user_response = client.users_lookupByEmail(email=email)
        user_id = user_response["user"]["id"]
    except SlackApiError as e:
        if e.response.get("error") == "users_not_found":
            return {"success": False, "error": "user_not_found"}
        raise

    # Step 2: Send DM (channel=user_id opens DM automatically)
    try:
        response = client.chat_postMessage(
            channel=user_id,
            text=message,
        )
        return {"success": True, "ts": response["ts"]}
    except SlackApiError as e:
        return {"success": False, "error": e.response.get("error")}
```

### Notification Message Format
```python
# Source: CONTEXT.md requirements - plain text with links
def format_notification(item: ActionItemData, smartsheet_url: str) -> str:
    parts = [
        f"*New action item assigned to you:*",
        f"> {item.description}",
    ]
    if item.due_date:
        parts.append(f"*Due:* {item.due_date}")
    parts.append(f"<{smartsheet_url}|View in Smartsheet>")
    return "\n".join(parts)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| gspread for Smartsheet | smartsheet-python-sdk | N/A (different APIs) | Native Smartsheet support with all features |
| Slack RTM API | Slack Web API | 2020+ | RTM deprecated; Web API is standard |
| Manual retry loops | SDK built-in retry | SDK 3.x | Automatic exponential backoff |

**Deprecated/outdated:**
- `simple-smartsheet`: Less maintained than official SDK
- Slack RTM bot: Use Web API with `chat.postMessage` instead
- Manual token refresh: SDK handles token management

## Open Questions

Things that couldn't be fully resolved:

1. **Exact batch size for Smartsheet**
   - What we know: API limit is 500 rows per add_rows call
   - What's unclear: Optimal batch size for performance vs. rate limiting
   - Recommendation: Start with 100 (conservative), tune based on observed rate limiting

2. **Reminder scheduling architecture**
   - What we know: CONTEXT.md requires 3-day reminders and overdue notifications
   - What's unclear: Where to run the scheduler (background task, cron, separate service)
   - Recommendation: Use APScheduler with AsyncIOScheduler in FastAPI lifespan; stores job state in memory for MVP

3. **Duplicate detection algorithm**
   - What we know: CONTEXT.md says "create new row, link to detected duplicates"
   - What's unclear: How to identify duplicates across meetings (same description? same owner+description?)
   - Recommendation: Hash of (description + owner) as unique key; store in Smartsheet column for lookup

## Sources

### Primary (HIGH confidence)
- [Smartsheet Python SDK Documentation](https://smartsheet.github.io/smartsheet-python-sdk/) - Client creation, row operations, folder operations
- [Smartsheet PyPI](https://pypi.org/project/smartsheet-python-sdk/) - Version 3.7.1, Python 3.7+ requirement
- [Slack API Rate Limits](https://docs.slack.dev/apis/web-api/rate-limits/) - Tier system, chat.postMessage limits
- [Slack users.lookupByEmail](https://docs.slack.dev/reference/methods/users.lookupByEmail) - User lookup by email

### Secondary (MEDIUM confidence)
- [Smartsheet API Rate Limits](https://developers.smartsheet.com/api/smartsheet/guides/basics/limitations) - 300 requests/min, 500 rows/batch
- [Smartsheet Community: Add Rows](https://community.smartsheet.com/discussion/106078/python-sdk-api-to-add-rows-with-multi-columns-to-smartsheet) - Column ID patterns
- [Slack chat.postMessage](https://docs.slack.dev/reference/methods/chat.postMessage) - DM via user ID

### Tertiary (LOW confidence)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/master/userguide.html) - Async scheduling for reminders

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official SDKs with good documentation
- Architecture: HIGH - Follows established patterns from Phase 5
- Pitfalls: MEDIUM - Based on API docs and community posts
- Reminder scheduling: LOW - Future work, not core to MVP

**Research date:** 2026-01-19
**Valid until:** 30 days (stable APIs)
