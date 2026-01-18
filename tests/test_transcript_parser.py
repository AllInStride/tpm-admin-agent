"""Unit tests for TranscriptParser service."""

import pytest

from src.services.transcript_parser import ParsedTranscript, TranscriptParser


@pytest.fixture
def parser() -> TranscriptParser:
    """Create a TranscriptParser instance."""
    return TranscriptParser()


@pytest.fixture
def vtt_with_voice_tags() -> str:
    """VTT content with voice tags for speaker identification."""
    return """WEBVTT

00:00:01.000 --> 00:00:05.000
<v John Smith>Hello everyone, welcome to the meeting.

00:00:05.000 --> 00:00:10.000
<v Jane Doe>Hi John, thanks for organizing this.

00:00:10.000 --> 00:00:15.000
<v John Smith>Let's get started with the agenda.
"""


@pytest.fixture
def srt_content() -> str:
    """SRT content without voice tags."""
    return """1
00:00:01,000 --> 00:00:05,000
Hello everyone, welcome to the meeting.

2
00:00:05,000 --> 00:00:10,000
Hi there, thanks for organizing this.

3
00:00:10,000 --> 00:00:15,000
Let's get started with the agenda.
"""


@pytest.fixture
def empty_vtt() -> str:
    """Empty VTT file with just header."""
    return "WEBVTT\n\n"


class TestVTTWithVoiceTags:
    """Tests for VTT files with voice tags."""

    def test_parses_utterances_count(
        self, parser: TranscriptParser, vtt_with_voice_tags: str
    ) -> None:
        """Should parse correct number of utterances."""
        result = parser.parse(vtt_with_voice_tags, ".vtt")
        assert len(result.utterances) == 3

    def test_extracts_speakers(
        self, parser: TranscriptParser, vtt_with_voice_tags: str
    ) -> None:
        """Should extract unique speakers from voice tags."""
        result = parser.parse(vtt_with_voice_tags, ".vtt")
        assert result.speakers == ["Jane Doe", "John Smith"]

    def test_assigns_speaker_to_utterances(
        self, parser: TranscriptParser, vtt_with_voice_tags: str
    ) -> None:
        """Should assign correct speaker to each utterance."""
        result = parser.parse(vtt_with_voice_tags, ".vtt")
        assert result.utterances[0].speaker == "John Smith"
        assert result.utterances[1].speaker == "Jane Doe"
        assert result.utterances[2].speaker == "John Smith"

    def test_timestamps_in_seconds(
        self, parser: TranscriptParser, vtt_with_voice_tags: str
    ) -> None:
        """Should convert timestamps to float seconds.

        Note: webvtt-py truncates to integer seconds via
        start_in_seconds/end_in_seconds properties.
        """
        result = parser.parse(vtt_with_voice_tags, ".vtt")
        assert result.utterances[0].start_time == 1.0
        assert result.utterances[0].end_time == 5.0
        assert result.utterances[1].start_time == 5.0
        assert result.utterances[1].end_time == 10.0

    def test_extracts_text_content(
        self, parser: TranscriptParser, vtt_with_voice_tags: str
    ) -> None:
        """Should extract text without voice tags."""
        result = parser.parse(vtt_with_voice_tags, ".vtt")
        assert result.utterances[0].text == "Hello everyone, welcome to the meeting."
        assert result.utterances[1].text == "Hi John, thanks for organizing this."


class TestSRTWithoutVoiceTags:
    """Tests for SRT files without voice tags."""

    def test_parses_utterances_count(
        self, parser: TranscriptParser, srt_content: str
    ) -> None:
        """Should parse correct number of utterances."""
        result = parser.parse(srt_content, ".srt")
        assert len(result.utterances) == 3

    def test_defaults_to_unknown_speaker(
        self, parser: TranscriptParser, srt_content: str
    ) -> None:
        """Should default all utterances to 'Unknown Speaker'."""
        result = parser.parse(srt_content, ".srt")
        assert result.speakers == ["Unknown Speaker"]
        for utterance in result.utterances:
            assert utterance.speaker == "Unknown Speaker"

    def test_timestamps_in_seconds(
        self, parser: TranscriptParser, srt_content: str
    ) -> None:
        """Should convert SRT timestamps (comma format) to float seconds.

        Note: webvtt-py truncates to integer seconds via
        start_in_seconds/end_in_seconds properties.
        """
        result = parser.parse(srt_content, ".srt")
        assert result.utterances[0].start_time == 1.0
        assert result.utterances[0].end_time == 5.0


