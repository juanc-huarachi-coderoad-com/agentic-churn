"""REQ-M6-05, REQ-M6-CAL-03a — `clamp(0.5^false_alarm_count × 1.15^correct_count, 0,
1.0)`, matching `examples/01-end-to-end-walkthrough.md` §14's exact worked checks.
`resolved` verdicts never affect `weight` (REQ-M6-CAL-03b) — they're tracked in
`resolved_count` only, which this formula doesn't take as an input at all."""

import pytest

from app.scoring.domain.services import DampingCalculator


def test_one_false_alarm_halves_the_weight():
    calculator = DampingCalculator()

    weight = calculator.compute_weight(false_alarm_count=1, correct_count=0)

    assert weight == pytest.approx(0.500)


def test_second_false_alarm_on_the_same_pattern():
    calculator = DampingCalculator()

    weight = calculator.compute_weight(false_alarm_count=2, correct_count=0)

    assert weight == pytest.approx(0.250)


def test_a_correct_verdict_partially_recovers_trust():
    """Two false alarms then one correct call: 0.5^2 * 1.15^1 = 0.2875 — never fully
    forgiven back to 1.0 by a single correct call after two false alarms (the
    intended asymmetry: losing trust is faster than regaining it)."""
    calculator = DampingCalculator()

    weight = calculator.compute_weight(false_alarm_count=2, correct_count=1)

    assert weight == pytest.approx(0.2875)


def test_weight_never_exceeds_one():
    calculator = DampingCalculator()

    weight = calculator.compute_weight(false_alarm_count=0, correct_count=10)

    assert weight == pytest.approx(1.0)


def test_no_verdicts_yet_is_the_undamped_default():
    calculator = DampingCalculator()

    weight = calculator.compute_weight(false_alarm_count=0, correct_count=0)

    assert weight == pytest.approx(1.0)
