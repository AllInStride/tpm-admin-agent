"""API router aggregation."""

from fastapi import APIRouter

from src.api.health import router as health_router
from src.api.meetings import router as meetings_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(meetings_router)
