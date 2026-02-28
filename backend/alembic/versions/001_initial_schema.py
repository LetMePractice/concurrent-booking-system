"""Initial schema: users, events, bookings with indexes and constraints.

Revision ID: 001
Revises: None
Create Date: 2026-02-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # Events table
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("seat_count", sa.Integer(), nullable=False),
        sa.Column("available_seats", sa.Integer(), nullable=False),
        sa.Column("organizer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("available_seats >= 0", name="check_available_seats_non_negative"),
        sa.CheckConstraint("seat_count > 0", name="check_seat_count_positive"),
        sa.CheckConstraint("available_seats <= seat_count", name="check_available_lte_total"),
    )
    op.create_index("ix_events_id", "events", ["id"])
    # INDEX ON EVENT DATE: Critical for performance.
    # Events are almost always queried by date range ("upcoming events", "events this week").
    # Without this index, every listing query does a full table scan.
    # With 100K+ events, this reduces query time from ~200ms to ~2ms.
    op.create_index("ix_events_date", "events", ["date"])
    # Composite index for the most common query pattern:
    # "Show me events that still have seats, sorted by date"
    # This covers WHERE available_seats > 0 ORDER BY date
    op.create_index("ix_events_available_date", "events", ["available_seats", "date"])

    # Bookings table
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("seat_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'confirmed'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "event_id", name="uq_user_event_booking"),
        sa.CheckConstraint("seat_count > 0", name="check_booking_seat_count_positive"),
        sa.CheckConstraint("status IN ('confirmed', 'cancelled')", name="check_booking_status"),
    )
    op.create_index("ix_bookings_id", "bookings", ["id"])
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.create_index("ix_bookings_event_id", "bookings", ["event_id"])


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("events")
    op.drop_table("users")
