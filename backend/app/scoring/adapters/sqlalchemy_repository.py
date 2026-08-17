"""SQLAlchemy implementations of the scoring ports. Raw parameterized SQL against
data-base/05-schema-reasoning.md's and data-base/06-schema-scoring.md's columns,
matching the rest of the codebase's DDL-first pattern (no ORM declarative models).
"""

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.scoring.application.ports import (
    BandHistoryRecord,
    ClientProfileMultipliersPort,
    CoverageCheckPort,
    DampingRepositoryPort,
    Finding,
    FindingLifecycle,
    FindingRepositoryPort,
    FindingTypeConfig,
    FindingTypeConfigChangeResult,
    FindingTypeConfigWritePort,
    FindingTypeNotFoundError,
    ProfileMultiplierContext,
    ScoreContribution,
    ScoreRun,
    ScoreRunRepositoryPort,
)
from app.scoring.domain.entities import is_positive_finding_type


class SqlAlchemyFindingRepository(FindingRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_validated(self) -> list[Finding]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, reader_type, reader_version, finding_type, magnitude, "
                    "confidence, cited_event_ids, stakeholder_id, product_area_id, "
                    "status, state FROM findings "
                    "WHERE status = 'validated'::finding_status"
                )
            )
        ).all()
        return [
            Finding(
                id=r.id,
                reader_type=r.reader_type,
                reader_version=r.reader_version,
                finding_type=r.finding_type,
                magnitude=float(r.magnitude),
                confidence=float(r.confidence),
                cited_event_ids=tuple(r.cited_event_ids),
                stakeholder_id=r.stakeholder_id,
                product_area_id=r.product_area_id,
                status=r.status,
                state=r.state,
                is_positive=is_positive_finding_type(r.finding_type),
            )
            for r in rows
        ]

    async def get_finding_type_config(self, finding_type: str) -> FindingTypeConfig:
        row = (
            await self._session.execute(
                text(
                    "SELECT base_points, half_life_days FROM finding_type_config "
                    "WHERE finding_type = :finding_type"
                ),
                {"finding_type": finding_type},
            )
        ).one()
        return FindingTypeConfig(
            base_points=float(row.base_points),
            half_life_days=(
                float(row.half_life_days) if row.half_life_days is not None else None
            ),
        )

    async def get_finding_type_config_version(self) -> str:
        row = (
            await self._session.execute(text("SELECT version FROM finding_type_config LIMIT 1"))
        ).one_or_none()
        return row.version if row is not None else "v1"

    async def resolve_lifecycle(self, finding: Finding) -> FindingLifecycle:
        if finding.finding_type not in ("broken_response_promise", "commitment_met"):
            return FindingLifecycle(
                state="open",
                business_hours_elapsed=None,
                threshold_business_hours=None,
                resolved_at=None,
            )

        row = (
            await self._session.execute(
                text(
                    "SELECT rp.state, rp.business_hours_elapsed, "
                    "c.threshold_business_hours, re.occurred_at AS resolved_at "
                    "FROM response_pairs rp "
                    "LEFT JOIN commitments c ON c.id = rp.commitment_id "
                    "LEFT JOIN events re ON re.id = rp.reply_event_id "
                    "WHERE rp.client_event_id = ANY((:cited_ids)::uuid[]) "
                    "LIMIT 1"
                ),
                {"cited_ids": list(finding.cited_event_ids)},
            )
        ).one_or_none()

        if row is None:
            return FindingLifecycle(
                state="open",
                business_hours_elapsed=None,
                threshold_business_hours=None,
                resolved_at=None,
            )

        return FindingLifecycle(
            state=row.state,
            business_hours_elapsed=(
                float(row.business_hours_elapsed)
                if row.business_hours_elapsed is not None
                else None
            ),
            threshold_business_hours=(
                float(row.threshold_business_hours)
                if row.threshold_business_hours is not None
                else None
            ),
            resolved_at=row.resolved_at,
        )

    async def list_issue_memberships(self) -> dict[UUID, list[UUID]]:
        rows = (
            await self._session.execute(text("SELECT issue_id, finding_id FROM finding_issue_map"))
        ).all()
        memberships: dict[UUID, list[UUID]] = {}
        for r in rows:
            memberships.setdefault(r.issue_id, []).append(r.finding_id)
        return memberships

    async def update_finding_state(self, finding_id: UUID, state: str) -> None:
        await self._session.execute(
            text("UPDATE findings SET state = (:state)::finding_state WHERE id = :id"),
            {"state": state, "id": finding_id},
        )
        await self._session.commit()

    async def upsert_ranks(self, ranks: dict[tuple[UUID, UUID], int]) -> None:
        for (finding_id, issue_id), rank in ranks.items():
            await self._session.execute(
                text(
                    "UPDATE finding_issue_map SET rank_within_issue = :rank "
                    "WHERE finding_id = :finding_id AND issue_id = :issue_id"
                ),
                {"rank": rank, "finding_id": finding_id, "issue_id": issue_id},
            )
        await self._session.commit()


