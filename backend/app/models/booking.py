"""
Booking model representing a user's reservation for an event.

Key design decisions:
- Unique constraint on (user_id, event_id) prevents duplicate bookings
- Status field allows cancellation without deleting records
- seat_count allows multi-seat bookings in one transaction
"""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    seat_count = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="confirmed")  # confirmed, cancelled

    # Relationships
    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")

    __table_args__ = (
        # One active booking per user per event
        UniqueConstraint("user_id", "event_id", name="uq_user_event_booking"),
        CheckConstraint("seat_count > 0", name="check_booking_seat_count_positive"),
        CheckConstraint("status IN ('confirmed', 'cancelled')", name="check_booking_status"),
    )

    def __repr__(self) -> str:
        return f"<Booking(id={self.id}, user={self.user_id}, event={self.event_id}, status={self.status})>"
