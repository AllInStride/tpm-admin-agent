# Phase 2: Transcript Ingestion - Research

**Researched:** 2026-01-17
**Domain:** File upload, VTT/SRT parsing, speaker extraction
**Confidence:** HIGH

## Summary

This phase involves building an API endpoint to accept Zoom transcript uploads (VTT or SRT format), parse them into structured meeting data with timestamped utterances, and persist them as Meeting events. The technical domain is well-understood with mature Python libraries available.

**Key findings:**
- VTT and SRT are simple text formats with well-defined specs
- `webvtt-py` is the standard Python library - handles both VTT and SRT parsing
- Zoom VTT exports use `<v SpeakerName>` voice tags for speaker identification
- FastAPI's `UploadFile` handles file uploads efficiently via `SpooledTemporaryFile`
- The existing `Utterance` model expects timestamps in seconds (float) - webvtt-py provides `start_in_seconds` and `end_in_seconds` properties

**Primary recommendation:** Use `webvtt-py` for parsing both VTT and SRT files. Parse speaker names from the `caption.voice` property. Validate files by attempting to parse them - the library raises exceptions for malformed files.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| webvtt-py | 0.5.1 | VTT/SRT parsing | Most complete Python VTT library, supports voice tags, handles both formats |
| python-multipart | 0.0.18+ | File uploads | Required by FastAPI for multipart/form-data |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiofiles | 24.1+ | Async file I/O | If saving uploaded files to disk before processing |
| chardet | 5.2+ | Encoding detection | If non-UTF-8 files are common (SRT files often have varied encodings) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| webvtt-py | pysrt + custom VTT | pysrt is SRT-only, would need separate VTT handling |
| webvtt-py | subtitle-parser | Less mature, fewer features, smaller community |
| File upload | Presigned URLs | Overkill for transcripts (typically <1MB) |

**Installation:**
```bash
uv add webvtt-py python-multipart
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── api/
│   └── meetings.py          # Upload endpoint
├── services/
│   └── transcript_parser.py # Parse VTT/SRT to Utterances
├── models/
│   └── meeting.py           # Existing Meeting/Utterance models
└── events/
    └── types.py             # MeetingCreated, TranscriptParsed events
```

### Pattern 1: Service Layer for Parsing

**What:** Separate parsing logic from API handlers into a dedicated service class
**When to use:** Always - keeps API handlers thin, makes parsing testable

```python
# src/services/transcript_parser.py
from dataclasses import dataclass
from typing import BinaryIO
import webvtt
from io import StringIO

from src.models.meeting import Utterance

@dataclass
class ParsedTranscript:
    utterances: list[Utterance]
    speakers: list[str]
    duration_seconds: float | None

class TranscriptParser:
    """Parse VTT and SRT transcript files into structured data."""

    SUPPORTED_FORMATS = {".vtt", ".srt"}

    def parse(self, content: str, format: str) -> ParsedTranscript:
        """Parse transcript content into structured data.

        Args:
            content: Raw transcript file content (UTF-8 decoded)
            format: File extension (".vtt" or ".srt")

        Returns:
            ParsedTranscript with utterances, speakers, and duration

        Raises:
            ValueError: If format unsupported or content malformed
        """
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}")

        # Parse based on format
        if format == ".vtt":
            captions = webvtt.from_string(content)
        else:  # .srt
            captions = webvtt.from_srt(StringIO(content))

        utterances = []
        speakers_seen: set[str] = set()

        for caption in captions:
            # Extract speaker from voice tag (e.g., "<v John Smith>Hello")
            speaker = caption.voice or "Unknown Speaker"
            speakers_seen.add(speaker)

            utterances.append(Utterance(
                speaker=speaker,
                text=caption.text,
                start_time=caption.start_in_seconds,
                end_time=caption.end_in_seconds,
            ))

        # Calculate total duration
        duration = None
        if captions:
            duration = captions.total_length

        return ParsedTranscript(
            utterances=utterances,
            speakers=sorted(speakers_seen),
            duration_seconds=duration,
        )
```

### Pattern 2: File Upload Validation

**What:** Validate file before processing with early rejection
**When to use:** Always - fail fast with clear error messages

