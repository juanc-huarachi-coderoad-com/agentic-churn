"""Real-DB: `PATCH /api/admin/finding-types/{finding_type}` against the real,
running ASGI app (specs/011-production-hardening, User Story 4).
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


async def _login(client, username: str, password: str) -> str:
    resp = await client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["token"]


@pytest.fixture
async def admin_token(client):
    return await _login(client, "admin-demo", "agentic-demo-2026-admin")


@pytest.fixture
async def cs_lead_token(client):
    return await _login(client, "marta", "agentic-demo-2026")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _current_base_points(finding_type: str) -> float:
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT base_points FROM finding_type_config WHERE finding_type = :ft"),
                {"ft": finding_type},
            )
        ).one()
    return float(row.base_points)


async def _latest_score_run_id() -> str | None:
    async with engine.begin() as conn:
        row = (
            await conn.execute(text("SELECT id FROM score_runs ORDER BY computed_at DESC LIMIT 1"))
        ).one_or_none()
    return str(row.id) if row is not None else None


async def _ensure_healthy_coverage() -> None:
    """`RecomputeScoreUseCase` freezes (REQ-M6-26) instead of computing fresh
    whenever the most recent coverage report shows a degraded source — real,
    existing, correct behavior, but it means this test's assertions about a
    *fresh* `finding_type_config_version` only hold with a healthy coverage
    state. Anchors to whatever the shared dev database's most recent
    collector_run already is, the same "don't assume, read the real state"
    pattern `tests/conftest.py`'s `ledger_floor` already establishes."""
    async with engine.begin() as conn:
        run_id = (
            await conn.execute(
                text("SELECT id FROM collector_runs ORDER BY started_at DESC LIMIT 1")
            )
        ).one()
        await conn.execute(
            text(
                "INSERT INTO coverage_reports "
                "(collector_run_id, sources_expected, sources_read, complete_to) "
                "VALUES (:run_id, 1, 1, now())"
            ),
            {"run_id": run_id.id},
        )


async def test_admin_updates_weight_and_triggers_weight_edit_replay(client, admin_token):
    await _ensure_healthy_coverage()
    finding_type = "broken_response_promise"
    original_base_points = await _current_base_points(finding_type)
    prior_run_id = await _latest_score_run_id()
    prior_score_snapshot = None
    if prior_run_id is not None:
        async with engine.begin() as conn:
            prior_score_snapshot = (
                await conn.execute(
                    text(
                        "SELECT score, total_points, finding_type_config_version "
                        "FROM score_runs WHERE id = :id"
                    ),
                    {"id": prior_run_id},
                )
            ).one()

    try:
        resp = await client.patch(
            f"/api/admin/finding-types/{finding_type}",
            json={"base_points": original_base_points + 5},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["base_points"] == original_base_points + 5

        # finding_type_config_changes audit row (FR-014).
        async with engine.begin() as conn:
            change = (
                await conn.execute(
                    text(
                        "SELECT previous_base_points, new_base_points, changed_by_user_id "
                        "FROM finding_type_config_changes "
                        "WHERE finding_type = :ft ORDER BY changed_at DESC LIMIT 1"
                    ),
                    {"ft": finding_type},
                )
            ).one()
        assert float(change.previous_base_points) == original_base_points
        assert float(change.new_base_points) == original_base_points + 5

        # A new score_runs row with trigger = weight_edit_replay and a different
        # finding_type_config_version than whatever came before (FR-013/SC-004).
        async with engine.begin() as conn:
            new_run = (
                await conn.execute(
                    text(
                        "SELECT trigger, finding_type_config_version FROM score_runs "
                        "ORDER BY computed_at DESC LIMIT 1"
                    )
                )
            ).one()
        assert new_run.trigger == "weight_edit_replay"
        assert new_run.finding_type_config_version == body["config_version"]

        # FR-015: the prior run (if one existed) is byte-identical afterward —
        # never retroactively touched by a later weight change.
        if prior_run_id is not None:
            async with engine.begin() as conn:
                prior_after = (
                    await conn.execute(
                        text(
                            "SELECT score, total_points, finding_type_config_version "
                            "FROM score_runs WHERE id = :id"
                        ),
                        {"id": prior_run_id},
                    )
                ).one()
            assert prior_after.score == prior_score_snapshot.score
            assert prior_after.total_points == prior_score_snapshot.total_points
            assert (
                prior_after.finding_type_config_version
                == prior_score_snapshot.finding_type_config_version
            )
    finally:
        # Restore the original weight unconditionally — even if an assertion
        # above failed — so this test never leaves the shared dev database's
        # seed weight permanently drifted (a real mistake this test made
        # during its own development: an early failing run skipped this
        # cleanup entirely, silently drifting broken_response_promise's
        # base_points upward by 5 on every subsequent debug run until caught
        # by tests/scoring/test_worked_example.py failing for an unrelated-
        # looking reason).
        await client.patch(
            f"/api/admin/finding-types/{finding_type}",
            json={"base_points": original_base_points},
            headers=_auth(admin_token),
        )


async def test_cs_lead_is_denied_and_nothing_is_written(client, cs_lead_token):
    finding_type = "broken_response_promise"
    before = await _current_base_points(finding_type)

    resp = await client.patch(
        f"/api/admin/finding-types/{finding_type}",
        json={"base_points": before + 100},
        headers=_auth(cs_lead_token),
    )
    assert resp.status_code == 403
    assert await _current_base_points(finding_type) == before


async def test_unknown_finding_type_returns_404(client, admin_token):
    resp = await client.patch(
        "/api/admin/finding-types/does_not_exist",
        json={"base_points": 10},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404


async def test_negative_base_points_returns_422(client, admin_token):
    resp = await client.patch(
        "/api/admin/finding-types/broken_response_promise",
        json={"base_points": -1},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 422
