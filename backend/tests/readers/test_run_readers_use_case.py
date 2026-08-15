"""SC-001/SC-002/SC-003, FR-014a — real-DB integration test: `RunReadersUseCase`
against the real, already-ingested Meridian ledger (`quickstart.md`'s
prerequisite: `scripts/run_collector.py --source simulated` has already run).
Reproduces `data-model.md`'s full worked-example table, confirms the REQ-M5-15
cache makes a re-run idempotent, confirms every finding's citation resolves to a
real event, and confirms Recurrence's own failure never blocks the other four
readers (2026-08-14 clarification).

`RecurrenceReader` here is wired to a **faked** `EmbeddingPort` for the
reproduction test — no live OpenAI call in the test suite (`plan.md`'s Testing
section) — and to the real `OpenAIEmbeddingAdapter` with an empty key for the
isolation test, which fails inside `embed()` with no network call at all
(`app.readers.adapters.openai_embedding`'s deferred-validation design).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory
from app.ingestion.adapters.encryption import FernetEncryption
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyCommitmentLookup,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import DetectAbsenceUseCase
from app.readers.adapters.openai_embedding import OpenAIEmbeddingAdapter
from app.readers.adapters.sqlalchemy_repository import (
    SqlAlchemyAbsenceEventRepository,
    SqlAlchemyCandidateCorpusRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyRelationshipContext,
    SqlAlchemyResponsePairRepository,
    SqlAlchemyRollupRepository,
)
from app.readers.application.absence_reader import AbsenceReader
from app.readers.application.commitment_reader import CommitmentReader
from app.readers.application.ports import CandidateCorpusPort, EmbeddingPort
from app.readers.application.recurrence_reader import RecurrenceReader
from app.readers.application.relationship_reader import RelationshipReader
from app.readers.application.usage_reader import UsageReader
from app.readers.application.use_cases import RunReadersUseCase


class _FixedVectorEmbeddingPort(EmbeddingPort):
    """Duplicate titles get an identical vector — real ticket #456 titles
    ("Slow API response") appear twice in the real fixture, real clustering
    input, just no live API call (`plan.md`'s Testing section)."""

    async def embed(self, text: str) -> list[float]:
        return [float(b) for b in text.encode()[:16].ljust(16, b"\x00")]


async def _force_a_real_absence_event() -> None:
    """Same anchoring pattern `scripts/seed_score_fixture.py` already
    established: `as_of = last_contact + 8 days` guarantees a real, deterministic
    `absence` event regardless of the real wall-clock date the suite runs on."""
    encryption = FernetEncryption(settings.encryption_key_path)
    async with async_session_factory() as session:
        commitments = SqlAlchemyCommitmentLookup(session)
        last_contact = await commitments.last_contact_at()
        as_of = (last_contact or datetime.now(UTC)) + timedelta(days=8)
        use_case = DetectAbsenceUseCase(
            commitments=commitments,
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            encryption=encryption,
            data_key_ref=settings.encryption_key_id,
        )
        await use_case.execute(as_of=as_of)


def _build_readers(*, candidates: CandidateCorpusPort, embeddings: EmbeddingPort, session):
    findings = SqlAlchemyFindingRepository(session)
    return [
        CommitmentReader(SqlAlchemyResponsePairRepository(session), findings),
        UsageReader(SqlAlchemyRollupRepository(session), findings),
        AbsenceReader(SqlAlchemyAbsenceEventRepository(session), findings),
        RelationshipReader(SqlAlchemyRelationshipContext(session), findings),
        RecurrenceReader(candidates, embeddings, findings),
    ], findings


async def test_run_readers_reproduces_the_full_worked_example_table():
    """SC-001 — every finding type `data-model.md`'s worked table names, real,
    persisted at `status = pending_validation`."""
    await _force_a_real_absence_event()

    async with async_session_factory() as session:
        readers, findings = _build_readers(
            candidates=SqlAlchemyCandidateCorpusRepository(session),
            embeddings=_FixedVectorEmbeddingPort(),
            session=session,
        )
        use_case = RunReadersUseCase(readers=readers, findings=findings)
        results = await use_case.execute()

    assert all(r.error is None for r in results)

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text("SELECT finding_type, status, cited_event_ids FROM findings")
            )
        ).all()

    finding_types = {r.finding_type for r in rows}
    assert {
        "broken_response_promise",
        "commitment_met",
        "usage_deviation",
        "contact_absence",
        "relationship_change",
        "recurring_issue",
    } <= finding_types
    assert all(r.status == "pending_validation" for r in rows)

    recurring = next(r for r in rows if r.finding_type == "recurring_issue")
    assert len(recurring.cited_event_ids) >= 2


async def test_rerun_over_an_unchanged_ledger_persists_nothing_new():
    """REQ-M5-15/SC-003 — the per-`(event, reader_version)` cache."""
    async with async_session_factory() as session:
        readers, findings = _build_readers(
            candidates=SqlAlchemyCandidateCorpusRepository(session),
            embeddings=_FixedVectorEmbeddingPort(),
            session=session,
        )
        use_case = RunReadersUseCase(readers=readers, findings=findings)
        await use_case.execute()  # first run — may or may not add rows
        results = await use_case.execute()  # second run over the same ledger

    assert all(r.error is None for r in results)
    assert all(r.findings_persisted == 0 for r in results)


async def test_every_finding_cites_a_real_event():
    """SC-002 — `cited_event_ids` is never a dangling reference."""
    async with async_session_factory() as session:
        rows = (await session.execute(text("SELECT cited_event_ids FROM findings"))).all()
        cited: set[UUID] = {event_id for r in rows for event_id in r.cited_event_ids}

        existing = (
            await session.execute(
                text("SELECT id FROM events WHERE id = ANY((:ids)::uuid[])"),
                {"ids": list(cited)},
            )
        ).all()

    assert {r.id for r in existing} == cited


async def test_recurrence_failure_is_isolated_from_the_other_four_readers():
    """FR-014a — Recurrence's own embedding-provider failure (an invalid/empty
    key, no live OpenAI call — `app.readers.adapters.openai_embedding`'s
    deferred-validation design) is caught and reported; the other four readers
    still run to completion without being cancelled by Recurrence's exception."""
    async with async_session_factory() as session:
        findings = SqlAlchemyFindingRepository(session)
        readers = [
            CommitmentReader(SqlAlchemyResponsePairRepository(session), findings),
            UsageReader(SqlAlchemyRollupRepository(session), findings),
            AbsenceReader(SqlAlchemyAbsenceEventRepository(session), findings),
            RelationshipReader(SqlAlchemyRelationshipContext(session), findings),
            RecurrenceReader(
                SqlAlchemyCandidateCorpusRepository(session),
                OpenAIEmbeddingAdapter(api_key=""),
                findings,
            ),
        ]
        use_case = RunReadersUseCase(readers=readers, findings=findings)
        results = await use_case.execute()

    by_type = {r.reader_type: r for r in results}
    assert by_type["recurrence"].error is not None
    assert by_type["commitment"].error is None
    assert by_type["usage"].error is None
    assert by_type["absence"].error is None
    assert by_type["relationship"].error is None
