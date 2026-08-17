"""Covers spec.md User Story 2's acceptance scenarios against the real,
already-scored Meridian database: `data-model.md`'s worked example, the 404
case, and the `/speckit-analyze` finding CV1 fallback for a `finding_type`
outside the five-entry dispatch table.
"""

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
    username = f"evidencetest-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Evidence Test', true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    login = await client.post("/auth/login", json={"username": username, "password": TEST_PASSWORD})
    token = login.json()["token"]
    yield token
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


async def test_evidence_requires_authentication(client):
    response = await client.get(f"/api/evidence/{uuid.uuid4()}")
    assert response.status_code == 401


async def test_evidence_404_for_a_nonexistent_contribution(client, auth_token):
    response = await client.get(
        f"/api/evidence/{uuid.uuid4()}", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404


async def test_evidence_reproduces_the_worked_example(client, auth_token):
    """data-model.md's ticket #456 contribution: 4h promised, 50h elapsed,
    still open, criticality/recency-only arithmetic."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT sc.id FROM score_contributions sc "
                    "JOIN findings f ON f.id = sc.finding_id "
                    "WHERE f.finding_type = 'broken_response_promise' "
                    "ORDER BY sc.points_contributed DESC LIMIT 1"
                )
            )
        ).one_or_none()
    if row is None:
        pytest.skip("no broken_response_promise contribution seeded yet")

    response = await client.get(
        f"/api/evidence/{row.id}", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["finding_type"] == "broken_response_promise"
    assert "promised business hours" in body["baseline_value"]
    assert "elapsed" in body["current_value"]
    assert len(body["quoted_messages"]) >= 1
    assert body["arithmetic_explanation"].startswith("Base ")
    assert body["arithmetic_explanation"].endswith(" points total.")


async def test_evidence_disclosure_text_absent_when_pattern_never_damped(client, auth_token):
    """spec.md User Story 2 Acceptance Scenario 2 — no disclosure is shown
    for a pattern that has never received a verdict."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT sc.id FROM score_contributions sc "
                    "JOIN findings f ON f.id = sc.finding_id "
                    "WHERE f.status = 'validated' LIMIT 1"
                )
            )
        ).one_or_none()
    if row is None:
        pytest.skip("no score_contribution seeded yet")

    response = await client.get(
        f"/api/evidence/{row.id}", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["disclosure_text"] is None


async def test_evidence_disclosure_text_present_once_pattern_is_damped(client, auth_token):
    """spec.md User Story 2 Acceptance Scenario 1 — REQ-M4-04."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT sc.id, f.reader_type, f.finding_type FROM score_contributions sc "
                    "JOIN findings f ON f.id = sc.finding_id "
                    "WHERE f.status = 'validated' LIMIT 1"
                )
            )
        ).one_or_none()
    if row is None:
        pytest.skip("no score_contribution seeded yet")
    pattern = f"{row.reader_type}+{row.finding_type}"

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO damping_weights "
                "(pattern_signature, weight, false_alarm_count, disclosure_text) "
                "VALUES (:ps, 0.500, 1, 'weight reduced — your team flagged this pattern "
                "as a false alarm')"
            ),
            {"ps": pattern},
        )
    try:
        response = await client.get(
            f"/api/evidence/{row.id}", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["disclosure_text"] == (
            "weight reduced — your team flagged this pattern as a false alarm"
        )
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM damping_weights WHERE pattern_signature = :ps"), {"ps": pattern}
            )


async def test_evidence_falls_back_honestly_for_a_finding_type_outside_the_dispatch_table(
    client, auth_token
):
    """`/speckit-analyze` finding CV1 — `escalation_language`/`tone_
    deterioration`/`csat_deviation` are real in this deployment's seed data
    (feature 007's future readers); the panel must not crash for them."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT sc.id FROM score_contributions sc "
                    "JOIN findings f ON f.id = sc.finding_id "
                    "WHERE f.finding_type IN "
                    "('escalation_language', 'tone_deterioration', 'csat_deviation') "
                    "LIMIT 1"
                )
            )
        ).one_or_none()
    if row is None:
        pytest.skip("no fallback-dispatch finding type seeded yet")

    response = await client.get(
        f"/api/evidence/{row.id}", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "isn't available" in body["baseline_value"]
    assert body["what_changed"] == []
    # quoted_messages/arithmetic_explanation stay fully real regardless of the
    # fallback (research.md's Decision).
    assert body["arithmetic_explanation"].startswith("Base ")
