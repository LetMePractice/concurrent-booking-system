"""
Central API router that aggregates all route modules.
"""

from fastapi import APIRouter
from app.api.routes import auth, events, bookings

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(bookings.router)
