"""Real-DB integration for `POST /api/feedback`, against the real,
already-scored Meridian database — matching `test_draft_routes_real_db.py`'s
own real-DB HTTP pattern. Covers spec.md's User Story 1 acceptance
scenarios 2-4 and the FR-005a rejection case (`quickstart.md` §1-2, §4,
§6-7).
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
    username = f"feedbacktest-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Feedback Test', true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    login = await client.post("/auth/login", json={"username": username, "password": TEST_PASSWORD})
    token = login.json()["token"]
    yield token
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


@pytest.fixture
async def validated_finding():
    """A real, already-validated finding from the seeded Meridian ledger —
    skipped honestly if this database hasn't been seeded/scored yet,
    matching `test_draft_routes_real_db.py`'s own fixture precedent."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT id, reader_type, finding_type FROM findings "
                    "WHERE status = 'validated' LIMIT 1"
                )
            )
        ).one_or_none()
    if row is None:
        pytest.skip("No validated finding seeded yet")
    pattern = f"{row.reader_type}+{row.finding_type}"
    yield row.id, pattern
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM feedback_verdicts WHERE pattern_signature = :ps"),
            {"ps": pattern},
        )
        await conn.execute(
            text("DELETE FROM damping_weights WHERE pattern_signature = :ps"),
            {"ps": pattern},
        )


async def test_feedback_requires_authentication(client):
    response = await client.post("/api/feedback", json={"finding_id": str(uuid.uuid4()), "verdict": "correct"})
    assert response.status_code == 401


async def test_feedback_requires_a_target(client, auth_token):
    response = await client.post(
        "/api/feedback",
        json={"verdict": "correct"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422


async def test_one_false_alarm_damps_to_0500(client, auth_token, validated_finding):
    finding_id, pattern = validated_finding

    response = await client.post(
        "/api/feedback",
        json={"finding_id": str(finding_id), "verdict": "false_alarm"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 204

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT weight, false_alarm_count, disclosure_text FROM damping_weights "
                    "WHERE pattern_signature = :ps"
                ),
                {"ps": pattern},
            )
        ).one()
    assert float(row.weight) == pytest.approx(0.500)
    assert row.false_alarm_count == 1
    assert row.disclosure_text


async def test_second_false_alarm_damps_to_0250(client, auth_token, validated_finding):
    finding_id, pattern = validated_finding

    for _ in range(2):
        response = await client.post(
            "/api/feedback",
            json={"finding_id": str(finding_id), "verdict": "false_alarm"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 204

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT weight, false_alarm_count FROM damping_weights WHERE pattern_signature = :ps"),
                {"ps": pattern},
            )
        ).one()
    assert float(row.weight) == pytest.approx(0.250)
    assert row.false_alarm_count == 2


async def test_past_score_run_unchanged_after_verdict(client, auth_token, validated_finding):
    finding_id, _pattern = validated_finding

    async with engine.begin() as conn:
        before = (
            await conn.execute(
                text("SELECT id, score, computed_at FROM score_runs ORDER BY computed_at DESC LIMIT 1")
            )
        ).one_or_none()
    if before is None:
        pytest.skip("No score_run exists yet")

    response = await client.post(
        "/api/feedback",
        json={"finding_id": str(finding_id), "verdict": "false_alarm"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 204

    async with engine.begin() as conn:
        after = (
            await conn.execute(
                text("SELECT id, score, computed_at FROM score_runs WHERE id = :id"),
                {"id": before.id},
            )
        ).one()
    assert after.score == before.score
    assert after.computed_at == before.computed_at


async def test_false_alarm_with_only_issue_id_is_rejected(client, auth_token):
    async with engine.begin() as conn:
        row = (await conn.execute(text("SELECT id FROM issues LIMIT 1"))).one_or_none()
    if row is None:
        pytest.skip("No issue seeded yet")

    response = await client.post(
        "/api/feedback",
        json={"issue_id": str(row.id), "verdict": "false_alarm"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422

    async with engine.begin() as conn:
        count = (
            await conn.execute(
                text("SELECT count(*) AS n FROM feedback_verdicts WHERE issue_id = :id"),
                {"id": row.id},
            )
        ).one()
    assert count.n == 0


# ---------------------------------------------------------------------------
# User Story 3 — correct/resolved via the real API (REQ-M6-CAL-03a/b).
# ---------------------------------------------------------------------------


async def test_two_false_alarms_then_correct_recovers_to_02875(client, auth_token, validated_finding):
    finding_id, pattern = validated_finding

    for verdict in ("false_alarm", "false_alarm", "correct"):
        response = await client.post(
            "/api/feedback",
            json={"finding_id": str(finding_id), "verdict": verdict},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 204

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT weight, false_alarm_count, correct_count FROM damping_weights "
                    "WHERE pattern_signature = :ps"
                ),
                {"ps": pattern},
            )
        ).one()
    # damping_weights.weight is NUMERIC(4,3) — only 3 decimal digits stored,
    # so 0.2875 rounds to 0.287/0.288 at the DB layer; the full-precision
    # value is already asserted at the application layer
    # (test_record_feedback_verdict_use_case.py, pure, no DB).
    assert float(row.weight) == pytest.approx(0.2875, abs=0.001)
    assert row.false_alarm_count == 2
    assert row.correct_count == 1


async def test_resolved_verdict_increments_count_without_touching_weight(
    client, auth_token, validated_finding
):
    finding_id, pattern = validated_finding

    response = await client.post(
        "/api/feedback",
        json={"finding_id": str(finding_id), "verdict": "resolved"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 204

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT weight, resolved_count FROM damping_weights "
                    "WHERE pattern_signature = :ps"
                ),
                {"ps": pattern},
            )
        ).one()
    assert row.resolved_count == 1
    assert float(row.weight) == pytest.approx(1.0)
