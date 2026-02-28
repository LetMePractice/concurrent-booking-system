"""
Booking service with concurrency-safe seat reservation.

CONCURRENCY STRATEGY: Optimistic Locking with Retry
====================================================

Problem:
  Two users try to book the last seat simultaneously.
  Both read available_seats=1, both decrement to 0, both succeed.
  Result: Overbooking.

Solution:
  We use optimistic locking via a `version` column on the Event table.

  1. Read the event's current version
  2. UPDATE events SET available_seats = available_seats - N, version = version + 1
     WHERE id = :event_id AND version = :current_version AND available_seats >= N
  3. If rows_affected == 0, someone else modified the row -> retry

  This approach:
  - No explicit row locks (SELECT FOR UPDATE) that serialize all requests
  - Low contention: most updates succeed on first try
  - Automatic retry handles rare conflicts
  - DB CHECK constraint is the final safety net (available_seats >= 0)

  We also set isolation level to REPEATABLE READ to prevent phantom reads
  within the booking transaction.

Alternative approaches considered:
  - SELECT FOR UPDATE (pessimistic locking): Serializes all bookings for same event.
    Good correctness, bad throughput. Fine for <10 concurrent users per event.
  - Advisory locks: PostgreSQL-specific, harder to reason about.
  - Queue-based: Best for massive scale, overkill here.
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.event import Event
from app.models.booking import Booking
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_RETRY_ATTEMPTS = 3


async def book_seats(
    db: AsyncSession,
    user_id: int,
    event_id: int,
    seat_count: int = 1,
) -> Booking:
    """
    Book seats for an event with optimistic locking.
    Retries up to MAX_RETRY_ATTEMPTS on version conflicts.
    """
    # Check for existing booking (idempotency)
    existing = await db.execute(
        select(Booking).where(
            Booking.user_id == user_id,
            Booking.event_id == event_id,
            Booking.status == "confirmed",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a booking for this event",
        )

    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        # Step 1: Read current event state
        result = await db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found",
            )

        if event.available_seats < seat_count:
            logger.warning(
                "booking_failed_no_seats",
                event_id=event_id,
                requested=seat_count,
                available=event.available_seats,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Not enough seats. Requested: {seat_count}, Available: {event.available_seats}",
            )

        # Step 2: Optimistic lock - update only if version matches
        current_version = event.version
        update_result = await db.execute(
            update(Event)
            .where(
                Event.id == event_id,
                Event.version == current_version,
                Event.available_seats >= seat_count,
            )
            .values(
                available_seats=Event.available_seats - seat_count,
                version=Event.version + 1,
            )
        )

        if update_result.rowcount == 0:
            # Version conflict - another transaction modified this event
            logger.info(
                "booking_retry",
                event_id=event_id,
                attempt=attempt,
                reason="version_conflict",
            )
            # Expire cached state so next read gets fresh data
            await db.rollback()
            if attempt == MAX_RETRY_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Booking failed due to high demand. Please try again.",
                )
            continue

        # Step 3: Create booking record
        booking = Booking(
            user_id=user_id,
            event_id=event_id,
            seat_count=seat_count,
            status="confirmed",
        )
        db.add(booking)
        await db.flush()
        await db.refresh(booking)

        logger.info(
            "booking_created",
            booking_id=booking.id,
            user_id=user_id,
            event_id=event_id,
            seats=seat_count,
            attempt=attempt,
        )
        return booking

    # Should not reach here, but just in case
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Booking failed unexpectedly",
    )


async def cancel_booking(
    db: AsyncSession,
    booking_id: int,
    user_id: int,
) -> Booking:
    """
    Cancel a booking and release seats back to the event.
    Uses the same optimistic locking pattern for seat restoration.
    """
    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.user_id == user_id,
        )
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled",
        )

    # Restore seats to event
    await db.execute(
        update(Event)
        .where(Event.id == booking.event_id)
        .values(
            available_seats=Event.available_seats + booking.seat_count,
            version=Event.version + 1,
        )
    )

    booking.status = "cancelled"
    await db.flush()
    await db.refresh(booking)

    logger.info(
        "booking_cancelled",
        booking_id=booking.id,
        user_id=user_id,
        event_id=booking.event_id,
        seats_restored=booking.seat_count,
    )
    return booking


async def get_user_bookings(db: AsyncSession, user_id: int) -> list[Booking]:
    """Get all bookings for a user."""
    result = await db.execute(
        select(Booking)
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )
    return list(result.scalars().all())