class SqlAlchemyScoreRunRepository(ScoreRunRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_band_history(self) -> BandHistoryRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT band, consecutive_runs_in_band FROM band_history "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return BandHistoryRecord(
            band=row.band, consecutive_runs_in_band=row.consecutive_runs_in_band
        )

    async def get_latest_score_run(self) -> ScoreRun | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT id, trigger, profile_version_id, finding_type_config_version, "
                    "total_negative_points, total_positive_points, positive_points_applied, "
                    "total_points, score, band, raw_band, stakes, source_degraded, "
                    "is_frozen, computed_at FROM score_runs "
                    "ORDER BY computed_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return ScoreRun(
            id=row.id,
            trigger=row.trigger,
            profile_version_id=row.profile_version_id,
            finding_type_config_version=row.finding_type_config_version,
            total_negative_points=float(row.total_negative_points),
            total_positive_points=float(row.total_positive_points),
            positive_points_applied=float(row.positive_points_applied),
            total_points=float(row.total_points),
            score=float(row.score),
            band=row.band,
            raw_band=row.raw_band,
            stakes=float(row.stakes) if row.stakes is not None else None,
            source_degraded=row.source_degraded,
            is_frozen=row.is_frozen,
            computed_at=row.computed_at,
        )

    async def persist_run(
        self, run: ScoreRun, contributions: list[ScoreContribution]
    ) -> None:
        await self._session.execute(
            text(
                "INSERT INTO score_runs (id, trigger, profile_version_id, "
                "finding_type_config_version, total_negative_points, "
                "total_positive_points, positive_points_applied, total_points, score, "
                "band, raw_band, stakes, source_degraded, is_frozen) "
                "VALUES (:id, (:trigger)::score_trigger, :profile_version_id, "
                ":finding_type_config_version, :total_negative_points, "
                ":total_positive_points, :positive_points_applied, :total_points, "
                ":score, (:band)::band, (:raw_band)::band, :stakes, "
                ":source_degraded, :is_frozen)"
            ),
            {
                "id": run.id,
                "trigger": run.trigger,
                "profile_version_id": run.profile_version_id,
                "finding_type_config_version": run.finding_type_config_version,
                "total_negative_points": run.total_negative_points,
                "total_positive_points": run.total_positive_points,
                "positive_points_applied": run.positive_points_applied,
                "total_points": run.total_points,
                "score": run.score,
                "band": run.band,
                "raw_band": run.raw_band,
                "stakes": run.stakes,
                "source_degraded": run.source_degraded,
                "is_frozen": run.is_frozen,
            },
        )
        for c in contributions:
            await self._session.execute(
                text(
                    "INSERT INTO score_contributions (id, score_run_id, finding_id, "
                    "issue_id, base, influence, criticality, confidence, magnitude, "
                    "recency, damping, rank_within_issue_factor, points_contributed, "
                    "is_positive) "
                    "VALUES (:id, :score_run_id, :finding_id, :issue_id, :base, "
                    ":influence, :criticality, :confidence, :magnitude, :recency, "
                    ":damping, :rank_factor, :points_contributed, :is_positive)"
                ),
                {
                    "id": uuid4(),
                    "score_run_id": c.score_run_id,
                    "finding_id": c.finding_id,
                    "issue_id": c.issue_id,
                    "base": c.base,
                    "influence": c.influence,
                    "criticality": c.criticality,
                    "confidence": c.confidence,
                    "magnitude": c.magnitude,
                    "recency": c.recency,
                    "damping": c.damping,
                    "rank_factor": c.rank_within_issue_factor,
                    "points_contributed": c.points_contributed,
                    "is_positive": c.is_positive,
                },
            )
        await self._session.commit()

    async def persist_band_history(
        self, *, score_run_id: UUID, band: str, consecutive_runs_in_band: int
    ) -> None:
        await self._session.execute(
            text(
                "INSERT INTO band_history (id, score_run_id, band, consecutive_runs_in_band) "
                "VALUES (:id, :score_run_id, (:band)::band, :count)"
            ),
            {
                "id": uuid4(),
                "score_run_id": score_run_id,
                "band": band,
                "count": consecutive_runs_in_band,
            },
        )
        await self._session.commit()


