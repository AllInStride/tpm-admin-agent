"""Pytest configuration and fixtures."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.db.turso import TursoClient
from src.events.bus import EventBus
from src.events.store import EventStore
from src.main import app


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """Create async test client for FastAPI app with database."""
    # Set up test database
    db_path = tmp_path / "test_api.db"
    db = TursoClient(url=f"file:{db_path}")
    await db.connect()

    # Initialize event store
    event_store = EventStore(db)
    await event_store.init_schema()

    # Set up app state
    app.state.db = db
    app.state.event_store = event_store
    app.state.event_bus = EventBus(store=event_store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    await db.close()
    # Clean up app state
    del app.state.db
    del app.state.event_store
    del app.state.event_bus
