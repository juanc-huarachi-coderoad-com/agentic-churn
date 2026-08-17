from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.db import get_session
from app.experience.adapters.sqlalchemy_repository import (
    SqlAlchemyDampingDisclosureReader,
    SqlAlchemyFindingReader,
    SqlAlchemyScoreReader,
)
from app.experience.application.use_cases import EvidenceNotFoundError, GetEvidenceTraceUseCase
from app.ingestion.adapters.encryption import FernetEncryption

router = APIRouter()


def _join_arithmetic(clauses: list[str]) -> str:
    """`"Base 20 points for X, increased 50% for Y — 39 points total."` —
    every clause but the last joined by commas, the last (always the running
    total) set off by an em dash (`base/...md` §11.4's own illustrative
    shape)."""
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0] + "."
    return ", ".join(clauses[:-1]) + " — " + clauses[-1] + "."


class QuotedMessage(BaseModel):
    event_id: UUID
    text: str | None
    occurred_at: datetime


class EvidenceTraceResponse(BaseModel):
    """Per `contracts/evidence.md` — `architecture/07-api-spec.md`'s
    `EvidenceTraceResponse`. `arithmetic_explanation` is the joined text of
    every non-neutral factor clause (`research.md`'s Decision)."""

    finding_id: UUID
    finding_type: str
    points: float
    baseline_value: str
    current_value: str
    what_changed: list[str]
    quoted_messages: list[QuotedMessage]
    arithmetic_explanation: str
    disclosure_text: str | None = None


@router.get("/api/evidence/{score_contribution_id}", response_model=EvidenceTraceResponse)
async def get_evidence(
    score_contribution_id: UUID,
    _current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EvidenceTraceResponse:
    encryption = FernetEncryption(settings.encryption_key_path)
    use_case = GetEvidenceTraceUseCase(
        score=SqlAlchemyScoreReader(session),
        findings=SqlAlchemyFindingReader(session, encryption),
        damping=SqlAlchemyDampingDisclosureReader(session),
    )
    try:
        result = await use_case.execute(score_contribution_id)
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Evidence not found") from exc

    return EvidenceTraceResponse(
        finding_id=result.finding_id,
        finding_type=result.finding_type,
        points=result.points,
        baseline_value=result.comparison.baseline_label,
        current_value=result.comparison.current_label,
        what_changed=list(result.comparison.what_changed),
        quoted_messages=[
            QuotedMessage(event_id=m.event_id, text=m.text, occurred_at=m.occurred_at)
            for m in result.quoted_messages
        ],
        arithmetic_explanation=_join_arithmetic([c.text for c in result.arithmetic]),
        disclosure_text=result.disclosure_text,
    )
