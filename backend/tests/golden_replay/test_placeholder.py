import pytest


@pytest.mark.skip(
    reason=(
        "Golden-replay content lands in build-order Phase 4 (Score engine) — see "
        "tests/strategy.md. This placeholder exists so the CI job step and directory "
        "structure are wired in before there is anything real to run (spec.md User "
        "Story 3), rather than being built from scratch once Phase 4 starts."
    )
)
def test_golden_replay_reproduces_dashboard_exactly() -> None:
    """Will assert byte-identical dashboard state after dropping and replaying
    projections, per tests/strategy.md §Golden-replay tests (REQ-NFR-09/28)."""
