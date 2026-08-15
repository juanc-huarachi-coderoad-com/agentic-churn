"""Background worker process — the hourly-heartbeat/event-triggered recompute host.

specs/003-ingestion-and-context registered the first real scheduled job: the absence
collector (REQ-M1-06). specs/004-score-engine adds the second: the score recompute
heartbeat (REQ-M6-24) — recency/ageing changes with time alone, so the score must
recompute hourly even with zero new evidence. Run with: uv run python -m app.worker
"""

import asyncio
import logging
import signal
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.db import async_session_factory
from app.ingestion.adapters.encryption import FernetEncryption
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyCommitmentLookup,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import DetectAbsenceUseCase
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
    encryption = FernetEncryption(settings.encryption_key_path)
    async with async_session_factory() as session:
        use_case = DetectAbsenceUseCase(
            commitments=SqlAlchemyCommitmentLookup(session),
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            encryption=encryption,
            data_key_ref=settings.encryption_key_id,
        )
        appended = await use_case.execute()
    if appended:
        logger.info("absence collector appended %d event(s)", len(appended))


def _run_score_recompute() -> None:
    asyncio.run(_recompute_score())


async def _recompute_score() -> None:
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


def main() -> None:
    scheduler = BackgroundScheduler()
    # Hourly heartbeat (architecture/03-technology-stack.md) — the absence collector
    # doesn't need finer granularity: cadences are measured in days (REQ-M1-06), so an
    # hourly check is well within any commitment's tolerance. The score recompute
    # (REQ-M6-24) needs exactly this granularity too — "time itself changes recency."
    scheduler.add_job(_run_absence_detection, "interval", hours=1, id="absence_collector")
    scheduler.add_job(_run_score_recompute, "interval", hours=1, id="score_recompute")
    scheduler.start()
    logger.info(
        "worker started — absence collector and score recompute registered on the "
        "hourly heartbeat"
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
