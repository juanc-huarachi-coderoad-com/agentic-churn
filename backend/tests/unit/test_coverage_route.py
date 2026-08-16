"""Covers spec.md User Story 3's system-health acceptance scenarios against
the real database: per-source status and an honestly-empty quarantine list
(`contracts/coverage.md`).
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
    username = f"coveragetest-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Coverage Test', true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    login = await client.post("/auth/login", json={"username": username, "password": TEST_PASSWORD})
    token = login.json()["token"]
    yield token
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


async def test_coverage_requires_authentication(client):
    response = await client.get("/api/coverage")
    assert response.status_code == 401


async def test_coverage_returns_real_per_source_status(client, auth_token):
    async with engine.begin() as conn:
        expected = (await conn.execute(text("SELECT count(*) FROM sources"))).scalar_one()

    response = await client.get(
        "/api/coverage", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["sources"]) == expected
    for source in body["sources"]:
        assert source["status"] in {"connected", "degraded", "disconnected"}


async def test_coverage_quarantine_is_real_and_empty_when_nothing_is_quarantined(
    client, auth_token
):
    """Real, not a stub — empty specifically because nothing has been
    quarantined in this isolated setup, not because the query is a
    placeholder (feature 007's `ValidationGate` is what actually populates
    `quarantine`, verified by the next test)."""
    finding_id = uuid.uuid4()
    async with engine.begin() as conn:
        assert (
            await conn.execute(
                text("SELECT count(*) FROM quarantine WHERE finding_id = :id"),
                {"id": finding_id},
            )
        ).scalar_one() == 0

    response = await client.get(
        "/api/coverage", headers={"Authorization": f"Bearer {auth_token}"}
    )
    ids_in_response = {entry["finding_id"] for entry in response.json()["quarantine"]}
    assert str(finding_id) not in ids_in_response


async def test_coverage_quarantine_reflects_a_real_quarantined_finding(client, auth_token):
    """REQ-M5A-04/SC-004 — once the validation gate quarantines a real
    finding, `GET /api/coverage` shows it, not the permanently-empty list
    feature 006 shipped."""
    async with engine.begin() as conn:
        finding_id = (
            await conn.execute(
                text(
                    "INSERT INTO findings (reader_type, reader_version, finding_type, "
                    "magnitude, confidence, cited_event_ids, status) "
                    "VALUES ('tone'::reader_type, 'coverage-test', 'tone_deterioration', "
                    "0.5, 0.1, ARRAY[gen_random_uuid()], 'quarantined'::finding_status) "
                    "RETURNING id"
                )
            )
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO quarantine (finding_id, failed_check) "
                "VALUES (:finding_id, 'confidence_below_floor'::validation_check)"
            ),
            {"finding_id": finding_id},
        )

    try:
        response = await client.get(
            "/api/coverage", headers={"Authorization": f"Bearer {auth_token}"}
        )
        entries = {e["finding_id"]: e["failed_check"] for e in response.json()["quarantine"]}
        assert entries[str(finding_id)] == "confidence_below_floor"
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM quarantine WHERE finding_id = :id"), {"id": finding_id}
            )
            await conn.execute(text("DELETE FROM findings WHERE id = :id"), {"id": finding_id})


async def test_ask_intent_coverage_reflects_real_ask_queries_rows(client, auth_token):
    """specs/008-narrator-and-ask-agent, SC-007 — the Ask agent's fallback
    rate visible without querying the database directly (found missing
    during `/speckit-analyze`, E1)."""
    user_id = uuid.uuid4()
    rows = [
        (uuid.uuid4(), "score_delta", "delta_breakdown", None),
        (uuid.uuid4(), None, None, "prediction"),
    ]
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, 'ask-coverage-test-user', 'x', 'Ask Coverage Test', true)"
            ),
            {"id": user_id},
        )
        for row_id, matched_intent, rendered_component, declined_reason in rows:
            await conn.execute(
                text(
                    "INSERT INTO ask_queries (id, question_text, matched_intent, "
                    "rendered_component, declined_reason, response_time_ms, asked_by_user_id) "
                    "VALUES (:id, 'test question', :matched_intent, :rendered_component, "
                    "CAST(:declined_reason AS declined_reason), 100, :user_id)"
                ),
                {
                    "id": row_id,
                    "matched_intent": matched_intent,
                    "rendered_component": rendered_component,
                    "declined_reason": declined_reason,
                    "user_id": user_id,
                },
            )

    try:
        response = await client.get(
            "/api/coverage", headers={"Authorization": f"Bearer {auth_token}"}
        )
        coverage = response.json()["ask_intent_coverage"]
        assert coverage is not None
        assert coverage["total_questions"] >= 2
        assert coverage["fallback_count"] >= 1
        assert 0.0 <= coverage["fallback_rate"] <= 1.0
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM ask_queries WHERE id = ANY(:ids)"),
                {"ids": [r[0] for r in rows]},
            )
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
