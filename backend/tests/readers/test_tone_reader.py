"""REQ-M5-06/REQ-M5-12/REQ-M6-CAL-04 — the Tone reader's baseline-relative
judgment, exercised through `ToneReader.interpret()` with a **faked**
`LLMPort` (fixed structured responses, no live Anthropic call). Covers
spec.md's User Story 1 acceptance scenarios 1-5, using the synthetic
fixtures `tests/fixtures/tone_baseline_sufficient.json`/
`tone_low_confidence.json` — the real Meridian fixture is deliberately too
small to clear REQ-M6-CAL-04's 5-message floor."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar

import pytest

from app.readers.application.ports import (
    ConfirmedBaselineRepositoryPort,
    FindingRepositoryPort,
    LLMPort,
    MessageEventRepositoryPort,
)
from app.readers.application.tone_reader import ToneModelOutput, ToneReader
from app.readers.domain.entities import ConfirmedBaselineWindow, MessageEventInfo
from app.scoring.domain.entities import Finding

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

T = TypeVar("T")


class _FakeMessageEventRepository(MessageEventRepositoryPort):
    def __init__(self, messages: list[MessageEventInfo]) -> None:
        self._messages = messages

    async def list_all(self) -> list[MessageEventInfo]:
        return self._messages


class _FakeConfirmedBaselineRepository(ConfirmedBaselineRepositoryPort):
    def __init__(self, windows: dict[uuid.UUID, ConfirmedBaselineWindow]) -> None:
        self._windows = windows

    async def get_confirmed_window(
        self, stakeholder_id: uuid.UUID
    ) -> ConfirmedBaselineWindow | None:
        return self._windows.get(stakeholder_id)


class _FakeLLM(LLMPort):
    """Fixed structured response — no live Anthropic call. Records every
    call's `schema` argument so tests can assert the closed-schema contract."""

    def __init__(self, response: Any) -> None:
        self._response = response
        self.calls: list[type[Any]] = []
        self.call_count = 0

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        self.call_count += 1
        self.calls.append(schema)
        return self._response


class _FakeFindingRepository(FindingRepositoryPort):
    def __init__(self, already_interpreted_ids: set[uuid.UUID] | None = None) -> None:
        self.persisted: list[Finding] = []
        self._already_interpreted_ids = already_interpreted_ids or set()

    async def already_interpreted(
        self, *, reader_type: str, reader_version: str, event_id: uuid.UUID
    ) -> bool:
        return event_id in self._already_interpreted_ids

    async def persist(self, finding: Finding) -> None:
        self.persisted.append(finding)


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES_DIR / name).read_text())


def _build_baseline_and_message(
    fixture: dict[str, Any],
) -> tuple[ConfirmedBaselineWindow, MessageEventInfo]:
    stakeholder_id = uuid.UUID(fixture["stakeholder_id"])
    window_end = datetime.now(UTC) - timedelta(days=1)
    baseline = ConfirmedBaselineWindow(
        stakeholder_id=stakeholder_id,
        window_start=window_end - timedelta(days=30),
        window_end=window_end,
        sample_texts=tuple(fixture["baseline_sample_texts"]),
    )
    message = MessageEventInfo(
        event_id=uuid.uuid4(),
        occurred_at=window_end + timedelta(hours=1),
        stakeholder_id=stakeholder_id,
        text=fixture["new_message_text"],
    )
    return baseline, message


async def test_emits_finding_when_baseline_sufficient_and_message_deviates():
    """Acceptance Scenario 1 — separate magnitude/confidence, citing the
    triggering event."""
    fixture = _load_fixture("tone_baseline_sufficient.json")
    baseline, message = _build_baseline_and_message(fixture)
    response = ToneModelOutput(**fixture["model_response"])
    llm = _FakeLLM(response)

    reader = ToneReader(
        messages=_FakeMessageEventRepository([message]),
        baselines=_FakeConfirmedBaselineRepository({baseline.stakeholder_id: baseline}),
        llm=llm,
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert len(findings) == 1
    finding = findings[0]
    assert finding.reader_type == "tone"
    assert finding.finding_type == "tone_deterioration"
    assert finding.magnitude == pytest.approx(response.magnitude)
    assert finding.confidence == pytest.approx(response.confidence)
    assert finding.cited_event_ids == (message.event_id,)
    assert finding.stakeholder_id == baseline.stakeholder_id
    assert finding.status == "pending_validation"


async def test_abstains_below_five_samples_without_calling_the_model():
    """Acceptance Scenario 2 — REQ-M5-04/REQ-M6-CAL-04, "no history, no
    opinion." The fake LLM must never be invoked."""
    stakeholder_id = uuid.uuid4()
    window_end = datetime.now(UTC) - timedelta(days=1)
    baseline = ConfirmedBaselineWindow(
        stakeholder_id=stakeholder_id,
        window_start=window_end - timedelta(days=30),
        window_end=window_end,
        sample_texts=("Only one prior message.",),
    )
    message = MessageEventInfo(
        event_id=uuid.uuid4(),
        occurred_at=window_end + timedelta(hours=1),
        stakeholder_id=stakeholder_id,
        text="Something new.",
    )
    llm = _FakeLLM(ToneModelOutput(deviation=0.9, magnitude=0.9, confidence=0.9))

    reader = ToneReader(
        messages=_FakeMessageEventRepository([message]),
        baselines=_FakeConfirmedBaselineRepository({stakeholder_id: baseline}),
        llm=llm,
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert findings == []
    assert llm.call_count == 0


async def test_no_finding_when_message_reads_consistent_with_baseline():
    """Acceptance Scenario 3 — the model itself judges zero deviation."""
    fixture = _load_fixture("tone_baseline_sufficient.json")
    baseline, message = _build_baseline_and_message(fixture)
    llm = _FakeLLM(ToneModelOutput(deviation=0.05, magnitude=0.0, confidence=0.5))

    reader = ToneReader(
        messages=_FakeMessageEventRepository([message]),
        baselines=_FakeConfirmedBaselineRepository({baseline.stakeholder_id: baseline}),
        llm=llm,
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert findings == []


async def test_model_call_uses_the_closed_structured_schema():
    """Acceptance Scenario 4 — `generate_structured` is always called with
    `ToneModelOutput`, never a free-form prompt-only path."""
    fixture = _load_fixture("tone_baseline_sufficient.json")
    baseline, message = _build_baseline_and_message(fixture)
    llm = _FakeLLM(ToneModelOutput(**fixture["model_response"]))

    reader = ToneReader(
        messages=_FakeMessageEventRepository([message]),
        baselines=_FakeConfirmedBaselineRepository({baseline.stakeholder_id: baseline}),
        llm=llm,
        findings=_FakeFindingRepository(),
    )

    await reader.interpret()

    assert llm.calls == [ToneModelOutput]


async def test_cached_event_is_never_reinterpreted():
    """Acceptance Scenario 5 / SC-005 — re-interpreting an already-cached
    event triggers zero additional model calls."""
    fixture = _load_fixture("tone_baseline_sufficient.json")
    baseline, message = _build_baseline_and_message(fixture)
    llm = _FakeLLM(ToneModelOutput(**fixture["model_response"]))

    reader = ToneReader(
        messages=_FakeMessageEventRepository([message]),
        baselines=_FakeConfirmedBaselineRepository({baseline.stakeholder_id: baseline}),
        llm=llm,
        findings=_FakeFindingRepository(already_interpreted_ids={message.event_id}),
    )

    findings = await reader.interpret()

    assert findings == []
    assert llm.call_count == 0
