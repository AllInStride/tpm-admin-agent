"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.router import api_router
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management.

    Startup: Initialize resources (database connection added in Plan 03)
    Shutdown: Cleanup resources
    """
    # Startup
    # app.state.db will be initialized in Plan 03
    yield
    # Shutdown
    # Cleanup will be added in Plan 03


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
