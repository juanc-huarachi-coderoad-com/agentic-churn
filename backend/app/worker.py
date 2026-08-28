"""Background worker process — the hourly-heartbeat/event-triggered recompute host.

specs/003-ingestion-and-context registered the first real scheduled job: the absence
collector (REQ-M1-06). specs/004-score-engine adds the second: the score recompute
heartbeat (REQ-M6-24) — recency/ageing changes with time alone, so the score must
recompute hourly even with zero new evidence. specs/011-production-hardening adds the
third: the daily retention/crypto-shredding job (FR-001). specs/019-meeting-audio-
ingestion adds the fourth: the meeting-audio collector, on its own configurable
interval (research.md Decision 9) — the first job whose `RunCollectorUseCase.execute()`
call can genuinely fail (the configured local storage location missing, unmounted, or
permission-denied — research.md Decision 12), which is exactly why that method gained a
real `try/except` and a caller-supplied `trigger` rather than a hard-coded literal
(research.md Decision 5's correction). specs/026-automated-pipeline-orchestration adds
the fifth: a 30-second poll (research.md Decision 3) that wires RunReadersUseCase and
NarrateScoreRunUseCase into a live, automatic trigger for the first time —
scripts/run_narrator.py's own docstring used to say "no live/chained trigger path exists
anywhere in this pipeline yet"; this job is that path. Skips entirely (no reader,
recompute, or narration work) when `events.created_at`'s max hasn't advanced since the
last cycle (research.md Decision 2) — a quiet, healthy account costs nothing between
real signals (constitution P6). specs/028-real-gmail-connector adds the sixth: the
second real, non-simulated `Collector` (`GmailCollector`, after `AudioCollector`) — its
own independent `RunCollectorUseCase.execute()` call, on its own configurable interval,
never merged with `SimulatedCollector`'s run (that collector and its JSON fixture are
untouched by this feature, an explicit requirement). specs/029-real-zendesk-connector
adds the seventh: the third real, non-simulated `Collector` (`ZendeskCollector`) — same
shape, same explicit "SimulatedCollector untouched" requirement; the one genuinely new
piece of domain logic is classifying each ticket's audit history into
created/resolved/reopened transitions, since Zendesk's own ticket object only exposes
current status, never a history of changes. specs/030-real-warehouse-connector adds the
eighth: the fourth real, non-simulated `Collector` (`WarehouseCollector`, a generic SQL
connection + a client-authored query, not a vendor SDK) — and, separately, closes a real
pre-existing gap in `_orchestrate_pipeline()` itself: `ComputeRollupsUseCase` (REQ-M2-06,
feature 005) had no caller anywhere in this codebase until now, so the Usage reader's
`rollups` projection was always empty in production regardless of source. Run with:
    uv run python -m app.worker                  # scheduler loop (production)
    uv run python -m app.worker --run-once absence
    uv run python -m app.worker --run-once score
    uv run python -m app.worker --run-once retention
    uv run python -m app.worker --run-once audio
    uv run python -m app.worker --run-once pipeline
    uv run python -m app.worker --run-once gmail
    uv run python -m app.worker --run-once zendesk
    uv run python -m app.worker --run-once warehouse
"""

