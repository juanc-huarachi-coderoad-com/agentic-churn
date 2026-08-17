"""Background worker process — the hourly-heartbeat/event-triggered recompute host.

specs/003-ingestion-and-context registered the first real scheduled job: the absence
collector (REQ-M1-06). specs/004-score-engine adds the second: the score recompute
heartbeat (REQ-M6-24) — recency/ageing changes with time alone, so the score must
recompute hourly even with zero new evidence. specs/011-production-hardening adds the
third: the daily retention/crypto-shredding job (FR-001). Run with:
    uv run python -m app.worker                  # scheduler loop (production)
    uv run python -m app.worker --run-once absence
    uv run python -m app.worker --run-once score
    uv run python -m app.worker --run-once retention
"""

import argparse
import asyncio
import logging
import signal
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.db import async_session_factory, shredder_session_factory
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyCommitmentLookup,
    SqlAlchemyEventRepository,
    SqlAlchemyRetentionJobRepository,
)
from app.ingestion.application.use_cases import DetectAbsenceUseCase, RunRetentionUseCase
from app.observability.adapters.tracing import setup_tracing, traced
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


_RUN_ONCE_JOBS = {
    "absence": _run_absence_detection,
    "score": _run_score_recompute,
    "retention": _run_retention,
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
    scheduler.start()
    logger.info(
        "worker started — absence collector and score recompute on the hourly "
        "heartbeat, retention job on the daily heartbeat"
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
