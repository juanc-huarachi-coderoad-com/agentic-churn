"""REQ-M6-09..12, REQ-M6-CAL-01/02 — recency computed purely from a finding's
lifecycle state, independent of every other finding."""

from datetime import UTC, datetime, timedelta

import pytest

from app.scoring.application.ports import FindingLifecycle
from app.scoring.domain.services import AgeingCalculator

_AS_OF = datetime(2026, 8, 14, tzinfo=UTC)


def test_open_finding_never_fades():
    calculator = AgeingCalculator()
    lifecycle = FindingLifecycle(
        state="open", business_hours_elapsed=None, threshold_business_hours=None, resolved_at=None
    )

    assert calculator.compute_recency(
        lifecycle, half_life_days=14, as_of=_AS_OF
    ) == pytest.approx(1.0)
    assert calculator.compute_recency(
        lifecycle, half_life_days=14, as_of=_AS_OF + timedelta(days=365)
    ) == pytest.approx(1.0)


def test_resolved_finding_fades_by_half_life():
    calculator = AgeingCalculator()
    half_life_days = 14.0
    resolved_at = _AS_OF - timedelta(days=half_life_days)
    lifecycle = FindingLifecycle(
        state="resolved",
        business_hours_elapsed=None,
        threshold_business_hours=None,
        resolved_at=resolved_at,
    )

    assert calculator.compute_recency(
        lifecycle, half_life_days=half_life_days, as_of=_AS_OF
    ) == pytest.approx(0.5)

    resolved_at_two_half_lives = _AS_OF - timedelta(days=2 * half_life_days)
    lifecycle_two = FindingLifecycle(
        state="resolved",
        business_hours_elapsed=None,
        threshold_business_hours=None,
        resolved_at=resolved_at_two_half_lives,
    )
    assert calculator.compute_recency(
        lifecycle_two, half_life_days=half_life_days, as_of=_AS_OF
    ) == pytest.approx(0.25)


def test_ticket_456_open_overdue_matches_worked_example():
    """19 elapsed business hours against a 4-hour threshold ->
    min(1.0 + 0.08 * ((19-4)/4), 2.0) = 1.30 (data-model.md, examples/01 §9.2)."""
    calculator = AgeingCalculator()
    lifecycle = FindingLifecycle(
        state="open_overdue",
        business_hours_elapsed=19.0,
        threshold_business_hours=4.0,
        resolved_at=None,
    )

    recency = calculator.compute_recency(lifecycle, half_life_days=None, as_of=_AS_OF)

    assert recency == pytest.approx(1.30)


def test_open_overdue_ageing_never_exceeds_the_cap():
    calculator = AgeingCalculator()
    lifecycle = FindingLifecycle(
        state="open_overdue",
        business_hours_elapsed=10_000.0,
        threshold_business_hours=4.0,
        resolved_at=None,
    )

    recency = calculator.compute_recency(lifecycle, half_life_days=None, as_of=_AS_OF)

    assert recency == pytest.approx(2.0)