```python
# src/api/meetings.py
from fastapi import APIRouter, UploadFile, HTTPException
from pathlib import Path

router = APIRouter(prefix="/meetings", tags=["meetings"])

ALLOWED_EXTENSIONS = {".vtt", ".srt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

async def validate_transcript_file(file: UploadFile) -> tuple[str, str]:
    """Validate uploaded transcript file.

    Returns:
        Tuple of (content, extension)

    Raises:
        HTTPException: If validation fails
    """
    # Check filename exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Read content
    content = await file.read()

    # Check size
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB"
        )

    # Check not empty
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Decode to string (VTT/SRT are text files)
    try:
        text_content = content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        # Try common fallback encodings for SRT
        try:
            text_content = content.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Could not decode file. Expected UTF-8 encoding."
            )

    return text_content, ext
```

### Pattern 3: Event Emission on Success

**What:** Emit domain events after successful operations
**When to use:** After meeting creation and transcript parsing

```python
# In API handler
from src.events.types import MeetingCreated, TranscriptParsed

async def create_meeting_from_transcript(
    file: UploadFile,
    event_bus: EventBus,
):
    # ... validation and parsing ...

    # Create meeting
    meeting = Meeting(
        title=extract_title_from_filename(file.filename),
        date=datetime.now(UTC),
        utterances=parsed.utterances,
        transcript_source="zoom",
        transcript_file=file.filename,
    )

    # Emit MeetingCreated event
    await event_bus.publish(MeetingCreated(
        aggregate_id=meeting.id,
        title=meeting.title,
        meeting_date=meeting.date,
        participant_count=len(parsed.speakers),
        transcript_filename=file.filename,
    ))

    # Emit TranscriptParsed event
    await event_bus.publish(TranscriptParsed(
        aggregate_id=meeting.id,
        utterance_count=len(parsed.utterances),
        speaker_count=len(parsed.speakers),
        duration_seconds=parsed.duration_seconds,
    ))
```

### Anti-Patterns to Avoid
- **Parsing in the API handler:** Keep handlers thin, delegate to services
- **Trusting Content-Type header:** Always validate file content, not just MIME type
- **Loading entire file into memory as bytes:** Use UploadFile for streaming (though for text transcripts <10MB this is acceptable)
- **Blocking I/O in async handlers:** Use async file operations or run in threadpool

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VTT parsing | Custom regex parser | webvtt-py | Edge cases: BOM, styles, comments, multi-line cues |
| SRT parsing | Custom regex parser | webvtt-py.from_srt() | Handles encoding, sequence validation, timestamp formats |
| Voice tag extraction | Regex for `<v name>` | caption.voice property | webvtt-py handles tag variations and escaping |
| Timestamp to seconds | Manual split/calculation | caption.start_in_seconds | Handles all timestamp formats correctly |
| File upload handling | Manual multipart parsing | FastAPI UploadFile | Memory management, streaming, async |

**Key insight:** VTT/SRT look simple but have many edge cases (BOM, encoding, overlapping timestamps, style tags, multi-line cues). webvtt-py handles all of these correctly.

## Common Pitfalls

### Pitfall 1: Zoom VTT Speaker Format Variations

**What goes wrong:** Zoom's VTT format has evolved. Older exports used `Speaker 0`, `Speaker 1` (generic). Newer exports may include actual names via voice tags. Some exports strip speaker info entirely.

**Why it happens:** Zoom changed their export format multiple times. Third-party tools also produce different formats.

**How to avoid:**
- Check for `caption.voice` property first (standard voice tag)
- Fall back to parsing text for `SpeakerName:` patterns at line start
- Default to "Unknown Speaker" if no speaker info found

**Warning signs:** All utterances have the same speaker name or "Unknown Speaker"

### Pitfall 2: SRT Encoding Chaos

**What goes wrong:** SRT files have no encoding standard. Files claim UTF-8 but contain Latin-1 characters. BOM presence is inconsistent.

**Why it happens:** SRT predates UTF-8 standardization. Different tools use different encodings.

**How to avoid:**
- Decode with `utf-8-sig` first (handles BOM)
- Fall back to `latin-1` if UTF-8 fails
- Consider using `chardet` for automatic detection if this becomes a frequent issue

**Warning signs:** UnicodeDecodeError exceptions, garbled characters in output

### Pitfall 3: Empty or Single-Speaker Transcripts

**What goes wrong:** Some transcripts have no speaker diarization (just one unnamed speaker). Code assumes multiple speakers exist.

