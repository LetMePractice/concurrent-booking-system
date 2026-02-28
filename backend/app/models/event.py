"""
Event model with seat inventory tracking.

Key design decisions:
- `available_seats` is denormalized for performance (avoids COUNT query on bookings)
- Index on `date` for range queries (e.g., "events this week")
- Index on `available_seats` for filtering events with availability
- `version` column enables optimistic locking for concurrent booking
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255), nullable=True)
    seat_count = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Optimistic locking version counter
    version = Column(Integer, nullable=False, default=1)

    # Relationships
    organizer = relationship("User", back_populates="events")
    bookings = relationship("Booking", back_populates="event", lazy="selectin")

    # Constraints
    __table_args__ = (
        # Prevent negative seat counts at the DB level
        CheckConstraint("available_seats >= 0", name="check_available_seats_non_negative"),
        CheckConstraint("seat_count > 0", name="check_seat_count_positive"),
        CheckConstraint("available_seats <= seat_count", name="check_available_lte_total"),
        # Index on date for range queries (upcoming events, events this week)
        Index("ix_events_date", "date"),
        # Composite index for common query: available events sorted by date
        Index("ix_events_available_date", "available_seats", "date"),
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title={self.title}, available={self.available_seats}/{self.seat_count})>"
