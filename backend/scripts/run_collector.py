"""Manual `SimulatedCollector` trigger (research.md's Decision: `SimulatedCollector`
triggered by a script, not a route or a timer) — mirrors `scripts/seed.py`'s pattern.

Run after ``alembic upgrade head`` and ``scripts/seed.py``:
    uv run python scripts/run_collector.py --source simulated
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.db import async_session_factory  # noqa: E402
from app.ingestion.adapters.encryption import FernetEncryption  # noqa: E402
from app.ingestion.adapters.simulated_collector import SimulatedCollector  # noqa: E402
from app.ingestion.adapters.sqlalchemy_repositories import (  # noqa: E402
    SqlAlchemyClientProfileContext,
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import ReplayUseCase, RunCollectorUseCase  # noqa: E402


async def run(source: str) -> None:
    if source != "simulated":
        raise SystemExit(f"Unknown --source {source!r} — only 'simulated' exists in this feature")

    encryption = FernetEncryption(settings.encryption_key_path)
    async with async_session_factory() as session:
        use_case = RunCollectorUseCase(
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
            data_key_ref=settings.encryption_key_id,
        )
        collector = SimulatedCollector(Path(settings.collector_fixture_path))
        window_end = datetime.now(UTC)
        result = await use_case.execute(collector, window_start=window_end, window_end=window_end)
        print(
            f"envelopes_emitted={result.envelopes_emitted} "
            f"duplicates_skipped={result.duplicates_skipped} "
            f"coverage_report_id={result.coverage_report_id}"
        )

        replay = ReplayUseCase(
            events=SqlAlchemyEventRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
        )
        replay_run_id = await replay.execute(trigger="manual")
        print(f"replay_run_id={replay_run_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="simulated")
    args = parser.parse_args()
    asyncio.run(run(args.source))
