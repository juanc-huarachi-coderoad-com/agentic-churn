"""`PATCH /api/admin/finding-types/{finding_type}` (specs/011-production-
hardening, User Story 4, `contracts/weight-recalibration.md`) — a new route,
no prior document names it (weight recalibration was always described as a
workshop *process*, `decisions/00-open-questions-resolved.md` Q4; this is the
system-side deliverable that process needs). Composition root, matching
`feedback_router.py`/`profile_router.py`'s existing pattern.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, require_admin
from app.db import get_session
from app.scoring.adapters.sqlalchemy_repository import (
    SqlAlchemyClientProfileMultipliers,
    SqlAlchemyCoverageCheck,
    SqlAlchemyDampingRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyFindingTypeConfigWriter,
    SqlAlchemyScoreRunRepository,
)
from app.scoring.application.ports import FindingTypeNotFoundError
from app.scoring.application.use_cases import (
    InvalidWeightError,
    RecomputeScoreUseCase,
    UpdateFindingTypeWeightUseCase,
)

router = APIRouter()


class WeightUpdateRequest(BaseModel):
    base_points: float


class WeightUpdateResponse(BaseModel):
    finding_type: str
    base_points: float
    config_version: str
    changed_at: datetime


def _build_use_case(session: AsyncSession) -> UpdateFindingTypeWeightUseCase:
    return UpdateFindingTypeWeightUseCase(
        finding_type_config=SqlAlchemyFindingTypeConfigWriter(session),
        recompute_score=RecomputeScoreUseCase(
            findings=SqlAlchemyFindingRepository(session),
            score_runs=SqlAlchemyScoreRunRepository(session),
            profile=SqlAlchemyClientProfileMultipliers(session),
            damping=SqlAlchemyDampingRepository(session),
            coverage=SqlAlchemyCoverageCheck(session),
        ),
    )


@router.patch(
    "/api/admin/finding-types/{finding_type}", response_model=WeightUpdateResponse
)
async def update_finding_type_weight(
    finding_type: str,
    body: WeightUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> WeightUpdateResponse:
    use_case = _build_use_case(session)
    try:
        result = await use_case.execute(
            finding_type=finding_type,
            new_base_points=body.base_points,
            changed_by_user_id=current_user.user_id,
        )
    except InvalidWeightError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except FindingTypeNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Unknown finding_type: {finding_type!r}"
        ) from None

    return WeightUpdateResponse(
        finding_type=finding_type,
        base_points=body.base_points,
        config_version=result.new_config_version,
        changed_at=result.changed_at,
    )
