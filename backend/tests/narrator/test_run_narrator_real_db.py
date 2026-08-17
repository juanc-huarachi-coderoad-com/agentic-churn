"""Real-DB integration for `NarrateScoreRunUseCase` — against the real,
already-scored Meridian fixture. `LLMPort` faked (no live Anthropic call
needed to prove the adapters read real data correctly); the honest-failure
case for a missing model key runs against the *real* `AnthropicLLMAdapter`,
since that's exactly the path with no key that needs proving.
"""

from typing import Any, TypeVar
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import engine
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.narrator.adapters.sqlalchemy_repository import (
    SqlAlchemyClientContextRepository,
    SqlAlchemyNarratorOutputRepository,
    SqlAlchemyPlaybookRepository,
    SqlAlchemyScoreContextRepository,
)
from app.narrator.application.prompts.narration_v1 import NarrationModelOutput
from app.narrator.application.use_cases import NarrateScoreRunUseCase
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter
from app.readers.application.ports import LLMPort

T = TypeVar("T")


class _FakeLLM(LLMPort):
    def __init__(self, response: Any) -> None:
        self._response = response

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        return self._response


async def _score_run_with_contributions() -> UUID | None:
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT sr.id FROM score_runs sr "
                    "JOIN score_contributions sc ON sc.score_run_id = sr.id "
                    "GROUP BY sr.id HAVING count(sc.id) > 0 "
                    "ORDER BY sr.computed_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        return row.id if row is not None else None


async def _cleanup(score_run_id: UUID) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM narrator_outputs WHERE score_run_id = :id"), {"id": score_run_id}
        )


async def test_fabricated_headline_falls_back_to_the_real_score_and_band():
    """Reproduces the exact live-verification scenario this feature's own
    tasks.md records: a fabricated headline is discarded, and the fallback
    template is filled from the real `score_runs`/`issues` rows, not test
    doubles."""
    score_run_id = await _score_run_with_contributions()
    if score_run_id is None:
        pytest.skip(
            "No score_runs row with contributions exists yet — run "
            "scripts/seed_score_fixture.py + compute_score.py first"
        )
    await _cleanup(score_run_id)

    # BucketedFernetEncryption, not the legacy FernetEncryption this file
    # used before specs/011-production-hardening's crypto-shredding work
    # (User Story 1) — every event body in the ledger is bucket-encrypted
    # now, so the old single-key adapter can no longer decrypt anything on a
    # freshly-seeded database (a real, previously-masked bug found via this
    # feature's own clean-slate verification: the shared dev database still
    # had pre-bucketing legacy-encrypted rows the old code happened to hit).
    encryption = BucketedFernetEncryption(
        FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
    )
    async with AsyncSession(engine) as session:
        use_case = NarrateScoreRunUseCase(
            llm=_FakeLLM(
                NarrationModelOutput(
                    headline="Fabricated: Xyzcorp lost 5000 points to Qwerty.",
                    reasons=[],
                    actions=[],
                )
            ),
            score_context=SqlAlchemyScoreContextRepository(session),
            client_context=SqlAlchemyClientContextRepository(session, encryption),
            playbook=SqlAlchemyPlaybookRepository(session),
            repository=SqlAlchemyNarratorOutputRepository(session),
        )
        output = await use_case.execute(score_run_id)

    assert output is not None
    assert output.fact_check_passed is False
    assert "Xyzcorp" not in output.headline
    assert " — " in output.headline  # "{score} — {band}. Top issue: ..."

    await _cleanup(score_run_id)


async def test_exactly_one_narrator_outputs_row_per_score_run():
    """`narrator_outputs.score_run_id UNIQUE` — a second `persist()` call for
    the same run is a real constraint violation, not just a documented
    intent."""
    score_run_id = await _score_run_with_contributions()
    if score_run_id is None:
        pytest.skip("No score_runs row with contributions exists yet")
    await _cleanup(score_run_id)

    # BucketedFernetEncryption, not the legacy FernetEncryption this file
    # used before specs/011-production-hardening's crypto-shredding work
    # (User Story 1) — every event body in the ledger is bucket-encrypted
    # now, so the old single-key adapter can no longer decrypt anything on a
    # freshly-seeded database (a real, previously-masked bug found via this
    # feature's own clean-slate verification: the shared dev database still
    # had pre-bucketing legacy-encrypted rows the old code happened to hit).
    encryption = BucketedFernetEncryption(
        FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
    )
    async with AsyncSession(engine) as session:
        repo = SqlAlchemyNarratorOutputRepository(session)
        fabricated = NarrationModelOutput(
            headline="Fabricated fact 999.", reasons=[], actions=[]
        )
        use_case = NarrateScoreRunUseCase(
            llm=_FakeLLM(fabricated),
            score_context=SqlAlchemyScoreContextRepository(session),
            client_context=SqlAlchemyClientContextRepository(session, encryption),
            playbook=SqlAlchemyPlaybookRepository(session),
            repository=repo,
        )
        await use_case.execute(score_run_id)

        with pytest.raises(Exception):  # noqa: B017 — asserts the real DB constraint, not a specific driver exception type
            await use_case.execute(score_run_id)

    await _cleanup(score_run_id)


async def test_missing_generation_model_key_fails_honestly_against_the_real_adapter():
    """quickstart.md §10 — a configuration failure must never look identical
    to the intentional total-fact-check-failure fallback."""
    score_run_id = await _score_run_with_contributions()
    if score_run_id is None:
        pytest.skip("No score_runs row with contributions exists yet")

    # BucketedFernetEncryption, not the legacy FernetEncryption this file
    # used before specs/011-production-hardening's crypto-shredding work
    # (User Story 1) — every event body in the ledger is bucket-encrypted
    # now, so the old single-key adapter can no longer decrypt anything on a
    # freshly-seeded database (a real, previously-masked bug found via this
    # feature's own clean-slate verification: the shared dev database still
    # had pre-bucketing legacy-encrypted rows the old code happened to hit).
    encryption = BucketedFernetEncryption(
        FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
    )
    async with AsyncSession(engine) as session:
        use_case = NarrateScoreRunUseCase(
            llm=AnthropicLLMAdapter("", "claude-sonnet-5"),  # empty key, real adapter
            score_context=SqlAlchemyScoreContextRepository(session),
            client_context=SqlAlchemyClientContextRepository(session, encryption),
            playbook=SqlAlchemyPlaybookRepository(session),
            repository=SqlAlchemyNarratorOutputRepository(session),
        )
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            await use_case.execute(score_run_id)
