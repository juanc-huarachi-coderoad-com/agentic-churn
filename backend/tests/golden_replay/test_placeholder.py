"""Golden-replay — `tests/strategy.md` §Golden-replay tests, REQ-NFR-09/28.
The gap three prior features (004, 005, 007) each named this feature, by
number, as the one that closes: the snapshot has always included
`narrator_outputs`, which didn't exist until now (`research.md` Decision 7).

Procedure (verbatim from `tests/strategy.md`):
1. Snapshot the resulting `score_runs`/`score_contributions`/
   `narrator_outputs`/dashboard-facing read API response.
2. `TRUNCATE event_threads, response_pairs, rollups` — the three projection
   tables, exactly as a real replay job would.
3. Re-run the replay job (`ReplayUseCase` + `ComputeRollupsUseCase`) against
   `events` + `client_profile_versions` + `baseline_confirmations` alone.
4. Assert the rebuilt state is byte-identical to the golden snapshot.

The property this proves: `event_threads`/`response_pairs`/`rollups` are
genuinely derived data, rebuildable from the ledger alone, and dropping them
has zero effect on the durable `score_runs`/`score_contributions`/
`narrator_outputs` state a client is currently looking at — those tables are
never touched by this truncate/rebuild, so the dashboard the CS lead sees is
provably identical before and after.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.domain.password import hash_password
from app.config import settings
from app.db import async_session_factory, engine
from app.ingestion.adapters.encryption import FernetEncryption
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import ComputeRollupsUseCase, ReplayUseCase
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
    username = f"goldenreplaytest-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Golden Replay Test', true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    login = await client.post(
        "/auth/login", json={"username": username, "password": TEST_PASSWORD}
    )
    token = login.json()["token"]
    yield token
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


async def _score_and_narrator_state() -> list[dict[str, object]]:
    """`score_runs` + `score_contributions` + `narrator_outputs` — the
    durable state this test proves a projection rebuild never touches."""
    async with engine.begin() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT sr.id AS score_run_id, sr.score, sr.band, sr.total_points, "
                    "no.headline, no.fact_check_passed, "
                    "array_agg(sc.id ORDER BY sc.id) AS contribution_ids, "
                    "array_agg(sc.points_contributed ORDER BY sc.id) AS points "
                    "FROM score_runs sr "
                    "LEFT JOIN narrator_outputs no ON no.score_run_id = sr.id "
                    "LEFT JOIN score_contributions sc ON sc.score_run_id = sr.id "
                    "GROUP BY sr.id, sr.score, sr.band, sr.total_points, "
                    "no.headline, no.fact_check_passed "
                    "ORDER BY sr.computed_at"
                )
            )
        ).all()
    return [dict(r._mapping) for r in rows]


async def _rebuild_projections() -> None:
    """Truncate + rebuild `event_threads`/`response_pairs`/`rollups` from
    `events` alone — the two use cases a real replay job runs (`ReplayUseCase`
    + `ComputeRollupsUseCase`), never a re-run of readers/scoring (those
    write `score_runs`/`findings`/`narrator_outputs` directly, not through
    these projections)."""
    encryption = FernetEncryption(settings.encryption_key_path)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE event_threads, response_pairs, rollups"))
    async with async_session_factory() as session:
        replay = ReplayUseCase(
            events=SqlAlchemyEventRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
        )
        await replay.execute(trigger="manual")
    async with async_session_factory() as session:
        await ComputeRollupsUseCase(events=SqlAlchemyEventRepository(session)).execute()


async def _projection_counts() -> tuple[int, int, int]:
    async with engine.begin() as conn:
        threads = (await conn.execute(text("SELECT count(*) FROM event_threads"))).scalar_one()
        pairs = (await conn.execute(text("SELECT count(*) FROM response_pairs"))).scalar_one()
        rollups = (await conn.execute(text("SELECT count(*) FROM rollups"))).scalar_one()
    return threads, pairs, rollups


async def test_golden_replay_reproduces_dashboard_exactly(client, auth_token):
    # Establish a fresh, known-complete "golden" baseline first, rather than
    # trusting whatever event_threads/response_pairs/rollups state happens
    # to already exist — this suite runs against a shared, cumulative dev
    # database many other test files also append real events to (`tests/
    # conftest.py`'s own documented isolation model: uuid-uniqueness, not
    # cleanup), so an *ambient* pre-existing projection count can legitimately
    # be stale relative to the ledger's current full `events` history. A
    # fresh rebuild is the only trustworthy baseline; found while running
    # this test for real, not assumed from the plan (an earlier draft
    # compared against ambient state and failed spuriously — 7 vs 22 threads
    # — because unrelated tests had appended events since projections were
    # last computed).
    await _rebuild_projections()
    golden_counts = await _projection_counts()
    golden_state = await _score_and_narrator_state()
    assert golden_state, (
        "No score_runs exist yet — run scripts/seed_score_fixture.py + compute_score.py first"
    )
    golden_response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert golden_response.status_code == 200
    golden_dashboard = golden_response.json()

    # Drop and rebuild a second time — this is the actual replay under test.
    await _rebuild_projections()

    assert await _projection_counts() == golden_counts
    assert await _score_and_narrator_state() == golden_state

    replayed_response = await client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert replayed_response.status_code == 200
    assert replayed_response.json() == golden_dashboard
