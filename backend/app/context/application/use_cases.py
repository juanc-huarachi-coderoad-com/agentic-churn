"""`SubmitProfileUseCase` (REQ-M3-01, REQ-M3-02, REQ-M3-06) — validates the on-disk
YAML, versions it, and triggers a full replay. Depends on `ReplayUseCase` directly
(application-layer -> application-layer, across modules) rather than redefining
"trigger a replay" a second time — REQ-M3-06 and REQ-M2-07 are explicitly the same
replay, not two similar ones.
"""

from uuid import UUID

from app.context.application.ports import ClientProfileRepositoryPort, ProfileVersionSummary
from app.context.domain.profile_schema import ClientProfileInput
from app.ingestion.application.use_cases import ReplayUseCase


class SubmitProfileUseCase:
    def __init__(
        self,
        repository: ClientProfileRepositoryPort,
        replay: ReplayUseCase,
    ) -> None:
        self._repository = repository
        self._replay = replay

    async def execute(
        self, profile: ClientProfileInput, *, authored_by_user_id: UUID
    ) -> ProfileVersionSummary:
        summary = await self._repository.insert_new_version(
            profile, authored_by_user_id=authored_by_user_id
        )
        await self._replay.execute(trigger="profile_edit")
        return summary
