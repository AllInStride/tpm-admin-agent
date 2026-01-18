"""Meetings API endpoints for transcript upload and processing."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

from src.events.bus import EventBus
from src.events.types import MeetingCreated, TranscriptParsed
from src.models.meeting import Meeting
from src.services.transcript_parser import TranscriptParser

# Constants
ALLOWED_EXTENSIONS = {".vtt", ".srt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/meetings", tags=["meetings"])


class MeetingResponse(BaseModel):
    """Response model for successful transcript upload with meeting details."""

    id: str
    title: str
    date: datetime
    speaker_count: int
    utterance_count: int
    duration_seconds: float | None


def get_event_bus(request: Request) -> EventBus:
    """Dependency to get EventBus from app state."""
    return request.app.state.event_bus


async def validate_transcript_file(file: UploadFile) -> tuple[str, str]:
    """Validate and decode an uploaded transcript file.

    Args:
        file: The uploaded file from the request.

    Returns:
        Tuple of (decoded_content, extension).

    Raises:
        HTTPException: With appropriate status codes for validation failures:
            - 400: Missing filename, empty file, or encoding failure
            - 413: File too large
            - 415: Unsupported file extension
    """
    # Check filename exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read content
    content_bytes = await file.read()

    # Check not empty
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # Check size
    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_mb}MB",
        )

    # Decode with UTF-8-sig first (handles BOM), fall back to Latin-1
    content: str
    try:
        content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = content_bytes.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Unable to decode file. Supported encodings: UTF-8, Latin-1",
            )

    return content, ext


@router.post("/upload", response_model=MeetingResponse)
async def upload_transcript(
    file: UploadFile,
    event_bus: EventBus = Depends(get_event_bus),
) -> MeetingResponse:
    """Upload a transcript file for processing.

    Accepts VTT or SRT transcript files, parses them into structured data,
    creates a Meeting, and emits events for persistence.

    Args:
        file: The transcript file (VTT or SRT format).
        event_bus: EventBus instance from app state.

    Returns:
        MeetingResponse with meeting ID, title, speaker count, utterance count.

    Raises:
        HTTPException: For validation failures (400, 413, 415).
    """
    content, ext = await validate_transcript_file(file)

    # Parse the transcript
    parser = TranscriptParser()
    try:
        parsed = parser.parse(content, ext)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse transcript: {e!s}",
        )

    # Create Meeting from parsed data
    meeting = Meeting(
        title=Path(file.filename or "untitled")
        .stem.replace("_", " ")
        .replace("-", " "),
        date=datetime.now(UTC),
        utterances=parsed.utterances,
        duration_minutes=int(parsed.duration_seconds / 60)
        if parsed.duration_seconds
        else None,
        transcript_source="zoom",
        transcript_file=file.filename,
    )

    # Emit and persist events
    await event_bus.publish_and_store(
        MeetingCreated(
            aggregate_id=meeting.id,
            title=meeting.title,
            meeting_date=meeting.date,
            participant_count=len(parsed.speakers),
            transcript_filename=file.filename,
        )
    )

    await event_bus.publish_and_store(
        TranscriptParsed(
            aggregate_id=meeting.id,
            utterance_count=len(parsed.utterances),
            speaker_count=len(parsed.speakers),
            duration_seconds=parsed.duration_seconds,
        )
    )

    return MeetingResponse(
        id=str(meeting.id),
        title=meeting.title,
        date=meeting.date,
        speaker_count=len(parsed.speakers),
        utterance_count=len(parsed.utterances),
        duration_seconds=parsed.duration_seconds,
    )
