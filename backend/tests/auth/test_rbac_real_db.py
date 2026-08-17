"""Real-DB: `require_full_access` applied to the real, running ASGI app
(specs/011-production-hardening, User Story 2, `contracts/rbac.md`'s full route
table). Uses well-formed bodies referencing nonexistent IDs where a body is
needed — this test verifies the *authorization* layer, not each route's own
business logic (already covered elsewhere): an `account_executive` token must
get `403` before any business logic runs; a `cs_lead` token must reach that
business logic and get whatever status it would have gotten before this
feature (never `403` — FR-007's "no new restriction").
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
    # raise_app_exceptions=False: cs_lead's /api/ask call reaches real business
    # logic in this test (no auth-layer 403), and this host has no ANTHROPIC_API_KEY
    # configured — that's a real, expected 500 in this environment (every other
    # feature's own precedent: "fails honestly"), not something this RBAC-focused
    # test should treat as a raised exception the way a real deployed server never
    # would.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def ae_token(client):
    async with engine.begin() as conn:
        user_id = uuid.uuid4()
        username = f"ae-test-{user_id.hex[:8]}"
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


_DUMMY_ID = str(uuid.uuid4())

# (method, path, json_body) for every route contracts/rbac.md names as gaining
# require_full_access.
_WRITE_ROUTES = [
    ("POST", "/api/feedback", {"finding_id": _DUMMY_ID, "verdict": "correct"}),
    ("POST", "/api/profile/reload", None),
    ("POST", "/api/ask", {"question": "is this normal?"}),
    (
        "POST",
        "/api/drafts",
        {"issue_id": _DUMMY_ID, "stakeholder_id": _DUMMY_ID, "tone_variant": "direct"},
    ),
    ("POST", f"/api/drafts/{_DUMMY_ID}/copy", None),
    ("POST", f"/api/drafts/{_DUMMY_ID}/log-as-sent", None),
]

_READ_ONLY_ROUTES = [
    ("GET", "/api/dashboard"),
    ("GET", f"/api/evidence/{_DUMMY_ID}"),
    ("GET", "/api/coverage"),
    ("GET", "/api/profile"),
]


@pytest.mark.parametrize("method,path,body", _WRITE_ROUTES)
async def test_account_executive_gets_403_on_every_write_route(
    client, ae_token, method, path, body
):
    resp = await client.request(method, path, json=body, headers=_auth(ae_token))
    assert resp.status_code == 403, f"{method} {path} returned {resp.status_code}, expected 403"


@pytest.mark.parametrize("method,path,body", _WRITE_ROUTES)
async def test_cs_lead_never_gets_403_on_any_write_route(
    client, cs_lead_token, method, path, body
):
    resp = await client.request(method, path, json=body, headers=_auth(cs_lead_token))
    assert resp.status_code != 403, f"{method} {path} returned 403 — FR-007 regression"


@pytest.mark.parametrize("method,path", _READ_ONLY_ROUTES)
async def test_account_executive_never_gets_403_on_any_read_only_route(
    client, ae_token, method, path
):
    resp = await client.request(method, path, headers=_auth(ae_token))
    assert resp.status_code != 403, f"{method} {path} returned 403 for an AE read-only route"


@pytest.mark.parametrize("method,path", _READ_ONLY_ROUTES)
async def test_cs_lead_unchanged_on_every_read_only_route(client, cs_lead_token, method, path):
    resp = await client.request(method, path, headers=_auth(cs_lead_token))
    assert resp.status_code != 403
