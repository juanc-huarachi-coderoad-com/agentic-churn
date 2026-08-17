"""Pure unit test for `UpdateFindingTypeWeightUseCase` (specs/011-production-
hardening, User Story 4) — `FindingTypeConfigWritePort` and `RecomputeScoreUseCase`
both faked, no DB."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.scoring.application.ports import FindingTypeConfigChangeResult
from app.scoring.application.use_cases import InvalidWeightError, UpdateFindingTypeWeightUseCase


class _FakeFindingTypeConfigWriter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float]] = []

    async def update_base_points(self, finding_type, new_base_points, changed_by_user_id):
        self.calls.append((finding_type, new_base_points))
        return FindingTypeConfigChangeResult(
            change_id=uuid4(),
            new_config_version="v-fake",
            changed_at=datetime.now(UTC),
        )


class _FakeRecomputeScoreUseCase:
    def __init__(self) -> None:
        self.triggers: list[str] = []

    async def execute(self, *, trigger: str, as_of=None):
        self.triggers.append(trigger)
        return None


async def test_valid_update_calls_writer_then_triggers_weight_edit_replay():
    writer = _FakeFindingTypeConfigWriter()
    recompute = _FakeRecomputeScoreUseCase()
    use_case = UpdateFindingTypeWeightUseCase(
        finding_type_config=writer,  # type: ignore[arg-type]
        recompute_score=recompute,  # type: ignore[arg-type]
    )

    result = await use_case.execute(
        finding_type="broken_response_promise",
        new_base_points=25.0,
        changed_by_user_id=uuid4(),
    )

    assert writer.calls == [("broken_response_promise", 25.0)]
    assert recompute.triggers == ["weight_edit_replay"]
    assert result.new_config_version == "v-fake"


async def test_negative_weight_raises_without_calling_the_writer():
    writer = _FakeFindingTypeConfigWriter()
    recompute = _FakeRecomputeScoreUseCase()
    use_case = UpdateFindingTypeWeightUseCase(
        finding_type_config=writer,  # type: ignore[arg-type]
        recompute_score=recompute,  # type: ignore[arg-type]
    )

    with pytest.raises(InvalidWeightError):
        await use_case.execute(
            finding_type="broken_response_promise",
            new_base_points=-1.0,
            changed_by_user_id=uuid4(),
        )

    assert writer.calls == []
    assert recompute.triggers == []
