"""Covers spec.md User Story 1's acceptance scenarios end to end against the real ASGI
app and a real database (DATABASE_URL, already migrated — see workflows/ci.yml). Not
mocked at the repository level: this is exactly the kind of behavior (password hashing,
token lifecycle, rate limiting) that's cheap to verify for real and easy to get subtly
wrong if verified only against a mock."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.adapters.router import limiter
from app.auth.application.dependencies import get_current_user
from app.auth.domain.password import hash_password
from app.db import engine
from app.main import app

TEST_PASSWORD = "test-password-123"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    # The rate limiter's in-memory storage is shared module-level state
    # (app.auth.adapters.router.limiter) — reset before every test so one test's
    # failed attempts can't trip another's (AGENTS.md: tests run in isolation).
    limiter.reset()
    yield


@pytest.fixture
async def test_user():
    user_id = uuid.uuid4()
    username = f"testuser-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Test User', true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    yield {"id": user_id, "username": username, "password": TEST_PASSWORD}
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


@pytest.fixture
async def deactivated_user():
    user_id = uuid.uuid4()
    username = f"deactivated-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Deactivated User', false)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    yield {"id": user_id, "username": username, "password": TEST_PASSWORD}
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_valid_login_returns_token_with_expiry(client, test_user):
    resp = await client.post(
        "/auth/login", json={"username": test_user["username"], "password": test_user["password"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["expires_at"]


async def test_wrong_password_and_unknown_username_are_identical(client, test_user):
    wrong_password = await client.post(
        "/auth/login", json={"username": test_user["username"], "password": "wrong"}
    )
    unknown_username = await client.post(
        "/auth/login", json={"username": "does-not-exist", "password": "wrong"}
    )
    assert wrong_password.status_code == 401
    assert unknown_username.status_code == 401
    assert wrong_password.json() == unknown_username.json()


async def test_deactivated_user_rejected_identically_to_unknown_username(
    client, deactivated_user
):
    resp = await client.post(
        "/auth/login",
        json={"username": deactivated_user["username"], "password": deactivated_user["password"]},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid credentials"}


async def test_successful_login_does_not_count_against_rate_limit(client, test_user):
    # A legitimately busy user logging in repeatedly must never be rate-limited —
    # only failures count (research.md's "failures only" implementation note).
    for _ in range(5):
        resp = await client.post(
            "/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
        )
        assert resp.status_code == 200


async def test_third_failed_attempt_is_rate_limited(client, test_user):
    for _ in range(2):
        resp = await client.post(
            "/auth/login", json={"username": test_user["username"], "password": "wrong"}
        )
        assert resp.status_code == 401
    third = await client.post(
        "/auth/login", json={"username": test_user["username"], "password": "wrong"}
    )
    assert third.status_code == 429


async def test_logout_revokes_token_and_get_current_user_rejects_it_on_next_use(
    client, test_user
):
    login = await client.post(
        "/auth/login", json={"username": test_user["username"], "password": test_user["password"]}
    )
    token = login.json()["token"]

    logout = await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 204

    # No protected business route exists yet in this feature — exercise the dependency
    # directly (FR-006's identity-resolution gate), matching what feature 006's
    # protected routes will rely on.
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    from app.auth.adapters.sqlalchemy_repository import SqlAlchemyTokenRepository
    from app.db import async_session_factory

    async with async_session_factory() as session:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                token_repository=SqlAlchemyTokenRepository(session),
            )
    assert exc_info.value.status_code == 401


async def test_get_current_user_resolves_the_correct_user_id(client, test_user):
    """FR-006: the identity resolved from a valid token must be the actual logging-in
    user, not just a boolean 'is authenticated'."""
    login = await client.post(
        "/auth/login", json={"username": test_user["username"], "password": test_user["password"]}
    )
    token = login.json()["token"]

    from fastapi.security import HTTPAuthorizationCredentials

    from app.auth.adapters.sqlalchemy_repository import SqlAlchemyTokenRepository
    from app.db import async_session_factory

    async with async_session_factory() as session:
        current_user = await get_current_user(
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            token_repository=SqlAlchemyTokenRepository(session),
        )
    assert current_user.user_id == test_user["id"]
