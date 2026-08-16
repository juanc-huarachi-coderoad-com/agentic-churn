"""Manual `NarrateScoreRunUseCase` trigger, mirroring `scripts/
compute_score.py`'s existing pattern — no live/chained trigger path exists
anywhere in this pipeline yet (`research.md` correction 2).

Run after ``scripts/compute_score.py``:
    uv run python scripts/run_narrator.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import async_session_factory  # noqa: E402
from app.ingestion.adapters.encryption import FernetEncryption  # noqa: E402
from app.narrator.adapters.sqlalchemy_repository import (  # noqa: E402
    SqlAlchemyClientContextRepository,
    SqlAlchemyNarratorOutputRepository,
    SqlAlchemyPlaybookRepository,
    SqlAlchemyScoreContextRepository,
)
from app.narrator.application.use_cases import NarrateScoreRunUseCase  # noqa: E402
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter  # noqa: E402


async def run() -> None:
    encryption = FernetEncryption(settings.encryption_key_path)
    async with async_session_factory() as session:
        latest_run = (
            await session.execute(
                text("SELECT id FROM score_runs ORDER BY computed_at DESC LIMIT 1")
            )
        ).one_or_none()
        if latest_run is None:
            print("No score_runs row exists yet — run scripts/compute_score.py first.")
            return

        use_case = NarrateScoreRunUseCase(
            llm=AnthropicLLMAdapter(settings.anthropic_api_key, settings.generation_model_id),
            score_context=SqlAlchemyScoreContextRepository(session),
            client_context=SqlAlchemyClientContextRepository(session, encryption),
            playbook=SqlAlchemyPlaybookRepository(session),
            repository=SqlAlchemyNarratorOutputRepository(session),
        )
        output = await use_case.execute(latest_run.id)
        if output is None:
            print("Nothing to narrate — this score run has no findings (a healthy account).")
            return
        print(
            f"headline={output.headline!r} fact_check_passed={output.fact_check_passed} "
            f"reasons={len(output.reasons)} actions={len(output.actions)}"
        )


if __name__ == "__main__":
    asyncio.run(run())
