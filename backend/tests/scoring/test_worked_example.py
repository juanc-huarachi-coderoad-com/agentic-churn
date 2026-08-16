"""T021, FR-012, REQ-M6-P1..P4, SC-006 — reproduces `examples/01-end-to-end-
walkthrough.md` §9's worked example end to end against a real database: the
"checkpoint" spec §16 Phase 4's own framing exists to prove. Runs the real
pipeline — `scripts/run_collector.py`'s collection+replay, `scripts/
seed_score_fixture.py`'s fixture insertion (real MVP events, a real absence event, a
real hash-chained synthetic CSAT event) — then `RecomputeScoreUseCase`, pinning
`as_of` to the exact reference points `examples/01` §9's own narrative bakes in
(ticket #456's "we took 19 hours to respond... we promised 4" and ticket #398's
same-day fast resolution), so every `score_contributions` row and `score_runs` total
reproduces the worked example's mathematically exact numbers to the decimal
(`data-model.md`'s own table pre-rounds `rank_within_issue_factor` to 2 decimals
before multiplying for display purposes — this test asserts against full-precision
arithmetic instead, since that is what a correct implementation actually produces;
see `_EXPECTED_POINTS` below for the exact figures and how they reconcile to
`data-model.md`'s rounded ones). Runs twice consecutively to reach `band_history`'s
confirmed `consecutive_runs_in_band = 2` state (`data-model.md`'s note that this
fixture's worked example is not its own first run), then a third time against the
same unchanged finding state to prove determinism (SC-006) directly —
`score_contributions` must match the second run's, row for row, not just an equal
final score.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory, engine
from app.ingestion.adapters.encryption import FernetEncryption
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import ReplayUseCase
from app.scoring.adapters.sqlalchemy_repository import (
    SqlAlchemyClientProfileMultipliers,
    SqlAlchemyCoverageCheck,
    SqlAlchemyDampingRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyScoreRunRepository,
)
from app.scoring.application.use_cases import RecomputeScoreUseCase
from scripts.run_collector import run as run_collector
from scripts.seed_score_fixture import seed as seed_score_fixture

_BOGOTA = ZoneInfo("America/Bogota")

# examples/01 §9's own narrative fact ("we took 19 hours to respond to ticket #456;
# we promised 4") pinned as the replay's `as_of` — reproduces ticket #456's
# open_overdue business_hours_elapsed=19.0 (threshold=4h -> overdue_ratio=3.75 ->
# recency=1.30) exactly, rather than drifting with real wall-clock time.
# business_hours_elapsed is computed once at replay time and stored in
# response_pairs, not re-derived at scoring time (app/ingestion/domain/
# business_hours.py's docstring), so this only needs pinning here, once.
_REPLAY_AS_OF = datetime(2026, 8, 11, 17, 0, tzinfo=_BOGOTA)

# Ticket #398 resolved at exactly this instant ("resolved fast") — pinning the score
# recompute's `as_of` to that same instant makes fnd-9's resolved half-life fade
# reproduce recency=1.00 exactly (0 days since resolution).
_SCORE_AS_OF = datetime(2026, 8, 11, 13, 2, tzinfo=_BOGOTA)

_RESET_TABLES = (
    "score_contributions",
    "band_history",
    "score_runs",
    "finding_issue_map",
    # validation_failures/quarantine must clear before findings — both carry
    # a FK to findings.id (quarantine.finding_id UNIQUE, REQ-M5A-03), and
    # feature 007's ValidationGate is the first real writer of either table.
    # Never populated before this feature, so this FK dependency never
    # actually fired against a real row until now (found during this
    # feature's own verification, not by inspection).
    "validation_failures",
    "quarantine",
    "findings",
    "issues",
)

# finding_type is unique per finding in demo/fixtures/score-engine-findings.json, so
# it doubles as this test's lookup key. Values are the mathematically exact
# base*influence*criticality*confidence*magnitude*recency*rank_factor products (rank
# factors as real 0.6**n powers, e.g. fnd-8's exact 0.216 and fnd-5's exact 0.1296) —
# data-model.md's own table pre-rounds rank_factor to 2 decimals for display (e.g.
# "0.22", "0.13") before multiplying, which is a presentation rounding in that
# document, not what a full-precision implementation (this one) actually computes;
# using the doc's rounded figures here would make this test fail against genuinely
# correct code. Issue A: 39.00 + 6.6825 + 2.916 = 48.5985. Issue B: 9.52 + 5.1408 +
# 2.7648 + 1.6416 + 0.3483648 = 19.4155648. total_negative_points = 68.0140648.
_EXPECTED_POINTS = {
    "broken_response_promise": 39.0,  # fnd-1, Issue A 1st
    "usage_deviation": 6.6825,  # fnd-3, Issue A 2nd
    "recurring_issue": 2.916,  # fnd-2, Issue A 3rd
    "escalation_language": 9.52,  # fnd-7, Issue B 1st
    "contact_absence": 5.1408,  # fnd-4, Issue B 2nd
    "tone_deterioration": 2.7648,  # fnd-6, Issue B 3rd
    "csat_deviation": 1.6416,  # fnd-8, Issue B 4th
    "relationship_change": 0.3483648,  # fnd-5, Issue B 5th
    "commitment_met": 4.0,  # fnd-9, standalone positive
}

# score_contributions columns are NUMERIC(8,3)/NUMERIC(10,3) — Postgres rounds each
# stored value to 3 decimals on insert, so a tolerance tighter than that would fail
# against genuinely correct, persisted data.
_DECIMAL3 = 0.0006
_TOTAL_NEGATIVE_POINTS = 68.0140648
_TOTAL_POINTS = 64.0140648
_SCORE = 85.627


async def _reset_scoring_state() -> None:
    """This test is the only writer of findings/issues/score_* rows in the suite (the
    fixture-seeded proof-case scope boundary, spec.md) — a full wipe-and-reseed is
    safe and gives the clean, zero-prior-runs state the worked example assumes. Never
    touches events/raw_envelopes/etc., which stay append-only at the DB level
    (tests/conftest.py's contract)."""
    async with engine.begin() as conn:
        for table in _RESET_TABLES:
            await conn.execute(text(f"DELETE FROM {table}"))


async def _pin_response_pairs(as_of: datetime) -> None:
    encryption = FernetEncryption(settings.encryption_key_path)
    async with async_session_factory() as session:
        replay = ReplayUseCase(
            events=SqlAlchemyEventRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
        )
        await replay.execute(trigger="manual", as_of=as_of)


async def _recompute(as_of: datetime):
    async with async_session_factory() as session:
        use_case = RecomputeScoreUseCase(
            findings=SqlAlchemyFindingRepository(session),
            score_runs=SqlAlchemyScoreRunRepository(session),
            profile=SqlAlchemyClientProfileMultipliers(session),
            damping=SqlAlchemyDampingRepository(session),
            coverage=SqlAlchemyCoverageCheck(session),
        )
        return await use_case.execute(trigger="manual", as_of=as_of)


async def _contributions_by_finding_type(score_run_id) -> dict[str, dict]:
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT f.finding_type, sc.base, sc.influence, sc.criticality, "
                    "sc.confidence, sc.magnitude, sc.recency, sc.damping, "
                    "sc.rank_within_issue_factor, sc.points_contributed, sc.is_positive "
                    "FROM score_contributions sc "
                    "JOIN findings f ON f.id = sc.finding_id "
                    "WHERE sc.score_run_id = :run_id"
                ),
                {"run_id": score_run_id},
            )
        ).all()
    return {
        r.finding_type: {
            "base": float(r.base),
            "influence": float(r.influence),
            "criticality": float(r.criticality),
            "confidence": float(r.confidence),
            "magnitude": float(r.magnitude),
            "recency": float(r.recency),
            "damping": float(r.damping),
            "rank_within_issue_factor": float(r.rank_within_issue_factor),
            "points_contributed": float(r.points_contributed),
            "is_positive": r.is_positive,
        }
        for r in rows
    }