class SqlAlchemyClientProfileMultipliers(ClientProfileMultipliersPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self) -> ProfileMultiplierContext:
        profile = (
            await self._session.execute(
                text(
                    "SELECT id, contract_value_band, renewal_date "
                    "FROM client_profile_versions WHERE is_current LIMIT 1"
                )
            )
        ).one()

        stakeholder_rows = (
            await self._session.execute(
                text(
                    "SELECT id, influence_multiplier FROM stakeholders "
                    "WHERE profile_version_id = :pv"
                ),
                {"pv": profile.id},
            )
        ).all()

        product_area_rows = (
            await self._session.execute(
                text(
                    "SELECT id, criticality_multiplier FROM product_areas "
                    "WHERE profile_version_id = :pv"
                ),
                {"pv": profile.id},
            )
        ).all()

        return ProfileMultiplierContext(
            profile_version_id=profile.id,
            stakeholder_multipliers={
                r.id: float(r.influence_multiplier) for r in stakeholder_rows
            },
            product_area_multipliers={
                r.id: float(r.criticality_multiplier) for r in product_area_rows
            },
            contract_value_band=profile.contract_value_band,
            renewal_date=profile.renewal_date,
        )


class SqlAlchemyDampingRepository(DampingRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_weight(self, pattern_signature: str) -> float:
        row = (
            await self._session.execute(
                text("SELECT weight FROM damping_weights WHERE pattern_signature = :ps"),
                {"ps": pattern_signature},
            )
        ).one_or_none()
        return float(row.weight) if row is not None else 1.0


class SqlAlchemyCoverageCheck(CoverageCheckPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_degraded(self) -> bool:
        row = (
            await self._session.execute(
                text(
                    "SELECT sources_read, sources_expected FROM coverage_reports "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None:
            return False
        return bool(row.sources_read < row.sources_expected)


class SqlAlchemyFindingTypeConfigWriter(FindingTypeConfigWritePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def update_base_points(
        self,
        finding_type: str,
        new_base_points: float,
        changed_by_user_id: UUID,
    ) -> FindingTypeConfigChangeResult:
        row = (
            await self._session.execute(
                text(
                    "SELECT base_points FROM finding_type_config "
                    "WHERE finding_type = :finding_type FOR UPDATE"
                ),
                {"finding_type": finding_type},
            )
        ).one_or_none()
        if row is None:
            raise FindingTypeNotFoundError(finding_type)
        previous_base_points = float(row.base_points)

        # `finding_type_config.version` is physically a per-row column, but every
        # existing reader (`get_finding_type_config_version()`,
        # `app.scoring.adapters.sqlalchemy_repository.SqlAlchemyFindingRepository`)
        # treats it as one logical, shared value — `SELECT version FROM
        # finding_type_config LIMIT 1`, no `ORDER BY`, relying entirely on every
        # row already agreeing. Bumping only the changed row's version (the first
        # version of this method) broke that invariant the moment the two values
        # diverged — `LIMIT 1` picked an arbitrary *other*, unchanged row, so
        # `score_runs.finding_type_config_version` silently kept reading the old
        # value. Found for real by `tests/scoring/test_weight_recalibration_
        # real_db.py`, not by inspection. Fixed by keeping the existing shared-
        # version contract intact: every row's `version` moves together.
        new_version = f"v-{uuid4().hex[:12]}"
        await self._session.execute(
            text("UPDATE finding_type_config SET version = :new_version"),
            {"new_version": new_version},
        )
        await self._session.execute(
            text(
                "UPDATE finding_type_config SET base_points = :new_base_points "
                "WHERE finding_type = :finding_type"
            ),
            {
                "new_base_points": new_base_points,
                "finding_type": finding_type,
            },
        )

        change_id = uuid4()
        inserted = (
            await self._session.execute(
                text(
                    "INSERT INTO finding_type_config_changes "
                    "(id, finding_type, previous_base_points, new_base_points, "
                    "changed_by_user_id, config_version_after) "
                    "VALUES (:id, :finding_type, :previous, :new_base_points, "
                    ":changed_by_user_id, :new_version) "
                    "RETURNING changed_at"
                ),
                {
                    "id": change_id,
                    "finding_type": finding_type,
                    "previous": previous_base_points,
                    "new_base_points": new_base_points,
                    "changed_by_user_id": changed_by_user_id,
                    "new_version": new_version,
                },
            )
        ).one()
        await self._session.commit()
        return FindingTypeConfigChangeResult(
            change_id=change_id,
            new_config_version=new_version,
            changed_at=inserted.changed_at,
        )