import argparse
import asyncio
import logging
import signal
import time
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory, shredder_session_factory
from app.ingestion.adapters.audio_collector import AudioCollector
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.gmail_collector import GmailCollector, _RealGmailClient
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.local_storage_client import LocalStorageClient
from app.ingestion.adapters.pyannote_diarization import diarize
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyCommitmentLookup,
    SqlAlchemyEventRepository,
    SqlAlchemyMeetingSeriesConsentRepository,
    SqlAlchemyRetentionJobRepository,
)
from app.ingestion.adapters.warehouse_collector import WarehouseCollector, _RealWarehouseClient
from app.ingestion.adapters.whisper_transcription import WhisperTranscriptionAdapter
from app.ingestion.adapters.zendesk_collector import ZendeskCollector, _RealZendeskClient
from app.ingestion.application.use_cases import (
    ComputeRollupsUseCase,
    DetectAbsenceUseCase,
    RunCollectorUseCase,
    RunRetentionUseCase,
)
from app.narrator.adapters.sqlalchemy_repository import (
    SqlAlchemyClientContextRepository,
    SqlAlchemyNarratorOutputRepository,
    SqlAlchemyPlaybookRepository,
    SqlAlchemyScoreContextRepository,
)
from app.narrator.application.use_cases import NarrateScoreRunUseCase
from app.observability.adapters.tracing import setup_tracing, traced
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter
from app.readers.adapters.openai_embedding import OpenAIEmbeddingAdapter
from app.readers.adapters.pgvector_embedding_cache import CachedEmbeddingAdapter
from app.readers.adapters.sqlalchemy_repository import (
    SqlAlchemyAbsenceEventRepository,
    SqlAlchemyCandidateCorpusRepository,
    SqlAlchemyConfirmedBaselineRepository,
    SqlAlchemyEventExistenceRepository,
    SqlAlchemyFindingTypeConfigRepository,
    SqlAlchemyMeetingTranscriptRepository,
    SqlAlchemyMessageEventRepository,
    SqlAlchemyQuarantineRepository,
    SqlAlchemyRelationshipContext,
    SqlAlchemyResponsePairRepository,
    SqlAlchemyRollupRepository,
)
from app.readers.adapters.sqlalchemy_repository import (
    SqlAlchemyFindingRepository as ReadersFindingRepository,
)
from app.readers.application.absence_reader import AbsenceReader
from app.readers.application.commitment_reader import CommitmentReader
from app.readers.application.intent_reader import IntentReader
from app.readers.application.meeting_reader import MeetingReader
from app.readers.application.recurrence_reader import RecurrenceReader
from app.readers.application.relationship_reader import RelationshipReader
from app.readers.application.tone_reader import ToneReader
from app.readers.application.usage_reader import UsageReader
from app.readers.application.use_cases import RunReadersUseCase
from app.readers.application.validation_gate import ValidationGate
from app.scoring.adapters.sqlalchemy_repository import (
    SqlAlchemyClientProfileMultipliers,
    SqlAlchemyCoverageCheck,
    SqlAlchemyDampingRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyScoreRunRepository,
)
from app.scoring.application.use_cases import RecomputeScoreUseCase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _run_absence_detection() -> None:
    asyncio.run(_detect_absence())


async def _detect_absence() -> None:
    with traced("absence_collector"):
        key_store = FileKeyStore(settings.data_keys_dir)
        encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
        async with async_session_factory() as session:
            use_case = DetectAbsenceUseCase(
                commitments=SqlAlchemyCommitmentLookup(session),
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                events=SqlAlchemyEventRepository(session),
                encryption=encryption,
                key_store=key_store,
            )
            appended = await use_case.execute()
        if appended:
            logger.info("absence collector appended %d event(s)", len(appended))


def _run_score_recompute() -> None:
    asyncio.run(_recompute_score())


async def _recompute_score() -> None:
    with traced("score_recompute"):
        async with async_session_factory() as session:
            use_case = RecomputeScoreUseCase(
                findings=SqlAlchemyFindingRepository(session),
                score_runs=SqlAlchemyScoreRunRepository(session),
                profile=SqlAlchemyClientProfileMultipliers(session),
                damping=SqlAlchemyDampingRepository(session),
                coverage=SqlAlchemyCoverageCheck(session),
            )
            run = await use_case.execute(trigger="hourly_heartbeat")
        logger.info("score recomputed: score=%.2f band=%s", run.score, run.band)


def _run_retention() -> None:
    asyncio.run(_retain())


async def _retain() -> None:
    # An enhancement on top of RunRetentionUseCase's own independent logging
    # (specs/011-production-hardening, `/speckit-analyze` findings I1/I2) — a
    # trace here is never a prerequisite for FR-004a, which User Story 1 already
    # satisfies alone.
    with traced("retention_job"):
        key_store = FileKeyStore(settings.data_keys_dir)
        async with (
            async_session_factory() as session,
            shredder_session_factory() as shredder_session,
        ):
            use_case = RunRetentionUseCase(
                key_store=key_store,
                retention_repo=SqlAlchemyRetentionJobRepository(session, shredder_session),
                retention_window_days=settings.retention_window_days,
            )
            result = await use_case.execute()
    logger.info(
        "retention job %s: %d/%d bucket(s) shredded",
        result.status,
        result.buckets_shredded,
        result.buckets_evaluated,
    )


def _run_audio_collector() -> None:
    asyncio.run(_collect_audio())


