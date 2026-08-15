"""REQ-M5-07 — Commitment's pure decision logic. `data-model.md`'s worked values
(`fnd-1`: magnitude=1.00/confidence=1.00; `fnd-9`: magnitude=0.50/confidence=1.00),
the 50%-threshold boundary for `commitment_met` (FR-005), and a `resolved` pair
that exceeded its threshold before resolving still emits `broken_response_promise`
(Acceptance Scenario 3)."""

import uuid

import pytest

from app.readers.domain.entities import ResponsePairInfo
from app.readers.domain.services import evaluate_commitment


def _pair(state: str, elapsed: float, threshold: float | None = 4.0) -> ResponsePairInfo:
    return ResponsePairInfo(
        client_event_id=uuid.uuid4(),
        state=state,
        business_hours_elapsed=elapsed,
        threshold_business_hours=threshold,
    )


def test_fnd_1_open_overdue_matches_the_worked_example():
    """19h elapsed vs 4h threshold — examples/01's own ticket #456 case."""
    result = evaluate_commitment(_pair("open_overdue", elapsed=19.0, threshold=4.0))

    assert result is not None
    assert result.finding_type == "broken_response_promise"
    assert result.magnitude == pytest.approx(1.00)
    assert result.confidence == pytest.approx(1.00)


def test_fnd_9_resolved_fast_matches_the_worked_example():
    """2h elapsed vs 4h threshold (50% exactly) — examples/01's ticket #398 case."""
    result = evaluate_commitment(_pair("resolved", elapsed=2.0, threshold=4.0))

    assert result is not None
    assert result.finding_type == "commitment_met"
    assert result.magnitude == pytest.approx(0.50)
    assert result.confidence == pytest.approx(1.00)


def test_commitment_met_boundary_is_inclusive_at_exactly_50_percent():
    result = evaluate_commitment(_pair("resolved", elapsed=2.0, threshold=4.0))
    assert result is not None
    assert result.finding_type == "commitment_met"


def test_commitment_met_does_not_fire_just_over_50_percent():
    result = evaluate_commitment(_pair("resolved", elapsed=2.01, threshold=4.0))
    assert result is None


def test_resolved_pair_that_exceeded_threshold_still_emits_broken_promise():
    """Acceptance Scenario 3 — a late-then-resolved response is a fact about what
    happened, not erased by the eventual resolution (Appendix A design commitment
    #9: unresolved problems never fade)."""
    result = evaluate_commitment(_pair("resolved", elapsed=6.0, threshold=4.0))

    assert result is not None
    assert result.finding_type == "broken_response_promise"
    assert result.magnitude == pytest.approx(0.5)  # overdue_ratio = (6-4)/4 = 0.5


def test_open_not_yet_overdue_emits_nothing():
    result = evaluate_commitment(_pair("open", elapsed=1.0, threshold=4.0))
    assert result is None


def test_resolved_between_50_and_100_percent_emits_nothing():
    """Met the promise, but not notable enough for a positive finding."""
    result = evaluate_commitment(_pair("resolved", elapsed=3.5, threshold=4.0))
    assert result is None


def test_no_threshold_configured_emits_nothing():
    """spec.md's Edge Cases — no matching commitment, no reasonable default to
    invent."""
    result = evaluate_commitment(_pair("open_overdue", elapsed=19.0, threshold=None))
    assert result is None


def test_extreme_overdue_ratio_saturates_at_one():
    result = evaluate_commitment(_pair("open_overdue", elapsed=1000.0, threshold=4.0))
    assert result is not None
    assert result.magnitude == pytest.approx(1.0)
