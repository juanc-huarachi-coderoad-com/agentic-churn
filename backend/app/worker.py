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
(research.md Decision 5's correction). Run with:
    uv run python -m app.worker                  # scheduler loop (production)
    uv run python -m app.worker --run-once absence
    uv run python -m app.worker --run-once score
    uv run python -m app.worker --run-once retention
    uv run python -m app.worker --run-once audio
"""

import argparse
import asyncio
import logging
import signal
import time
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.db import async_session_factory, shredder_session_factory
from app.ingestion.adapters.audio_collector import AudioCollector
from app.ingestion.adapters.encryption import BucketedFernetEncryption
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
from app.ingestion.adapters.whisper_transcription import WhisperTranscriptionAdapter
from app.ingestion.application.use_cases import (
    DetectAbsenceUseCase,
    RunCollectorUseCase,
    RunRetentionUseCase,
)
from app.observability.adapters.tracing import setup_tracing, traced
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter
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


_RUN_ONCE_JOBS = {
    "absence": _run_absence_detection,
    "score": _run_score_recompute,
    "retention": _run_retention,
    "audio": _run_audio_collector,
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
    scheduler.start()
    logger.info(
        "worker started — absence collector and score recompute on the hourly "
        "heartbeat, retention job on the daily heartbeat, audio collector every "
        "%d hour(s)",
        settings.audio_poll_interval_hours,
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
