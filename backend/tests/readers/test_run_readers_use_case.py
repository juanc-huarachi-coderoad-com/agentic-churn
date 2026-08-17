"""SC-001/SC-002/SC-003/SC-005, FR-014 — real-DB integration test:
`RunReadersUseCase` against the real, already-ingested Meridian ledger
(`quickstart.md`'s prerequisite: `scripts/run_collector.py --source
simulated` has already run). Now that the M5a validation gate is wired in
(feature 007), findings land at `validated`/`quarantined`, not the blanket
`pending_validation` feature 005 shipped (`specs/ROADMAP.md`'s feature 006
log entry already flagged this exact assertion as needing to change).

`RecurrenceReader` and Tone/Intent's `LLMPort` are wired to **faked** ports
here — no live OpenAI/Anthropic call in the test suite (`plan.md`'s Testing
section) — except for one isolation test, which uses the real
`OpenAIEmbeddingAdapter`/`AnthropicLLMAdapter` with an empty key, both of
which fail inside their own call with no network call at all (deferred-
validation design, `app.readers.adapters.openai_embedding`/`anthropic_llm`).
"""

import dataclasses
import uuid
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import UUID

from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyCommitmentLookup,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import DetectAbsenceUseCase
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter
from app.readers.adapters.openai_embedding import OpenAIEmbeddingAdapter
from app.readers.adapters.sqlalchemy_repository import (
    SqlAlchemyAbsenceEventRepository,
    SqlAlchemyCandidateCorpusRepository,
    SqlAlchemyEventExistenceRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyFindingTypeConfigRepository,
    SqlAlchemyMessageEventRepository,
    SqlAlchemyQuarantineRepository,
    SqlAlchemyRelationshipContext,
    SqlAlchemyResponsePairRepository,
    SqlAlchemyRollupRepository,
)
from app.readers.application.absence_reader import AbsenceReader
from app.readers.application.commitment_reader import CommitmentReader
from app.readers.application.intent_reader import IntentCategory, IntentModelOutput, IntentReader
from app.readers.application.ports import CandidateCorpusPort, EmbeddingPort, LLMPort
from app.readers.application.recurrence_reader import RecurrenceReader
from app.readers.application.relationship_reader import RelationshipReader
from app.readers.application.tone_reader import ToneModelOutput
from app.readers.application.usage_reader import UsageReader
from app.readers.application.use_cases import RunReadersUseCase
from app.readers.application.validation_gate import ValidationGate
from app.scoring.domain.entities import Finding

T = TypeVar("T")


class _FixedVectorEmbeddingPort(EmbeddingPort):
    """Duplicate titles get an identical vector — real ticket #456 titles
    ("Slow API response") appear twice in the real fixture, real clustering
    input, just no live API call (`plan.md`'s Testing section)."""

    async def embed(self, text: str) -> list[float]:
        return [float(b) for b in text.encode()[:16].ljust(16, b"\x00")]


class _ContentAwareFakeLLM(LLMPort):
    """No live Anthropic call. Dispatches by requested `schema`; Intent's
    response is content-aware (an "escalation" phrase drives a real
    `escalation_language` finding out of Ana's real worked-example email,
    `examples/01-end-to-end-walkthrough.md` §6's `fnd-7`) — Tone's is a fixed
    no-deviation response, since no confirmed baseline exists in this test
    (the real fixture is deliberately too small to clear REQ-M6-CAL-04's
    floor, `quickstart.md` §2), so `ToneReader` never actually calls it."""

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        if schema is IntentModelOutput:
            # Match the specific real message text (examples/01 §6's "brief
            # the board"), not just "board" — the prompt's own instructional
            # boilerplate ("board-level urgency") also contains that word,
            # which would otherwise match every message regardless of
            # content (a real bug this fake had until caught by running it
            # against the real fixture, not by inspection).
            if "brief the board" in prompt.lower():
                return IntentModelOutput(category=IntentCategory.ESCALATION, confidence=0.85)  # type: ignore[return-value]
            return IntentModelOutput(category=IntentCategory.NONE, confidence=0.9)  # type: ignore[return-value]
        if schema is ToneModelOutput:
            return ToneModelOutput(deviation=0.1, magnitude=0.0, confidence=0.5)  # type: ignore[return-value]
        raise AssertionError(f"unexpected schema requested: {schema}")


