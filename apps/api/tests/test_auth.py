"""Auth endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_me(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "password123", "name": "New User"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert "id" in data

    # Cookie session from register should work for /me
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_login_invalid(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpass1"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_register(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "password123", "name": "Dup"}
    assert (await client.post("/api/auth/register", json=payload)).status_code == 200
    again = await client.post("/api/auth/register", json=payload)
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "password123", "name": "Login"},
    )
    # Clear cookies then login
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "login@example.com"
