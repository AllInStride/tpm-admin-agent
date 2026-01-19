# Phase 5: Output Generation - Research

**Researched:** 2026-01-18
**Domain:** Template rendering, adapter pattern, Google Workspace APIs
**Confidence:** HIGH

## Summary

This phase generates meeting minutes from extracted RAID artifacts and establishes an adapter pattern for writing to target systems. The codebase already has a solid adapter foundation (RosterAdapter, SlackAdapter, CalendarAdapter) that can be extended for output.

The standard approach is:
1. **Jinja2** for template rendering (established Python standard, supports simple `{{placeholder}}` syntax)
2. **Abstract base class** with Protocol typing for the adapter interface
3. **gspread** (already installed) for Google Sheets writes
4. **google-api-python-client** (already installed) for Google Drive uploads
5. **tenacity** for retry logic with exponential backoff
6. **structlog** (already used) for audit logging

**Primary recommendation:** Use composition-based adapters with a common interface, Jinja2 for templates, and tenacity-wrapped async methods for reliable delivery.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.6 | Template rendering | De facto Python standard, 11k+ GitHub stars, Ansible/Flask use it |
| tenacity | 9.0+ | Retry with exponential backoff | Purpose-built for retries, async support, widely adopted |

### Already Installed (reuse)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| gspread | 6.1.0 | Google Sheets API wrapper | Already in pyproject.toml |
| google-api-python-client | 2.170.0 | Google Drive API | Already in pyproject.toml |
| google-auth | 2.40.0 | Service account auth | Already in pyproject.toml |
| structlog | 25.5.0 | Structured logging | Already in pyproject.toml |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 | Mako | Mako is faster but Jinja2 has simpler syntax matching CONTEXT.md requirement |
| Jinja2 | Python f-strings | f-strings can't load from files; templates need external storage |
| tenacity | Built-in asyncio retry | tenacity has battle-tested backoff strategies, callbacks |

**Installation:**
```bash
pip install Jinja2 tenacity
```

Or add to pyproject.toml:
```toml
"jinja2>=3.1.0",
"tenacity>=9.0.0",
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── adapters/
│   ├── __init__.py           # Existing - add new exports
│   ├── base.py               # NEW: OutputAdapter Protocol
│   ├── roster_adapter.py     # Existing (read)
│   ├── slack_adapter.py      # Existing (read)
│   ├── calendar_adapter.py   # Existing (read)
│   ├── sheets_adapter.py     # NEW: Write RAID items to Sheets
│   └── drive_adapter.py      # NEW: Upload minutes to Drive
├── output/
│   ├── __init__.py
│   ├── schemas.py            # Output data models (MinutesData, etc.)
│   ├── renderer.py           # Jinja2 template rendering
│   ├── router.py             # Routes output to adapters by config
│   └── queue.py              # Retry queue for failed writes
├── templates/
│   └── default_minutes.md.j2 # Default meeting minutes template
└── ...
```

### Pattern 1: Adapter Protocol with ABC Backup

Use `typing.Protocol` for structural subtyping, allowing adapters to be swapped without inheritance coupling.

```python
# src/adapters/base.py
from typing import Protocol, runtime_checkable
from abc import ABC, abstractmethod

@runtime_checkable
class OutputAdapter(Protocol):
    """Protocol for output destination adapters."""

    async def write(
        self,
        data: dict,
        destination: str,
        *,
        dry_run: bool = False,
    ) -> WriteResult:
        """Write data to destination.

        Args:
            data: Structured data to write
            destination: Target identifier (sheet ID, folder ID, etc.)
            dry_run: If True, validate but don't write

        Returns:
            WriteResult with success status and metadata
        """
        ...

    async def health_check(self) -> bool:
        """Verify adapter can reach its target system."""
        ...
```

### Pattern 2: Retry Wrapper with Tenacity

Wrap adapter methods with tenacity for automatic retry:

```python
# src/output/queue.py
from tenacity import (
    AsyncRetrying,
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import structlog

logger = structlog.get_logger()

# Decorator for adapter methods
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def write_with_retry(adapter: OutputAdapter, data: dict, dest: str) -> WriteResult:
    return await adapter.write(data, dest)
```

### Pattern 3: Template Rendering with Jinja2

Simple placeholder syntax matching CONTEXT.md requirements:

