"""Tests for OutputRouter orchestration."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.adapters.base import WriteResult
from src.output.config import ProjectOutputConfig
from src.output.router import OutputResult, OutputRouter
from src.output.schemas import (
    ActionItemData,
    DecisionItem,
    IssueItem,
    MinutesContext,
    RaidBundle,
    RenderedMinutes,
    RiskItem,
)


@pytest.fixture
def sample_context():
    """Create sample MinutesContext for testing."""
    return MinutesContext(
        meeting_id=uuid4(),
        meeting_title="Sprint Planning",
        meeting_date=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
        duration_minutes=60,
        attendees=["Alice (PM)", "Bob (Engineer)"],
        decisions=[
            DecisionItem(description="Use Python 3.12", confidence=0.95),
        ],
        action_items=[
            ActionItemData(
                description="Create design doc",
                assignee_name="Bob",
                due_date="2026-01-20",
                confidence=0.9,
            ),
        ],
        risks=[
            RiskItem(
                description="API rate limits",
                severity="HIGH",
                owner_name="Alice",
                confidence=0.85,
            ),
        ],
        issues=[
            IssueItem(
                description="CI pipeline slow",
                priority="MEDIUM",
                status="Open",
                confidence=0.8,
            ),
        ],
        next_steps=["Create design doc"],
    )


@pytest.fixture
def sample_bundle(sample_context):
    """Create sample RaidBundle for testing."""
    return RaidBundle(
        meeting_id=sample_context.meeting_id,
        decisions=sample_context.decisions,
        action_items=sample_context.action_items,
        risks=sample_context.risks,
        issues=sample_context.issues,
    )


@pytest.fixture
def config_with_destinations():
    """Create config with destination IDs."""
    return ProjectOutputConfig(
        minutes_destination="folder123",
        raid_destination="sheet456",
        raid_sheet_name="RAID",
        template_name="default_minutes",
        enabled_targets=["drive", "sheets"],
    )


@pytest.fixture
def mock_renderer():
    """Create mock MinutesRenderer."""
    renderer = MagicMock()
    renderer.render.return_value = RenderedMinutes(
        meeting_id=uuid4(),
        markdown="# Meeting Minutes\n\nContent here",
        html="<h1>Meeting Minutes</h1><p>Content here</p>",
        template_used="default_minutes",
    )
    return renderer


@pytest.fixture
def mock_drive_adapter():
    """Create mock DriveAdapter."""
    adapter = MagicMock()
    adapter.upload_minutes = AsyncMock(
        return_value=WriteResult(
            success=True,
            dry_run=False,
            item_count=1,
            external_id="file789",
            url="https://drive.google.com/file/d/file789",
        )
    )
    return adapter


@pytest.fixture
def mock_sheets_adapter():
    """Create mock SheetsAdapter."""
    adapter = MagicMock()
    adapter.write_raid_items = AsyncMock(
        return_value=WriteResult(
            success=True,
            dry_run=False,
            item_count=4,
            external_id="sheet456",
            url="https://docs.google.com/spreadsheets/d/sheet456",
        )
    )
    return adapter


@pytest.mark.asyncio
async def test_generate_output_dry_run(
    sample_context,
    sample_bundle,
    config_with_destinations,
    mock_renderer,
    mock_drive_adapter,
    mock_sheets_adapter,
):
    """Full pipeline in dry-run mode returns rendered content with dry-run writes."""
    # Set up adapters to return dry-run results
    mock_drive_adapter.upload_minutes = AsyncMock(
        return_value=WriteResult(success=True, dry_run=True, item_count=1)
    )
    mock_sheets_adapter.write_raid_items = AsyncMock(
        return_value=WriteResult(success=True, dry_run=True, item_count=4)
    )

    router = OutputRouter(
        renderer=mock_renderer,
        drive_adapter=mock_drive_adapter,
        sheets_adapter=mock_sheets_adapter,
    )

    result = await router.generate_output(
        sample_context, sample_bundle, config_with_destinations, dry_run=True
    )

    assert result.rendered is not None
    assert result.rendered.markdown.startswith("# Meeting Minutes")
    # Writes attempted with dry_run=True
    assert result.minutes_result.success
    assert result.minutes_result.dry_run
    assert result.raid_result.success
    assert result.raid_result.dry_run


@pytest.mark.asyncio
async def test_route_minutes_generates_filename(
    mock_renderer, mock_drive_adapter, sample_context
):
    """Route minutes generates proper filename with date and slug."""
    router = OutputRouter(renderer=mock_renderer, drive_adapter=mock_drive_adapter)

    rendered = mock_renderer.render.return_value
    result = await router.route_minutes(
        rendered,
        "folder123",
        meeting_date=sample_context.meeting_date,
        dry_run=False,
    )

    assert result.success
    # Check the filename passed to adapter
    call_args = mock_drive_adapter.upload_minutes.call_args
    filename = call_args.kwargs.get("filename")
    assert filename == "2026-01-15-default-minutes.md"


@pytest.mark.asyncio
async def test_route_raid_items_includes_type(
    mock_renderer, mock_sheets_adapter, sample_bundle
):
    """Route RAID items adds type field to each item."""
    router = OutputRouter(renderer=mock_renderer, sheets_adapter=mock_sheets_adapter)

    result = await router.route_raid_items(
        sample_bundle,
        "sheet456",
        "RAID",
        dry_run=False,
    )

    assert result.success
    # Check items passed to adapter
    call_args = mock_sheets_adapter.write_raid_items.call_args
    items = call_args.kwargs.get("items")
    assert len(items) == 4  # 1 decision + 1 action + 1 risk + 1 issue
    types = [item["type"] for item in items]
    assert "Decision" in types
    assert "Action" in types
    assert "Risk" in types
    assert "Issue" in types


@pytest.mark.asyncio
async def test_adapters_optional():
    """Router works with None adapters for dry-run only mode."""
    router = OutputRouter(
        renderer=None,
        sheets_adapter=None,
        drive_adapter=None,
    )

    # Should create default renderer
    assert router.renderer is not None

    # Should return failure when trying to route without adapters
    bundle = RaidBundle(meeting_id=uuid4())
    result = await router.route_raid_items(bundle, "sheet123")
    assert not result.success
    assert "not configured" in result.error_message


def test_output_result_all_successful():
    """OutputResult.all_successful computed property works correctly."""
    rendered = RenderedMinutes(
        meeting_id=uuid4(),
        markdown="# Test",
        html="<h1>Test</h1>",
        template_used="test",
    )

    # Both successful
    result = OutputResult(
        rendered=rendered,
        minutes_result=WriteResult(success=True),
        raid_result=WriteResult(success=True),
    )
    assert result.all_successful is True

    # One failed
    result_failed = OutputResult(
        rendered=rendered,
        minutes_result=WriteResult(success=True),
        raid_result=WriteResult(success=False, error_message="API error"),
    )
    assert result_failed.all_successful is False

    # None attempted (dry-run with no destinations)
    result_none = OutputResult(
        rendered=rendered,
        minutes_result=None,
        raid_result=None,
    )
    assert result_none.all_successful is True


@pytest.mark.asyncio
async def test_audit_logging(
    sample_context,
    sample_bundle,
    config_with_destinations,
    mock_renderer,
    mock_drive_adapter,
    mock_sheets_adapter,
):
    """Verify structlog called with write details."""
    router = OutputRouter(
        renderer=mock_renderer,
        drive_adapter=mock_drive_adapter,
        sheets_adapter=mock_sheets_adapter,
    )

    with patch("src.output.router.logger") as mock_logger:
        await router.generate_output(
            sample_context, sample_bundle, config_with_destinations, dry_run=False
        )

        # Verify logging calls made
        assert mock_logger.info.called
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        # Check that key events were logged
        assert any("rendered minutes" in str(call) for call in log_calls)
        assert any("routed minutes" in str(call) for call in log_calls)
        assert any("routed raid" in str(call) for call in log_calls)


@pytest.mark.asyncio
async def test_config_enables_targets(
    sample_context,
    sample_bundle,
    mock_renderer,
    mock_drive_adapter,
    mock_sheets_adapter,
):
    """Verify enabled_targets filtering works."""
    router = OutputRouter(
        renderer=mock_renderer,
        drive_adapter=mock_drive_adapter,
        sheets_adapter=mock_sheets_adapter,
    )

    # Only drive enabled
    config_drive_only = ProjectOutputConfig(
        minutes_destination="folder123",
        raid_destination="sheet456",
        enabled_targets=["drive"],
    )

    result = await router.generate_output(
        sample_context, sample_bundle, config_drive_only, dry_run=False
    )

    # Drive called, Sheets not called
    assert mock_drive_adapter.upload_minutes.called
    mock_sheets_adapter.write_raid_items.assert_not_called()
    assert result.minutes_result is not None
    assert result.raid_result is None


@pytest.mark.asyncio
async def test_retry_on_failure(mock_renderer, sample_bundle):
    """Mock adapter to fail, verify retry attempted."""
    # Create adapter that fails with retriable error then succeeds
    failing_adapter = MagicMock()
    call_count = 0

    async def failing_then_success(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Transient failure")
        return WriteResult(success=True, item_count=4)

    failing_adapter.write_raid_items = AsyncMock(side_effect=failing_then_success)

    router = OutputRouter(renderer=mock_renderer, sheets_adapter=failing_adapter)

    result = await router.route_raid_items(sample_bundle, "sheet123")

    # Should succeed after retry
    assert result.success
    assert call_count == 2  # First failed, second succeeded
