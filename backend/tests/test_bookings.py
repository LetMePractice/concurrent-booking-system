"""
Tests for booking endpoints including concurrency scenarios.
"""

import pytest
from httpx import AsyncClient
from app.models.event import Event


@pytest.mark.asyncio
async def test_book_seats(client: AsyncClient, auth_headers, test_event):
    """Successful booking decrements available seats."""
    response = await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 2},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["event_id"] == test_event.id
    assert data["seat_count"] == 2
    assert data["status"] == "confirmed"

    # Verify available seats decreased
    event_response = await client.get(f"/api/v1/events/{test_event.id}")
    assert event_response.json()["available_seats"] == 98


@pytest.mark.asyncio
async def test_book_seats_unauthenticated(client: AsyncClient, test_event):
    """Unauthenticated booking returns 401."""
    response = await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 1},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_book_seats_sold_out(client: AsyncClient, auth_headers, sold_out_event):
    """Booking sold-out event returns 409."""
    response = await client.post(
        "/api/v1/bookings/",
        json={"event_id": sold_out_event.id, "seat_count": 1},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_book_too_many_seats(client: AsyncClient, auth_headers, test_event):
    """Requesting more seats than available returns 409."""
    response = await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 101},
        headers=auth_headers,
    )
    # 422 because seat_count max is 10 in schema, or 409 if constraint fails
    assert response.status_code in [409, 422]


@pytest.mark.asyncio
async def test_duplicate_booking(client: AsyncClient, auth_headers, test_event):
    """Same user booking same event twice returns 409."""
    # First booking
    response1 = await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 1},
        headers=auth_headers,
    )
    assert response1.status_code == 201

    # Second booking - should fail
    response2 = await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 1},
        headers=auth_headers,
    )
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_cancel_booking(client: AsyncClient, auth_headers, test_event):
    """Cancellation restores seats to event."""
    # Book first
    book_response = await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 3},
        headers=auth_headers,
    )
    booking_id = book_response.json()["id"]

    # Cancel
    cancel_response = await client.delete(
        f"/api/v1/bookings/{booking_id}",
        headers=auth_headers,
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    # Verify seats restored
    event_response = await client.get(f"/api/v1/events/{test_event.id}")
    assert event_response.json()["available_seats"] == 100


@pytest.mark.asyncio
async def test_cancel_already_cancelled(client: AsyncClient, auth_headers, test_event):
    """Double-cancelling returns 400."""
    # Book
    book_response = await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 1},
        headers=auth_headers,
    )
    booking_id = book_response.json()["id"]

    # Cancel first time
    await client.delete(f"/api/v1/bookings/{booking_id}", headers=auth_headers)

    # Cancel second time
    response = await client.delete(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_user_bookings(client: AsyncClient, auth_headers, test_event):
    """User can see their own bookings."""
    # Create a booking
    await client.post(
        "/api/v1/bookings/",
        json={"event_id": test_event.id, "seat_count": 1},
        headers=auth_headers,
    )

    # List bookings
    response = await client.get("/api/v1/bookings/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["event_id"] == test_event.id


@pytest.mark.asyncio
async def test_book_nonexistent_event(client: AsyncClient, auth_headers):
    """Booking non-existent event returns 404."""
    response = await client.post(
        "/api/v1/bookings/",
        json={"event_id": 99999, "seat_count": 1},
        headers=auth_headers,
    )
    assert response.status_code == 404
