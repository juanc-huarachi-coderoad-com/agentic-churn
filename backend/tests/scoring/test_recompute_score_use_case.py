"""T027 — REQ-M6-20..26, REQ-M6-P2 — `RecomputeScoreUseCase` orchestration behavior:
the three real triggers this feature wires (`manual`, `hourly_heartbeat`,
`profile_edit_replay`) all persist correctly, the source-degraded freeze path (REQ-
M6-26) copies the prior run forward without touching `band_history`, and — the F5
remediation — the previous score is never read as an input to a fresh computation
(REQ-M6-20/P2: "recomputed entirely from zero every time"). Uses zero-to-few
findings, not the full worked-example fixture — this file is about trigger/freeze
plumbing, not per-finding arithmetic (that's test_worked_example.py's job).
"""

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db import async_session_factory, engine
from app.scoring.adapters.sqlalchemy_repository import (
    SqlAlchemyClientProfileMultipliers,
    SqlAlchemyCoverageCheck,
    SqlAlchemyDampingRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyScoreRunRepository,
)
from app.scoring.application.use_cases import RecomputeScoreUseCase

_RESET_TABLES = ("score_contributions", "band_history", "score_runs")


async def _reset_score_runs() -> None:
    """This file never touches findings/issues (it runs against whatever validated
    findings already exist, typically none in a freshly seeded DB) — only wipes the
    run-history tables it itself needs a clean slate for."""
    async with engine.begin() as conn:
        for table in _RESET_TABLES:
            await conn.execute(text(f"DELETE FROM {table}"))


async def _recompute(trigger: str):
    async with async_session_factory() as session:
        use_case = RecomputeScoreUseCase(
            findings=SqlAlchemyFindingRepository(session),
            score_runs=SqlAlchemyScoreRunRepository(session),
            profile=SqlAlchemyClientProfileMultipliers(session),
            damping=SqlAlchemyDampingRepository(session),
            coverage=SqlAlchemyCoverageCheck(session),
        )
        return await use_case.execute(trigger=trigger)


async def _insert_degraded_coverage_report() -> None:
    """A coverage_reports row with sources_read < sources_expected — the real
    condition SqlAlchemyCoverageCheck.is_degraded() queries for (REQ-M6-26), not a
    stub. Needs its own collector_runs row for the FK, same minimal bookkeeping
    tests/conftest.py's make_envelope fixture uses."""
    async with engine.begin() as conn:
        source = (
            await conn.execute(text("SELECT id FROM sources WHERE source_type = 'gmail' LIMIT 1"))
        ).one()
        run_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO collector_runs (id, source_id, trigger, window_start, window_end) "
                "VALUES (:id, :source_id, 'manual'::collector_trigger, now(), now())"
            ),
            {"id": run_id, "source_id": source.id},
        )
        await conn.execute(
            text(
                "INSERT INTO coverage_reports "
                "(id, collector_run_id, sources_expected, sources_read, gap_reason, complete_to) "
                "VALUES (:id, :run_id, 3, 1, 'zendesk source failed', now())"
            ),
            {"id": uuid4(), "run_id": run_id},
        )


async def _insert_healthy_coverage_report() -> None:
    async with engine.begin() as conn:
        source = (
            await conn.execute(text("SELECT id FROM sources WHERE source_type = 'gmail' LIMIT 1"))
        ).one()
        run_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO collector_runs (id, source_id, trigger, window_start, window_end) "
                "VALUES (:id, :source_id, 'manual'::collector_trigger, now(), now())"
            ),
            {"id": run_id, "source_id": source.id},
        )
        await conn.execute(
            text(
                "INSERT INTO coverage_reports "
                "(id, collector_run_id, sources_expected, sources_read, gap_reason, complete_to) "
                "VALUES (:id, :run_id, 3, 3, NULL, now())"
            ),
            {"id": uuid4(), "run_id": run_id},
        )


