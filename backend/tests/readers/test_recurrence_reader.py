"""REQ-M5-09 — Recurrence's clustering/decision logic, exercised through
`RecurrenceReader.interpret()` with a **faked** `EmbeddingPort` (fixed vectors
for known input strings, no live OpenAI call — `plan.md`'s Testing section).
Reproduces `data-model.md`'s worked shape (`fnd-2`: `magnitude = 0.33`, two-
event citation) and confirms an unrelated ticket with no genuinely related
prior occurrence produces no finding (Acceptance Scenario 4)."""

import uuid

import pytest

from app.readers.application.ports import (
    CandidateCorpusPort,
    EmbeddingPort,
    FindingRepositoryPort,
)
from app.readers.application.recurrence_reader import RecurrenceReader
from app.readers.domain.entities import CandidateTicket
from app.scoring.domain.entities import Finding


class _FakeCandidateCorpusPort(CandidateCorpusPort):
    def __init__(self, candidates: list[CandidateTicket]) -> None:
        self._candidates = candidates

    async def list_candidates(self) -> list[CandidateTicket]:
        return self._candidates


class _FakeEmbeddingPort(EmbeddingPort):
    """Fixed vectors keyed by title — no live OpenAI call."""

    def __init__(self, vectors_by_title: dict[str, list[float]]) -> None:
        self._vectors_by_title = vectors_by_title

    async def embed(self, text: str) -> list[float]:
        return self._vectors_by_title[text]


class _FakeFindingRepository(FindingRepositoryPort):
    def __init__(self) -> None:
        self.persisted: list[Finding] = []

    async def already_interpreted(
        self, *, reader_type: str, reader_version: str, event_id: uuid.UUID
    ) -> bool:
        return False

    async def persist(self, finding: Finding) -> None:
        self.persisted.append(finding)


async def test_fnd_2_matches_the_worked_shape():
    """Ticket #456's creation and reopening — textually identical titles, real
    embeddings would place them together. `magnitude = (2-1)/3.0 = 0.33`,
    citing both real events (`data-model.md`'s corrected two-event citation)."""
    created_event_id = uuid.uuid4()
    reopened_event_id = uuid.uuid4()
    title = "Slow API response"
    candidates = [
        CandidateTicket(event_id=created_event_id, ticket_number=456, title=title),
        CandidateTicket(event_id=reopened_event_id, ticket_number=456, title=title),
    ]
    reader = RecurrenceReader(
        candidates=_FakeCandidateCorpusPort(candidates),
        embeddings=_FakeEmbeddingPort({title: [1.0, 0.0, 0.0]}),
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert len(findings) == 1
    finding = findings[0]
    assert finding.finding_type == "recurring_issue"
    assert finding.magnitude == pytest.approx(0.33, abs=0.01)
    assert set(finding.cited_event_ids) == {created_event_id, reopened_event_id}


async def test_unrelated_ticket_with_no_related_occurrence_emits_nothing():
    """Acceptance Scenario 4 — two tickets whose embeddings are far apart (no
    genuinely related prior occurrence) never cluster, regardless of how
    HDBSCAN's density estimate treats such a small corpus (the
    `_RECURRENCE_MAX_PAIRWISE_DISTANCE` floor catches it either way)."""
    candidates = [
        CandidateTicket(event_id=uuid.uuid4(), ticket_number=456, title="Slow API response"),
        CandidateTicket(
            event_id=uuid.uuid4(),
            ticket_number=512,
            title="Login page displays wrong company logo",
        ),
    ]
    reader = RecurrenceReader(
        candidates=_FakeCandidateCorpusPort(candidates),
        embeddings=_FakeEmbeddingPort(
            {
                "Slow API response": [1.0, 0.0, 0.0],
                "Login page displays wrong company logo": [-1.0, 0.0, 0.0],
            }
        ),
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert findings == []


async def test_single_candidate_corpus_emits_nothing():
    """A cluster of size 1 cannot exist — below `interpret()`'s own early-exit
    floor, no embedding call is even made."""
    candidates = [
        CandidateTicket(event_id=uuid.uuid4(), ticket_number=512, title="Solo ticket")
    ]
    reader = RecurrenceReader(
        candidates=_FakeCandidateCorpusPort(candidates),
        embeddings=_FakeEmbeddingPort({}),
        findings=_FakeFindingRepository(),
    )

    findings = await reader.interpret()

    assert findings == []
