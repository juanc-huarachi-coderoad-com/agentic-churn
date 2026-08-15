"""REQ-M5-10 — Absence's pure decision logic. `data-model.md`'s worked shape
(`fnd-4`: `confidence = 0.85`), and confirms no finding is emitted when no
`absence`-type event exists (Acceptance Scenario 2 — tested at the reader level
via an empty port, not the pure function, since the function itself has nothing
to abstain from)."""

import pytest

from app.readers.domain.services import absence_confidence, absence_magnitude


def test_confidence_is_fixed_at_0_85():
    assert absence_confidence() == pytest.approx(0.85)


def test_no_prior_contact_ever_is_maximally_severe():
    assert absence_magnitude(silence_days=None, cadence_days=7) == pytest.approx(1.0)


def test_magnitude_scales_with_missed_cadence_periods():
    """Exactly one cadence period of silence (7 days silent, 7-day cadence) is a
    mild signal — half of the 2x-cadence severity floor."""
    magnitude = absence_magnitude(silence_days=7, cadence_days=7)
    assert magnitude == pytest.approx(0.5)


def test_magnitude_saturates_at_one():
    magnitude = absence_magnitude(silence_days=100, cadence_days=7)
    assert magnitude == pytest.approx(1.0)


def test_zero_cadence_days_is_treated_as_maximally_severe():
    """Defensive floor — a zero-length cadence window shouldn't divide by zero."""
    assert absence_magnitude(silence_days=5, cadence_days=0) == pytest.approx(1.0)