```python
# src/output/renderer.py
from jinja2 import Environment, FileSystemLoader, select_autoescape

class MinutesRenderer:
    """Render meeting minutes from templates."""

    def __init__(self, template_dir: str = "templates"):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_markdown(
        self,
        template_name: str,
        context: MinutesContext,
    ) -> str:
        """Render minutes to Markdown.

        Template placeholders:
        - {{meeting_date}}
        - {{meeting_title}}
        - {{attendees}}
        - {{decisions}}
        - {{action_items}}
        - {{risks}}
        - {{issues}}
        - {{next_steps}}
        """
        template = self.env.get_template(template_name)
        return template.render(context.model_dump())
```

### Pattern 4: Output Router

Route outputs to appropriate adapters based on project configuration:

```python
# src/output/router.py
class OutputRouter:
    """Route meeting output to configured destinations."""

    def __init__(
        self,
        sheets_adapter: SheetsAdapter | None = None,
        drive_adapter: DriveAdapter | None = None,
    ):
        self._sheets = sheets_adapter
        self._drive = drive_adapter

    async def route_output(
        self,
        minutes: RenderedMinutes,
        raid_items: RaidBundle,
        config: ProjectOutputConfig,
    ) -> list[WriteResult]:
        """Route output according to project config.

        Default routing (per CONTEXT.md):
        - Minutes -> Google Drive
        - RAID items -> Google Sheets
        """
        results = []

        if config.minutes_destination and self._drive:
            results.append(
                await self._drive.write(minutes, config.minutes_destination)
            )

        if config.raid_destination and self._sheets:
            results.append(
                await self._sheets.write(raid_items, config.raid_destination)
            )

        return results
```

### Anti-Patterns to Avoid

- **God adapter:** Don't create one adapter that handles all destinations. Keep Sheets and Drive separate.
- **Sync writes in request:** Don't block HTTP response waiting for Google API. Use background tasks.
- **Hardcoded credentials:** Don't embed service account paths. Use env vars consistently (already done in existing adapters).
- **Silent failures:** Don't swallow write errors. Queue for retry and alert user.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template rendering | Custom string replacement | Jinja2 | Escaping, filters, inheritance built-in |
| Retry logic | Custom while loops | tenacity | Backoff algorithms, jitter, callbacks |
| Google Sheets API | Raw HTTP | gspread | OAuth, batch updates, error handling |
| Google Drive API | Raw HTTP | google-api-python-client | Resumable uploads, MIME handling |
| Structured logging | Custom JSON formatter | structlog | Already in codebase, processors, context binding |

**Key insight:** All integration complexity lives in authentication and rate limiting. Libraries handle both; custom code reinvents poorly.

## Common Pitfalls

### Pitfall 1: Google Sheets Rate Limits

**What goes wrong:** 429 RESOURCE_EXHAUSTED errors when writing many rows
**Why it happens:** Sheets API limits: 300 req/60s/project, 60 req/60s/user
**How to avoid:**
- Use `batch_update()` instead of individual cell writes
- Batch RAID items into single API call
- Implement exponential backoff with tenacity
**Warning signs:** Sporadic write failures, especially during bulk operations

### Pitfall 2: Jinja2 Template Security

**What goes wrong:** Template injection if user-controlled content contains `{{`
**Why it happens:** Jinja2 interprets placeholders in all text
**How to avoid:**
- Use `autoescape=True` for HTML templates
- Don't allow users to edit templates with arbitrary Jinja2 syntax (CONTEXT.md says simple placeholders only)
- Validate template syntax before saving
**Warning signs:** Rendered output contains raw `{{` or crashes on user data

### Pitfall 3: Credentials Path Confusion

**What goes wrong:** Works in dev, fails in production
**Why it happens:** Hardcoded paths, missing env vars
**How to avoid:**
- Follow existing pattern: `os.environ.get("GOOGLE_SHEETS_CREDENTIALS")`
- Document all required env vars
- Fail fast with clear error messages (existing adapters do this well)
**Warning signs:** "credentials not found" only in certain environments

### Pitfall 4: Sync Adapter in Async Context

**What goes wrong:** Event loop blocked, slow API responses
**Why it happens:** gspread methods are synchronous
**How to avoid:**
- Wrap sync calls in `asyncio.to_thread()` (existing pattern in EventBus)
- Or use async-native approach from start
**Warning signs:** Slow response times when writing to Sheets

### Pitfall 5: Missing Audit Trail

**What goes wrong:** Can't debug what was written where
**Why it happens:** Writes happen but no record kept
**How to avoid:**
- Log every write attempt with structlog
- Include: destination, item count, success/failure, duration
- Store audit records in local DB (per CONTEXT.md)
**Warning signs:** User reports "item missing" but no way to verify

## Code Examples

### Google Sheets Batch Write

