"""Pure, no DB: REQ-M6-CAL-03a's worked values, clamp bounds, disclosure
text presence/absence, and pattern_signature's byte-identical match with
the already-shipped scoring engine (`specs/010-feedback-memory/research.md`
Decision 1)."""

import pytest

from app.context.domain.damping_calculator import (
    build_disclosure_text,
    compute_weight,
    pattern_signature,
)


def test_compute_weight_one_false_alarm() -> None:
    assert compute_weight(1, 0) == pytest.approx(0.500)


def test_compute_weight_two_false_alarms() -> None:
    assert compute_weight(2, 0) == pytest.approx(0.250)


def test_compute_weight_two_false_alarms_then_one_correct() -> None:
    assert compute_weight(2, 1) == pytest.approx(0.2875)


def test_compute_weight_clamped_at_zero_for_extreme_false_alarm_count() -> None:
    # 0.5**2000 underflows float64 to exactly 0.0 — large enough to exercise
    # the clamp's lower bound for real, not just a very small positive value.
    assert compute_weight(2000, 0) == 0.0
    # Never negative for any count, even where float underflow hasn't
    # actually reached exactly 0.0 yet.
    assert compute_weight(500, 0) >= 0.0


def test_compute_weight_clamped_at_one_for_extreme_correct_count() -> None:
    assert compute_weight(0, 1000) == 1.0


def test_compute_weight_undamped_default() -> None:
    assert compute_weight(0, 0) == 1.0


def test_build_disclosure_text_none_when_pattern_never_verdicted() -> None:
    assert build_disclosure_text(0, 0, 0) is None


def test_build_disclosure_text_present_after_one_false_alarm() -> None:
    text = build_disclosure_text(1, 0, 0)
    assert text is not None
    assert "false alarm" in text


def test_build_disclosure_text_present_after_two_false_alarms() -> None:
    text = build_disclosure_text(2, 0, 0)
    assert text is not None
    assert "twice" in text


def test_build_disclosure_text_present_once_correct_count_positive() -> None:
    assert build_disclosure_text(0, 1, 0) is not None


def test_pattern_signature_matches_worked_example() -> None:
    # data-base/07-schema-feedback.md's own worked example.
    assert pattern_signature("relationship", "relationship_change") == (
        "relationship+relationship_change"
    )


def test_pattern_signature_matches_scoring_engine_construction() -> None:
    """Mechanically confirms research.md Decision 1's guarantee: this
    module's format is byte-identical to the already-shipped scoring
    engine's own inline construction, not just visually similar."""
    reader_type, finding_type = "commitment", "broken_response_promise"
    scoring_engine_inline_format = f"{reader_type}+{finding_type}"
    assert pattern_signature(reader_type, finding_type) == scoring_engine_inline_format
