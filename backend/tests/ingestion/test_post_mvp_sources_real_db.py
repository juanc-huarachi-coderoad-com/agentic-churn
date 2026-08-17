"""Real-DB: Slack/CSAT/Calendar (specs/011-production-hardening, User Story 6,
FR-020/021/022/023) actually reach the ledger and the readers designed to
consume them.

Deliberately stops short of asserting a statistically-triggered `csat_
deviation`/chat-silence `contact_absence` Finding: those readers' own
decision logic (`z_score`, cadence math) is already exhaustively covered by
`tests/readers/test_usage_reader.py`/`test_absence_reader.py`'s pure
domain-function tests and `tests/readers/test_run_readers_use_case.py`'s
real-DB pass — forcing enough synthetic historical samples here just to
cross a statistical threshold would duplicate that coverage without adding
confidence. What genuinely is new and untested elsewhere is whether
Post-MVP-sourced *data* actually reaches each reader's own input port at
all (FR-021/022) and whether FR-023's consent gate holds end to end — that's
what this file asserts, directly against each reader's real adapter.
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
from app.ingestion.application.use_cases import ComputeRollupsUseCase, RunCollectorUseCase
from app.readers.adapters.sqlalchemy_repository import (
    SqlAlchemyMeetingTranscriptRepository,
    SqlAlchemyMessageEventRepository,
    SqlAlchemyRollupRepository,
)
from tests.conftest import ledger_floor

_FIXTURE = Path(__file__).resolve().parents[2] / "demo" / "fixtures" / "meridian-week.json"
_PHASE1_ONLY_FIXTURE = (
    Path(__file__).resolve().parents[2] / "demo" / "fixtures" / "meridian-week-phase1-only.json"
)


async def _build_fixture(tmp_path: Path, suffix: str, session, source: Path = _FIXTURE) -> Path:
    items = json.loads(source.read_text())
    floor = await ledger_floor(session)
    earliest = min(datetime.fromisoformat(item["occurred_at"]) for item in items)
    offset = floor - earliest + timedelta(seconds=1)
    ticket_offset = int(suffix, 16) % 900000 + 100000
    for item in items:
        item["source_native_id"] = f"{item['source_native_id']}-{suffix}"
        item["occurred_at"] = (datetime.fromisoformat(item["occurred_at"]) + offset).isoformat()
        if "ticket_number" in item:
            item["ticket_number"] += ticket_offset
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(items))
    return fixture_path


async def _run_collector(tmp_path, suffix, source: Path = _FIXTURE):
    async with async_session_factory() as floor_session:
        fixture_path = await _build_fixture(tmp_path, suffix, floor_session, source=source)
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
        return await use_case.execute(collector, window_start=now, window_end=now)


async def test_post_mvp_sources_are_expected_in_coverage(tmp_path):
    suffix = uuid.uuid4().hex[:8]
    result = await _run_collector(tmp_path, suffix)

    async with engine.begin() as conn:
        report = (
            await conn.execute(
                text("SELECT sources_expected FROM coverage_reports WHERE id = :id"),
                {"id": result.coverage_report_id},
            )
        ).one()
        source_types = {
            r.source_type
            for r in (await conn.execute(text("SELECT source_type::text FROM sources"))).all()
        }

    # 3 Phase 1 sources + slack/csat/transcripts, all present in this run's
    # own fixture data (RunCollectorUseCase._POST_MVP_SOURCE_TYPES's
    # docstring — "connected" is inferred from this run's own data, there
    # being no separate connection-state entity, `data-model.md`'s Decision).
    assert report.sources_expected == 6
    assert {"slack", "csat", "transcripts"} <= source_types


async def test_unconsented_calendar_series_never_reaches_the_ledger(tmp_path):
    """FR-023, restated at this layer against the real DB (also covered at
    the collector layer by `test_simulated_collector.py`)."""
    suffix = uuid.uuid4().hex[:8]
    await _run_collector(tmp_path, suffix)

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT count(*) AS n FROM raw_envelopes WHERE source_native_id = :id"),
                {"id": f"calendar-series-standup-2026w32-{suffix}"},
            )
        ).one()
    assert row.n == 0


async def test_slack_and_csat_comment_reach_the_shared_tone_intent_corpus(tmp_path):
    """FR-021 (Slack reaches Absence/Relationship's source-agnostic queries
    — and, as a natural consequence of `message` being the shared event_type,
    Tone/Intent's corpus too) and FR-022 (a CSAT written comment joins the
    same corpus; a score-only CSAT response does not)."""
    suffix = uuid.uuid4().hex[:8]
    await _run_collector(tmp_path, suffix)

    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
    async with async_session_factory() as session:
        messages = await SqlAlchemyMessageEventRepository(session, encryption).list_all()

    texts = [m.text for m in messages]
    assert any("reporting export job fail overnight" in t for t in texts)  # slack
    assert any("Support has been slower to resolve things" in t for t in texts)  # csat w/ comment
    assert not any(t.startswith("CSAT score: 9") for t in texts)  # score-only, never surfaced


async def test_consented_transcript_reaches_the_meeting_reader_corpus(tmp_path):
    """FR-021/023: the one consented calendar series is readable by
    `MeetingReader`'s own dedicated port; the non-consented one never even
    reached the ledger (proven separately above), so it structurally can't
    appear here either."""
    suffix = uuid.uuid4().hex[:8]
    await _run_collector(tmp_path, suffix)

    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
    async with async_session_factory() as session:
        transcripts = await SqlAlchemyMeetingTranscriptRepository(session, encryption).list_all()

    series_ids = {t.series_id for t in transcripts}
    assert "meridian-qbr" in series_ids
    assert "meridian-standup" not in series_ids


async def test_csat_score_reaches_the_usage_readers_rollups(tmp_path):
    """FR-022: a CSAT numeric score becomes a `stakeholder`-scoped rollup
    row, the same projection shape `UsageReader` already reads a warehouse
    metric from (`tests/readers/test_usage_reader.py`'s orchestration tests
    cover the routing logic once a row like this exists)."""
    suffix = uuid.uuid4().hex[:8]
    await _run_collector(tmp_path, suffix)

    async with async_session_factory() as session:
        await ComputeRollupsUseCase(SqlAlchemyEventRepository(session)).execute()
        rollups = SqlAlchemyRollupRepository(session)
        subjects = await rollups.list_subjects()

    assert any(
        subject_type == "stakeholder" and metric == "csat_score"
        for subject_type, _subject_id, metric in subjects
    )


async def test_a_client_connecting_none_of_the_three_sources_sees_identical_behavior(tmp_path):
    """FR-024 — `demo/fixtures/meridian-week-phase1-only.json` is the exact,
    byte-for-byte pre-Phase-11 fixture content, preserved specifically for
    this regression check (`meridian-week.json` itself was extended in place
    for User Story 6, so it can no longer stand in for "connects none of
    them"). Coverage reporting must be identical to feature 010's own
    pre-existing behavior: exactly the 3 Phase 1 sources expected, none of
    the Post-MVP ones phantom-appearing just because this feature's code
    exists."""
    suffix = uuid.uuid4().hex[:8]
    result = await _run_collector(tmp_path, suffix, source=_PHASE1_ONLY_FIXTURE)

    assert result.envelopes_emitted == 14
    async with engine.begin() as conn:
        report = (
            await conn.execute(
                text("SELECT sources_expected FROM coverage_reports WHERE id = :id"),
                {"id": result.coverage_report_id},
            )
        ).one()
    assert report.sources_expected == 3
