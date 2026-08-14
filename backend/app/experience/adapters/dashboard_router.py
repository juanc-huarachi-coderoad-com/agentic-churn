from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, get_current_user
from app.db import get_session
from app.experience.adapters.sqlalchemy_repository import SqlAlchemyClientProfileRepository
from app.experience.application.use_cases import DashboardState, GetDashboardShellUseCase

router = APIRouter()


class ClientHeader(BaseModel):
    client_name: str


class DashboardShellResponse(BaseModel):
    client_header: ClientHeader | None
    state: DashboardState
    learning_message: str | None = None


@router.get("/api/dashboard", response_model=DashboardShellResponse)
async def get_dashboard(
    _current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardShellResponse:
    """Per contracts/dashboard.md — a narrowed view of the full DashboardResponse
    schema (architecture/07-api-spec.md). score_block/contribution_bars/pulse_timeline/
    stakeholder_cards/coverage_line are absent, not empty placeholders (feature 006's
    job, once score_runs data exists)."""
    use_case = GetDashboardShellUseCase(
        profile_repository=SqlAlchemyClientProfileRepository(session)
    )
    result = await use_case.execute()

    return DashboardShellResponse(
        client_header=ClientHeader(client_name=result.client_name) if result.client_name else None,
        state=result.state,
        learning_message=result.learning_message,
    )
