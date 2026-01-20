"""API router aggregation."""

from fastapi import APIRouter

from src.api.communication import router as communication_router
from src.api.extraction import router as extraction_router
from src.api.health import router as health_router
from src.api.identity import router as identity_router
from src.api.integration import router as integration_router
from src.api.meetings import router as meetings_router
from src.api.output import router as output_router
from src.api.prep import router as prep_router
from src.api.search import search_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(meetings_router)
# Extraction is a sub-operation of meetings, so include with meetings prefix
api_router.include_router(extraction_router, prefix="/meetings")
# Identity resolution endpoints
api_router.include_router(identity_router)
# Output generation endpoints
api_router.include_router(output_router, prefix="/output", tags=["output"])
# Integration endpoints (Smartsheet + Slack)
api_router.include_router(integration_router)
# Search and dashboard endpoints
api_router.include_router(search_router)
# Meeting prep endpoints
api_router.include_router(prep_router)
# Communication artifact generation endpoints
api_router.include_router(communication_router)
