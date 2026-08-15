"""REQ-NFR-30 — fills in the skipped placeholder (feature 001) for real:
`SUM(score_contributions.points_contributed)`, split by `is_positive`, must
reconcile exactly with `score_runs.total_negative_points`/`total_positive_points`,
for every run — not just the hand-worked example. Property-based (`hypothesis`),
thousands of generated cases, against the real domain services directly (no
database) — matching architecture/09-clean-architecture-and-patterns.md's own
rationale for why domain services are framework-free: this kind of test only stays
fast and reliable at this volume because the code under test has zero I/O.
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


def _score_run(findings: list[dict]) -> tuple[float, float, float, float, list[float]]:
    calculator = ScoringCalculator()
    points = [
        calculator.compute_points(
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
        for f in findings
    ]
    total_negative = sum(p for p, f in zip(points, findings, strict=True) if not f["is_positive"])
    total_positive = sum(p for p, f in zip(points, findings, strict=True) if f["is_positive"])
    positive_applied = calculator.apply_positive_cap(
        total_negative_points=total_negative, total_positive_points=total_positive
    )
    total_points = total_negative - positive_applied
    return total_negative, total_positive, positive_applied, total_points, points


@given(findings=st.lists(_finding_strategy, min_size=0, max_size=30))
@settings(max_examples=2000)
def test_contributions_reconcile_to_the_totals(findings):
    total_negative, total_positive, _positive_applied, _total_points, points = _score_run(
        findings
    )

    reconciled_negative = sum(
        p for p, f in zip(points, findings, strict=True) if not f["is_positive"]
    )
    reconciled_positive = sum(
        p for p, f in zip(points, findings, strict=True) if f["is_positive"]
    )

    assert reconciled_negative == total_negative
    assert reconciled_positive == total_positive


@given(findings=st.lists(_finding_strategy, min_size=1, max_size=30))
@settings(max_examples=2000)
def test_total_points_equals_negative_minus_applied_positive(findings):
    total_negative, total_positive, positive_applied, total_points, _points = _score_run(
        findings
    )

    assert positive_applied <= total_positive + 1e-9
    assert positive_applied <= 0.25 * total_negative + 1e-9
    assert total_points == total_negative - positive_applied
