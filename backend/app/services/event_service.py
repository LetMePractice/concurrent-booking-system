"""
Event service handling CRUD operations.
"""

from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.event import Event
from app.schemas.event import EventCreate
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_event(db: AsyncSession, event_data: EventCreate, organizer_id: int) -> Event:
    """Create a new event with full seat availability."""
    if event_data.date <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event date must be in the future",
        )

    event = Event(
        title=event_data.title,
        description=event_data.description,
        date=event_data.date,
        location=event_data.location,
        seat_count=event_data.seat_count,
        available_seats=event_data.seat_count,  # All seats available initially
        organizer_id=organizer_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    logger.info("event_created", event_id=event.id, title=event.title, seats=event.seat_count)
    return event


async def get_event(db: AsyncSession, event_id: int) -> Event:
    """Get a single event by ID."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )
    return event


async def list_events(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    upcoming_only: bool = True,
) -> tuple[list[Event], int]:
    """
    List events with pagination.
    Uses the ix_events_date index for efficient date filtering.
    Uses the ix_events_available_date composite index when filtering available events.
    """
    query = select(Event)

    if upcoming_only:
        query = query.where(Event.date >= datetime.now(timezone.utc))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results - uses ix_events_date index
    events_query = (
        query
        .order_by(Event.date.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(events_query)
    events = list(result.scalars().all())

    return events, total