async def _collect_audio() -> None:
    # specs/019-meeting-audio-ingestion — a second, independent collector run
    # alongside the absence collector above, never merged into it (research.md
    # Decision 1). `trigger="poll"` here, `trigger="manual"` at the
    # `POST /api/meeting-audio/refresh` endpoint — both now real, caller-
    # supplied values (research.md Decision 5's correction), not the
    # previously hard-coded `"manual"` literal every `RunCollectorUseCase`
    # call used to record regardless of how it was actually triggered.
    with traced("audio_collector"):
        key_store = FileKeyStore(settings.data_keys_dir)
        encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
        async with async_session_factory() as session:
            collector = AudioCollector(
                storage=LocalStorageClient(settings.meeting_audio_storage_path),
                transcriber=WhisperTranscriptionAdapter(
                    openai_api_key=settings.openai_api_key,
                    llm=AnthropicLLMAdapter(settings.anthropic_api_key, settings.reader_model_id),
                    diarize=diarize,
                ),
                consent=SqlAlchemyMeetingSeriesConsentRepository(session),
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                profile_context=SqlAlchemyClientProfileContext(session),
            )
            use_case = RunCollectorUseCase(
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                events=SqlAlchemyEventRepository(session),
                profile_context=SqlAlchemyClientProfileContext(session),
                encryption=encryption,
                key_store=key_store,
            )
            now = datetime.now(UTC)
            result = await use_case.execute(
                collector, window_start=now, window_end=now, trigger="poll"
            )
    logger.info(
        "audio collector: envelopes_emitted=%d duplicates_skipped=%d coverage_report_id=%s",
        result.envelopes_emitted,
        result.duplicates_skipped,
        result.coverage_report_id,
    )


def _run_gmail_collector() -> None:
    asyncio.run(_collect_gmail())


async def _collect_gmail() -> None:
    # specs/028-real-gmail-connector — a third, independent collector run,
    # never merged with the absence/audio collectors above (mirrors research.md
    # Decision 1's precedent from specs/019). SimulatedCollector and its JSON
    # fixture are never touched by this job.
    with traced("gmail_collector"):
        key_store = FileKeyStore(settings.data_keys_dir)
        encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
        async with async_session_factory() as session:
            collector = GmailCollector(
                client=_RealGmailClient(
                    settings.gmail_client_id,
                    settings.gmail_client_secret,
                    settings.gmail_refresh_token,
                ),
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                session=session,
            )
            use_case = RunCollectorUseCase(
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                events=SqlAlchemyEventRepository(session),
                profile_context=SqlAlchemyClientProfileContext(session),
                encryption=encryption,
                key_store=key_store,
            )
            now = datetime.now(UTC)
            # window_start/window_end are unused by GmailCollector.fetch() itself
            # (it derives its own window from the ledger, research.md Decision 4)
            # — passed through only for collector_runs' own record-keeping,
            # mirroring AudioCollector's identical now()/now() call above.
            result = await use_case.execute(
                collector, window_start=now, window_end=now, trigger="poll"
            )
    logger.info(
        "gmail collector: envelopes_emitted=%d duplicates_skipped=%d coverage_report_id=%s",
        result.envelopes_emitted,
        result.duplicates_skipped,
        result.coverage_report_id,
    )


def _run_zendesk_collector() -> None:
    asyncio.run(_collect_zendesk())


async def _collect_zendesk() -> None:
    # specs/029-real-zendesk-connector — a fourth, independent collector run,
    # never merged with the others above. SimulatedCollector and its JSON
    # fixture are never touched by this job.
    with traced("zendesk_collector"):
        key_store = FileKeyStore(settings.data_keys_dir)
        encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
        async with async_session_factory() as session:
            collector = ZendeskCollector(
                client=_RealZendeskClient(
                    settings.zendesk_subdomain,
                    settings.zendesk_agent_email,
                    settings.zendesk_api_token,
                ),
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                session=session,
            )
            use_case = RunCollectorUseCase(
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                events=SqlAlchemyEventRepository(session),
                profile_context=SqlAlchemyClientProfileContext(session),
                encryption=encryption,
                key_store=key_store,
            )
            now = datetime.now(UTC)
            # window_start/window_end unused by ZendeskCollector.fetch() itself
            # (research.md Decision 6) — same shape as GmailCollector above.
            result = await use_case.execute(
                collector, window_start=now, window_end=now, trigger="poll"
            )
    logger.info(
        "zendesk collector: envelopes_emitted=%d duplicates_skipped=%d coverage_report_id=%s",
        result.envelopes_emitted,
        result.duplicates_skipped,
        result.coverage_report_id,
    )