```python
# src/adapters/sheets_adapter.py
# Source: gspread docs + existing RosterAdapter pattern
import asyncio
from typing import Any
import gspread
from google.oauth2.service_account import Credentials
import structlog

logger = structlog.get_logger()

class SheetsAdapter:
    """Adapter for writing RAID items to Google Sheets."""

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(self, credentials_path: str | None = None):
        self._credentials_path = credentials_path or os.environ.get(
            "GOOGLE_SHEETS_CREDENTIALS"
        )
        self._client: gspread.Client | None = None

    async def write_raid_items(
        self,
        spreadsheet_id: str,
        items: list[dict],
        sheet_name: str = "RAID",
        *,
        dry_run: bool = False,
    ) -> WriteResult:
        """Batch write RAID items to sheet.

        Uses batch_update for efficiency (single API call).
        Includes UUID in hidden column for upsert support.
        """
        if dry_run:
            logger.info("Dry run", item_count=len(items), sheet=sheet_name)
            return WriteResult(success=True, dry_run=True, item_count=len(items))

        # Run sync gspread in thread pool
        return await asyncio.to_thread(
            self._write_sync, spreadsheet_id, items, sheet_name
        )

    def _write_sync(
        self,
        spreadsheet_id: str,
        items: list[dict],
        sheet_name: str,
    ) -> WriteResult:
        """Synchronous write (called via to_thread)."""
        client = self._get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(sheet_name, rows=100, cols=20)

        # Prepare rows with UUID in first column (for upsert)
        rows = []
        for item in items:
            rows.append([
                item.get("uuid"),  # Hidden column A for upsert
                item.get("type"),  # Decision/Action/Risk/Issue
                item.get("description"),
                item.get("owner"),
                item.get("due_date", ""),
                item.get("status", ""),
                item.get("confidence"),
            ])

        # Batch update in single API call
        if rows:
            worksheet.batch_update([{
                "range": f"A2:G{len(rows) + 1}",
                "values": rows,
            }], value_input_option="USER_ENTERED")

        logger.info(
            "Wrote RAID items to sheet",
            spreadsheet_id=spreadsheet_id,
            sheet=sheet_name,
            item_count=len(rows),
        )
        return WriteResult(success=True, item_count=len(rows))
```

### Google Drive Upload

```python
# src/adapters/drive_adapter.py
# Source: Google Drive API docs + existing CalendarAdapter pattern
import asyncio
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import structlog

logger = structlog.get_logger()

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class DriveAdapter:
    """Adapter for uploading meeting minutes to Google Drive."""

    def __init__(self, credentials_path: str | None = None):
        self._credentials_path = (
            credentials_path
            or os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
            or os.environ.get("GOOGLE_SHEETS_CREDENTIALS")  # Fallback
        )
        self._service = None

    async def upload_minutes(
        self,
        content: str,
        filename: str,
        folder_id: str,
        mime_type: str = "text/markdown",
        *,
        dry_run: bool = False,
    ) -> WriteResult:
        """Upload meeting minutes to Drive folder.

        Args:
            content: Rendered minutes content
            filename: Name for the file (e.g., "2026-01-18-standup-minutes.md")
            folder_id: Google Drive folder ID
            mime_type: Content type (text/markdown or text/html)
            dry_run: Validate but don't upload
        """
        if dry_run:
            logger.info("Dry run upload", filename=filename, folder=folder_id)
            return WriteResult(success=True, dry_run=True)

        return await asyncio.to_thread(
            self._upload_sync, content, filename, folder_id, mime_type
        )

    def _upload_sync(
        self,
        content: str,
        filename: str,
        folder_id: str,
        mime_type: str,
    ) -> WriteResult:
        """Synchronous upload (called via to_thread)."""
        service = self._get_service()

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype=mime_type,
            resumable=True,
        )

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,webViewLink",
        ).execute()

        logger.info(
            "Uploaded minutes to Drive",
            file_id=file.get("id"),
            filename=filename,
            folder=folder_id,
        )

        return WriteResult(
            success=True,
            external_id=file.get("id"),
            url=file.get("webViewLink"),
        )
```

### Meeting Minutes Template

