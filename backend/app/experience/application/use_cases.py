from dataclasses import dataclass
from typing import Literal

from app.experience.application.ports import ClientProfileRepositoryPort

DashboardState = Literal["learning", "no_profile"]


@dataclass(frozen=True)
class DashboardShellResult:
    client_name: str | None
    state: DashboardState
    learning_message: str | None


class GetDashboardShellUseCase:
    """Renders only what's honestly available today (REQ-M8-01, REQ-M8-07) — never the
    full REQ-M8-02 component set, which needs score_runs/narrator_outputs/rollups data
    that doesn't exist until feature 006 (contracts/dashboard.md)."""

    def __init__(self, profile_repository: ClientProfileRepositoryPort) -> None:
        self._profiles = profile_repository

    async def execute(self) -> DashboardShellResult:
        profile = await self._profiles.get_current()
        if profile is None:
            return DashboardShellResult(client_name=None, state="no_profile", learning_message=None)

        return DashboardShellResult(
            client_name=profile.client_name,
            state="learning",
            learning_message="Still learning — 0 of 6 signal types available.",
        )
