"""FastAPI application entry point."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from src.api.router import api_router
from src.config import settings
from src.db.turso import TursoClient
from src.events.bus import EventBus
from src.events.store import EventStore
from src.events.types import (
    ActionItemExtracted,
    DecisionExtracted,
    IssueExtracted,
    MeetingCreated,
    RiskExtracted,
    TranscriptParsed,
)
from src.repositories.open_items_repo import OpenItemsRepository
from src.repositories.projection_repo import ProjectionRepository
from src.search.duplicate_detector import DuplicateDetector
from src.search.fts_service import FTSService
from src.search.projections import ProjectionBuilder

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _initialize_communication_service(app: FastAPI, db: TursoClient) -> None:
    """Initialize CommunicationService with dependencies.

    Creates DataAggregator and LLMClient, then sets up
    CommunicationService in app state.
    """
    from src.communication.data_aggregator import DataAggregator
    from src.communication.service import CommunicationService
    from src.services.llm_client import LLMClient

    # DataAggregator needs repositories
    data_aggregator = DataAggregator(
        open_items_repo=app.state.open_items_repo,
        projection_repo=app.state.projection_repo,
    )

    # LLM client for structured extraction
    llm_client = LLMClient()

    # Create and register CommunicationService
    communication_service = CommunicationService(
        llm_client=llm_client,
        data_aggregator=data_aggregator,
    )
    app.state.communication_service = communication_service
    logger.info("CommunicationService initialized")


async def _initialize_prep_service(app: FastAPI, db: TursoClient) -> None:
    """Initialize PrepService with adapters.

    Creates adapters based on available credentials and sets up
    the PrepService singleton.
    """
    from src.adapters.calendar_adapter import CalendarAdapter
    from src.adapters.drive_adapter import DriveAdapter
    from src.adapters.slack_adapter import SlackAdapter
    from src.prep.context_gatherer import ContextGatherer
    from src.prep.item_matcher import ItemMatcher
    from src.prep.prep_service import PrepService
    from src.prep.schemas import PrepConfig

    # Create adapters - they handle missing credentials gracefully
    calendar_adapter = CalendarAdapter()
    slack_adapter = SlackAdapter()

    # ItemMatcher needs database
    item_matcher = ItemMatcher(db)

    # ContextGatherer with optional adapters
    drive_adapter = None
    if os.environ.get("GOOGLE_SHEETS_CREDENTIALS"):
        drive_adapter = DriveAdapter()

    context_gatherer = ContextGatherer(
        item_matcher=item_matcher,
        drive_adapter=drive_adapter,
        slack_adapter=slack_adapter,
        fts_service=app.state.fts_service,
    )

    # Create and register PrepService
    config = PrepConfig()
    prep_service = PrepService(
        calendar_adapter=calendar_adapter,
        slack_adapter=slack_adapter,
        item_matcher=item_matcher,
        context_gatherer=context_gatherer,
        config=config,
    )
    PrepService.set_instance(prep_service)
    app.state.prep_service = prep_service
    logger.info("PrepService initialized")


def _get_prep_scheduler_context():
    """Get prep scheduler lifespan context manager.

    Returns a no-op context if scheduler is disabled via environment.
    """
    from contextlib import asynccontextmanager

    from src.prep.scheduler import prep_scheduler_lifespan

    # Allow disabling scheduler for tests
    if os.environ.get("DISABLE_PREP_SCHEDULER"):

        @asynccontextmanager
        async def noop_context():
            yield

        return noop_context()

    return prep_scheduler_lifespan()


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

    # Initialize projection repository and builder
    projection_repo = ProjectionRepository(db)
    await projection_repo.initialize()
    app.state.projection_repo = projection_repo
    logger.info("Projection repository initialized")

    projection_builder = ProjectionBuilder(event_store, projection_repo)
    app.state.projection_builder = projection_builder

    # Subscribe projection builder to all RAID-related events
    event_types = [
        MeetingCreated,
        TranscriptParsed,
        ActionItemExtracted,
        DecisionExtracted,
        RiskExtracted,
        IssueExtracted,
    ]

    for event_type in event_types:
        event_bus.subscribe(event_type, projection_builder.handle_event_object)

    logger.info(f"Projection builder subscribed to {len(event_types)} event types")

    # Initialize search and dashboard services
    app.state.fts_service = FTSService(db)
    app.state.duplicate_detector = DuplicateDetector(db)
    app.state.open_items_repo = OpenItemsRepository(db)
    logger.info("Search and dashboard services initialized")

    # Initialize communication service
    await _initialize_communication_service(app, db)

    # Initialize meeting prep service and scheduler
    async with AsyncExitStack() as stack:
        await _initialize_prep_service(app, db)
        await stack.enter_async_context(_get_prep_scheduler_context())
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