```jinja2
{# templates/default_minutes.md.j2 #}
# Meeting Minutes: {{ meeting_title }}

**Date:** {{ meeting_date }}
**Duration:** {{ duration_minutes }} minutes
**Attendees:** {{ attendees | join(", ") }}

---

## Decisions

{% for decision in decisions %}
### {{ loop.index }}. {{ decision.description }}{% if decision.confidence < 0.7 %} [LOW CONFIDENCE]{% endif %}

{% if decision.rationale %}**Rationale:** {{ decision.rationale }}{% endif %}
{% if decision.alternatives %}**Alternatives considered:** {{ decision.alternatives | join("; ") }}{% endif %}

{% endfor %}
{% if not decisions %}*No decisions recorded.*{% endif %}

---

## Action Items

| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|
{% for action in action_items %}
| {{ loop.index }} | {{ action.description }}{% if action.confidence < 0.7 %} [?]{% endif %} | {{ action.assignee_name or "Unassigned" }} | {{ action.due_date or "TBD" }} | Pending |
{% endfor %}
{% if not action_items %}
| - | *No action items recorded.* | - | - | - |
{% endif %}

---

## Risks

{% for risk in risks %}
### {{ loop.index }}. {{ risk.description }}{% if risk.confidence < 0.7 %} [LOW CONFIDENCE]{% endif %}

- **Severity:** {{ risk.severity | upper }}
- **Owner:** {{ risk.owner_name or "Unassigned" }}
{% if risk.mitigation %}- **Mitigation:** {{ risk.mitigation }}{% endif %}

{% endfor %}
{% if not risks %}*No risks identified.*{% endif %}

---

## Issues

{% for issue in issues %}
### {{ loop.index }}. {{ issue.description }}{% if issue.confidence < 0.7 %} [LOW CONFIDENCE]{% endif %}

- **Priority:** {{ issue.priority | upper }}
- **Status:** {{ issue.status }}
- **Owner:** {{ issue.owner_name or "Unassigned" }}
{% if issue.impact %}- **Impact:** {{ issue.impact }}{% endif %}

{% endfor %}
{% if not issues %}*No issues raised.*{% endif %}

---

## Next Steps

{% for step in next_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}

---

*Generated: {{ generated_at }}*
```

### Audit Logging

```python
# Audit log entry structure (stored in local DB)
# Source: structlog best practices + CONTEXT.md requirements
class AuditLogEntry(BaseModel):
    """Record of write operation."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    operation: str  # "write_minutes", "write_raid_items"
    adapter: str    # "sheets", "drive"
    destination: str  # Sheet ID, folder ID
    item_count: int
    success: bool
    error_message: str | None = None
    duration_ms: int
    dry_run: bool = False

    # What was written (for debugging)
    meeting_id: UUID | None = None
    item_ids: list[UUID] = Field(default_factory=list)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| gspread v5 API | gspread v6 API | 2024 | batch_update args swapped (range, values) |
| google-api-python-client sync only | asyncio.to_thread wrapper | Python 3.9+ | Non-blocking I/O |
| Custom retry loops | tenacity library | N/A | Standardized backoff patterns |
| f-string templates | Jinja2 external templates | N/A | Templates stored in Drive per CONTEXT.md |

**Deprecated/outdated:**
- gspread `batch_update(values, range)` order (v5) - now `batch_update(range, values)` in v6, use named args for compatibility
- PyDrive wrapper - original project abandoned, use google-api-python-client directly

## Open Questions

1. **Template storage location in Google Drive**
   - What we know: CONTEXT.md says "Templates stored in Google Drive as editable docs"
   - What's unclear: Folder structure, how to discover project-specific templates
   - Recommendation: Define convention (e.g., `templates/` folder in project Drive folder)

2. **HTML styling approach**
   - What we know: CONTEXT.md says "HTML template styling" is Claude's discretion
   - What's unclear: Inline CSS vs external stylesheet
   - Recommendation: Inline CSS for portability; simple clean styling

3. **Retry queue persistence**
   - What we know: Queue items when retries exhausted
   - What's unclear: Store in-memory vs SQLite vs event store
   - Recommendation: SQLite table (simple, matches existing Turso pattern)

## Sources

### Primary (HIGH confidence)
- gspread 6.1.2 docs - batch_update, rate limits, authentication
- Jinja2 3.1.x docs - template syntax, filters, environment setup
- Google Drive API docs - file upload, MediaFileUpload
- tenacity docs - AsyncRetrying, exponential backoff, callbacks

### Secondary (MEDIUM confidence)
- Existing codebase adapters (RosterAdapter, SlackAdapter, CalendarAdapter) - established patterns
- structlog usage in existing adapters - logging pattern

### Tertiary (LOW confidence)
- WebSearch results for adapter pattern best practices - general patterns verified against existing code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Jinja2 and tenacity are well-documented, widely used
- Architecture: HIGH - extends proven patterns already in codebase
- Pitfalls: HIGH - Google API limits are well-documented; gspread rate limits verified in official docs

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - stable libraries, unlikely to change)
