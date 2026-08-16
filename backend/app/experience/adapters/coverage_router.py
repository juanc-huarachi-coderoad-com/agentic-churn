from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, get_current_user
from app.db import get_session
from app.experience.adapters.sqlalchemy_repository import SqlAlchemyCoverageReader
from app.experience.application.use_cases import GetCoverageUseCase

router = APIRouter()


class SourceStatus(BaseModel):
    source_type: str
    status: str
    last_successful_sync_at: datetime | None


class QuarantineEntry(BaseModel):
    finding_id: UUID
    failed_check: str


class AskIntentCoverage(BaseModel):
    """specs/008-narrator-and-ask-agent — `null` when no `ask_queries` rows
    exist yet, closing SC-007's own promise that the Ask agent's fallback
    rate is visible without querying the database directly."""

    total_questions: int
    fallback_count: int
    fallback_rate: float


class CoverageResponse(BaseModel):
    """Per `contracts/coverage.md` — `architecture/07-api-spec.md`'s
    `CoverageResponse`. `quarantine` is real (feature 007's `ValidationGate`
    populates it) — empty only when nothing has actually been quarantined."""

    sources: list[SourceStatus]
    quarantine: list[QuarantineEntry]
    ask_intent_coverage: AskIntentCoverage | None = None


@router.get("/api/coverage", response_model=CoverageResponse)
async def get_coverage(
    _current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CoverageResponse:
    use_case = GetCoverageUseCase(coverage=SqlAlchemyCoverageReader(session))
    result = await use_case.execute()

    return CoverageResponse(
        sources=[
            SourceStatus(
                source_type=s.source_type,
                status=s.status,
                last_successful_sync_at=s.last_successful_sync_at,
            )
            for s in result.sources
        ],
        quarantine=[
            QuarantineEntry(finding_id=q.finding_id, failed_check=q.failed_check)
            for q in result.quarantine
        ],
        ask_intent_coverage=(
            AskIntentCoverage(
                total_questions=result.ask_intent_coverage.total_questions,
                fallback_count=result.ask_intent_coverage.fallback_count,
                fallback_rate=result.ask_intent_coverage.fallback_rate,
            )
            if result.ask_intent_coverage is not None
            else None
        ),
    )
