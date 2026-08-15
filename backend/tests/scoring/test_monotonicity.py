"""REQ-NFR-31, REQ-M6-P4 — fills in the skipped placeholder (feature 001) for real:
adding any single validated negative finding to an existing, valid scoring state
must never produce a lower score. Property-based (`hypothesis`), thousands of
generated cases, against the real domain services directly (no database) — the same
approach as `test_reconciliation.py`, and exactly the kind of bug a single
hand-picked example (the worked example alone) would likely miss.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.scoring.domain.services import FindingWeightInputs, ScoringCalculator

_finding_strategy = st.fixed_dictionaries(
    {
        "base": st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
        "influence": st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
        "criticality": st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
        "confidence": st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        "magnitude": st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        "recency": st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
        "damping": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        "rank_within_issue_factor": st.floats(min_value=0.05, max_value=1.0, allow_nan=False),
        "is_positive": st.booleans(),
    }
)

_negative_finding_strategy = st.fixed_dictionaries(
    {
        "base": st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
        "influence": st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
        "criticality": st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
        "confidence": st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        "magnitude": st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        "recency": st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
        "damping": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        "rank_within_issue_factor": st.floats(min_value=0.05, max_value=1.0, allow_nan=False),
    }
)


def _compute_score(findings: list[dict]) -> float:
    calculator = ScoringCalculator()
    total_negative = 0.0
    total_positive = 0.0
    for f in findings:
        points = calculator.compute_points(
            FindingWeightInputs(
                base=f["base"],
                influence=f["influence"],
                criticality=f["criticality"],
                confidence=f["confidence"],
                magnitude=f["magnitude"],
                recency=f["recency"],
                damping=f["damping"],
                rank_within_issue_factor=f["rank_within_issue_factor"],
            )
        )
        if f["is_positive"]:
            total_positive += points
        else:
            total_negative += points
    positive_applied = calculator.apply_positive_cap(
        total_negative_points=total_negative, total_positive_points=total_positive
    )
    total_points = total_negative - positive_applied
    return calculator.points_to_score(total_points)


@given(
    existing=st.lists(_finding_strategy, min_size=0, max_size=25),
    new_negative=_negative_finding_strategy,
)
@settings(max_examples=3000)
def test_adding_a_negative_finding_never_lowers_the_score(existing, new_negative):
    score_before = _compute_score(existing)

    new_finding = {**new_negative, "is_positive": False}
    score_after = _compute_score([*existing, new_finding])

    assert score_after >= score_before - 1e-9