@pytest.mark.parametrize("trigger", ["manual", "hourly_heartbeat", "profile_edit_replay"])
async def test_each_real_trigger_persists_its_own_trigger_value(trigger):
    """REQ-M6-25/REQ-M2-07/REQ-M3-06 — the three triggers this feature actually
    wires (a manual script, worker.py's hourly heartbeat, and
    SubmitProfileUseCase's post-replay call) all reach RecomputeScoreUseCase and
    persist their own trigger label, not a hardcoded one."""
    await _reset_score_runs()
    await _insert_healthy_coverage_report()

    run = await _recompute(trigger)

    assert run.trigger == trigger
    assert run.is_frozen is False

    async with async_session_factory() as session:
        row = (
            await session.execute(
                text("SELECT trigger FROM score_runs WHERE id = :id"), {"id": run.id}
            )
        ).one()
    assert row.trigger == trigger


async def test_source_degraded_freezes_the_prior_run_without_touching_band_history():
    """REQ-M6-26, REQ-NFR-32 — a degraded source freezes the score at its last real
    value rather than computing on an incomplete picture, and band_history is
    untouched (nothing new was learned about band stability from a frozen run)."""
    await _reset_score_runs()
    await _insert_healthy_coverage_report()
    healthy_run = await _recompute("manual")

    async with async_session_factory() as session:
        band_history_count_before = (
            await session.execute(text("SELECT count(*) AS n FROM band_history"))
        ).one().n

    await _insert_degraded_coverage_report()
    frozen_run = await _recompute("hourly_heartbeat")

    assert frozen_run.is_frozen is True
    assert frozen_run.source_degraded is True
    assert frozen_run.trigger == "hourly_heartbeat"
    # abs tolerances account for score_runs' NUMERIC(5,2)/NUMERIC(10,3) DB rounding —
    # frozen_run.score/total_points are copied from healthy_run's in-memory (full
    # float precision) value, then round-tripped through the DB on persist.
    assert frozen_run.score == pytest.approx(healthy_run.score, abs=0.01)
    assert frozen_run.band == healthy_run.band
    assert frozen_run.total_points == pytest.approx(healthy_run.total_points, abs=0.001)

    async with async_session_factory() as session:
        contributions_count = (
            await session.execute(
                text(
                    "SELECT count(*) AS n FROM score_contributions WHERE score_run_id = :id"
                ),
                {"id": frozen_run.id},
            )
        ).one().n
        band_history_count_after = (
            await session.execute(text("SELECT count(*) AS n FROM band_history"))
        ).one().n

    assert contributions_count == 0
    assert band_history_count_after == band_history_count_before


async def test_degraded_with_no_prior_run_computes_fresh_marked_degraded():
    """spec.md's Edge Case: the very first run ever, with a degraded source, has
    nothing to freeze at — it computes normally but stays marked degraded for
    visibility rather than silently pretending coverage was complete."""
    await _reset_score_runs()
    await _insert_degraded_coverage_report()

    run = await _recompute("manual")

    assert run.is_frozen is False
    assert run.source_degraded is True


async def test_previous_score_is_never_read_as_an_input_to_a_fresh_computation():
    """F5 remediation, REQ-M6-20/REQ-M6-P2 ("recomputed entirely from zero every
    time") — corrupt the prior score_runs.score directly in the database, then
    recompute against the same unchanged findings/profile/damping state. If the
    prior score were ever read as an input, the corrupted value would leak into the
    new computation; since RecomputeScoreUseCase.get_latest_score_run() is only
    consulted for `.band` (the displayed-band hysteresis input) and the freeze path,
    a healthy (non-degraded) recompute must reproduce the same score regardless of
    what the prior row's `.score` column holds."""
    await _reset_score_runs()
    await _insert_healthy_coverage_report()
    first_run = await _recompute("manual")

    async with async_session_factory() as session:
        await session.execute(
            text("UPDATE score_runs SET score = 0.0 WHERE id = :id"), {"id": first_run.id}
        )
        await session.commit()

    await _insert_healthy_coverage_report()
    second_run = await _recompute("manual")

    assert second_run.score == pytest.approx(first_run.score)
