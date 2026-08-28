"""REQ-M6-01, REQ-M6-13..16, FR-012 — per-finding weight formula, the 25%-of-negative
positive cap, the saturating points->score conversion, and `stakes`'s new pinned
constants (`spec.md`'s 2026-08-14 clarification)."""

from datetime import date

import pytest

from app.scoring.domain.services import FindingWeightInputs, ScoringCalculator, compute_stakes


def test_fnd_1_matches_the_worked_example():
    """20 x 1.0 x 1.5 x 1.00 x 1.00 x 1.30 (open_overdue ageing) x 1.0 (damping) x
    1.0 (1st in issue) = 39.00 (data-model.md, examples/01 §9.2)."""
    calculator = ScoringCalculator()
    inputs = FindingWeightInputs(
        base=20,
        influence=1.0,
        criticality=1.5,
        confidence=1.00,
        magnitude=1.00,
        recency=1.30,
        damping=1.0,
        rank_within_issue_factor=1.0,
    )

    assert calculator.compute_points(inputs) == pytest.approx(39.00)


def test_fnd_7_matches_the_worked_example():
    """14 x 1.6 (Ana's sponsor multiplier) x 1.0 x 0.85 x 0.50 x 1.0 x 1.0 x 1.0 =
    9.52 (data-model.md, examples/01 §9.3)."""
    calculator = ScoringCalculator()
    inputs = FindingWeightInputs(
        base=14,
        influence=1.6,
        criticality=1.0,
        confidence=0.85,
        magnitude=0.50,
        recency=1.0,
        damping=1.0,
        rank_within_issue_factor=1.0,
    )

    assert calculator.compute_points(inputs) == pytest.approx(9.52)


def test_default_multipliers_are_neutral_when_unresolved():
    """spec.md's Edge Case: a finding whose product area/stakeholder doesn't
    resolve, or whose profile has no first_response commitment, defaults
    influence/criticality to 1.0 — the formula needs no special case for this,
    since 1.0 is already the multiplicative identity."""
    calculator = ScoringCalculator()
    inputs = FindingWeightInputs(
        base=10,
        influence=1.0,
        criticality=1.0,
        confidence=0.80,
        magnitude=0.50,
        recency=1.0,
        damping=1.0,
        rank_within_issue_factor=1.0,
    )

    assert calculator.compute_points(inputs) == pytest.approx(10 * 0.80 * 0.50)


def test_positive_cap_applies_in_full_when_under_the_ceiling():
    calculator = ScoringCalculator()

    applied = calculator.apply_positive_cap(
        total_negative_points=68.04, total_positive_points=4.00
    )

    assert applied == pytest.approx(4.00)


def test_positive_cap_clamps_when_it_would_exceed_25_percent_of_negative():
    calculator = ScoringCalculator()

    applied = calculator.apply_positive_cap(
        total_negative_points=10.0, total_positive_points=5.0
    )

    assert applied == pytest.approx(2.5)


def test_points_to_score_matches_the_worked_example():
    calculator = ScoringCalculator()

    score = calculator.points_to_score(64.04)

    assert score == pytest.approx(85.64, abs=0.01)


def test_score_never_reaches_100():
    """`total_points=1_000_000` underflows `e^(-total_points/33)` to exactly 0.0 in
    float64 — the pathological case that would otherwise silently produce
    `score == 100.0` exactly, violating REQ-M6-16 and score_runs.score's DB CHECK.
    99.99 is the largest value the NUMERIC(5,2) column can represent below 100."""
    calculator = ScoringCalculator()

    score = calculator.points_to_score(1_000_000.0)

    assert score < 100.0
    assert score == pytest.approx(99.99, abs=1e-9)


def test_score_approaches_100_smoothly_for_large_but_representable_points():
    """A large total_points, safely below the 99.995 boundary where
    `points_to_score`'s own NUMERIC(5,2)-rounding safeguard kicks in (raw values from
    there round up to 100.00 at insert and fail `score_runs.score`'s CHECK —
    specs/030-real-warehouse-connector, first surfaced once `ComputeRollupsUseCase`
    started feeding the Usage reader real data), keeps its real sub-100 precision —
    proves points_to_score's saturation is genuine asymptotic behavior, not just the
    99.99 clamp applying everywhere above some threshold. (total_points=1000.0, used
    here previously, actually lands at raw≈99.999999999993 — inside the clamp zone —
    so it no longer demonstrates unclamped behavior; 200.0 does.)"""
    calculator = ScoringCalculator()

    score = calculator.points_to_score(200.0)

    assert score < 99.995
    assert score == pytest.approx(99.7667, abs=0.001)


def test_stakes_worked_check_for_meridian():
    """contract_value_band=strategic -> 1.5; renewal in ~86 days ->
    clamp(2.0 - 86/90, 0.5, 2.0) ~= 1.044; stakes ~= 1.567 (data-model.md — a new
    worked check this feature introduces, no prior calibration existed)."""
    stakes = compute_stakes(
        contract_value_band="strategic",
        renewal_date=date(2026, 11, 8),
        as_of=date(2026, 8, 14),
    )

    assert stakes == pytest.approx(1.567, abs=0.01)


def test_stakes_clamps_at_the_floor_and_ceiling():
    far_future = compute_stakes(
        contract_value_band="smb", renewal_date=date(2030, 1, 1), as_of=date(2026, 1, 1)
    )
    assert far_future == pytest.approx(0.6 * 0.5)

    overdue = compute_stakes(
        contract_value_band="smb", renewal_date=date(2026, 1, 1), as_of=date(2026, 6, 1)
    )
    assert overdue == pytest.approx(0.6 * 2.0)
