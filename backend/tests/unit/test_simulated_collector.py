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
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
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
    # The real, persistent deployment key store, not a throwaway per-test one —
    # these envelopes' encrypted bodies are permanent (events can't be deleted), and
    # any later replay (this run or a future one) decrypts every message-type event
    # in the whole ledger with whatever keys are currently active (see
    # test_replay.py's identical note). `key_store=` replaces the old literal
    # `data_key_ref="test-key"` — RunCollectorUseCase now resolves the real bucket id
    # itself (specs/011-production-hardening, research.md Decision 1).
    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
    collector = SimulatedCollector(fixture_path)
    now = datetime.now(UTC)
    async with async_session_factory() as session:
        use_case = RunCollectorUseCase(
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
            key_store=key_store,
        )
        return await use_case.execute(
            collector, window_start=now, window_end=now, fail_sources=fail_sources
        )


async def test_run_twice_is_idempotent(tmp_path):
    suffix = uuid.uuid4().hex[:8]

    # 14 Phase 1 items + 2 slack + 2 csat + 1 consented calendar item (the
    # fixture's second calendar item has consent_documented: false and is
    # dropped by SimulatedCollector.fetch() before it's ever counted here —
    # FR-023, also covered explicitly by
    # test_unconsented_calendar_item_is_never_collected below).
    first = await _run(tmp_path, suffix)
    assert first.envelopes_emitted == 19
    assert first.duplicates_skipped == 0

    second = await _run(tmp_path, suffix)
    assert second.envelopes_emitted == 0
    assert second.duplicates_skipped == 19


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
    # gmail (3) + warehouse (6) + slack (2) + csat (2) + transcripts (1
    # consented calendar item — the other lacks consent and is never
    # collected at all) succeed; zendesk (5 items) skipped entirely
    # (specs/005-deterministic-findings grew the fixture's zendesk/warehouse/
    # gmail counts beyond feature 003's original 2/1/2 split; specs/011-
    # production-hardening added the Post-MVP sources).
    assert result.envelopes_emitted == 14
    # slack/csat/transcripts are only "expected" because this run's own
    # envelopes actually contain them (RunCollectorUseCase._POST_MVP_SOURCE_
    # TYPES's docstring) — 3 Phase 1 + 3 Post-MVP sources this run.
    assert report.sources_expected == 6


async def test_unconsented_calendar_item_is_never_collected(tmp_path):
    """FR-023: a calendar item with `consent_documented: false` produces
    zero `raw_envelopes` rows — filtered at `SimulatedCollector.fetch()`,
    before it's ever normalized into an Envelope, not merely abstained on by
    `MeetingReader`."""
    suffix = uuid.uuid4().hex[:8]
    await _run(tmp_path, suffix)

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT count(*) AS n FROM raw_envelopes WHERE source_native_id = :id"),
                {"id": f"calendar-series-standup-2026w32-{suffix}"},
            )
        ).one()

    assert row.n == 0
