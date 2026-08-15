"""Run `SimulatedCollector` against the Meridian fixture twice (idempotency, FR-010);
confirm identity resolution matches Ana and leaves the Zendesk reporter unresolved
(REQ-M1-04/05); confirm the sixth fixture item's `legal_threads` content is redacted
(H1 remediation, REQ-M1-09); confirm a simulated source failure produces an honest
coverage report (G1 remediation, REQ-M1-07/08).

Each test builds its own copy of the committed fixture with uuid-suffixed native IDs
so repeated test-suite runs never collide on `idempotency_key` (tests/conftest.py's
docstring explains why: `events` can't be deleted, so isolation comes from
uniqueness, not cleanup).
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory, engine
from app.ingestion.adapters.encryption import FernetEncryption
from app.ingestion.adapters.simulated_collector import SimulatedCollector
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import RunCollectorUseCase
from tests.conftest import ledger_floor

_FIXTURE = Path(__file__).resolve().parents[3] / "demo" / "fixtures" / "meridian-week.json"


async def _build_fixture(tmp_path: Path, suffix: str, session) -> Path:
    items = json.loads(_FIXTURE.read_text())
    # Shift every item's occurred_at forward by the same offset, past the ledger's
    # current floor, preserving relative spacing exactly (ticket #398's 2-hour
    # created->resolved gap must stay 2 hours) — EventRepositoryPort.append requires
    # global occurred_at-order appends (tests/conftest.py's `ledger_floor` docstring),
    # but the fixture's own timestamps are fixed 2026 dates that would otherwise
    # collide with whatever later-dated data other tests have already appended.
    floor = await ledger_floor(session)
    earliest = min(datetime.fromisoformat(item["occurred_at"]) for item in items)
    offset = floor - earliest + timedelta(seconds=1)
    # ticket_number offset, not just source_native_id's suffix: _rebuild_projections
    # (app/ingestion/application/use_cases.py) keys its open_pairs tracking by
    # ticket_number across the WHOLE ledger's history, not by source_native_id — a
    # uuid-suffixed native_id alone still lets this test's ticket #456 shadow (or be
    # shadowed by) any other real or synthetic ticket #456 elsewhere in the ledger.
    # 100000+ stays well clear of the demo fixture's own real ticket numbers (398,
    # 456).
    ticket_offset = int(suffix, 16) % 900000 + 100000
    for item in items:
        item["source_native_id"] = f"{item['source_native_id']}-{suffix}"
        item["occurred_at"] = (datetime.fromisoformat(item["occurred_at"]) + offset).isoformat()
        if "ticket_number" in item:
            item["ticket_number"] += ticket_offset
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(items))
    return fixture_path


async def _run(tmp_path, suffix, fail_sources=frozenset()):
    async with async_session_factory() as floor_session:
        fixture_path = await _build_fixture(tmp_path, suffix, floor_session)
    # The real, persistent deployment key, not a throwaway per-test one — these
    # envelopes' encrypted bodies are permanent (events can't be deleted), and any
    # later replay (this run or a future one) decrypts every message-type event in
    # the whole ledger with whatever key is currently configured (see
    # test_replay.py's identical note).
    encryption = FernetEncryption(settings.encryption_key_path)
    collector = SimulatedCollector(fixture_path)
    now = datetime.now(UTC)
    async with async_session_factory() as session:
        use_case = RunCollectorUseCase(
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
            data_key_ref="test-key",
        )
        return await use_case.execute(
            collector, window_start=now, window_end=now, fail_sources=fail_sources
        )


async def test_run_twice_is_idempotent(tmp_path):
    suffix = uuid.uuid4().hex[:8]

    first = await _run(tmp_path, suffix)
    assert first.envelopes_emitted == 14
    assert first.duplicates_skipped == 0

    second = await _run(tmp_path, suffix)
    assert second.envelopes_emitted == 0
    assert second.duplicates_skipped == 14


async def test_identity_resolution_matches_ana_and_leaves_zendesk_unresolved(tmp_path):
    suffix = uuid.uuid4().hex[:8]
    await _run(tmp_path, suffix)

    async with engine.begin() as conn:
        ana_row = (
            await conn.execute(
                text("SELECT identity_status FROM raw_envelopes WHERE source_native_id = :id"),
                {"id": f"gmail-msg-8831-{suffix}"},
            )
        ).one()
        zendesk_row = (
            await conn.execute(
                text("SELECT identity_status FROM raw_envelopes WHERE source_native_id = :id"),
                {"id": f"zendesk-456-reopened-{suffix}"},
            )
        ).one()

    assert ana_row.identity_status == "resolved"
    assert zendesk_row.identity_status == "unresolved"


async def test_legal_threads_content_is_redacted(tmp_path):
    suffix = uuid.uuid4().hex[:8]
    await _run(tmp_path, suffix)

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT redacted_fields FROM raw_envelopes WHERE source_native_id = :id"),
                {"id": f"gmail-msg-8845-{suffix}"},
            )
        ).one()

    assert "legal_threads" in row.redacted_fields


async def test_source_failure_produces_honest_coverage_report(tmp_path):
    suffix = uuid.uuid4().hex[:8]
    result = await _run(tmp_path, suffix, fail_sources=frozenset({"zendesk"}))

    async with engine.begin() as conn:
        report = (
            await conn.execute(
                text(
                    "SELECT sources_expected, sources_read, gap_reason FROM coverage_reports "
                    "WHERE id = :id"
                ),
                {"id": result.coverage_report_id},
            )
        ).one()

    assert report.sources_read < report.sources_expected
    assert report.gap_reason is not None
    assert "zendesk" in report.gap_reason
    # gmail (3 items) + warehouse (6 items) succeed; zendesk (5 items) skipped entirely
    # (specs/005-deterministic-findings grew the fixture's zendesk/warehouse/gmail
    # counts beyond feature 003's original 2/1/2 split).
    assert result.envelopes_emitted == 9
