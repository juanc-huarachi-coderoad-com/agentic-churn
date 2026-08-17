"""`POST /api/feedback` (`architecture/07-api-spec.md`, `contracts/
feedback.md`) — M4's first real route. Composition root, matching
`profile_router.py`'s existing pattern in the same module.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, get_current_user
from app.context.adapters.sqlalchemy_repository import (
    SqlAlchemyFeedbackFindingReader,
    SqlAlchemyFeedbackVerdictRepository,
    SqlAlchemyIssueTopFindingReader,
)
from app.context.application.use_cases import (
    FindingNotFoundError,
    IssueNotFoundError,
    RecordFeedbackVerdictUseCase,
    VerdictRequiresFindingError,
)
from app.db import get_session

router = APIRouter()


class FeedbackRequest(BaseModel):
    finding_id: UUID | None = None
    issue_id: UUID | None = None
    verdict: Literal["correct", "false_alarm", "resolved"]


def _build_use_case(session: AsyncSession) -> RecordFeedbackVerdictUseCase:
    return RecordFeedbackVerdictUseCase(
        findings=SqlAlchemyFeedbackFindingReader(session),
        issues=SqlAlchemyIssueTopFindingReader(session),
        verdicts=SqlAlchemyFeedbackVerdictRepository(session),
    )


@router.post("/api/feedback", status_code=204)
async def submit_feedback(
    body: FeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    if body.finding_id is None and body.issue_id is None:
        raise HTTPException(status_code=422, detail="finding_id or issue_id is required")

    use_case = _build_use_case(session)
    try:
        await use_case.execute(
            finding_id=body.finding_id,
            issue_id=body.issue_id,
            verdict=body.verdict,
            submitted_by_user_id=current_user.user_id,
        )
    except VerdictRequiresFindingError:
        raise HTTPException(
            status_code=422,
            detail="false_alarm/correct verdicts require a specific finding_id",
        ) from None
    except (FindingNotFoundError, IssueNotFoundError):
        raise HTTPException(status_code=404, detail="Not found") from None
