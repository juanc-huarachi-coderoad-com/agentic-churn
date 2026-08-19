from datetime import datetime
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.db import get_session
from app.experience.adapters.sqlalchemy_repository import (
    SqlAlchemyClientProfileRepository,
    SqlAlchemyCoverageReader,
    SqlAlchemyIdentityGapReader,
    SqlAlchemyNarratorReadRepository,
    SqlAlchemyPulseEventReader,
    SqlAlchemyScoreReader,
    SqlAlchemyStakeholderReader,
)
from app.experience.application.use_cases import GetDashboardUseCase
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.observability.adapters.tracing import traced

router = APIRouter()


class ClientHeader(BaseModel):
    client_name: str
    band: str | None = None
    days_to_renewal: int | None = None


class ScoreBlock(BaseModel):
    score: float
    band: str
    trend: list[float]


class ContributionBar(BaseModel):
    score_contribution_id: UUID
    label: str
    points: float
    is_positive: bool


class PulseEvent(BaseModel):
    event_id: UUID
    occurred_at: datetime
    event_type: str
    severity: str
    quoted_text: str | None
    score_contribution_id: UUID


class StakeholderCard(BaseModel):
    stakeholder_id: UUID | None
    name: str
    role: str
    tone_trajectory: str
    last_seen_at: datetime | None
    status: str


class CoverageLine(BaseModel):
    sources_read: int
    sources_expected: int
    complete_to: datetime | None
    status: str


class NarratorReason(BaseModel):
    text: str
    points: float
    evidence_event_ids: list[str]


class NarratorAction(BaseModel):
    text: str
    owner: str
    due_date: str


class NarratorSummary(BaseModel):
    """specs/008-narrator-and-ask-agent — `contracts/dashboard.md`."""

    headline: str
    reasons: list[NarratorReason]
    actions: list[NarratorAction]


class DashboardResponse(BaseModel):
    """Per `contracts/dashboard.md` — the full `DashboardResponse` shape
    (`architecture/07-api-spec.md`) once a current profile exists;
    `client_header: None, state: "no_profile"` (all other fields default-
    empty) for a freshly-provisioned, unseeded database (feature 002)."""

    client_header: ClientHeader | None
    state: str
    message: str | None = None
    score_block: ScoreBlock | None = None
    contribution_bars: list[ContributionBar] = []
    pulse_timeline: list[PulseEvent] = []
    stakeholder_cards: list[StakeholderCard] = []
    coverage_line: CoverageLine | None = None
    narrator: NarratorSummary | None = None


@router.get("/api/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    _current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardResponse:
    encryption = BucketedFernetEncryption(
        FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
    )
    use_case = GetDashboardUseCase(
        profile=SqlAlchemyClientProfileRepository(session),
        score=SqlAlchemyScoreReader(session),
        pulse=SqlAlchemyPulseEventReader(session, encryption),
        stakeholders=SqlAlchemyStakeholderReader(session),
        coverage=SqlAlchemyCoverageReader(session),
        identity_gaps=SqlAlchemyIdentityGapReader(session),
        narrator=SqlAlchemyNarratorReadRepository(session),
    )
    with traced("dashboard_load"):
        result = await use_case.execute()

    return DashboardResponse(
        client_header=(
            ClientHeader(
                client_name=result.client_header.client_name,
                band=result.client_header.band,
                days_to_renewal=result.client_header.days_to_renewal,
            )
            if result.client_header is not None
            else None
        ),
        state=result.state,
        message=result.message,
        score_block=(
            ScoreBlock(
                score=result.score_block.score,
                band=result.score_block.band,
                trend=result.score_block.trend,
            )
            if result.score_block is not None
            else None
        ),
        contribution_bars=[
            ContributionBar(
                score_contribution_id=c.score_contribution_id,
                label=c.label,
                points=c.points,
                is_positive=c.is_positive,
            )
            for c in result.contribution_bars
        ],
        pulse_timeline=[
            PulseEvent(
                event_id=p.event_id,
                occurred_at=p.occurred_at,
                event_type=p.event_type,
                severity=p.severity,
                quoted_text=p.quoted_text,
                score_contribution_id=p.score_contribution_id,
            )
            for p in result.pulse_timeline
        ],
        stakeholder_cards=[
            StakeholderCard(
                stakeholder_id=s.stakeholder_id,
                name=s.name,
                role=s.role,
                tone_trajectory=s.tone_trajectory,
                last_seen_at=s.last_seen_at,
                status=s.status,
            )
            for s in result.stakeholder_cards
        ],
        coverage_line=(
            CoverageLine(
                sources_read=result.coverage_line.sources_read,
                sources_expected=result.coverage_line.sources_expected,
                complete_to=result.coverage_line.complete_to,
                status=result.coverage_line.status,
            )
            if result.coverage_line is not None
            else None
        ),
        narrator=(
            NarratorSummary(
                headline=result.narrator.headline,
                reasons=[
                    NarratorReason(
                        text=str(r["text"]),
                        points=float(r["points"]),  # type: ignore[arg-type]
                        evidence_event_ids=[
                            str(e) for e in cast(list[Any], r["evidence_event_ids"])
                        ],
                    )
                    for r in result.narrator.reasons
                ],
                actions=[
                    NarratorAction(
                        text=str(a["text"]), owner=str(a["owner"]), due_date=str(a["due_date"])
                    )
                    for a in result.narrator.actions
                ],
            )
            if result.narrator is not None
            else None
        ),
    )
