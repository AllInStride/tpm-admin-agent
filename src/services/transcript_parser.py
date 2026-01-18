"""Transcript parser service for VTT and SRT files."""

from dataclasses import dataclass
from io import StringIO

import webvtt

from src.models.meeting import Utterance


@dataclass
class ParsedTranscript:
    """Result of parsing a transcript file."""

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
            ValueError: If format is unsupported
            webvtt.errors.MalformedFileError: If content is malformed
        """
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}")

        # Handle empty content
        content_stripped = content.strip()
        if not content_stripped or content_stripped == "WEBVTT":
            return ParsedTranscript(
                utterances=[],
                speakers=[],
                duration_seconds=None,
            )

        # Parse based on format using from_buffer which supports both formats
        # Strip leading dot for format parameter (webvtt expects "vtt" not ".vtt")
        format_type = format.lstrip(".")
        captions = webvtt.from_buffer(StringIO(content), format=format_type)

        utterances: list[Utterance] = []
        speakers_seen: set[str] = set()

        for caption in captions:
            # Extract speaker from voice tag (e.g., "<v John Smith>Hello")
            # Falls back to "Unknown Speaker" if no voice tag
            speaker = caption.voice or "Unknown Speaker"
            speakers_seen.add(speaker)

            utterances.append(
                Utterance(
                    speaker=speaker,
                    text=caption.text,
                    start_time=caption.start_in_seconds,
                    end_time=caption.end_in_seconds,
                )
            )

        # Calculate total duration from last caption's end time
        duration = None
        if utterances:
            duration = utterances[-1].end_time

        return ParsedTranscript(
            utterances=utterances,
            speakers=sorted(speakers_seen),
            duration_seconds=duration,
        )