def _run_warehouse_collector() -> None:
    asyncio.run(_collect_warehouse())


async def _collect_warehouse() -> None:
    # specs/030-real-warehouse-connector — a fifth, independent collector run,
    # never merged with the others above. SimulatedCollector and its JSON
    # fixture are never touched by this job.
    with traced("warehouse_collector"):
        key_store = FileKeyStore(settings.data_keys_dir)
        encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
        async with async_session_factory() as session:
            collector = WarehouseCollector(
                client=_RealWarehouseClient(
                    settings.warehouse_connection_url,
                    settings.warehouse_query_path,
                ),
                collector_runs=SqlAlchemyCollectorRunRepository(session),
            )
            use_case = RunCollectorUseCase(
                collector_runs=SqlAlchemyCollectorRunRepository(session),
                events=SqlAlchemyEventRepository(session),
                profile_context=SqlAlchemyClientProfileContext(session),
                encryption=encryption,
                key_store=key_store,
            )
            now = datetime.now(UTC)
            # window_start/window_end unused by WarehouseCollector.fetch() itself
            # (research.md Decision 5 — no connector-derived window).
            result = await use_case.execute(
                collector, window_start=now, window_end=now, trigger="poll"
            )
    logger.info(
        "warehouse collector: envelopes_emitted=%d duplicates_skipped=%d coverage_report_id=%s",
        result.envelopes_emitted,
        result.duplicates_skipped,
        result.coverage_report_id,
    )


# specs/026-automated-pipeline-orchestration, research.md Decision 2 — in-process only,
# not persisted. A restart re-runs one harmless cycle if nothing changed (the readers'
# own idempotency checks, e.g. RecurrenceReader's already_interpreted() dedup, make a
# redundant cycle produce zero duplicate findings); persisting this to survive restarts
# would be schema surface disproportionate to that one-time, harmless cost (P10).
_last_seen_event_at: datetime | None = None


def _run_pipeline_orchestration() -> None:
    asyncio.run(_orchestrate_pipeline())