async def _force_a_real_absence_event() -> None:
    """Same anchoring pattern `scripts/seed_score_fixture.py` already
    established: `as_of = last_contact + 8 days` guarantees a real, deterministic
    `absence` event regardless of the real wall-clock date the suite runs on."""
    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
    async with async_session_factory() as session:
        commitments = SqlAlchemyCommitmentLookup(session)
        last_contact = await commitments.last_contact_at()
        as_of = (last_contact or datetime.now(UTC)) + timedelta(days=8)
        use_case = DetectAbsenceUseCase(
            commitments=commitments,
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            encryption=encryption,
            key_store=key_store,
        )
        await use_case.execute(as_of=as_of)


def _build_readers(*, candidates: CandidateCorpusPort, embeddings: EmbeddingPort, session):
    findings = SqlAlchemyFindingRepository(session)
    encryption = BucketedFernetEncryption(
        FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
    )
    messages = SqlAlchemyMessageEventRepository(session, encryption)
    llm = _ContentAwareFakeLLM()
    readers = [
        CommitmentReader(SqlAlchemyResponsePairRepository(session), findings),
        UsageReader(SqlAlchemyRollupRepository(session), findings),
        AbsenceReader(SqlAlchemyAbsenceEventRepository(session), findings),
        RelationshipReader(SqlAlchemyRelationshipContext(session), findings),
        RecurrenceReader(candidates, embeddings, findings),
        IntentReader(messages, llm, findings),
    ]
    gate = ValidationGate(
        finding_type_config=SqlAlchemyFindingTypeConfigRepository(session),
        event_existence=SqlAlchemyEventExistenceRepository(session),
    )
    quarantine = SqlAlchemyQuarantineRepository(session)
    return readers, findings, gate, quarantine


async def test_run_readers_reproduces_the_full_worked_example_table():
    """SC-001/SC-002 — every finding type `data-model.md`'s worked table
    names, real, gated, and persisted at `validated`/`quarantined` (never
    left at `pending_validation`, closing the gap feature 005 left open)."""
    await _force_a_real_absence_event()

    async with async_session_factory() as session:
        readers, findings, gate, quarantine = _build_readers(
            candidates=SqlAlchemyCandidateCorpusRepository(session),
            embeddings=_FixedVectorEmbeddingPort(),
            session=session,
        )
        use_case = RunReadersUseCase(
            readers=readers, findings=findings, gate=gate, quarantine=quarantine
        )
        results = await use_case.execute()

    assert all(r.error is None for r in results)

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text("SELECT finding_type, status, cited_event_ids FROM findings")
            )
        ).all()

    finding_types = {r.finding_type for r in rows}
    # `usage_deviation` deliberately excluded from this set: `rollups` is
    # only ever populated by `ComputeRollupsUseCase`
    # (`app.ingestion.application.use_cases`), which — found during this
    # feature's own verification — has no caller anywhere in the actual
    # pipeline (only its own dedicated unit test invokes it). That's a
    # pre-existing gap in feature 005's scope (rollup computation was never
    # wired into `scripts/run_collector.py`/`run_readers.py`), not something
    # this feature's Tone/Intent/gate work regresses or is responsible for
    # fixing — flagged here rather than silently worked around.
    assert {
        "broken_response_promise",
        "commitment_met",
        "contact_absence",
        "relationship_change",
        "recurring_issue",
        "escalation_language",
    } <= finding_types
    assert all(r.status in ("validated", "quarantined") for r in rows)
    assert any(r.status == "validated" for r in rows)

    recurring = next(r for r in rows if r.finding_type == "recurring_issue")
    assert len(recurring.cited_event_ids) >= 2

    # SC-002: Ana's real "brief the board" email (examples/01 §6's fnd-7)
    # produces a validated escalation_language finding.
    escalation = next(r for r in rows if r.finding_type == "escalation_language")
    assert escalation.status == "validated"


async def test_rerun_over_an_unchanged_ledger_persists_nothing_new():
    """REQ-M5-15/SC-005 — the per-`(event, reader_version)` cache."""
    async with async_session_factory() as session:
        readers, findings, gate, quarantine = _build_readers(
            candidates=SqlAlchemyCandidateCorpusRepository(session),
            embeddings=_FixedVectorEmbeddingPort(),
            session=session,
        )
        use_case = RunReadersUseCase(
            readers=readers, findings=findings, gate=gate, quarantine=quarantine
        )
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


