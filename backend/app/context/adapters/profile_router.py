"""`POST /api/profile/reload` and `GET /api/profile` (contracts/profile-reload.md,
architecture/07-api-spec.md). Both routes require a bearer token — feature 002's gate
applies to every route except `/auth/login` and `/health`.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, get_current_user, require_full_access
from app.config import settings
from app.context.adapters.sqlalchemy_repository import SqlAlchemyClientProfileRepository
from app.context.adapters.yaml_profile_loader import ProfileFileNotFoundError, load_profile_yaml
from app.context.application.ports import ProfileVersionSummary
from app.context.application.use_cases import SubmitProfileUseCase
from app.context.domain.profile_schema import ClientProfileInput
from app.db import get_session
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.use_cases import ReplayUseCase
from app.scoring.adapters.sqlalchemy_repository import (
    SqlAlchemyClientProfileMultipliers,
    SqlAlchemyCoverageCheck,
    SqlAlchemyDampingRepository,
    SqlAlchemyFindingRepository,
    SqlAlchemyScoreRunRepository,
)
from app.scoring.application.use_cases import RecomputeScoreUseCase

router = APIRouter()


class StakeholderResponse(BaseModel):
    name: str
    role: str | None
    influence: str
    signs_renewal: bool


class ProductAreaResponse(BaseModel):
    key: str
    criticality: str


class CommitmentResponse(BaseModel):
    type: str
    threshold_business_hours: float | None


class ProfileResponse(BaseModel):
    version_number: int
    client_name: str
    renewal_date: str
    contract_value_band: str
    stakeholders: list[StakeholderResponse]
    product_areas: list[ProductAreaResponse]
    commitments: list[CommitmentResponse]
    # specs/011-production-hardening, User Story 5 (FR-017) — previously missing
    # from this response entirely, even though the editor needs to show both.
    exclusions: list[str]
    communication_norms: str | None


def _to_response(summary: ProfileVersionSummary) -> ProfileResponse:
    return ProfileResponse(
        version_number=summary.version_number,
        client_name=summary.client_name,
        renewal_date=summary.renewal_date.isoformat(),
        contract_value_band=summary.contract_value_band,
        stakeholders=[
            StakeholderResponse(
                name=s.name, role=s.role, influence=s.influence, signs_renewal=s.signs_renewal
            )
            for s in summary.stakeholders
        ],
        product_areas=[
            ProductAreaResponse(key=a.key, criticality=a.criticality)
            for a in summary.product_areas
        ],
        commitments=[
            CommitmentResponse(type=c.type, threshold_business_hours=c.threshold_business_hours)
            for c in summary.commitments
        ],
        exclusions=summary.exclusions,
        communication_norms=summary.communication_norms,
    )


# Composition-root-adjacent: this feature has no dedicated encryption dependency-
# override yet (app.main provides one BucketedFernetEncryption instance at import
# time), so the replay path constructs its own from settings — matching app.main's
# own startup wiring rather than adding a second injection mechanism for one route.
def _build_replay_use_case(session: AsyncSession) -> ReplayUseCase:
    return ReplayUseCase(
        events=SqlAlchemyEventRepository(session),
        profile_context=SqlAlchemyClientProfileContext(session),
        encryption=BucketedFernetEncryption(
            FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
        ),
    )


def _build_recompute_score_use_case(session: AsyncSession) -> RecomputeScoreUseCase:
    return RecomputeScoreUseCase(
        findings=SqlAlchemyFindingRepository(session),
        score_runs=SqlAlchemyScoreRunRepository(session),
        profile=SqlAlchemyClientProfileMultipliers(session),
        damping=SqlAlchemyDampingRepository(session),
        coverage=SqlAlchemyCoverageCheck(session),
    )


@router.post("/api/profile/reload", response_model=ProfileResponse)
async def reload_profile(
    current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    try:
        profile = load_profile_yaml(settings.client_profile_path)
    except ProfileFileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except ValidationError as exc:
        # include_context=False: pydantic's default errors() embeds the raw exception
        # object in `ctx` (e.g. a ValueError instance), which isn't JSON-serializable —
        # FastAPI's default handler would 500 trying to render this 422's own body.
        raise HTTPException(
            status_code=422, detail=exc.errors(include_context=False, include_url=False)
        ) from None

    use_case = SubmitProfileUseCase(
        repository=SqlAlchemyClientProfileRepository(session),
        replay=_build_replay_use_case(session),
        recompute_score=_build_recompute_score_use_case(session),
    )
    summary = await use_case.execute(profile, authored_by_user_id=current_user.user_id)
    return _to_response(summary)


@router.post("/api/profile", response_model=ProfileResponse)
async def submit_profile(
    profile: ClientProfileInput,
    current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    """specs/011-production-hardening, User Story 5 — the Post-MVP editor route
    `architecture/07-api-spec.md` already named ahead of time. `profile`'s type
    is `ClientProfileInput` — the exact same Pydantic model `load_profile_yaml`
    already builds from the YAML file, so FastAPI validates a structured JSON
    submission with the identical rules (`research.md` Decision 4): a malformed
    body is rejected with a `422` and its own field-level detail *before* this
    function is even called, and a body that fails a cross-field rule (e.g. no
    stakeholder with `signs_renewal: true`) raises the same `pydantic.
    ValidationError` FastAPI already turns into a structured `422` by default.
    `SubmitProfileUseCase` is unmodified — this route is a second front door to
    code that already exists.
    """
    use_case = SubmitProfileUseCase(
        repository=SqlAlchemyClientProfileRepository(session),
        replay=_build_replay_use_case(session),
        recompute_score=_build_recompute_score_use_case(session),
    )
    summary = await use_case.execute(profile, authored_by_user_id=current_user.user_id)
    return _to_response(summary)


@router.get("/api/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    summary = await SqlAlchemyClientProfileRepository(session).get_current()
    if summary is None:
        raise HTTPException(status_code=404, detail="No client profile exists yet")
    return _to_response(summary)
