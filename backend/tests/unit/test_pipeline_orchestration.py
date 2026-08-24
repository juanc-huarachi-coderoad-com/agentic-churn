"""specs/026-automated-pipeline-orchestration — real-DB coverage for the one genuinely
new decision this feature adds to `app.worker`: the high-water-mark skip/run branch in
`_orchestrate_pipeline()` (`research.md` Decision 2). Everything downstream of that
branch (readers, score recompute, narration) is already covered by its own existing
test suite — this file does not re-test `RunReadersUseCase`/`RecomputeScoreUseCase`/
`NarrateScoreRunUseCase` internals, only that the new orchestration function calls them
in the right circumstances.

`app.worker._last_seen_event_at` is module-level, process-global state — each test
resets it via `monkeypatch` rather than relying on import order, so these tests stay
independent of whatever other test files or a prior worker run in the same process may
have already done (constitution, Full-Stack Engineering S4: "Test data MUST be
explicitly arranged... State MUST NOT leak between test cases").
"""

from datetime import timedelta

from sqlalchemy import text

import app.worker as worker
from app.db import async_session_factory
from app.ingestion.adapters.sqlalchemy_repositories import SqlAlchemyEventRepository
from app.ingestion.application.ports import NewEvent
from tests.conftest import ledger_floor


async def _append_one_event(make_envelope) -> None:
    async with async_session_factory() as session:
        occurred_at = await ledger_floor(session) + timedelta(seconds=1)
    envelope_id = await make_envelope(occurred_at)
    async with async_session_factory() as session:
        await SqlAlchemyEventRepository(session).append(
            NewEvent(envelope_id=envelope_id, event_type="message", occurred_at=occurred_at),
            data_key_ref="test-key",
        )


async def _new_event_score_run_count() -> int:
    async with async_session_factory() as session:
        return (
            await session.execute(
                text("SELECT COUNT(*) FROM score_runs WHERE trigger = 'new_event'")
            )
        ).scalar_one()


async def test_no_new_events_skips_the_pipeline(monkeypatch, make_envelope):
    monkeypatch.setattr(worker, "_last_seen_event_at", None)
    await _append_one_event(make_envelope)

    # First call: something new exists relative to a fresh (None) high-water-mark, so
    # this must run the full pipeline and establish the baseline for real.
    await worker._orchestrate_pipeline()
    assert worker._last_seen_event_at is not None
    before = await _new_event_score_run_count()

    # Second call, no new event appended in between: must be a pure no-op — the whole
    # point of research.md Decision 2 (constitution P6, FR-004).
    await worker._orchestrate_pipeline()
    after = await _new_event_score_run_count()

    assert after == before


async def test_a_new_event_triggers_the_full_pipeline(monkeypatch, make_envelope):
    monkeypatch.setattr(worker, "_last_seen_event_at", None)
    before = await _new_event_score_run_count()

    await _append_one_event(make_envelope)
    await worker._orchestrate_pipeline()

    after = await _new_event_score_run_count()
    # A new `score_runs` row with trigger='new_event' can only exist here if readers
    # ran first and RecomputeScoreUseCase ran after them without raising — proving
    # FR-001/FR-002/FR-003's run-and-ordering requirement by construction, not by
    # re-testing RunReadersUseCase/RecomputeScoreUseCase's own already-tested internals.
    assert after == before + 1
    assert worker._last_seen_event_at is not None
