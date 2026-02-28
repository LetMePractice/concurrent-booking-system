"""
Event endpoints with Redis caching on list operations.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.event import EventCreate, EventResponse, EventListResponse
from app.services.event_service import create_event, get_event, list_events
from app.services.cache_service import get_cached_events, set_cached_events, invalidate_event_cache
from app.core.security import get_current_user_id
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event_endpoint(
    event_data: EventCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new event. Requires authentication."""
    event = await create_event(db, event_data, user_id)
    # Invalidate cache since event list has changed
    await invalidate_event_cache()
    return event


@router.get("/", response_model=EventListResponse)
async def list_events_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    upcoming_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    List events with pagination.
    Results are cached in Redis for 5 minutes.
    Cache is invalidated when events are created or seats are booked.
    """
    # Try cache first
    cached = await get_cached_events(page, page_size, upcoming_only)
    if cached:
        logger.info("events_list_cache_hit", page=page)
        cached["cached"] = True
        return EventListResponse(**cached)

    # Cache miss - query database
    events, total = await list_events(db, page, page_size, upcoming_only)

    response_data = {
        "events": [EventResponse.model_validate(e).model_dump() for e in events],
        "total": total,
        "page": page,
        "page_size": page_size,
        "cached": False,
    }

    # Store in cache for next request
    await set_cached_events(page, page_size, upcoming_only, response_data)

    return EventListResponse(**response_data)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event_endpoint(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single event by ID. Not cached (needs real-time seat counts)."""
    event = await get_event(db, event_id)
    return event
