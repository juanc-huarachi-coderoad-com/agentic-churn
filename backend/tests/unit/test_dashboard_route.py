"""Covers spec.md User Story 2's acceptance scenarios: the auth gate on /api/dashboard,
the Learning-state response against the real seeded profile, and the no_profile edge
case (spec.md Edge Cases, contracts/dashboard.md)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.domain.password import hash_password
from app.db import engine
from app.main import app

TEST_PASSWORD = "test-password-123"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_token(client):
    user_id = uuid.uuid4()
    username = f"dashtest-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Dash Test', true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    login = await client.post("/auth/login", json={"username": username, "password": TEST_PASSWORD})
    token = login.json()["token"]
    yield token
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


async def test_dashboard_requires_authentication(client):
    response = await client.get("/api/dashboard")
    assert response.status_code == 401


async def test_dashboard_returns_learning_state_for_the_seeded_profile(client, auth_token):
    response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "learning"
    assert body["client_header"]["client_name"] == "Meridian Logistics"
    assert body["learning_message"] == "Still learning — 0 of 6 signal types available."
    # The full REQ-M8-02 component set is explicitly out of scope for this feature
    # (contracts/dashboard.md) — absent, not present-as-empty.
    assert "score_block" not in body
    assert "contribution_bars" not in body


async def test_dashboard_returns_no_profile_state_when_none_is_current(client, auth_token):
    async with engine.begin() as conn:
        current = await conn.execute(
            text("SELECT id FROM client_profile_versions WHERE is_current = true")
        )
        current_id = current.scalar_one()
        await conn.execute(text("UPDATE client_profile_versions SET is_current = false"))
    try:
        response = await client.get(
            "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "no_profile"
        assert body["client_header"] is None
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE client_profile_versions SET is_current = true WHERE id = :id"),
                {"id": current_id},
            )