async def _orchestrate_pipeline() -> None:
    # specs/026-automated-pipeline-orchestration — no blanket try/except around
    # readers/RecomputeScoreUseCase (research.md Decision — FR-010): a failure there
    # must propagate through traced() (which marks the span degraded) to APScheduler's
    # own executor logging, exactly like every other job in this file.
    # RunReadersUseCase's own internal per-reader try/except is what satisfies FR-005
    # — unchanged, reused as-is. NarrateScoreRunUseCase gets its own narrower
    # try/except below (not blanket) — found necessary by this feature's own live CI
    # verification, not assumed up front: unlike RecomputeScoreUseCase (pure
    # arithmetic, P2, never touches an LLM), narration always constructs a real
    # AnthropicLLMAdapter and can fail on a missing/misconfigured key exactly the way
    # Tone/Intent already can — but unlike those two readers, nothing here isolated
    # that failure, so it used to crash the whole cycle AND (worse) skip updating
    # `_last_seen_event_at`, which would have retried the full readers+recompute+
    # narrate sequence every 30s forever against a persistently-misconfigured key.
    # The score/findings are already correct and visible on the dashboard the moment
    # RecomputeScoreUseCase returns — narration text is the one part of this cycle
    # that's allowed to fail without undoing that.
    global _last_seen_event_at
    with traced("pipeline_orchestration"):
        async with async_session_factory() as session:
            latest_at = (
                await session.execute(text("SELECT MAX(created_at) FROM events"))
            ).scalar_one_or_none()
            # research.md Decision 2 — events.id is a UUID, not orderable; created_at
            # (insertion time, monotonic) is the only usable high-water-mark. The
            # `is not None` guard on the module-level variable is required, not
            # optional: comparing `latest_at <= _last_seen_event_at` while the latter
            # is still None (the very first tick after process start) would raise
            # TypeError — that first tick must run once to establish the baseline.
            if latest_at is None:
                return
            if _last_seen_event_at is not None and latest_at <= _last_seen_event_at:
                return
            captured_at = latest_at  # read-cursor-then-work, so a mid-cycle arrival
            # is never lost — it simply becomes the next cycle's trigger instead.

            encryption = BucketedFernetEncryption(
                FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
            )

            # specs/030-real-warehouse-connector, research.md Decision 6 — closes a
            # real, pre-existing gap: ComputeRollupsUseCase (REQ-M2-06, feature 005)
            # had no caller anywhere in this codebase until now, so `rollups` was
            # always empty in production regardless of source, and UsageReader below
            # could never see real usage/CSAT data. Rebuilds `rollups` from every
            # usage_measurement/survey_response event in the ledger — the same
            # "truncate + rebuild from events" shape event_threads/response_pairs
            # already have, unmodified from its own existing implementation.
            await ComputeRollupsUseCase(SqlAlchemyEventRepository(session)).execute()

            reader_findings = ReadersFindingRepository(session)
            messages = SqlAlchemyMessageEventRepository(session, encryption)
            gate = ValidationGate(
                finding_type_config=SqlAlchemyFindingTypeConfigRepository(session),
                event_existence=SqlAlchemyEventExistenceRepository(session),
            )
            quarantine = SqlAlchemyQuarantineRepository(session)
            reader_llm = AnthropicLLMAdapter(settings.anthropic_api_key, settings.reader_model_id)
            readers = [
                CommitmentReader(SqlAlchemyResponsePairRepository(session), reader_findings),
                UsageReader(SqlAlchemyRollupRepository(session), reader_findings),
                AbsenceReader(SqlAlchemyAbsenceEventRepository(session), reader_findings),
                RelationshipReader(SqlAlchemyRelationshipContext(session), reader_findings),
                RecurrenceReader(
                    SqlAlchemyCandidateCorpusRepository(session),
                    # specs/027-pgvector-embedding-store — a repeated candidate
                    # title across pipeline cycles costs zero additional
                    # embedding calls; RecurrenceReader itself is unaware of this.
                    CachedEmbeddingAdapter(
                        session,
                        OpenAIEmbeddingAdapter.MODEL_ID,
                        OpenAIEmbeddingAdapter(settings.openai_api_key),
                    ),
                    reader_findings,
                ),
                ToneReader(
                    messages,
                    SqlAlchemyConfirmedBaselineRepository(session, encryption),
                    reader_llm,
                    reader_findings,
                ),
                IntentReader(messages, reader_llm, reader_findings),
                MeetingReader(
                    SqlAlchemyMeetingTranscriptRepository(session, encryption),
                    reader_llm,
                    reader_findings,
                ),
            ]
            reader_results = await RunReadersUseCase(
                readers=readers, findings=reader_findings, gate=gate, quarantine=quarantine
            ).execute()
            for result in reader_results:
                if result.error is not None:
                    logger.warning(
                        "pipeline orchestration: reader %s failed (isolated): %s",
                        result.reader_type,
                        result.error,
                    )

            score_run = await RecomputeScoreUseCase(
                findings=SqlAlchemyFindingRepository(session),
                score_runs=SqlAlchemyScoreRunRepository(session),
                profile=SqlAlchemyClientProfileMultipliers(session),
                damping=SqlAlchemyDampingRepository(session),
                coverage=SqlAlchemyCoverageCheck(session),
            ).execute(trigger="new_event")
            # The cursor advances here, not after narration — readers and score
            # recompute have already fully processed everything up to captured_at;
            # narration's own fate (below) must never cause a re-processing retry.
            _last_seen_event_at = captured_at

            # research.md Decision 5 — NarrateScoreRunUseCase.execute() already
            # returns None when the score run has no findings ("a genuinely healthy
            # run"), which already satisfies FR-009 with no extra check needed here.
            narrator_output = None
            try:
                narrator_output = await NarrateScoreRunUseCase(
                    llm=AnthropicLLMAdapter(
                        settings.anthropic_api_key, settings.generation_model_id
                    ),
                    score_context=SqlAlchemyScoreContextRepository(session),
                    client_context=SqlAlchemyClientContextRepository(session, encryption),
                    playbook=SqlAlchemyPlaybookRepository(session),
                    repository=SqlAlchemyNarratorOutputRepository(session),
                ).execute(score_run.id)
            except Exception:
                logger.exception(
                    "pipeline orchestration: narration failed for score_run %s "
                    "(score/findings already persisted; not retried this cycle)",
                    score_run.id,
                )
        logger.info(
            "pipeline orchestration: score=%.2f band=%s narrated=%s",
            score_run.score,
            score_run.band,
            narrator_output is not None,
        )