class TestEmptyContent:
    """Tests for empty or minimal content."""

    def test_empty_vtt_returns_empty_result(
        self, parser: TranscriptParser, empty_vtt: str
    ) -> None:
        """Should return empty result for VTT with just header."""
        result = parser.parse(empty_vtt, ".vtt")
        assert result.utterances == []
        assert result.speakers == []
        assert result.duration_seconds is None

    def test_whitespace_only_returns_empty_result(
        self, parser: TranscriptParser
    ) -> None:
        """Should return empty result for whitespace-only content."""
        result = parser.parse("   \n\n  ", ".vtt")
        assert result.utterances == []
        assert result.speakers == []
        assert result.duration_seconds is None


class TestInvalidFormat:
    """Tests for unsupported formats."""

    def test_raises_value_error_for_unsupported_format(
        self, parser: TranscriptParser
    ) -> None:
        """Should raise ValueError for unsupported file formats."""
        with pytest.raises(ValueError, match="Unsupported format: .txt"):
            parser.parse("some content", ".txt")

    def test_raises_value_error_for_mp3(self, parser: TranscriptParser) -> None:
        """Should raise ValueError for audio formats."""
        with pytest.raises(ValueError, match="Unsupported format: .mp3"):
            parser.parse("some content", ".mp3")


class TestMalformedContent:
    """Tests for malformed transcript content."""

    def test_raises_on_malformed_vtt(self, parser: TranscriptParser) -> None:
        """Should raise exception for malformed VTT content."""
        malformed = "This is not valid VTT content at all"
        with pytest.raises(Exception):  # webvtt raises various exceptions
            parser.parse(malformed, ".vtt")

    def test_raises_on_malformed_srt(self, parser: TranscriptParser) -> None:
        """Should raise exception for malformed SRT content."""
        malformed = "This is not valid SRT content at all"
        with pytest.raises(Exception):  # webvtt raises various exceptions
            parser.parse(malformed, ".srt")


class TestDurationCalculation:
    """Tests for duration calculation."""

    def test_calculates_duration_from_last_caption(
        self, parser: TranscriptParser, vtt_with_voice_tags: str
    ) -> None:
        """Should calculate duration from last caption's end time."""
        result = parser.parse(vtt_with_voice_tags, ".vtt")
        assert result.duration_seconds == 15.0

    def test_duration_none_for_empty_content(
        self, parser: TranscriptParser, empty_vtt: str
    ) -> None:
        """Should return None duration for empty content."""
        result = parser.parse(empty_vtt, ".vtt")
        assert result.duration_seconds is None

    def test_single_caption_duration(self, parser: TranscriptParser) -> None:
        """Should calculate duration for single caption.

        Note: webvtt-py truncates to integer seconds via end_in_seconds.
        """
        vtt = """WEBVTT

00:00:00.000 --> 00:00:30.000
<v Speaker>Single statement here.
"""
        result = parser.parse(vtt, ".vtt")
        assert result.duration_seconds == 30.0


class TestParsedTranscriptDataclass:
    """Tests for ParsedTranscript dataclass."""

    def test_parsed_transcript_attributes(
        self, parser: TranscriptParser, vtt_with_voice_tags: str
    ) -> None:
        """Should have correct attributes on ParsedTranscript."""
        result = parser.parse(vtt_with_voice_tags, ".vtt")
        assert isinstance(result, ParsedTranscript)
        assert hasattr(result, "utterances")
        assert hasattr(result, "speakers")
        assert hasattr(result, "duration_seconds")


class TestSupportedFormats:
    """Tests for SUPPORTED_FORMATS constant."""

    def test_supported_formats_constant(self, parser: TranscriptParser) -> None:
        """Should have VTT and SRT in supported formats."""
        assert ".vtt" in TranscriptParser.SUPPORTED_FORMATS
        assert ".srt" in TranscriptParser.SUPPORTED_FORMATS
        assert len(TranscriptParser.SUPPORTED_FORMATS) == 2
