"""Real-DB, real-ASGI-app: `GET`/`POST /api/meeting-audio/consent`
(specs/019-meeting-audio-ingestion, `contracts/meeting-audio.md`). Mirrors
`tests/auth/test_rbac_real_db.py`'s fixture pattern for a real `cs_lead`
token (the seeded `marta` demo user) and a throwaway `account_executive`
token.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.domain.password import hash_password
from app.db import engine
from app.main import app

_PASSWORD = "test-password-123"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def ae_token(client):
    async with engine.begin() as conn:
        user_id = uuid.uuid4()
        username = f"ae-consent-test-{user_id.hex[:8]}"
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, role, "
                "is_active) VALUES (:id, :username, :password_hash, 'AE Test', "
                "'account_executive'::user_role, true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(_PASSWORD)},
        )
    resp = await client.post("/auth/login", json={"username": username, "password": _PASSWORD})
    yield resp.json()["token"]
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


@pytest.fixture
async def cs_lead_token(client):
    resp = await client.post(
        "/auth/login", json={"username": "marta", "password": "agentic-demo-2026"}
    )
    return resp.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_cs_lead_can_grant_and_it_appears_in_the_list(client, cs_lead_token):
    series_id = f"series-{uuid.uuid4().hex[:8]}"

    post_resp = await client.post(
        "/api/meeting-audio/consent",
        json={
            "series_id": series_id,
            "status": "granted",
            "all_parties_confirmed": True,
            "note": "confirmed verbally",
        },
        headers=_auth(cs_lead_token),
    )
    assert post_resp.status_code == 201
    body = post_resp.json()
    assert body["series_id"] == series_id
    assert body["status"] == "granted"
    # documented_by is a resolved username (contracts/meeting-audio.md's
    # documented example shape), never the raw user_id UUID
    # (`/speckit-analyze` finding C3).
    assert body["documented_by"] == "marta"

    get_resp = await client.get("/api/meeting-audio/consent", headers=_auth(cs_lead_token))
    assert get_resp.status_code == 200
    entries = {e["series_id"]: e for e in get_resp.json()["series"]}
    assert entries[series_id]["status"] == "granted"
    assert entries[series_id]["documented_by"] == "marta"


async def test_granting_without_all_parties_confirmed_returns_422(client, cs_lead_token):
    series_id = f"series-{uuid.uuid4().hex[:8]}"

    resp = await client.post(
        "/api/meeting-audio/consent",
        json={"series_id": series_id, "status": "granted", "all_parties_confirmed": False},
        headers=_auth(cs_lead_token),
    )

    assert resp.status_code == 422


async def test_account_executive_gets_403_on_post(client, ae_token):
    series_id = f"series-{uuid.uuid4().hex[:8]}"

    resp = await client.post(
        "/api/meeting-audio/consent",
        json={"series_id": series_id, "status": "granted", "all_parties_confirmed": True},
        headers=_auth(ae_token),
    )

    assert resp.status_code == 403


async def test_account_executive_never_gets_403_on_get(client, ae_token):
    resp = await client.get("/api/meeting-audio/consent", headers=_auth(ae_token))

    assert resp.status_code != 403


async def test_revoke_is_a_new_row_not_an_update(client, cs_lead_token):
    series_id = f"series-{uuid.uuid4().hex[:8]}"

    await client.post(
        "/api/meeting-audio/consent",
        json={"series_id": series_id, "status": "granted", "all_parties_confirmed": True},
        headers=_auth(cs_lead_token),
    )
    revoke_resp = await client.post(
        "/api/meeting-audio/consent",
        json={"series_id": series_id, "status": "revoked", "all_parties_confirmed": True},
        headers=_auth(cs_lead_token),
    )
    assert revoke_resp.status_code == 201

    async with engine.begin() as conn:
        count = (
            await conn.execute(
                text("SELECT count(*) AS n FROM meeting_series_consent WHERE series_id = :sid"),
                {"sid": series_id},
            )
        ).one()
    assert count.n == 2

    get_resp = await client.get("/api/meeting-audio/consent", headers=_auth(cs_lead_token))
    entries = {e["series_id"]: e for e in get_resp.json()["series"]}
    assert entries[series_id]["status"] == "revoked"