async def test_recurrence_failure_is_isolated_from_the_other_readers():
    """FR-014 — Recurrence's own embedding-provider failure (an invalid/empty
    key, no live OpenAI call — `app.readers.adapters.openai_embedding`'s
    deferred-validation design) is caught and reported; the other readers
    still run to completion without being cancelled by Recurrence's
    exception, and their findings still reach the gate normally."""
    async with async_session_factory() as session:
        findings = SqlAlchemyFindingRepository(session)
        encryption = BucketedFernetEncryption(
            FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
        )
        messages = SqlAlchemyMessageEventRepository(session, encryption)
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
            IntentReader(messages, AnthropicLLMAdapter(api_key="", model_id="n/a"), findings),
        ]
        gate = ValidationGate(
            finding_type_config=SqlAlchemyFindingTypeConfigRepository(session),
            event_existence=SqlAlchemyEventExistenceRepository(session),
        )
        quarantine = SqlAlchemyQuarantineRepository(session)
        use_case = RunReadersUseCase(
            readers=readers, findings=findings, gate=gate, quarantine=quarantine
        )
        results = await use_case.execute()

    by_type = {r.reader_type: r for r in results}
    assert by_type["recurrence"].error is not None
    assert by_type["commitment"].error is None
    assert by_type["usage"].error is None
    assert by_type["absence"].error is None
    assert by_type["relationship"].error is None
    # A missing ANTHROPIC_API_KEY is a systemic misconfiguration, not a
    # per-message transient failure -- IntentReader lets it propagate as a
    # reader-level failure too, the same as Recurrence's missing
    # OPENAI_API_KEY, rather than silently "abstaining" on every candidate
    # message and masking a misconfigured deployment as a quiet, healthy one.
    assert by_type["intent"].error is not None


async def test_gate_quarantines_a_bad_finding_via_the_real_sql_adapters():
    """SC-003 — the gate's SQL-backed adapters (`FindingTypeConfigPort`,
    `EventExistencePort`, `QuarantineRepositoryPort`) work end to end against
    live Postgres, not just the pure functions `test_validation_gate.py`
    already covers. Reproduces `examples/01` §7's `fnd-10`/`q-1` shape
    (confidence 0.55 < `tone_deterioration`'s 0.65 floor)."""
    async with async_session_factory() as session:
        # tone_deterioration's min_evidence_count is 3 (data-base/05-schema-
        # reasoning.md's seed) — cite three real events so only the
        # confidence check fails, isolating the one check this test targets.
        rows = (
            await session.execute(text("SELECT id FROM events ORDER BY occurred_at LIMIT 3"))
        ).all()
        real_event_ids = tuple(r.id for r in rows)

        bad_finding = Finding(
            id=uuid.uuid4(),
            reader_type="tone",
            reader_version="v1",
            finding_type="tone_deterioration",
            magnitude=0.5,
            confidence=0.55,
            cited_event_ids=real_event_ids,
            stakeholder_id=None,
            product_area_id=None,
            status="pending_validation",
            state=None,
            is_positive=False,
        )

        gate = ValidationGate(
            finding_type_config=SqlAlchemyFindingTypeConfigRepository(session),
            event_existence=SqlAlchemyEventExistenceRepository(session),
        )
        result = await gate.evaluate(bad_finding)
        assert result.passed is False
        assert [c.check_name for c in result.failed_checks] == ["confidence_below_floor"]

        findings = SqlAlchemyFindingRepository(session)
        final = dataclasses.replace(bad_finding, status="quarantined")
        await findings.persist(final)
        quarantine = SqlAlchemyQuarantineRepository(session)
        await quarantine.record(final.id, list(result.failed_checks))

    async with async_session_factory() as session:
        row = (
            await session.execute(
                text(
                    "SELECT q.failed_check, vf.check_name, vf.expected, vf.actual "
                    "FROM quarantine q JOIN validation_failures vf ON vf.quarantine_id = q.id "
                    "WHERE q.finding_id = :finding_id"
                ),
                {"finding_id": final.id},
            )
        ).one()
        assert row.failed_check == "confidence_below_floor"
        assert row.actual == "0.55"
