"""REQ-M5A-01..04 — the M5a validation gate's four checks, exercised through
`ValidationGate.evaluate()` with **faked** `FindingTypeConfigPort`/
`EventExistencePort` (pure, no live DB). Covers spec.md's User Story 3
acceptance scenarios, using hand-constructed `Finding` values — no dependency
on `ToneReader`/`IntentReader` existing (spec.md's own Independent Test)."""

import uuid

from app.readers.application.ports import EventExistencePort, FindingTypeConfigPort
from app.readers.application.validation_gate import ValidationGate
from app.scoring.domain.entities import Finding

_CONFIGURED_TYPE = "tone_deterioration"
_CONFIDENCE_FLOOR = 0.65
_MIN_EVIDENCE_COUNT = 3


class _FakeFindingTypeConfigRepository(FindingTypeConfigPort):
    def __init__(self, thresholds_by_type: dict[str, tuple[float, int]]) -> None:
        self._thresholds_by_type = thresholds_by_type

    async def get_thresholds(self, finding_type: str) -> tuple[float, int] | None:
        return self._thresholds_by_type.get(finding_type)


class _FakeEventExistenceRepository(EventExistencePort):
    def __init__(self, existing_ids: set[uuid.UUID]) -> None:
        self._existing_ids = existing_ids

    async def existing_ids(self, ids: list[uuid.UUID]) -> set[uuid.UUID]:
        return {i for i in ids if i in self._existing_ids}


def _make_finding(
    *,
    finding_type: str = _CONFIGURED_TYPE,
    magnitude: float = 0.6,
    confidence: float = 0.8,
    cited_event_ids: tuple[uuid.UUID, ...] = (),
) -> Finding:
    return Finding(
        id=uuid.uuid4(),
        reader_type="tone",
        reader_version="v1",
        finding_type=finding_type,
        magnitude=magnitude,
        confidence=confidence,
        cited_event_ids=cited_event_ids,
        stakeholder_id=None,
        product_area_id=None,
        status="pending_validation",
        state=None,
        is_positive=False,
    )


def _default_gate(existing_ids: set[uuid.UUID]) -> ValidationGate:
    return ValidationGate(
        finding_type_config=_FakeFindingTypeConfigRepository(
            {_CONFIGURED_TYPE: (_CONFIDENCE_FLOOR, _MIN_EVIDENCE_COUNT)}
        ),
        event_existence=_FakeEventExistenceRepository(existing_ids),
    )


async def test_a_finding_passing_all_four_checks_is_validated():
    """Acceptance Scenario 5."""
    event_ids = tuple(uuid.uuid4() for _ in range(_MIN_EVIDENCE_COUNT))
    finding = _make_finding(confidence=0.9, cited_event_ids=event_ids)
    gate = _default_gate(existing_ids=set(event_ids))

    result = await gate.evaluate(finding)

    assert result.passed is True
    assert result.failed_checks == ()


async def test_unconfigured_finding_type_is_schema_invalid_not_an_exception():
    """The `thresholds is None` path (`research.md` Decision 6.1) — never
    raises."""
    finding = _make_finding(finding_type="not_a_real_type", cited_event_ids=(uuid.uuid4(),))
    gate = _default_gate(existing_ids=set(finding.cited_event_ids))

    result = await gate.evaluate(finding)

    assert result.passed is False
    assert [c.check_name for c in result.failed_checks] == ["schema_invalid"]


async def test_out_of_range_magnitude_is_schema_invalid():
    finding = _make_finding(magnitude=1.5, cited_event_ids=(uuid.uuid4(),))
    gate = _default_gate(existing_ids=set(finding.cited_event_ids))

    result = await gate.evaluate(finding)

    assert result.passed is False
    assert any(c.check_name == "schema_invalid" for c in result.failed_checks)


async def test_cited_event_that_does_not_exist_is_quarantined():
    real_id = uuid.uuid4()
    fake_id = uuid.uuid4()
    finding = _make_finding(
        cited_event_ids=(real_id, real_id, fake_id)  # 3 citations, clears min-evidence
    )
    gate = _default_gate(existing_ids={real_id})  # fake_id never resolves to a real row

    result = await gate.evaluate(finding)

    assert result.passed is False
    assert [c.check_name for c in result.failed_checks] == ["cited_event_missing"]


async def test_too_few_cited_events_is_insufficient_evidence():
    event_ids = (uuid.uuid4(),)  # below _MIN_EVIDENCE_COUNT of 3
    finding = _make_finding(cited_event_ids=event_ids)
    gate = _default_gate(existing_ids=set(event_ids))

    result = await gate.evaluate(finding)

    assert result.passed is False
    assert [c.check_name for c in result.failed_checks] == ["insufficient_evidence"]


async def test_confidence_below_floor_is_quarantined():
    """Reproduces `examples/01-end-to-end-walkthrough.md` §7's `fnd-10`/`q-1`
    (`0.55 < 0.65`)."""
    event_ids = tuple(uuid.uuid4() for _ in range(_MIN_EVIDENCE_COUNT))
    finding = _make_finding(confidence=0.55, cited_event_ids=event_ids)
    gate = _default_gate(existing_ids=set(event_ids))

    result = await gate.evaluate(finding)

    assert result.passed is False
    assert [c.check_name for c in result.failed_checks] == ["confidence_below_floor"]
    assert result.failed_checks[0].actual == "0.55"


async def test_confidence_exactly_equal_to_the_floor_passes():
    """`spec.md`'s Edge Cases — the floor is inclusive."""
    event_ids = tuple(uuid.uuid4() for _ in range(_MIN_EVIDENCE_COUNT))
    finding = _make_finding(confidence=_CONFIDENCE_FLOOR, cited_event_ids=event_ids)
    gate = _default_gate(existing_ids=set(event_ids))

    result = await gate.evaluate(finding)

    assert result.passed is True


async def test_a_finding_failing_two_checks_at_once_produces_two_entries():
    """Acceptance Scenario 3 — each failed check is its own entry, not
    collapsed to a single label."""
    event_ids = (uuid.uuid4(),)  # below min-evidence AND ...
    finding = _make_finding(confidence=0.1, cited_event_ids=event_ids)  # ... below floor
    gate = _default_gate(existing_ids=set(event_ids))

    result = await gate.evaluate(finding)

    assert result.passed is False
    assert {c.check_name for c in result.failed_checks} == {
        "insufficient_evidence",
        "confidence_below_floor",
    }
    assert len(result.failed_checks) == 2
