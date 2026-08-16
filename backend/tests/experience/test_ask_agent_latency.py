"""Real `AnthropicLLMAdapter`, real Postgres — asserts end-to-end response
time stays under 3s for an intent-matched question (REQ-M9-08). Run
separately from `test_ask_agent_graph.py`'s fake-backed branch-coverage
tests, since this one needs the real network round trip those deliberately
avoid (`tests/strategy.md`).
"""

import time
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import engine
from app.experience.adapters.ask_agent_graph import AskAgentToolkit, LangGraphAskAgent
from app.experience.adapters.sqlalchemy_repository import (
    SqlAlchemyAskQueryRepository,
    SqlAlchemyCoverageReader,
    SqlAlchemyFindingReader,
    SqlAlchemyLedgerQueryRepository,
    SqlAlchemyNarratorReadRepository,
    SqlAlchemyScoreReader,
    SqlAlchemyStakeholderReader,
)
from app.ingestion.adapters.encryption import FernetEncryption
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter

_LATENCY_BUDGET_SECONDS = 3.0


@pytest.mark.skipif(
    not settings.anthropic_api_key,
    reason="ANTHROPIC_API_KEY not configured — this test needs a real model call (REQ-M9-08)",
)
async def test_intent_matched_question_responds_within_the_3s_budget():
    encryption = FernetEncryption(settings.encryption_key_path)
    async with AsyncSession(engine) as session:
        toolkit = AskAgentToolkit(
            ledger=SqlAlchemyLedgerQueryRepository(session, encryption),
            findings=SqlAlchemyFindingReader(session, encryption),
            score=SqlAlchemyScoreReader(session),
            stakeholders=SqlAlchemyStakeholderReader(session),
        )
        agent = LangGraphAskAgent(
            llm=AnthropicLLMAdapter(settings.anthropic_api_key, settings.generation_model_id),
            toolkit=toolkit,
            narrator=SqlAlchemyNarratorReadRepository(session),
            coverage=SqlAlchemyCoverageReader(session),
            ask_queries=SqlAlchemyAskQueryRepository(session),
        )

        started = time.monotonic()
        result = await agent.answer("why did the score go up?", asked_by_user_id=uuid4())
        elapsed = time.monotonic() - started

    assert elapsed < _LATENCY_BUDGET_SECONDS
    assert result.response_time_ms < _LATENCY_BUDGET_SECONDS * 1000