**Why it happens:** Zoom's free tier doesn't always include speaker diarization. Manual transcripts often lack speaker tags.

**How to avoid:**
- Handle single-speaker case gracefully
- Don't error on missing voice tags
- Consider adding a flag: `has_speaker_diarization: bool`

**Warning signs:** Empty speaker lists, all utterances attributed to same generic speaker

### Pitfall 4: Overlapping Timestamps

**What goes wrong:** Some transcripts have cues with overlapping time ranges (one speaker starts before another finishes).

**Why it happens:** Real conversations have overlapping speech. Some transcription tools capture this.

**How to avoid:**
- Don't assume sequential non-overlapping timestamps
- Don't reorder utterances - preserve original order
- Store timestamps as provided; let downstream consumers handle overlap

**Warning signs:** end_time of utterance N > start_time of utterance N+1

### Pitfall 5: File Size and Memory

**What goes wrong:** Very long meetings (4+ hours) can have large transcript files. Reading entire file into memory can cause issues.

**Why it happens:** Transcripts grow linearly with meeting duration.

**How to avoid:**
- Set reasonable file size limits (10MB handles ~50 hours of transcription)
- FastAPI's UploadFile uses SpooledTemporaryFile (memory-backed until 1MB, then disk)
- For typical transcripts (<1MB), in-memory processing is fine

**Warning signs:** Memory usage spikes during upload processing

## Code Examples

Verified patterns from official sources and research:

### Complete Upload Endpoint

```python
# src/api/meetings.py
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, HTTPException, Depends, Request
from pydantic import BaseModel

from src.models.meeting import Meeting, Utterance
from src.services.transcript_parser import TranscriptParser, ParsedTranscript
from src.events.bus import EventBus
from src.events.types import MeetingCreated, TranscriptParsed

router = APIRouter(prefix="/meetings", tags=["meetings"])

ALLOWED_EXTENSIONS = {".vtt", ".srt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class MeetingResponse(BaseModel):
    """Response model for meeting creation."""
    id: str
    title: str
    date: datetime
    speaker_count: int
    utterance_count: int
    duration_seconds: float | None


def get_event_bus(request: Request) -> EventBus:
    """Dependency to get EventBus from app state."""
    return request.app.state.event_bus


@router.post("/upload", response_model=MeetingResponse)
async def upload_transcript(
    file: UploadFile,
    event_bus: EventBus = Depends(get_event_bus),
) -> MeetingResponse:
    """Upload a VTT or SRT transcript file to create a meeting.

    The transcript is parsed to extract:
    - Timestamped utterances
    - Speaker names (from voice tags)
    - Total duration

    A Meeting is created and persisted via events.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {ext}. Allowed: .vtt, .srt"
        )

    # Read and validate content
    content_bytes = await file.read()

    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB"
        )

    # Decode to string
    try:
        content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = content_bytes.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Could not decode file. Expected UTF-8 encoding."
            )

    # Parse transcript
    parser = TranscriptParser()
    try:
        parsed = parser.parse(content, ext)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse transcript: {str(e)}"
        )

    # Create meeting
    meeting = Meeting(
        title=Path(file.filename).stem.replace("_", " ").replace("-", " "),
        date=datetime.now(UTC),
        utterances=parsed.utterances,
        duration_minutes=int(parsed.duration_seconds / 60) if parsed.duration_seconds else None,
        transcript_source="zoom",
        transcript_file=file.filename,
    )

    # Emit events
    await event_bus.publish(MeetingCreated(
        aggregate_id=meeting.id,
        title=meeting.title,
        meeting_date=meeting.date,
        participant_count=len(parsed.speakers),
        transcript_filename=file.filename,
    ))

    await event_bus.publish(TranscriptParsed(
        aggregate_id=meeting.id,
        utterance_count=len(parsed.utterances),
        speaker_count=len(parsed.speakers),
        duration_seconds=parsed.duration_seconds,
    ))

    return MeetingResponse(
        id=str(meeting.id),
        title=meeting.title,
        date=meeting.date,
        speaker_count=len(parsed.speakers),
        utterance_count=len(parsed.utterances),
        duration_seconds=parsed.duration_seconds,
    )
```

### Reading VTT with Voice Tags

