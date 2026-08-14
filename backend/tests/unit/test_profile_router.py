"""Exercises `POST /api/profile/reload` end to end: new version created, prior
version's `is_current` flips, `422` on an invalid profile with no new version created."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.adapters.router import limiter
from app.config import settings
from app.context.adapters import profile_router
from app.db import engine
from app.main import app

SEEDED_USERNAME = "marta"
SEEDED_PASSWORD = "agentic-demo-2026"

_VALID_YAML = """
client: Test Client Co
renewal_date: 2027-01-01
contract_value_band: standard
stakeholders:
  - id: stk_test
    name: Test Sponsor
    influence: sponsor
    signs_renewal: true
    identifiers: [test.sponsor@example.com]
communication:
  working_hours: 08:00-18:00
  timezone: UTC
  languages: [en]
"""

_INVALID_YAML = """
client: Test Client Co
renewal_date: 2027-01-01
contract_value_band: standard
stakeholders:
  - id: stk_test
    name: Test Sponsor
    influence: sponsor
    signs_renewal: false
    identifiers: [test.sponsor@example.com]
communication:
  working_hours: 08:00-18:00
  timezone: UTC
  languages: [en]
"""


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture(autouse=True)
async def _restore_current_profile():
    """A successful `POST /api/profile/reload` flips `is_current` onto a brand-new
    version — real, correct behavior (REQ-M3-02), but this test file is the only thing
    in the suite that mutates *which* profile version is current, and every other test
    (business-hours arithmetic, redaction against the seeded exclusions list, identity
    resolution's stakeholder-lookup fallback) assumes the seeded Meridian profile stays
    current. `client_profile_versions` rows are never deleted, so restoring
    `is_current` afterward (same try/finally pattern as
    test_dashboard_route.py::test_dashboard_returns_no_profile_state_when_none_is_current)
    fully undoes the pollution without touching the row itself."""
    async with engine.begin() as conn:
        before = (
            await conn.execute(text("SELECT id FROM client_profile_versions WHERE is_current"))
        ).one_or_none()
    yield
    if before is not None:
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE client_profile_versions SET is_current = false"))
            await conn.execute(
                text("UPDATE client_profile_versions SET is_current = true WHERE id = :id"),
                {"id": before.id},
            )


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_token(client):
    resp = await client.post(
        "/auth/login", json={"username": SEEDED_USERNAME, "password": SEEDED_PASSWORD}
    )
    assert resp.status_code == 200
    return resp.json()["token"]


async def _current_version_number() -> int | None:
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT version_number FROM client_profile_versions WHERE is_current LIMIT 1")
            )
        ).one_or_none()
    return row.version_number if row is not None else None


async def test_reload_creates_new_version_and_flips_prior_current(
    client, auth_token, tmp_path, monkeypatch
):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_VALID_YAML)
    monkeypatch.setattr(settings, "client_profile_path", str(profile_path))

    before = await _current_version_number()

    resp = await client.post(
        "/api/profile/reload", headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["client_name"] == "Test Client Co"
    if before is not None:
        assert body["version_number"] == before + 1

    async with engine.begin() as conn:
        current_rows = (
            await conn.execute(
                text(
                    "SELECT id FROM client_profile_versions WHERE is_current AND "
                    "version_number = :v"
                ),
                {"v": body["version_number"]},
            )
        ).all()
    assert len(current_rows) == 1, "exactly one is_current row must exist after reload"


async def test_reload_rejects_invalid_profile_and_creates_no_new_version(
    client, auth_token, tmp_path, monkeypatch
):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_INVALID_YAML)
    monkeypatch.setattr(settings, "client_profile_path", str(profile_path))

    before = await _current_version_number()

    resp = await client.post(
        "/api/profile/reload", headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert resp.status_code == 422
    assert await _current_version_number() == before


async def test_reload_requires_authentication(tmp_path, monkeypatch, client):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(_VALID_YAML)
    monkeypatch.setattr(settings, "client_profile_path", str(profile_path))

    resp = await client.post("/api/profile/reload")

    assert resp.status_code == 401


async def test_get_profile_returns_current_version(client, auth_token):
    resp = await client.get("/api/profile", headers={"Authorization": f"Bearer {auth_token}"})

    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert "client_name" in resp.json()


# Guards against a future refactor accidentally importing profile_router's settings
# reference from a different module object than app.config.settings (which would make
# monkeypatch.setattr above a silent no-op against the wrong instance).
def test_profile_router_uses_the_shared_settings_singleton():
    assert profile_router.settings is settings
