"""Meetings API endpoints for transcript upload and processing."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

# Constants
ALLOWED_EXTENSIONS = {".vtt", ".srt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/meetings", tags=["meetings"])


class UploadResponse(BaseModel):
    """Response model for successful transcript upload."""

    status: str
    filename: str
    size: int
    format: str


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


@router.post("/upload", response_model=UploadResponse)
async def upload_transcript(file: UploadFile) -> UploadResponse:
    """Upload a transcript file for processing.

    Accepts VTT or SRT transcript files and validates them for processing.
    The actual parsing will be wired in Plan 02-03.

    Args:
        file: The transcript file (VTT or SRT format).

    Returns:
        UploadResponse with validation status, filename, size, and format.

    Raises:
        HTTPException: For validation failures (400, 413, 415).
    """
    content, ext = await validate_transcript_file(file)

    return UploadResponse(
        status="validated",
        filename=file.filename or "unknown",
        size=len(content),
        format=ext,
    )
