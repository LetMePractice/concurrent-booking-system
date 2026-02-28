"""
Booking endpoints with concurrency-safe seat reservation.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.booking import BookingCreate, BookingResponse, BookingCancelResponse
from app.services.booking_service import book_seats, cancel_booking, get_user_bookings
from app.services.cache_service import invalidate_event_cache
from app.core.security import get_current_user_id
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Book seats for an event.

    Uses optimistic locking to prevent overbooking under concurrent load.
    If the booking conflicts with another simultaneous booking, it retries
    up to 3 times before returning a 409 error.
    """
    booking = await book_seats(db, user_id, booking_data.event_id, booking_data.seat_count)
    # Invalidate event list cache since available_seats changed
    await invalidate_event_cache()
    return booking


@router.delete("/{booking_id}", response_model=BookingCancelResponse)
async def cancel_booking_endpoint(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a booking and release seats back to the event."""
    booking = await cancel_booking(db, booking_id, user_id)
    await invalidate_event_cache()
    return BookingCancelResponse(
        message="Booking cancelled successfully",
        booking_id=booking.id,
        status=booking.status,
    )


@router.get("/", response_model=list[BookingResponse])
async def list_user_bookings(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all bookings for the authenticated user."""
    bookings = await get_user_bookings(db, user_id)
    return bookings
