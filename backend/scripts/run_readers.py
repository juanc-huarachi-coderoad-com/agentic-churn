"""Manual `RunReadersUseCase` trigger, mirroring `scripts/run_collector.py`/
`compute_score.py`'s pattern — runs all five M5 readers over the ledger's
current state and prints a per-reader summary, including any isolated failure
(FR-014a).

Run after ``scripts/run_collector.py``:
    uv run python scripts/run_readers.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.db import async_session_factory  # noqa: E402
from app.readers.adapters.openai_embedding import OpenAIEmbeddingAdapter  # noqa: E402
from app.readers.adapters.sqlalchemy_repository import (  # noqa: E402
    SqlAlchemyAbsenceEventRepository,
    SqlAlchemyCandidateCorpusRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyRelationshipContext,
    SqlAlchemyResponsePairRepository,
    SqlAlchemyRollupRepository,
)
from app.readers.application.absence_reader import AbsenceReader  # noqa: E402
from app.readers.application.commitment_reader import CommitmentReader  # noqa: E402
from app.readers.application.recurrence_reader import RecurrenceReader  # noqa: E402
from app.readers.application.relationship_reader import RelationshipReader  # noqa: E402
from app.readers.application.usage_reader import UsageReader  # noqa: E402
from app.readers.application.use_cases import RunReadersUseCase  # noqa: E402


async def run() -> None:
    async with async_session_factory() as session:
        findings = SqlAlchemyFindingRepository(session)
        readers = [
            CommitmentReader(SqlAlchemyResponsePairRepository(session), findings),
            UsageReader(SqlAlchemyRollupRepository(session), findings),
            AbsenceReader(SqlAlchemyAbsenceEventRepository(session), findings),
            RelationshipReader(SqlAlchemyRelationshipContext(session), findings),
            RecurrenceReader(
                SqlAlchemyCandidateCorpusRepository(session),
                OpenAIEmbeddingAdapter(settings.openai_api_key),
                findings,
            ),
        ]
        use_case = RunReadersUseCase(readers=readers, findings=findings)
        results = await use_case.execute()

        for result in results:
            if result.error is None:
                print(f"{result.reader_type}: findings_persisted={result.findings_persisted}")
            else:
                print(f"{result.reader_type}: FAILED — {result.error}")


if __name__ == "__main__":
    asyncio.run(run())
