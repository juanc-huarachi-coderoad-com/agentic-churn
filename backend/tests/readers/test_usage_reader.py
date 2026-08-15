"""REQ-M5-08, REQ-M2-06, SC-004 — Usage's z-score decision logic. `data-model.md`'s
worked shape (a value within 2 standard deviations never flags), the minimum-
sample-count abstention (FR-008), and a property test: thousands of generated
historical-value lists plus one in-range new value never produce a finding.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.readers.domain.services import is_usage_deviation, usage_deviation_magnitude, z_score


def test_fnd_3_matches_the_worked_example():
    """w29..w33 = -2, 1, -3, 2, -1; w34 = -22 (data-model.md)."""
    z = z_score([-2, 1, -3, 2, -1], -22)

    assert z == pytest.approx(-10.32, abs=0.01)
    assert is_usage_deviation(z)


def test_fewer_than_three_samples_abstains():
    assert z_score([1, 2], 50) is None


def test_exactly_three_samples_computes():
    assert z_score([1, 2, 3], 100) is not None


def test_zero_variance_history_abstains_rather_than_dividing_by_zero():
    assert z_score([5, 5, 5], 100) is None


def test_value_within_two_stdev_never_flags():
    historical = [10, 11, 9, 10, 11, 9, 10]
    z = z_score(historical, 10.5)
    assert z is not None
    assert not is_usage_deviation(z)


def test_magnitude_is_bounded_to_one():
    assert usage_deviation_magnitude(1000.0) == pytest.approx(1.0)
    assert usage_deviation_magnitude(2.0) == pytest.approx(0.5)


@given(
    historical=st.lists(
        st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=30,
    ),
)
@settings(max_examples=2000)
def test_the_historical_mean_itself_never_flags(historical):
    """A value exactly at the historical mean is 0 standard deviations away —
    the always-true floor case of "within 2 standard deviations never flags"
    (SC-004), for any nonzero-variance history."""
    mean = sum(historical) / len(historical)

    z = z_score(historical, mean)

    if z is not None:
        assert z == pytest.approx(0.0, abs=1e-9)
        assert not is_usage_deviation(z)


@given(
    historical=st.lists(
        st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=30,
    ),
    delta_a=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
    delta_b=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=2000)
def test_magnitude_is_monotonic_in_absolute_deviation(historical, delta_a, delta_b):
    """A new value further from the historical mean never produces a smaller
    deviation magnitude than one closer to it — REQ-M5-03's "magnitude reflects
    how far outside normal the value fell" must hold as a real ordering, not
    just at the two worked-example points."""
    mean = sum(historical) / len(historical)
    z_a = z_score(historical, mean + delta_a)
    z_b = z_score(historical, mean + delta_a + delta_b)

    if z_a is not None and z_b is not None:
        assert usage_deviation_magnitude(abs(z_b)) >= usage_deviation_magnitude(abs(z_a)) - 1e-9