```python
# Source: webvtt-py documentation
import webvtt

for caption in webvtt.read('captions.vtt'):
    print(caption.identifier)      # cue identifier if any
    print(caption.start)           # "00:00:01.000" (string)
    print(caption.end)             # "00:00:05.000" (string)
    print(caption.start_in_seconds)  # 1.0 (float)
    print(caption.end_in_seconds)    # 5.0 (float)
    print(caption.text)            # caption text (tags removed)
    print(caption.voice)           # speaker name from <v> tag
    print(caption.raw_text)        # text with tags preserved
```

### Parsing from String (No File)

```python
# Source: webvtt-py documentation
import webvtt

vtt_content = """WEBVTT

00:00:01.000 --> 00:00:05.000
<v John>Hello everyone

00:00:05.000 --> 00:00:10.000
<v Jane>Hi John, welcome to the meeting
"""

captions = webvtt.from_string(vtt_content)
for caption in captions:
    print(f"{caption.voice}: {caption.text}")
```

### Converting SRT to VTT Objects

```python
# Source: webvtt-py documentation
import webvtt
from io import StringIO

srt_content = """1
00:00:01,000 --> 00:00:05,000
Hello everyone

2
00:00:05,000 --> 00:00:10,000
Welcome to the meeting
"""

# from_srt expects a file path, so use StringIO for strings
captions = webvtt.from_srt(StringIO(srt_content))
# Note: SRT doesn't have voice tags, speaker will be None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pysrt for SRT, custom VTT | webvtt-py handles both | webvtt-py 0.4+ | Single library for all subtitle formats |
| Manual voice tag regex | caption.voice property | webvtt-py 0.5 (2024) | Built-in speaker extraction |
| Sync file reads | FastAPI async UploadFile | FastAPI 0.100+ | Better concurrency |

**Deprecated/outdated:**
- pyvtt: Multiple forks, unclear maintenance status
- Manual VTT parsing: webvtt-py handles edge cases

## Open Questions

Things that couldn't be fully resolved:

1. **Zoom VTT speaker name reliability**
   - What we know: Zoom uses `<v Speaker>` tags when available
   - What's unclear: Exact conditions when Zoom includes real names vs generic "Speaker 0"
   - Recommendation: Treat speaker names as best-effort; plan for fuzzy matching in participant resolution (Phase 3+)

2. **Meeting title extraction**
   - What we know: Filename often contains meeting title (e.g., "Weekly_Standup_2024-01-15.vtt")
   - What's unclear: Standardized naming conventions across organizations
   - Recommendation: Use filename as initial title; allow override via request parameter or future editing

3. **Calendar event linking**
   - What we know: Meeting model has `calendar_event_id` field
   - What's unclear: How to correlate uploaded transcript with calendar event
   - Recommendation: Defer to Phase 4+; for now, leave field null

## Sources

### Primary (HIGH confidence)
- [webvtt-py PyPI](https://pypi.org/project/webvtt-py/) - Version 0.5.1, MIT license
- [webvtt-py documentation](https://webvtt-py.readthedocs.io/en/latest/usage.html) - API usage, voice tags
- [webvtt-py GitHub](https://github.com/glut23/webvtt-py) - Source code, start_in_seconds property
- [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/) - UploadFile, python-multipart

### Secondary (MEDIUM confidence)
- [MDN WebVTT Format](https://developer.mozilla.org/en-US/docs/Web/API/WebVTT_API/Web_Video_Text_Tracks_Format) - VTT specification, voice tags
- [Wikipedia SubRip](https://en.wikipedia.org/wiki/SubRip) - SRT format specification
- [Better Stack FastAPI File Upload Guide](https://betterstack.com/community/guides/scaling-python/uploading-files-using-fastapi/) - Validation patterns

### Tertiary (LOW confidence)
- [Zoom Community Discussion](https://community.zoom.com/t5/Zoom-Meetings/List-names-in-audio-recording-transcript/m-p/92322) - Speaker name limitations in Zoom exports
- [BrassTranscripts Blog](https://brasstranscripts.com/blog/multi-speaker-transcript-formats-srt-vtt-json) - Multi-speaker format examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - webvtt-py is well-documented, actively maintained (last release May 2024)
- Architecture: HIGH - Standard FastAPI patterns, verified with official docs
- Pitfalls: MEDIUM - Based on WebSearch and community reports, not personal experience

**Research date:** 2026-01-17
**Valid until:** 2026-03-17 (stable domain, 60 days validity)
