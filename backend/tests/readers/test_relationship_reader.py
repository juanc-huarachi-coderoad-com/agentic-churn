"""REQ-M5-11 — Relationship's pure decision logic. `data-model.md`'s worked
value (`fnd-5`: `magnitude = 0.50`, `confidence = 0.70`)."""

import pytest

from app.readers.domain.services import relationship_change_finding


def test_fnd_5_matches_the_worked_example():
    magnitude, confidence = relationship_change_finding()

    assert magnitude == pytest.approx(0.50)
    assert confidence == pytest.approx(0.70)


def test_values_are_fixed_not_derived():
    """Called twice, always the same — a deliberate, honest fixed pair for this
    reader's reduced-strength signal (`research.md`'s Decision), not a formula
    that could vary."""
    first = relationship_change_finding()
    second = relationship_change_finding()

    assert first == second
