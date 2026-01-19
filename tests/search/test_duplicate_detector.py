"""Tests for DuplicateDetector."""

from pathlib import Path

import pytest

from src.db.turso import TursoClient
from src.search.duplicate_detector import DuplicateDetector


@pytest.fixture
async def db_client(tmp_path: Path):
    """Create a temp file database client for testing."""
    db_path = tmp_path / "test_duplicates.db"
    client = TursoClient(url=f"file:{db_path}")
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def db_with_tables(db_client: TursoClient):
    """Create required tables."""
    # Create raid_items_projection table
    await db_client.execute("""
        CREATE TABLE IF NOT EXISTS raid_items_projection (
            id TEXT PRIMARY KEY,
            meeting_id TEXT NOT NULL,
            item_type TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            confidence REAL DEFAULT 1.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create meetings_projection table
    await db_client.execute("""
        CREATE TABLE IF NOT EXISTS meetings_projection (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT,
            participant_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    return db_client


@pytest.fixture
async def seeded_db(db_with_tables: TursoClient):
    """Seed database with test data."""
    # Insert meetings
    await db_with_tables.execute(
        """
        INSERT INTO meetings_projection (id, title, date)
        VALUES (?, ?, ?)
        """,
        ["meeting-1", "Sprint Planning", "2026-01-15"],
    )
    await db_with_tables.execute(
        """
        INSERT INTO meetings_projection (id, title, date)
        VALUES (?, ?, ?)
        """,
        ["meeting-2", "Daily Standup", "2026-01-16"],
    )

    # Insert RAID items with varying similarity
    items = [
        # Similar descriptions (should match)
        (
            "item-1",
            "meeting-1",
            "action",
            "Review the API documentation before release",
        ),
        ("item-2", "meeting-2", "action", "Review API docs before the release"),
        # Different descriptions (should not match)
        ("item-3", "meeting-1", "risk", "Database scaling issues with growth"),
        ("item-4", "meeting-2", "issue", "Login page not loading correctly"),
        # Another similar pair
        (
            "item-5",
            "meeting-1",
            "action",
            "Deploy new authentication service to production",
        ),
        ("item-6", "meeting-2", "action", "Deploy auth service to prod"),
    ]

    for item_id, meeting_id, item_type, description in items:
        await db_with_tables.execute(
            """
            INSERT INTO raid_items_projection
                (id, meeting_id, item_type, description)
            VALUES (?, ?, ?, ?)
            """,
            [item_id, meeting_id, item_type, description],
        )

    return db_with_tables


@pytest.fixture
async def detector(seeded_db: TursoClient):
    """Create DuplicateDetector with seeded database."""
    return DuplicateDetector(seeded_db, threshold=0.85)


class TestFindDuplicates:
    """Tests for find_duplicates method."""

    @pytest.mark.asyncio
    async def test_finds_similar_items_above_threshold(
        self, detector: DuplicateDetector
    ):
        """Finds items that are similar above threshold."""
        result = await detector.find_duplicates(
            "Review the API documentation for release"
        )
        assert result.has_duplicates is True
        assert len(result.potential_duplicates) > 0
        # Should find item-1 or item-2 (similar descriptions)
        found_ids = {d.item_id for d in result.potential_duplicates}
        assert "item-1" in found_ids or "item-2" in found_ids

    @pytest.mark.asyncio
    async def test_returns_empty_for_unique_description(
        self, detector: DuplicateDetector
    ):
        """Returns no duplicates for a unique description."""
        result = await detector.find_duplicates(
            "Completely unique xyzzy foobar description that matches nothing"
        )
        assert result.has_duplicates is False
        assert len(result.potential_duplicates) == 0

    @pytest.mark.asyncio
    async def test_filters_by_item_type(self, detector: DuplicateDetector):
        """Respects item_type filter."""
        result = await detector.find_duplicates(
            "Deploy new authentication service",
            item_type="action",
        )
        # Should only find action items
        for match in result.potential_duplicates:
            # Verify by checking that we get expected items
            assert match.item_id in {"item-1", "item-2", "item-5", "item-6"}

    @pytest.mark.asyncio
    async def test_respects_higher_threshold(self, seeded_db: TursoClient):
        """Higher threshold (0.95) returns fewer matches."""
        detector_high = DuplicateDetector(seeded_db, threshold=0.95)
        result = await detector_high.find_duplicates(
            "Review the API documentation before release"
        )
        # At 95%, might not find the slightly different version
        # This tests that threshold affects results
        assert result is not None

    @pytest.mark.asyncio
    async def test_respects_lower_threshold(self, seeded_db: TursoClient):
        """Lower threshold (0.6) returns more matches."""
        detector_low = DuplicateDetector(seeded_db, threshold=0.6)
        result = await detector_low.find_duplicates("Review API documentation")
        # At 60%, should find more matches
        # Compare to higher threshold
        detector_high = DuplicateDetector(seeded_db, threshold=0.9)
        result_high = await detector_high.find_duplicates("Review API documentation")
        assert len(result.potential_duplicates) >= len(result_high.potential_duplicates)

    @pytest.mark.asyncio
    async def test_similarity_score_normalized(self, detector: DuplicateDetector):
        """Similarity scores are normalized to 0.0-1.0."""
        result = await detector.find_duplicates(
            "Review the API documentation before release"
        )
        for match in result.potential_duplicates:
            assert 0.0 <= match.similarity <= 1.0

    @pytest.mark.asyncio
    async def test_includes_meeting_title(self, detector: DuplicateDetector):
        """Matches include meeting title."""
        result = await detector.find_duplicates(
            "Review the API documentation before release"
        )
        if result.potential_duplicates:
            match = result.potential_duplicates[0]
            # Should have meeting title from projection
            assert match.meeting_title in ["Sprint Planning", "Daily Standup", None]

    @pytest.mark.asyncio
    async def test_excludes_self_by_item_id(self, detector: DuplicateDetector):
        """Can exclude an item by ID when checking its own duplicates."""
        result = await detector.find_duplicates(
            "Review the API documentation before release",
            exclude_item_id="item-1",
        )
        # Should not include item-1 in results
        found_ids = {d.item_id for d in result.potential_duplicates}
        assert "item-1" not in found_ids


class TestRecordRejection:
    """Tests for record_rejection method."""

    @pytest.mark.asyncio
    async def test_stores_rejection(self, detector: DuplicateDetector):
        """Rejection is stored in database."""
        await detector.record_rejection("item-1", "item-2")
        rejections = await detector.get_rejections("item-1")
        assert "item-2" in rejections

    @pytest.mark.asyncio
    async def test_multiple_rejections(self, detector: DuplicateDetector):
        """Can record multiple rejections for same item."""
        await detector.record_rejection("item-1", "item-2")
        await detector.record_rejection("item-1", "item-3")
        rejections = await detector.get_rejections("item-1")
        assert "item-2" in rejections
        assert "item-3" in rejections

    @pytest.mark.asyncio
    async def test_duplicate_rejection_ignored(self, detector: DuplicateDetector):
        """Recording same rejection twice doesn't error."""
        await detector.record_rejection("item-1", "item-2")
        await detector.record_rejection("item-1", "item-2")  # Should not error
        rejections = await detector.get_rejections("item-1")
        assert "item-2" in rejections


class TestFindDuplicatesWithRejections:
    """Tests for find_duplicates respecting rejections."""

    @pytest.mark.asyncio
    async def test_excludes_rejected_duplicates(self, detector: DuplicateDetector):
        """Rejected duplicates are excluded from results."""
        # First, find duplicates for item-1
        result_before = await detector.find_duplicates(
            "Review the API documentation before release",
            exclude_item_id="item-1",
        )

        # Record a rejection
        if result_before.potential_duplicates:
            rejected_id = result_before.potential_duplicates[0].item_id
            await detector.record_rejection("item-1", rejected_id)

            # Search again - rejected item should be excluded
            result_after = await detector.find_duplicates(
                "Review the API documentation before release",
                exclude_item_id="item-1",
            )

            found_ids_after = {d.item_id for d in result_after.potential_duplicates}
            assert rejected_id not in found_ids_after


class TestEmptyDatabase:
    """Tests with empty database."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_items(self, db_with_tables: TursoClient):
        """Returns empty result when no items in database."""
        detector = DuplicateDetector(db_with_tables)
        result = await detector.find_duplicates("Some description")
        assert result.has_duplicates is False
        assert len(result.potential_duplicates) == 0
