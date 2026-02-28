"""
Pydantic schemas for booking-related request/response validation.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    event_id: int
    seat_count: int = Field(default=1, gt=0, le=10)


class BookingResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    seat_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingCancelResponse(BaseModel):
    message: str
    booking_id: int
    status: str
