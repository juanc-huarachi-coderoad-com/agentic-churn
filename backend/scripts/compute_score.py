"""Manual `RecomputeScoreUseCase` trigger (`trigger = manual`), mirroring
`scripts/run_collector.py`'s pattern.

Run after ``scripts/seed_score_fixture.py``:
    uv run python scripts/compute_score.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import async_session_factory  # noqa: E402
from app.scoring.adapters.sqlalchemy_repository import (  # noqa: E402
    SqlAlchemyClientProfileMultipliers,
    SqlAlchemyCoverageCheck,
    SqlAlchemyDampingRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyScoreRunRepository,
)
from app.scoring.application.use_cases import RecomputeScoreUseCase  # noqa: E402


async def run() -> None:
    async with async_session_factory() as session:
        use_case = RecomputeScoreUseCase(
            findings=SqlAlchemyFindingRepository(session),
            score_runs=SqlAlchemyScoreRunRepository(session),
            profile=SqlAlchemyClientProfileMultipliers(session),
            damping=SqlAlchemyDampingRepository(session),
            coverage=SqlAlchemyCoverageCheck(session),
        )
        run_result = await use_case.execute(trigger="manual")
        print(
            f"score={run_result.score:.2f} band={run_result.band} "
            f"total_points={run_result.total_points:.2f}"
        )


if __name__ == "__main__":
    asyncio.run(run())
