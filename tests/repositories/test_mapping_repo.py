"""Tests for MappingRepository."""

from pathlib import Path

import pytest

from src.db.turso import TursoClient
from src.repositories.mapping_repo import MappingRepository


@pytest.fixture
async def db_client(tmp_path: Path):
    """Create a temp file database client for testing."""
    db_path = tmp_path / "test_mappings.db"
    client = TursoClient(url=f"file:{db_path}")
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def repo(db_client: TursoClient):
    """Create MappingRepository with initialized table."""
    repo = MappingRepository(db_client)
    await repo.initialize()
    return repo


@pytest.mark.asyncio
async def test_initialize_creates_table(db_client: TursoClient):
    """Initialize should create learned_mappings table."""
    repo = MappingRepository(db_client)
    await repo.initialize()

    # Verify table exists by querying schema
    result = await db_client.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='learned_mappings'"
    )
    assert len(result.rows) == 1
    assert result.rows[0][0] == "learned_mappings"


@pytest.mark.asyncio
async def test_save_and_get_mapping(repo: MappingRepository):
    """Should save mapping and retrieve it."""
    await repo.save_mapping(
        project_id="proj-123",
        transcript_name="Bob Smith",
        resolved_email="robert.smith@example.com",
        resolved_name="Robert Smith",
        created_by="user-1",
    )

    result = await repo.get_mapping("proj-123", "Bob Smith")

    assert result is not None
    email, name = result
    assert email == "robert.smith@example.com"
    assert name == "Robert Smith"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(repo: MappingRepository):
    """Should return None for nonexistent mapping."""
    result = await repo.get_mapping("proj-123", "Unknown Person")

    assert result is None


@pytest.mark.asyncio
async def test_save_overwrites_existing(repo: MappingRepository):
    """Save should upsert (update existing mapping)."""
    # Save initial mapping
    await repo.save_mapping(
        project_id="proj-123",
        transcript_name="Bob",
        resolved_email="wrong@example.com",
        resolved_name="Wrong Person",
    )

    # Overwrite with correct mapping
    await repo.save_mapping(
        project_id="proj-123",
        transcript_name="Bob",
        resolved_email="correct@example.com",
        resolved_name="Correct Person",
    )

    result = await repo.get_mapping("proj-123", "Bob")
    assert result is not None
    email, name = result
    assert email == "correct@example.com"
    assert name == "Correct Person"


@pytest.mark.asyncio
async def test_delete_mapping(repo: MappingRepository):
    """Should delete existing mapping and return True."""
    await repo.save_mapping(
        project_id="proj-123",
        transcript_name="Bob",
        resolved_email="bob@example.com",
        resolved_name="Bob Jones",
    )

    deleted = await repo.delete_mapping("proj-123", "Bob")

    assert deleted is True
    result = await repo.get_mapping("proj-123", "Bob")
    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false(repo: MappingRepository):
    """Should return False when deleting nonexistent mapping."""
    deleted = await repo.delete_mapping("proj-123", "Unknown")

    assert deleted is False


@pytest.mark.asyncio
async def test_get_all_mappings(repo: MappingRepository):
    """Should return all mappings for a project."""
    # Add multiple mappings
    await repo.save_mapping(
        project_id="proj-123",
        transcript_name="Alice",
        resolved_email="alice@example.com",
        resolved_name="Alice Johnson",
    )
    await repo.save_mapping(
        project_id="proj-123",
        transcript_name="Bob",
        resolved_email="bob@example.com",
        resolved_name="Bob Smith",
    )
    # Different project - should not be included
    await repo.save_mapping(
        project_id="proj-456",
        transcript_name="Charlie",
        resolved_email="charlie@example.com",
        resolved_name="Charlie Brown",
    )

    mappings = await repo.get_all_mappings("proj-123")

    assert len(mappings) == 2
    # Sorted by transcript_name
    assert mappings[0]["transcript_name"] == "Alice"
    assert mappings[0]["resolved_email"] == "alice@example.com"
    assert mappings[1]["transcript_name"] == "Bob"
    assert mappings[1]["resolved_email"] == "bob@example.com"


@pytest.mark.asyncio
async def test_project_isolation(repo: MappingRepository):
    """Same transcript name in different projects should be independent."""
    await repo.save_mapping(
        project_id="proj-A",
        transcript_name="Bob",
        resolved_email="bob-a@example.com",
        resolved_name="Bob from A",
    )
    await repo.save_mapping(
        project_id="proj-B",
        transcript_name="Bob",
        resolved_email="bob-b@example.com",
        resolved_name="Bob from B",
    )

    result_a = await repo.get_mapping("proj-A", "Bob")
    result_b = await repo.get_mapping("proj-B", "Bob")

    assert result_a is not None
    assert result_b is not None
    assert result_a[0] == "bob-a@example.com"
    assert result_b[0] == "bob-b@example.com"
