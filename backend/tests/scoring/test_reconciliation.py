import pytest


@pytest.mark.skip(
    reason=(
        "Decimal-reconciliation content lands in build-order Phase 4 (Score engine) — "
        "see tests/strategy.md. Placeholder only (spec.md User Story 3): scaffolds the "
        "CI job step and directory before the scoring engine exists to test."
    )
)
def test_score_contributions_reconcile_to_the_total() -> None:
    """Will assert SUM(score_contributions.points_contributed) reconciles to
    score_runs.total_negative_points / total_positive_points to full NUMERIC(10,3)
    precision, per tests/strategy.md §Decimal reconciliation tests (REQ-NFR-30)."""
