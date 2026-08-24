"""`RecordFeedbackVerdictUseCase` — all three ports faked (no DB), matching
`test_generate_draft_use_case.py`'s own fake-in-tests precedent. Covers
spec.md's User Story 1 acceptance scenarios 2 (Edge Cases: FR-005a
rejection, unknown finding/issue)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.context.application.ports import (
    FeedbackFindingReadPort,
    FeedbackVerdictRepositoryPort,
    IssueTopFindingReadPort,
)
from app.context.application.use_cases import (
    FindingNotFoundError,
    IssueNotFoundError,
    RecordFeedbackVerdictUseCase,
    VerdictRequiresFindingError,
)
from app.context.domain.entities import DampingWeight, FindingPatternComponents

_FINDING_ID = uuid4()
_ISSUE_ID = uuid4()
_SUBMITTED_BY = uuid4()
_PATTERN = "relationship+relationship_change"


class _FakeFindingReader(FeedbackFindingReadPort):
    def __init__(self, components: FindingPatternComponents | None) -> None:
        self._components = components

    async def get_pattern_components(self, finding_id: UUID) -> FindingPatternComponents | None:
        return self._components


class _FakeIssueReader(IssueTopFindingReadPort):
    def __init__(self, top_finding_id: UUID | None) -> None:
        self._top_finding_id = top_finding_id

    async def get_top_finding_id(self, issue_id: UUID) -> UUID | None:
        return self._top_finding_id


class _FakeVerdictRepository(FeedbackVerdictRepositoryPort):
    def __init__(self, initial: DampingWeight | None = None) -> None:
        self._row = initial
        self.recorded_calls: list[dict] = []

    async def get_damping(self, pattern_signature: str) -> DampingWeight:
        if self._row is not None:
            return self._row
        return DampingWeight(
            pattern_signature=pattern_signature,
            weight=1.0,
            false_alarm_count=0,
            resolved_count=0,
            correct_count=0,
            disclosure_text=None,
            last_updated_at=datetime.now(UTC),
        )

    async def record(self, *, finding_id, issue_id, verdict, submitted_by_user_id, updated) -> None:
        self.recorded_calls.append(
            {
                "finding_id": finding_id,
                "issue_id": issue_id,
                "verdict": verdict,
                "submitted_by_user_id": submitted_by_user_id,
                "updated": updated,
            }
        )
        self._row = updated


_DEFAULT_COMPONENTS = FindingPatternComponents(
    reader_type="relationship", finding_type="relationship_change"
)
_UNSET: FindingPatternComponents | None = FindingPatternComponents(
    reader_type="__unset__", finding_type="__unset__"
)


def _use_case(
    *,
    components: FindingPatternComponents | None = _UNSET,
    top_finding_id: UUID | None = None,
    verdicts: _FakeVerdictRepository | None = None,
) -> tuple[RecordFeedbackVerdictUseCase, _FakeVerdictRepository]:
    repo = verdicts or _FakeVerdictRepository()
    resolved_components = _DEFAULT_COMPONENTS if components is _UNSET else components
    use_case = RecordFeedbackVerdictUseCase(
        findings=_FakeFindingReader(resolved_components),
        issues=_FakeIssueReader(top_finding_id),
        verdicts=repo,
    )
    return use_case, repo


@pytest.mark.asyncio
async def test_one_false_alarm_yields_weight_0500() -> None:
    use_case, repo = _use_case()
    await use_case.execute(
        finding_id=_FINDING_ID, issue_id=None, verdict="false_alarm",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    assert repo.recorded_calls[-1]["updated"].weight == pytest.approx(0.500)


@pytest.mark.asyncio
async def test_second_false_alarm_yields_weight_0250() -> None:
    use_case, repo = _use_case()
    await use_case.execute(
        finding_id=_FINDING_ID, issue_id=None, verdict="false_alarm",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    await use_case.execute(
        finding_id=_FINDING_ID, issue_id=None, verdict="false_alarm",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    assert repo.recorded_calls[-1]["updated"].weight == pytest.approx(0.250)
    assert repo.recorded_calls[-1]["updated"].false_alarm_count == 2


@pytest.mark.asyncio
async def test_false_alarm_with_only_issue_id_raises_verdict_requires_finding() -> None:
    use_case, _ = _use_case()
    with pytest.raises(VerdictRequiresFindingError):
        await use_case.execute(
            finding_id=None, issue_id=_ISSUE_ID, verdict="false_alarm",
            submitted_by_user_id=_SUBMITTED_BY,
        )


@pytest.mark.asyncio
async def test_correct_with_only_issue_id_raises_verdict_requires_finding() -> None:
    use_case, _ = _use_case()
    with pytest.raises(VerdictRequiresFindingError):
        await use_case.execute(
            finding_id=None, issue_id=_ISSUE_ID, verdict="correct",
            submitted_by_user_id=_SUBMITTED_BY,
        )


@pytest.mark.asyncio
async def test_unknown_finding_id_raises_finding_not_found() -> None:
    use_case, _ = _use_case(components=None)
    with pytest.raises(FindingNotFoundError):
        await use_case.execute(
            finding_id=_FINDING_ID, issue_id=None, verdict="false_alarm",
            submitted_by_user_id=_SUBMITTED_BY,
        )


@pytest.mark.asyncio
async def test_finding_less_issue_id_raises_issue_not_found() -> None:
    use_case, _ = _use_case(top_finding_id=None)
    with pytest.raises(IssueNotFoundError):
        await use_case.execute(
            finding_id=None, issue_id=_ISSUE_ID, verdict="resolved",
            submitted_by_user_id=_SUBMITTED_BY,
        )


@pytest.mark.asyncio
async def test_resolved_verdict_scoped_to_issue_resolves_via_top_ranked_finding() -> None:
    use_case, repo = _use_case(top_finding_id=_FINDING_ID)
    await use_case.execute(
        finding_id=None, issue_id=_ISSUE_ID, verdict="resolved",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    call = repo.recorded_calls[-1]
    assert call["finding_id"] is None
    assert call["issue_id"] == _ISSUE_ID
    assert call["updated"].resolved_count == 1
    assert call["updated"].weight == 1.0


# ---------------------------------------------------------------------------
# User Story 3 — correct/resolved behave distinctly from false_alarm
# (REQ-M6-CAL-03a/b). RecordFeedbackVerdictUseCase already handles all three
# verdict types generically (built in User Story 1) — these tests prove
# that behavior, they don't exercise any new production code.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_false_alarms_then_one_correct_recovers_to_02875() -> None:
    use_case, repo = _use_case()
    for _ in range(2):
        await use_case.execute(
            finding_id=_FINDING_ID, issue_id=None, verdict="false_alarm",
            submitted_by_user_id=_SUBMITTED_BY,
        )
    await use_case.execute(
        finding_id=_FINDING_ID, issue_id=None, verdict="correct",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    updated = repo.recorded_calls[-1]["updated"]
    assert updated.weight == pytest.approx(0.2875)
    assert updated.false_alarm_count == 2
    assert updated.correct_count == 1


@pytest.mark.asyncio
async def test_resolved_verdict_on_fresh_pattern_leaves_weight_at_one() -> None:
    use_case, repo = _use_case()
    await use_case.execute(
        finding_id=_FINDING_ID, issue_id=None, verdict="resolved",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    updated = repo.recorded_calls[-1]["updated"]
    assert updated.resolved_count == 1
    assert updated.weight == 1.0
    assert updated.false_alarm_count == 0
    assert updated.correct_count == 0


@pytest.mark.asyncio
async def test_resolved_verdict_on_already_damped_pattern_leaves_weight_unchanged() -> None:
    use_case, repo = _use_case()
    await use_case.execute(
        finding_id=_FINDING_ID, issue_id=None, verdict="false_alarm",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    weight_after_false_alarm = repo.recorded_calls[-1]["updated"].weight

    await use_case.execute(
        finding_id=_FINDING_ID, issue_id=None, verdict="resolved",
        submitted_by_user_id=_SUBMITTED_BY,
    )
    updated = repo.recorded_calls[-1]["updated"]
    assert updated.weight == weight_after_false_alarm
    assert updated.false_alarm_count == 1
    assert updated.correct_count == 0
    assert updated.resolved_count == 1