_RUN_ONCE_JOBS = {
    "absence": _run_absence_detection,
    "score": _run_score_recompute,
    "retention": _run_retention,
    "audio": _run_audio_collector,
    "pipeline": _run_pipeline_orchestration,
    "gmail": _run_gmail_collector,
    "zendesk": _run_zendesk_collector,
    "warehouse": _run_warehouse_collector,
}


def main() -> None:
    setup_tracing()  # User Story 3 — before either the --run-once or loop path
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-once",
        choices=sorted(_RUN_ONCE_JOBS),
        help="Run one job immediately and exit, instead of starting the scheduler loop "
        "(manual triggering / quickstart.md verification).",
    )
    args = parser.parse_args()
    if args.run_once:
        _RUN_ONCE_JOBS[args.run_once]()
        return

    scheduler = BackgroundScheduler()
    # Hourly heartbeat (architecture/03-technology-stack.md) — the absence collector
    # doesn't need finer granularity: cadences are measured in days (REQ-M1-06), so an
    # hourly check is well within any commitment's tolerance. The score recompute
    # (REQ-M6-24) needs exactly this granularity too — "time itself changes recency."
    # The retention job (FR-001) runs daily — the clarified cadence
    # (specs/011-production-hardening spec.md Clarifications, 2026-08-16).
    scheduler.add_job(_run_absence_detection, "interval", hours=1, id="absence_collector")
    scheduler.add_job(_run_score_recompute, "interval", hours=1, id="score_recompute")
    scheduler.add_job(_run_retention, "interval", days=1, id="retention_job")
    # specs/019-meeting-audio-ingestion, research.md Decision 9 — its own
    # configurable interval, not tied to the hourly heartbeat above.
    scheduler.add_job(
        _run_audio_collector,
        "interval",
        hours=settings.audio_poll_interval_hours,
        id="audio_collector",
    )
    # specs/026-automated-pipeline-orchestration, research.md Decisions 1/3 — a
    # 30-second poll (same primitive as every job above), not LISTEN/NOTIFY or a
    # message broker; matches architecture/03-technology-stack.md's own stated
    # "30-second batching window" design intent and stays inside REQ-NFR-02's 60s
    # cap. No max_instances override — BackgroundScheduler's own default (1) is
    # exactly FR-006's "never two overlapping cycles" requirement (research.md
    # Decision 6), already relied upon, silently, by every job above.
    scheduler.add_job(
        _run_pipeline_orchestration, "interval", seconds=30, id="pipeline_orchestration"
    )
    # specs/028-real-gmail-connector — its own configurable interval, like the
    # audio collector above; email is not on the ~30-60s automated-pipeline path.
    scheduler.add_job(
        _run_gmail_collector,
        "interval",
        hours=settings.gmail_poll_interval_hours,
        id="gmail_collector",
    )
    # specs/029-real-zendesk-connector — its own configurable interval, same
    # shape as the gmail collector above.
    scheduler.add_job(
        _run_zendesk_collector,
        "interval",
        hours=settings.zendesk_poll_interval_hours,
        id="zendesk_collector",
    )
    # specs/030-real-warehouse-connector — its own configurable interval, same
    # shape as the gmail/zendesk collectors above.
    scheduler.add_job(
        _run_warehouse_collector,
        "interval",
        hours=settings.warehouse_poll_interval_hours,
        id="warehouse_collector",
    )
    scheduler.start()
    logger.info(
        "worker started — absence collector and score recompute on the hourly "
        "heartbeat, retention job on the daily heartbeat, audio collector every "
        "%d hour(s), pipeline orchestration (readers/recompute/narration) every 30s, "
        "gmail collector every %d hour(s), zendesk collector every %d hour(s), "
        "warehouse collector every %d hour(s)",
        settings.audio_poll_interval_hours,
        settings.gmail_poll_interval_hours,
        settings.zendesk_poll_interval_hours,
        settings.warehouse_poll_interval_hours,
    )

    running = True

    def _stop(signum: int, _frame: object) -> None:
        nonlocal running
        logger.info("received signal %s, shutting down", signum)
        running = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    try:
        while running:
            time.sleep(1)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
