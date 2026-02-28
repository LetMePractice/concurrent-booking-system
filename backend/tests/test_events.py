"""
Tests for event CRUD endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_event(client: AsyncClient, auth_headers):
    """Authenticated user can create an event."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    response = await client.post(
        "/api/v1/events/",
        json={
            "title": "Python Conference 2026",
            "description": "Annual Python gathering",
            "date": future_date,
            "location": "Convention Center",
            "seat_count": 500,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Python Conference 2026"
    assert data["seat_count"] == 500
    assert data["available_seats"] == 500  # All seats available initially


@pytest.mark.asyncio
async def test_create_event_unauthenticated(client: AsyncClient):
    """Unauthenticated request returns 401."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    response = await client.post("/api/v1/events/", json={
        "title": "Unauthorized Event",
        "date": future_date,
        "seat_count": 100,
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_event_past_date(client: AsyncClient, auth_headers):
    """Event with past date returns 400."""
    past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = await client.post(
        "/api/v1/events/",
        json={
            "title": "Past Event",
            "date": past_date,
            "seat_count": 100,
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_event_invalid_seats(client: AsyncClient, auth_headers):
    """Zero or negative seat count returns 422."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    response = await client.post(
        "/api/v1/events/",
        json={
            "title": "No Seats",
            "date": future_date,
            "seat_count": 0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_events(client: AsyncClient, test_event):
    """List events returns paginated results."""
    response = await client.get("/api/v1/events/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["events"]) >= 1
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_events_pagination(client: AsyncClient, test_event):
    """Pagination parameters work correctly."""
    response = await client.get("/api/v1/events/?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_get_event(client: AsyncClient, test_event):
    """Get single event by ID."""
    response = await client.get(f"/api/v1/events/{test_event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_event.id
    assert data["title"] == "Test Concert"


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient):
    """Non-existent event returns 404."""
    response = await client.get("/api/v1/events/99999")
    assert response.status_code == 404
