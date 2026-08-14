import pytest


@pytest.mark.skip(
    reason=(
        "Monotonicity content lands in build-order Phase 4 (Score engine) — see "
        "tests/strategy.md. Placeholder only (spec.md User Story 3): scaffolds the CI "
        "job step and directory before the scoring engine exists to test."
    )
)
def test_adding_a_negative_finding_never_lowers_the_score() -> None:
    """Will be a hypothesis property test: for thousands of generated valid
    score_runs states, adding one more validated negative finding and recomputing must
    never produce a lower score, per tests/strategy.md §Monotonicity tests (REQ-NFR-31)."""
