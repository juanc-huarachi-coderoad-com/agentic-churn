"""REQ-M5-14/FR-023 — `MeetingReader.interpret()` with a **faked**
`MeetingTranscriptRepositoryPort`/`LLMPort` (mirroring `test_intent_reader.py`'s
style, no live Anthropic call). FR-023's actual consent gate is proven at the
collection layer (`tests/unit/test_simulated_collector.py`'s
`test_unconsented_calendar_item_is_never_collected` and
`tests/ingestion/test_post_mvp_sources_real_db.py`) — by the time a transcript
reaches this reader, consent is a structural guarantee, not something this
reader re-checks (see `meeting_reader.py`'s own module docstring)."""

import uuid
from datetime import UTC, datetime
from typing import Any, TypeVar

from app.readers.application.meeting_reader import (
    ExtractedCommitment,
    MeetingModelOutput,
    MeetingReader,
)
from app.readers.application.ports import (
    FindingRepositoryPort,
    LLMPort,
    MeetingTranscriptRepositoryPort,
)
from app.readers.domain.entities import MeetingTranscriptInfo
from app.scoring.domain.entities import Finding

T = TypeVar("T")


class _FakeMeetingTranscriptRepository(MeetingTranscriptRepositoryPort):
    def __init__(self, transcripts: list[MeetingTranscriptInfo]) -> None:
        self._transcripts = transcripts

    async def list_all(self) -> list[MeetingTranscriptInfo]:
        return self._transcripts


class _FakeLLM(LLMPort):
    def __init__(self, response: Any) -> None:
        self._response = response
        self.call_count = 0

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        self.call_count += 1
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


def _transcript(text: str, stakeholder_id: uuid.UUID | None = None) -> MeetingTranscriptInfo:
    return MeetingTranscriptInfo(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(UTC),
        stakeholder_id=stakeholder_id or uuid.uuid4(),
        series_id="meridian-qbr",
        text=text,
    )


async def test_extracted_commitment_produces_a_finding():
    transcript = _transcript(
        "Diego: Understood — engineering will ship the reporting CSV export by next Friday."
    )
    llm = _FakeLLM(
        MeetingModelOutput(
            commitments=[
                ExtractedCommitment(
                    who="Diego",
                    what="ship the reporting CSV export",
                    by_when="next Friday",
                    source_segment="engineering will ship the reporting CSV export by next Friday",
                )
            ],
            confidence=0.8,
        )
    )

    reader = MeetingReader(
        transcripts=_FakeMeetingTranscriptRepository([transcript]),
        llm=llm,
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert len(findings) == 1
    finding = findings[0]
    assert finding.reader_type == "meeting"
    assert finding.finding_type == "meeting_commitment"
    assert finding.confidence == 0.8
    assert finding.cited_event_ids == (transcript.event_id,)
    assert finding.stakeholder_id == transcript.stakeholder_id
    assert finding.status == "pending_validation"


async def test_no_commitment_extracted_emits_nothing():
    transcript = _transcript("Diego: internal standup notes, nothing promised.")
    llm = _FakeLLM(MeetingModelOutput(commitments=[], confidence=0.9))

    reader = MeetingReader(
        transcripts=_FakeMeetingTranscriptRepository([transcript]),
        llm=llm,
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert findings == []


async def test_cached_event_is_never_reinterpreted():
    transcript = _transcript("Ana: We need the CSV export fix live before the board review.")
    llm = _FakeLLM(
        MeetingModelOutput(
            commitments=[ExtractedCommitment(who="Ana", what="x", by_when="y", source_segment="z")],
            confidence=0.8,
        )
    )

    reader = MeetingReader(
        transcripts=_FakeMeetingTranscriptRepository([transcript]),
        llm=llm,
        findings=_FakeFindingRepository(already_interpreted_ids={transcript.event_id}),
    )

    findings = await reader.interpret()

    assert findings == []
    assert llm.call_count == 0


async def test_missing_api_key_propagates_as_reader_level_failure():
    """Mirrors ToneReader/IntentReader's identical guard — a systemic
    misconfiguration must never look like an honest "nothing to report"
    abstention."""

    class _RaisingLLM(LLMPort):
        async def generate_structured(self, prompt: str, schema: type[T]) -> T:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

    transcript = _transcript("Ana: We need the CSV export fix live before the board review.")
    reader = MeetingReader(
        transcripts=_FakeMeetingTranscriptRepository([transcript]),
        llm=_RaisingLLM(),
        findings=_FakeFindingRepository(),
    )

    try:
        await reader.interpret()
        raise AssertionError("expected ValueError to propagate")
    except ValueError:
        pass
