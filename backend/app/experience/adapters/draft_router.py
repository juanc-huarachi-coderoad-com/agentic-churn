"""`POST /api/drafts`, `.../copy`, `.../log-as-sent` — the draft composer's
three routes. Composition root: constructs the use case with all its port
implementations, matching `ask_router.py`/`dashboard_router.py`'s existing
pattern. First real implementation of these routes —
`architecture/07-api-spec.md` has documented their schemas since before
this feature existed.

**There is no `/send` route in this file, or anywhere in this codebase —
not disabled, not feature-flagged (REQ-M10-P1).** Mechanically confirmed by
`tests/experience/test_no_external_transport.py`, not just this file's own
absence of one.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, require_full_access
from app.config import settings
from app.db import get_session
from app.experience.adapters.sqlalchemy_repository import (
    SqlAlchemyClientProfileRepository,
    SqlAlchemyDraftMessageRepository,
    SqlAlchemyFindingReader,
    SqlAlchemyLedgerQueryRepository,
    SqlAlchemyNarratorReadRepository,
    SqlAlchemyPlaybookReader,
    SqlAlchemyScoreReader,
    SqlAlchemyStakeholderReader,
)
from app.experience.application.use_cases import (
    DraftCheckFailedError,
    EvidenceNotFoundError,
    GenerateDraftUseCase,
    StakeholderNotFoundError,
)
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter

router = APIRouter()

_CHECK_FAILURE_DETAIL = "Couldn't generate a draft — try again"
"""The exact string `architecture/06-error-handling.md` already defines for
this component's generation errors/timeouts — reused verbatim for a
pre-display-check failure too, no distinction between the two failure
kinds (`research.md` Decision 7, Clarifications 2026-08-16)."""


class DraftRequest(BaseModel):
    score_contribution_id: UUID
    stakeholder_id: UUID
    tone_variant: str


class DraftResponse(BaseModel):
    id: UUID
    draft_text: str
    tone_variant: str
    evidence_event_ids: list[UUID]
    checks_passed: bool


def _build_use_case(session: AsyncSession) -> GenerateDraftUseCase:
    encryption = BucketedFernetEncryption(
        FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
    )
    llm = AnthropicLLMAdapter(settings.anthropic_api_key, settings.generation_model_id)
    return GenerateDraftUseCase(
        score=SqlAlchemyScoreReader(session),
        stakeholders=SqlAlchemyStakeholderReader(session),
        profile=SqlAlchemyClientProfileRepository(session),
        ledger=SqlAlchemyLedgerQueryRepository(session, encryption),
        narrator=SqlAlchemyNarratorReadRepository(session),
        playbook=SqlAlchemyPlaybookReader(session),
        findings=SqlAlchemyFindingReader(session, encryption),
        drafts=SqlAlchemyDraftMessageRepository(session),
        llm=llm,
    )


@router.post("/api/drafts", response_model=DraftResponse)
async def create_draft(
    request: DraftRequest,
    current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> DraftResponse:
    use_case = _build_use_case(session)
    try:
        result = await use_case.execute(
            score_contribution_id=request.score_contribution_id,
            stakeholder_id=request.stakeholder_id,
            tone_variant=request.tone_variant,
            requested_by_user_id=current_user.user_id,
        )
    except (EvidenceNotFoundError, StakeholderNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    except DraftCheckFailedError as exc:
        raise HTTPException(status_code=422, detail=_CHECK_FAILURE_DETAIL) from exc

    return DraftResponse(
        id=result.id,
        draft_text=result.draft_text,
        tone_variant=result.tone_variant,
        evidence_event_ids=list(result.evidence_event_ids),
        checks_passed=result.checks_passed,
    )


@router.post("/api/drafts/{draft_id}/copy", status_code=204)
async def copy_draft(
    draft_id: UUID,
    _current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> None:
    found = await SqlAlchemyDraftMessageRepository(session).stamp_copied(draft_id)
    if not found:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/api/drafts/{draft_id}/log-as-sent", status_code=204)
async def log_draft_as_sent(
    draft_id: UUID,
    _current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> None:
    found = await SqlAlchemyDraftMessageRepository(session).stamp_logged_manually(draft_id)
    if not found:
        raise HTTPException(status_code=404, detail="Not found")
