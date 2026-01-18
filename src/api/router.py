"""API router aggregation."""

from fastapi import APIRouter

from src.api.extraction import router as extraction_router
from src.api.health import router as health_router
from src.api.identity import router as identity_router
from src.api.meetings import router as meetings_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(meetings_router)
# Extraction is a sub-operation of meetings, so include with meetings prefix
api_router.include_router(extraction_router, prefix="/meetings")
# Identity resolution endpoints
api_router.include_router(identity_router)