async def test_worked_example_reproduces_examples_01_section_9():
    await _reset_scoring_state()

    await run_collector("simulated")
    await _pin_response_pairs(_REPLAY_AS_OF)
    await seed_score_fixture()

    await _recompute(_SCORE_AS_OF)
    run_2 = await _recompute(_SCORE_AS_OF)

    assert run_2.raw_band == "at_risk"
    assert run_2.band == "at_risk"
    assert run_2.total_negative_points == pytest.approx(_TOTAL_NEGATIVE_POINTS, abs=_DECIMAL3)
    assert run_2.total_positive_points == pytest.approx(4.00, abs=_DECIMAL3)
    assert run_2.positive_points_applied == pytest.approx(4.00, abs=_DECIMAL3)
    assert run_2.total_points == pytest.approx(_TOTAL_POINTS, abs=_DECIMAL3)
    assert run_2.score == pytest.approx(_SCORE, abs=0.01)

    async with async_session_factory() as session:
        band_history_row = (
            await session.execute(
                text(
                    "SELECT band, consecutive_runs_in_band FROM band_history "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).one()
    assert band_history_row.band == "at_risk"
    assert band_history_row.consecutive_runs_in_band == 2

    contributions = await _contributions_by_finding_type(run_2.id)
    assert set(contributions) == set(_EXPECTED_POINTS)
    for finding_type, expected_points in _EXPECTED_POINTS.items():
        assert contributions[finding_type]["points_contributed"] == pytest.approx(
            expected_points, abs=_DECIMAL3
        ), finding_type

    assert contributions["broken_response_promise"]["recency"] == pytest.approx(
        1.30, abs=0.005
    )
    assert contributions["commitment_met"]["recency"] == pytest.approx(1.00, abs=0.005)
    assert contributions["commitment_met"]["is_positive"] is True
    for finding_type in _EXPECTED_POINTS:
        if finding_type not in ("broken_response_promise", "commitment_met"):
            assert contributions[finding_type]["recency"] == pytest.approx(1.00, abs=0.005)

    # SC-006 — determinism: a third run against the same unchanged finding state
    # reproduces score_contributions row for row, not just an equal final score.
    run_3 = await _recompute(_SCORE_AS_OF)
    contributions_3 = await _contributions_by_finding_type(run_3.id)
    assert contributions_3 == contributions
    assert run_3.score == pytest.approx(run_2.score, abs=1e-9)
    assert run_3.band == run_2.band
