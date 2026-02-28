"""
Pydantic schemas for event-related request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    date: datetime
    location: Optional[str] = Field(None, max_length=255)
    seat_count: int = Field(..., gt=0, le=100000)


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    date: datetime
    location: Optional[str]
    seat_count: int
    available_seats: int
    organizer_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    events: list[EventResponse]
    total: int
    page: int
    page_size: int
    cached: bool = False
