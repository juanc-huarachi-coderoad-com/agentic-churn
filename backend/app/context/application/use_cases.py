"""`SubmitProfileUseCase` (REQ-M3-01, REQ-M3-02, REQ-M3-06) — validates the on-disk
YAML, versions it, triggers a full replay, then recomputes the score using the
newly-current profile version's multipliers (REQ-M6-25, REQ-M3-05). Depends on
`ReplayUseCase` and `RecomputeScoreUseCase` directly (application-layer ->
application-layer, across modules) rather than redefining "trigger a replay"/
"trigger a recompute" a second time — REQ-M3-06/REQ-M2-07 are explicitly the same
replay, and REQ-M6-25's post-edit recompute is explicitly the same pipeline
`RecomputeScoreUseCase` already implements, not two similar ones.

`RecomputeScoreUseCase` is optional (`None` in features/tests that don't need
scoring wired up yet) so this use case doesn't hard-require specs/004-score-engine's
module to exist for callers that only care about profile submission itself.
"""

from uuid import UUID

from app.context.application.ports import ClientProfileRepositoryPort, ProfileVersionSummary
from app.context.domain.profile_schema import ClientProfileInput
from app.ingestion.application.use_cases import ReplayUseCase
from app.scoring.application.use_cases import RecomputeScoreUseCase


class SubmitProfileUseCase:
    def __init__(
        self,
        repository: ClientProfileRepositoryPort,
        replay: ReplayUseCase,
        recompute_score: RecomputeScoreUseCase | None = None,
    ) -> None:
        self._repository = repository
        self._replay = replay
        self._recompute_score = recompute_score

    async def execute(
        self, profile: ClientProfileInput, *, authored_by_user_id: UUID
    ) -> ProfileVersionSummary:
        summary = await self._repository.insert_new_version(
            profile, authored_by_user_id=authored_by_user_id
        )
        await self._replay.execute(trigger="profile_edit")
        if self._recompute_score is not None:
            await self._recompute_score.execute(trigger="profile_edit_replay")
        return summary
