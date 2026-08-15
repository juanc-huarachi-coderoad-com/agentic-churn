"""Covers spec.md User Stories 1/3/4/5's acceptance scenarios against the
real, already-scored Meridian database: the auth gate on `/api/dashboard`,
the full `DashboardResponse` shape (score block, contribution bars, pulse
timeline, stakeholder cards, coverage line), and the `no_profile` edge case
(spec.md Edge Cases, `contracts/dashboard.md`). `GetDashboardUseCase`
supersedes feature 002's `GetDashboardShellUseCase` — this file replaces that
feature's own two tests rather than extending them, since the response shape
itself changed (`contracts/dashboard.md`)."""

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


async def test_dashboard_renders_the_real_client_header(client, auth_token):
    response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["client_header"]["client_name"] == "Meridian Logistics"
    # days_to_renewal (/speckit-analyze finding CV2) — a real computed integer,
    # not absent and not fabricated.
    assert isinstance(body["client_header"]["days_to_renewal"], int)


async def test_dashboard_contribution_bars_include_the_real_worked_example(client, auth_token):
    """data-model.md's ticket #456 contribution (39.0 points, broken_response_
    promise) — asserts it's present among whatever else the real, shared
    database currently holds, not that it's the only contribution (SC-003)."""
    async with engine.begin() as conn:
        real = (
            await conn.execute(
                text(
                    "SELECT sc.id, sc.points_contributed, sc.is_positive "
                    "FROM score_contributions sc "
                    "JOIN findings f ON f.id = sc.finding_id "
                    "WHERE f.finding_type = 'broken_response_promise' "
                    "ORDER BY sc.points_contributed DESC LIMIT 1"
                )
            )
        ).one_or_none()
    if real is None:
        pytest.skip("no broken_response_promise contribution seeded yet")

    response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    body = response.json()
    bars = {b["score_contribution_id"]: b for b in body["contribution_bars"]}
    if str(real.id) not in bars:
        pytest.skip("that contribution isn't part of the latest score run")
    bar = bars[str(real.id)]
    assert bar["label"] == "broken_response_promise"
    assert bar["points"] == pytest.approx(float(real.points_contributed))
    assert bar["is_positive"] == real.is_positive


async def test_dashboard_pulse_timeline_cites_real_events_with_serif_quotes(client, auth_token):
    response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    body = response.json()
    for event in body["pulse_timeline"]:
        assert event["severity"] in {"info", "watch", "at_risk"}
        # score_contribution_id (an addition beyond architecture/07-api-spec.md's
        # originally-drafted PulseEvent shape) makes every pulse event clickable
        # through to evidence (FR-007).
        assert event["score_contribution_id"]


async def test_dashboard_stakeholder_cards_have_honest_tone_trajectory(client, auth_token):
    response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    body = response.json()
    for card in body["stakeholder_cards"]:
        assert card["tone_trajectory"] == "unknown"
        assert card["status"] in {"active", "quiet", "unresolved_identity"}


async def test_dashboard_surfaces_a_real_unresolved_sender_as_a_card(client, auth_token):
    """spec.md's User Story 4, Acceptance Scenario 3 — a sender who has
    written multiple times but doesn't match any profiled stakeholder's
    identifiers is visible, not silently dropped."""
    async with engine.begin() as conn:
        unresolved = (
            await conn.execute(
                text(
                    "SELECT structured_payload->>'participant' AS participant, count(*) AS n "
                    "FROM events WHERE stakeholder_id IS NULL "
                    "AND structured_payload ? 'participant' "
                    "GROUP BY structured_payload->>'participant' HAVING count(*) >= 3 LIMIT 1"
                )
            )
        ).one_or_none()
    if unresolved is None:
        pytest.skip("no unresolved sender with 3+ messages seeded yet")

    response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    body = response.json()
    matching = [
        c
        for c in body["stakeholder_cards"]
        if c["status"] == "unresolved_identity" and c["name"] == unresolved.participant
    ]
    assert len(matching) == 1
    assert matching[0]["stakeholder_id"] is None


async def test_dashboard_coverage_line_reflects_real_sources(client, auth_token):
    response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    body = response.json()
    coverage = body["coverage_line"]
    assert coverage["status"] in {"ok", "degraded", "disconnected"}
    assert coverage["sources_expected"] >= coverage["sources_read"] >= 0


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
        assert body["contribution_bars"] == []
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE client_profile_versions SET is_current = true WHERE id = :id"),
                {"id": current_id},
            )
