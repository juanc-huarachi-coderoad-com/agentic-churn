"""Background worker process — the hourly-heartbeat/event-triggered recompute host.

Starts and stays running in this feature; real scheduled jobs (the sense loop's hourly
heartbeat, Postgres LISTEN/NOTIFY-triggered recompute) are added starting build-order
Phase 3+ once the ledger and scoring engine exist (architecture/03-technology-stack.md
§Background/scheduled processing). Run with: uv run python -m app.worker
"""

import logging
import signal
import time

from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    scheduler = BackgroundScheduler()
    scheduler.start()
    logger.info("worker started — no scheduled jobs registered yet (Project Foundation)")

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
