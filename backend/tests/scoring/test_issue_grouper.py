"""REQ-M6-06..08 — one general ranking algorithm (raw points descending, recency
excluded), no fixture-specific exception. Reproduces `data-model.md`'s corrected
Issue A/B worked numbers, which superseded `examples/01` §9.2's own published rank
order (found during `/speckit-analyze`, `research.md`'s Decision) — this test is
exactly what proves the correction is real, general arithmetic, not a special case."""

import uuid

import pytest

from app.scoring.domain.services import IssueGrouper, RawFindingWeight


def _weight(raw_points: float) -> RawFindingWeight:
    return RawFindingWeight(finding_id=uuid.uuid4(), raw_points=raw_points)


def test_issue_a_ranks_by_raw_points_descending_not_the_published_narrative_order():
    """fnd-1=30.00, fnd-3=11.1375, fnd-2=8.10 -> fnd-1 1st, fnd-3 2nd, fnd-2 3rd
    (data-model.md) — the correct general rule, not examples/01 §9.2's published
    fnd-2-then-fnd-3 order, which doesn't match its own stated ranking rule."""
    grouper = IssueGrouper()
    fnd_1, fnd_2, fnd_3 = _weight(30.00), _weight(8.10), _weight(11.1375)

    ranked = grouper.rank_within_issue([fnd_1, fnd_2, fnd_3])
    by_id = {r.finding_id: r for r in ranked}

    assert by_id[fnd_1.finding_id].rank == 1
    assert by_id[fnd_1.finding_id].rank_factor == pytest.approx(1.00)
    assert by_id[fnd_3.finding_id].rank == 2
    assert by_id[fnd_3.finding_id].rank_factor == pytest.approx(0.60)
    assert by_id[fnd_2.finding_id].rank == 3
    assert by_id[fnd_2.finding_id].rank_factor == pytest.approx(0.36)


def test_issue_b_five_findings_rank_order_and_diminishing_factors():
    """fnd-7=9.52, fnd-4=8.568, fnd-6=7.68, fnd-8=7.6, fnd-5=2.688 (data-model.md) —
    raw points already descend in this exact order, so no correction needed here."""
    grouper = IssueGrouper()
    fnd_7, fnd_4, fnd_6, fnd_8, fnd_5 = (
        _weight(9.52),
        _weight(8.568),
        _weight(7.68),
        _weight(7.6),
        _weight(2.688),
    )

    ranked = grouper.rank_within_issue([fnd_7, fnd_4, fnd_6, fnd_8, fnd_5])
    by_id = {r.finding_id: r for r in ranked}

    assert [by_id[w.finding_id].rank for w in (fnd_7, fnd_4, fnd_6, fnd_8, fnd_5)] == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert by_id[fnd_5.finding_id].rank_factor == pytest.approx(0.6**4)


def test_single_finding_issue_ranks_first_at_full_weight():
    grouper = IssueGrouper()
    only = _weight(10.0)

    ranked = grouper.rank_within_issue([only])

    assert len(ranked) == 1
    assert ranked[0].rank == 1
    assert ranked[0].rank_factor == pytest.approx(1.0)
