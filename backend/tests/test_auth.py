"""
Tests for authentication endpoints: registration and login.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Successful registration returns user data."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "username": "newuser",
        "password": "securepassword123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["username"] == "newuser"
    assert "hashed_password" not in data  # Never expose password hash


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Duplicate email returns 409."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "different",
        "password": "securepassword123",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user):
    """Duplicate username returns 409."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "different@example.com",
        "username": "testuser",
        "password": "securepassword123",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Password under 8 chars returns 422."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "short",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Valid credentials return JWT token."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Wrong password returns 401."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    """Non-existent email returns 401."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "anypassword123",
    })
    assert response.status_code == 401
