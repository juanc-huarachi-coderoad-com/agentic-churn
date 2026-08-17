"""`RecomputeScoreUseCase` (`architecture/09-clean-architecture-and-patterns.md`) —
orchestrates the five domain services into one scoring run: fetch validated findings,
derive each finding's lifecycle state, age it, rank it within its issue, weight it,
cap positive signals, convert to a score, classify a hysteresis-protected band, and
persist everything — recomputed entirely from zero every time (REQ-M6-20, REQ-M6-P2).
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.context.domain.damping_calculator import pattern_signature
from app.scoring.application.ports import (
    ClientProfileMultipliersPort,
    CoverageCheckPort,
    DampingRepositoryPort,
    FindingRepositoryPort,
    ScoreRunRepositoryPort,
)
from app.scoring.domain.entities import ScoreContribution, ScoreRun
from app.scoring.domain.services import (
    AgeingCalculator,
    BandClassifier,
    FindingWeightInputs,
    IssueGrouper,
    RawFindingWeight,
    ScoringCalculator,
    compute_stakes,
)


class RecomputeScoreUseCase:
    def __init__(
        self,
        findings: FindingRepositoryPort,
        score_runs: ScoreRunRepositoryPort,
        profile: ClientProfileMultipliersPort,
        damping: DampingRepositoryPort,
        coverage: CoverageCheckPort,
    ) -> None:
        self._findings = findings
        self._score_runs = score_runs
        self._profile = profile
        self._damping = damping
        self._coverage = coverage
        self._ageing = AgeingCalculator()
        self._band_classifier = BandClassifier()
        self._issue_grouper = IssueGrouper()
        self._scoring = ScoringCalculator()

    async def execute(self, *, trigger: str, as_of: datetime | None = None) -> ScoreRun:
        as_of = as_of or datetime.now(UTC)
        degraded = await self._coverage.is_degraded()

        if degraded:
            prior = await self._score_runs.get_latest_score_run()
            if prior is not None:
                return await self._freeze(trigger=trigger, prior=prior, as_of=as_of)
            # First-ever run, degraded: nothing to freeze at — compute normally,
            # marked degraded for visibility (spec.md's Edge Cases).

        return await self._compute_fresh(trigger=trigger, as_of=as_of, degraded=degraded)

    async def _freeze(self, *, trigger: str, prior: ScoreRun, as_of: datetime) -> ScoreRun:
        """REQ-M6-26/REQ-NFR-32: a degraded source freezes the score at its last
        value rather than computing on an incomplete picture. Does not touch
        `band_history` — nothing new was learned about band stability."""
        frozen = ScoreRun(
            id=uuid4(),
            trigger=trigger,
            profile_version_id=prior.profile_version_id,
            finding_type_config_version=prior.finding_type_config_version,
            total_negative_points=prior.total_negative_points,
            total_positive_points=prior.total_positive_points,
            positive_points_applied=prior.positive_points_applied,
            total_points=prior.total_points,
            score=prior.score,
            band=prior.band,
            raw_band=prior.raw_band,
            stakes=prior.stakes,
            source_degraded=True,
            is_frozen=True,
            computed_at=as_of,
        )
        await self._score_runs.persist_run(frozen, [])
        return frozen

    async def _compute_fresh(
        self, *, trigger: str, as_of: datetime, degraded: bool
    ) -> ScoreRun:
        score_run_id = uuid4()
        profile_ctx = await self._profile.get_current()
        findings = await self._findings.list_validated()
        finding_type_config_version = await self._findings.get_finding_type_config_version()
        memberships = await self._findings.list_issue_memberships()
        findings_by_id = {f.id: f for f in findings}

        base_points: dict[UUID, float] = {}
        half_life: dict[UUID, float | None] = {}
        recency: dict[UUID, float] = {}

        for finding in findings:
            lifecycle = await self._findings.resolve_lifecycle(finding)
            await self._findings.update_finding_state(finding.id, lifecycle.state)

            config = await self._findings.get_finding_type_config(finding.finding_type)
            base_points[finding.id] = config.base_points
            half_life[finding.id] = config.half_life_days

            recency[finding.id] = self._ageing.compute_recency(
                lifecycle, half_life_days=config.half_life_days, as_of=as_of
            )

        def _influence(finding_id: UUID) -> float:
            stakeholder_id = findings_by_id[finding_id].stakeholder_id
            if stakeholder_id is None:
                return 1.0
            return profile_ctx.stakeholder_multipliers.get(stakeholder_id, 1.0)

        def _criticality(finding_id: UUID) -> float:
            product_area_id = findings_by_id[finding_id].product_area_id
            if product_area_id is None:
                return 1.0
            return profile_ctx.product_area_multipliers.get(product_area_id, 1.0)

        # Issue-relative ranking (REQ-M6-06..08) — one general algorithm, no
        # fixture-specific exception (research.md's Decision).
        rank_factor: dict[UUID, float] = {}
        finding_issue_of: dict[UUID, UUID] = {}
        ranks_to_persist: dict[tuple[UUID, UUID], int] = {}
        for issue_id, finding_ids in memberships.items():
            weights = [
                RawFindingWeight(
                    finding_id=fid,
                    raw_points=(
                        base_points[fid]
                        * _influence(fid)
                        * _criticality(fid)
                        * findings_by_id[fid].confidence
                        * findings_by_id[fid].magnitude
                    ),
                )
                for fid in finding_ids
                if fid in findings_by_id
            ]
            for ranked in self._issue_grouper.rank_within_issue(weights):
                rank_factor[ranked.finding_id] = ranked.rank_factor
                finding_issue_of[ranked.finding_id] = issue_id
                ranks_to_persist[(ranked.finding_id, issue_id)] = ranked.rank
        await self._findings.upsert_ranks(ranks_to_persist)

        contributions: list[ScoreContribution] = []
        total_negative_points = 0.0
        total_positive_points = 0.0

        for finding in findings:
            damping = await self._damping.get_weight(
                pattern_signature(finding.reader_type, finding.finding_type)
            )
            influence = _influence(finding.id)
            criticality = _criticality(finding.id)

            inputs = FindingWeightInputs(
                base=base_points[finding.id],
                influence=influence,
                criticality=criticality,
                confidence=finding.confidence,
                magnitude=finding.magnitude,
                recency=recency[finding.id],
                damping=damping,
                rank_within_issue_factor=rank_factor.get(finding.id, 1.0),
            )
            points = self._scoring.compute_points(inputs)

            contributions.append(
                ScoreContribution(
                    score_run_id=score_run_id,
                    finding_id=finding.id,
                    issue_id=finding_issue_of.get(finding.id),
                    base=inputs.base,
                    influence=influence,
                    criticality=criticality,
                    confidence=finding.confidence,
                    magnitude=finding.magnitude,
                    recency=recency[finding.id],
                    damping=damping,
                    rank_within_issue_factor=inputs.rank_within_issue_factor,
                    points_contributed=points,
                    is_positive=finding.is_positive,
                )
            )
            if finding.is_positive:
                total_positive_points += points
            else:
                total_negative_points += points

        positive_points_applied = self._scoring.apply_positive_cap(
            total_negative_points=total_negative_points,
            total_positive_points=total_positive_points,
        )
        total_points = total_negative_points - positive_points_applied
        score = self._scoring.points_to_score(total_points)

        stakes = compute_stakes(
            contract_value_band=profile_ctx.contract_value_band,
            renewal_date=profile_ctx.renewal_date,
            as_of=as_of.date(),
        )

        band_history = await self._score_runs.get_latest_band_history()
        latest_run = await self._score_runs.get_latest_score_run()
        classification = self._band_classifier.classify(
            score,
            prior_displayed_band=latest_run.band if latest_run is not None else None,
            prior_qualifying_band=band_history.band if band_history is not None else None,
            prior_qualifying_streak=(
                band_history.consecutive_runs_in_band if band_history is not None else 0
            ),
        )

        run = ScoreRun(
            id=score_run_id,
            trigger=trigger,
            profile_version_id=profile_ctx.profile_version_id,
            finding_type_config_version=finding_type_config_version,
            total_negative_points=total_negative_points,
            total_positive_points=total_positive_points,
            positive_points_applied=positive_points_applied,
            total_points=total_points,
            score=score,
            band=classification.displayed_band,
            raw_band=classification.raw_band,
            stakes=stakes,
            source_degraded=degraded,
            is_frozen=False,
            computed_at=as_of,
        )

        await self._score_runs.persist_run(run, contributions)
        await self._score_runs.persist_band_history(
            score_run_id=score_run_id,
            band=classification.qualifying_band,
            consecutive_runs_in_band=classification.consecutive_runs_in_band,
        )

        return run
