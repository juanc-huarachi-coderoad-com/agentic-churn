"""Manual `RunReadersUseCase` trigger, mirroring `scripts/run_collector.py`/
`compute_score.py`'s pattern — runs all eight M5 readers over the ledger's
current state, gates every finding through M5a before persisting (feature
007), and prints a per-reader summary, including any isolated failure
(FR-014a).

Run after ``scripts/run_collector.py`` (and, for a real Tone finding,
``scripts/confirm_baseline.py``):
    uv run python scripts/run_readers.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.db import async_session_factory  # noqa: E402
from app.ingestion.adapters.encryption import BucketedFernetEncryption  # noqa: E402
from app.ingestion.adapters.key_store import FileKeyStore  # noqa: E402
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter  # noqa: E402
from app.readers.adapters.openai_embedding import OpenAIEmbeddingAdapter  # noqa: E402
from app.readers.adapters.pgvector_embedding_cache import CachedEmbeddingAdapter  # noqa: E402
from app.readers.adapters.sqlalchemy_repository import (  # noqa: E402
    SqlAlchemyAbsenceEventRepository,
    SqlAlchemyCandidateCorpusRepository,
    SqlAlchemyConfirmedBaselineRepository,
    SqlAlchemyEventExistenceRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyFindingTypeConfigRepository,
    SqlAlchemyMeetingTranscriptRepository,
    SqlAlchemyMessageEventRepository,
    SqlAlchemyQuarantineRepository,
    SqlAlchemyRelationshipContext,
    SqlAlchemyResponsePairRepository,
    SqlAlchemyRollupRepository,
)
from app.readers.application.absence_reader import AbsenceReader  # noqa: E402
from app.readers.application.commitment_reader import CommitmentReader  # noqa: E402
from app.readers.application.intent_reader import IntentReader  # noqa: E402
from app.readers.application.meeting_reader import MeetingReader  # noqa: E402
from app.readers.application.recurrence_reader import RecurrenceReader  # noqa: E402
from app.readers.application.relationship_reader import RelationshipReader  # noqa: E402
from app.readers.application.tone_reader import ToneReader  # noqa: E402
from app.readers.application.usage_reader import UsageReader  # noqa: E402
from app.readers.application.use_cases import RunReadersUseCase  # noqa: E402
from app.readers.application.validation_gate import ValidationGate  # noqa: E402


async def run() -> None:
    encryption = BucketedFernetEncryption(
        FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
    )
    async with async_session_factory() as session:
        findings = SqlAlchemyFindingRepository(session)
        messages = SqlAlchemyMessageEventRepository(session, encryption)
        gate = ValidationGate(
            finding_type_config=SqlAlchemyFindingTypeConfigRepository(session),
            event_existence=SqlAlchemyEventExistenceRepository(session),
        )
        quarantine = SqlAlchemyQuarantineRepository(session)
        llm = AnthropicLLMAdapter(settings.anthropic_api_key, settings.reader_model_id)

        readers = [
            CommitmentReader(SqlAlchemyResponsePairRepository(session), findings),
            UsageReader(SqlAlchemyRollupRepository(session), findings),
            AbsenceReader(SqlAlchemyAbsenceEventRepository(session), findings),
            RelationshipReader(SqlAlchemyRelationshipContext(session), findings),
            RecurrenceReader(
                SqlAlchemyCandidateCorpusRepository(session),
                # specs/027-pgvector-embedding-store — same cached wiring as
                # app.worker, so this manual script exercises the real path.
                CachedEmbeddingAdapter(
                    session,
                    OpenAIEmbeddingAdapter.MODEL_ID,
                    OpenAIEmbeddingAdapter(settings.openai_api_key),
                ),
                findings,
            ),
            ToneReader(
                messages,
                SqlAlchemyConfirmedBaselineRepository(session, encryption),
                llm,
                findings,
            ),
            IntentReader(messages, llm, findings),
            MeetingReader(
                SqlAlchemyMeetingTranscriptRepository(session, encryption), llm, findings
            ),
        ]
        use_case = RunReadersUseCase(
            readers=readers, findings=findings, gate=gate, quarantine=quarantine
        )
        results = await use_case.execute()

        for result in results:
            if result.error is None:
                print(
                    f"{result.reader_type}: findings_persisted={result.findings_persisted} "
                    f"findings_quarantined={result.findings_quarantined}"
                )
            else:
                print(
                    f"{result.reader_type}: findings_persisted={result.findings_persisted} "
                    f"findings_quarantined={result.findings_quarantined} "
                    f"FAILED — {result.error}"
                )


if __name__ == "__main__":
    asyncio.run(run())
