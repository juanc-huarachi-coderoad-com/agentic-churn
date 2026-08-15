"""REQ-M6-17..19, REQ-M6-CAL-07 — hysteresis (65 enter / 55 exit for `at_risk`) and
2-consecutive-run stickiness for any band change."""

from app.scoring.domain.services import BandClassifier


def test_first_ever_run_displays_raw_band_immediately():
    classifier = BandClassifier()

    result = classifier.classify(
        78.0, prior_displayed_band=None, prior_qualifying_band=None, prior_qualifying_streak=0
    )

    assert result.raw_band == "at_risk"
    assert result.displayed_band == "at_risk"
    assert result.consecutive_runs_in_band == 1


def test_new_candidate_band_does_not_display_until_second_confirming_run():
    classifier = BandClassifier()

    # Run A: score newly crosses 65 for the first time, coming from `watch`.
    run_a = classifier.classify(
        70.0,
        prior_displayed_band="watch",
        prior_qualifying_band="watch",
        prior_qualifying_streak=5,
    )
    assert run_a.raw_band == "at_risk"
    assert run_a.displayed_band == "watch", "not confirmed yet — REQ-M6-19"
    assert run_a.consecutive_runs_in_band == 1

    # Run B: the same qualifying band holds a second consecutive time -> confirmed.
    run_b = classifier.classify(
        78.0,
        prior_displayed_band="watch",
        prior_qualifying_band=run_a.qualifying_band,
        prior_qualifying_streak=run_a.consecutive_runs_in_band,
    )
    assert run_b.displayed_band == "at_risk"
    assert run_b.consecutive_runs_in_band == 2


def test_sequences_06_worked_example_week_1_stays_at_risk():
    """sequences/06-state-band-hysteresis.md's own worked example: week 0 = 78
    (already-confirmed at_risk), week 1 = 61 — below the 65 entry threshold but
    above the 55 exit floor, so the display stays at_risk."""
    classifier = BandClassifier()

    week_1 = classifier.classify(
        61.0,
        prior_displayed_band="at_risk",
        prior_qualifying_band="at_risk",
        prior_qualifying_streak=2,
    )

    assert week_1.raw_band == "watch"
    assert week_1.displayed_band == "at_risk", "61 > 55 exit floor — stays at_risk"
    assert week_1.consecutive_runs_in_band == 3


def test_at_risk_exits_only_below_the_55_floor():
    classifier = BandClassifier()

    result = classifier.classify(
        50.0,
        prior_displayed_band="at_risk",
        prior_qualifying_band="at_risk",
        prior_qualifying_streak=4,
    )
    assert result.raw_band == "watch"
    # Below 55 -> no longer qualifies for at_risk -> new candidate starts its own streak.
    assert result.qualifying_band == "watch"
    assert result.displayed_band == "at_risk", "needs a second confirming run to exit"
    assert result.consecutive_runs_in_band == 1
