"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.router import api_router
from src.config import settings
from src.db.turso import TursoClient
from src.events.bus import EventBus
from src.events.store import EventStore

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management.

    Startup:
    - Initialize database connection
    - Initialize event store schema
    - Initialize event bus

    Shutdown:
    - Close database connection
    """
    import src.db.turso as turso_module

    # Startup
    logger.info("Starting TPM Admin Agent...")

    # Initialize database
    db = TursoClient()
    await db.connect()
    app.state.db = db
    turso_module.db_client = db
    logger.info(f"Database connected: {db.url}")

    # Initialize event store
    event_store = EventStore(db)
    await event_store.init_schema()
    app.state.event_store = event_store
    logger.info("Event store initialized")

    # Initialize event bus with store
    event_bus = EventBus(store=event_store)
    app.state.event_bus = event_bus
    logger.info("Event bus initialized")

    yield

    # Shutdown
    logger.info("Shutting down TPM Admin Agent...")
    await db.close()
    logger.info("Database connection closed")


app = FastAPI(
    title=settings.app_name,
    description="Meeting intelligence automation for TPMs",
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
