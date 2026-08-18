"""`POST /api/ask` — the Ask agent's route. Composition root: constructs
`LangGraphAskAgent` with all its port implementations, matching
`dashboard_router.py`/`coverage_router.py`'s existing pattern. First real
implementation of this route — `architecture/07-api-spec.md` has documented
its schema since before this feature existed.
"""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, require_full_access
from app.config import settings
from app.db import get_session
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
from app.experience.domain.entities import ComponentPart, TextPart
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.observability.adapters.tracing import traced
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter

router = APIRouter()


class AskRequest(BaseModel):
    question: str


class ResponsePartSchema(BaseModel):
    """specs/014-ask-agent-response-formats — a discriminated union: `markdown`
    is present iff `type == "text"`; `component`/`component_props` are
    present iff `type == "component"` (contracts/ask.md)."""

    type: Literal["text", "component"]
    markdown: str | None = None
    component: str | None = None
    component_props: dict[str, Any] | None = None


class AskAnsweredResponse(BaseModel):
    """Replaces the old flat `AskComponentResponse`. For `response_mode ==
    "component_only"` (unchanged default), `parts` is always exactly one
    component part carrying the identical data the old shape returned —
    contracts/ask.md's backward-compatibility guarantee."""

    intent: str
    parts: list[ResponsePartSchema]


class AskFallbackResponse(BaseModel):
    fallback_text: str
    sources: list[UUID]
    declined_reason: str | None = None


@router.post("/api/ask", response_model=AskAnsweredResponse | AskFallbackResponse)
async def ask(
    request: AskRequest,
    current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> AskAnsweredResponse | AskFallbackResponse:
    with traced("ask_query"):
        encryption = BucketedFernetEncryption(
            FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
        )
        llm = AnthropicLLMAdapter(settings.anthropic_api_key, settings.generation_model_id)
        toolkit = AskAgentToolkit(
            ledger=SqlAlchemyLedgerQueryRepository(session, encryption),
            findings=SqlAlchemyFindingReader(session, encryption),
            score=SqlAlchemyScoreReader(session),
            stakeholders=SqlAlchemyStakeholderReader(session),
        )
        agent = LangGraphAskAgent(
            llm=llm,
            toolkit=toolkit,
            narrator=SqlAlchemyNarratorReadRepository(session),
            coverage=SqlAlchemyCoverageReader(session),
            ask_queries=SqlAlchemyAskQueryRepository(session),
        )

        result = await agent.answer(request.question, asked_by_user_id=current_user.user_id)

    if result.parts:
        parts: list[ResponsePartSchema] = []
        for part in result.parts:
            if isinstance(part, TextPart):
                parts.append(ResponsePartSchema(type="text", markdown=part.markdown))
            elif isinstance(part, ComponentPart):
                parts.append(
                    ResponsePartSchema(
                        type="component",
                        component=part.component,
                        component_props=part.component_props,
                    )
                )
        return AskAnsweredResponse(intent=result.intent or "", parts=parts)
    return AskFallbackResponse(
        fallback_text=result.fallback_text or "",
        sources=list(result.sources),
        declined_reason=result.declined_reason,
    )
