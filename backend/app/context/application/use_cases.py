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

from app.context.application.ports import (
    ClientProfileRepositoryPort,
    FeedbackFindingReadPort,
    FeedbackVerdictRepositoryPort,
    IssueTopFindingReadPort,
    ProfileVersionSummary,
)
from app.context.domain.damping_calculator import (
    build_disclosure_text,
    compute_weight,
    pattern_signature,
)
from app.context.domain.entities import DampingWeight
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


# ---------------------------------------------------------------------------
# M4 · Feedback memory (`specs/010-feedback-memory/data-model.md`)
# ---------------------------------------------------------------------------


class VerdictRequiresFindingError(Exception):
    """FR-005a — `false_alarm`/`correct` submitted with only `issue_id`."""


class FindingNotFoundError(Exception):
    """The target finding doesn't exist or isn't `validated`."""


class IssueNotFoundError(Exception):
    """The target issue doesn't exist or has no mapped findings."""


_TARGETED_VERDICTS = {"false_alarm", "correct"}


class RecordFeedbackVerdictUseCase:
    """REQ-M4-01/02/03, REQ-M6-CAL-03a/b. Handles all three verdict types
    generically — `resolved` never touches `false_alarm_count`/
    `correct_count`, so `compute_weight` recomputes an unchanged weight for
    it with no branch needed here (`data-model.md`)."""

    def __init__(
        self,
        findings: FeedbackFindingReadPort,
        issues: IssueTopFindingReadPort,
        verdicts: FeedbackVerdictRepositoryPort,
    ) -> None:
        self._findings = findings
        self._issues = issues
        self._verdicts = verdicts

    async def execute(
        self,
        *,
        finding_id: UUID | None,
        issue_id: UUID | None,
        verdict: str,
        submitted_by_user_id: UUID,
    ) -> None:
        if verdict in _TARGETED_VERDICTS and finding_id is None:
            raise VerdictRequiresFindingError(verdict)

        target_finding_id = finding_id
        if target_finding_id is None:
            # Zero Trust Validation (constitution, Full-Stack Engineering §5) — the
            # route already rejects finding_id=None/issue_id=None before calling
            # execute(), but the use case re-checks its own invariant rather than
            # trusting the caller, and this narrows issue_id to non-None for mypy.
            if issue_id is None:
                raise VerdictRequiresFindingError(verdict)
            target_finding_id = await self._issues.get_top_finding_id(issue_id)
            if target_finding_id is None:
                raise IssueNotFoundError(issue_id)

        components = await self._findings.get_pattern_components(target_finding_id)
        if components is None:
            raise FindingNotFoundError(target_finding_id)

        pattern = pattern_signature(components.reader_type, components.finding_type)
        current = await self._verdicts.get_damping(pattern)

        false_alarm_count = current.false_alarm_count
        correct_count = current.correct_count
        resolved_count = current.resolved_count
        if verdict == "false_alarm":
            false_alarm_count += 1
        elif verdict == "correct":
            correct_count += 1
        elif verdict == "resolved":
            resolved_count += 1

        weight = compute_weight(false_alarm_count, correct_count)
        disclosure_text = build_disclosure_text(false_alarm_count, correct_count, resolved_count)

        updated = DampingWeight(
            pattern_signature=pattern,
            weight=weight,
            false_alarm_count=false_alarm_count,
            resolved_count=resolved_count,
            correct_count=correct_count,
            disclosure_text=disclosure_text,
            last_updated_at=current.last_updated_at,
        )
        await self._verdicts.record(
            finding_id=finding_id,
            issue_id=issue_id,
            verdict=verdict,
            submitted_by_user_id=submitted_by_user_id,
            updated=updated,
        )
