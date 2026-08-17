"""Real-DB: `POST /api/profile` against the real, running ASGI app
(specs/011-production-hardening, User Story 5).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def cs_lead_token(client):
    resp = await client.post(
        "/auth/login", json={"username": "marta", "password": "agentic-demo-2026"}
    )
    return resp.json()["token"]


@pytest.fixture
async def ae_token(client):
    resp = await client.post(
        "/auth/login", json={"username": "ae-demo", "password": "agentic-demo-2026-ae"}
    )
    return resp.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _valid_profile_body(*, note: str) -> dict:
    return {
        "client": "Meridian Logistics",
        "renewal_date": "2026-11-08",
        "contract_value_band": "strategic",
        "business_goals": ["reduce delivery disputes by 30% this year"],
        "stakeholders": [
            {
                "id": "stk_ana",
                "name": "Ana Reyes",
                "role": "CTO",
                "influence": "sponsor",
                "signs_renewal": True,
                "identifiers": ["ana.reyes@meridian.com"],
            },
            {
                "id": "stk_new",
                "name": "New Stakeholder",
                "role": "VP Eng",
                "influence": "daily_user",
                "signs_renewal": False,
                "identifiers": [],
            },
        ],
        "product_areas": [{"key": "tracking_api", "criticality": "critical"}],
        "commitments": [
            {"type": "first_response", "priority": "P1", "threshold_business_hours": 4.0}
        ],
        "communication": {
            "working_hours": "08:00-18:00",
            "timezone": "America/Bogota",
            "languages": ["es", "en"],
            "norms": note,
        },
        "exclusions": ["legal_threads", "commercial_negotiation"],
        "history": [],
    }


async def _current_version_number() -> int:
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT version_number FROM client_profile_versions "
                    "WHERE is_current ORDER BY version_number DESC LIMIT 1"
                )
            )
        ).one()
    return int(row.version_number)


async def test_valid_submission_creates_a_new_version(client, cs_lead_token):
    before = await _current_version_number()

    resp = await client.post(
        "/api/profile",
        json=_valid_profile_body(note="Real-DB test edit"),
        headers=_auth(cs_lead_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["version_number"] == before + 1
    assert len(body["stakeholders"]) == 2

    after = await _current_version_number()
    assert after == before + 1

    # `version_number` is not globally unique across this shared dev database's
    # several independent profile lineages (other tests' own "Test Client Co"
    # profiles interleave the same counter) — `is_current` is the one column
    # guaranteed unique to exactly one row at a time.
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT authored_by_user_id FROM client_profile_versions WHERE is_current")
            )
        ).one()
    async with engine.begin() as conn:
        user_row = (
            await conn.execute(text("SELECT id FROM users WHERE username = 'marta'"))
        ).one()
    assert str(row.authored_by_user_id) == str(user_row.id)


async def test_invalid_submission_returns_422_and_creates_no_version(client, cs_lead_token):
    before = await _current_version_number()

    invalid_body = _valid_profile_body(note="no signer")
    for stakeholder in invalid_body["stakeholders"]:
        stakeholder["signs_renewal"] = False  # violates "at least one signs_renewal"

    resp = await client.post("/api/profile", json=invalid_body, headers=_auth(cs_lead_token))
    assert resp.status_code == 422

    after = await _current_version_number()
    assert after == before


async def test_account_executive_gets_403(client, ae_token):
    before = await _current_version_number()

    resp = await client.post(
        "/api/profile", json=_valid_profile_body(note="should be blocked"), headers=_auth(ae_token)
    )
    assert resp.status_code == 403
    assert await _current_version_number() == before
