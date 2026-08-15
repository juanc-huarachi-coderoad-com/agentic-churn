"""SQLAlchemy implementations of the experience (M8) read ports. Raw
parameterized SQL against data-base/02,03,04,05,06's columns, matching the
rest of the codebase's DDL-first pattern (no ORM declarative models).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.experience.application.ports import (
    ClientProfileRecord,
    ClientProfileRepositoryPort,
    CoveragePort,
    CoverageReportRecord,
    FindingReadPort,
    FindingRecord,
    IdentityGapPort,
    PulseEventPort,
    PulseEventRecord,
    QuarantineRecord,
    ScoreReadPort,
    ScoreRunRecord,
    SourceRecord,
    StakeholderReadPort,
    StakeholderRecord,
    UnresolvedParticipantRecord,
)
from app.experience.domain.entities import (
    CitedEventRecord,
    CommitmentComparisonRecord,
    ContributionRecord,
    UsageComparisonRecord,
)
from app.ingestion.application.ports import EncryptionPort

# source_type -> one of the six counted signal types (REQ-M8-07's own list:
# Tickets, Email, Chat, Product usage, Surveys, Meetings). CRM/contracts is
# reference data for the client profile, not a counted signal type.
_SIGNAL_TYPE_GROUPS: dict[str, str] = {
    "zendesk": "tickets",
    "jira": "tickets",
    "intercom": "tickets",
    "gmail": "email",
    "microsoft365": "email",
    "slack": "chat",
    "teams": "chat",
    "warehouse": "product_usage",
    "csat": "surveys",
    "nps": "surveys",
    "calendar": "meetings",
    "transcripts": "meetings",
}


def _quoted_text(
    structured_payload: dict[str, object],
    body_encrypted: bytes | None,
    encryption: EncryptionPort,
) -> str | None:
    """A real client message body where one exists; a `ticket_state_change`'s
    own title stands in otherwise; `None` for events with no textual content
    (e.g. `usage_measurement`) — never fabricated (spec.md's Edge Cases)."""
    if body_encrypted is not None:
        return encryption.decrypt(body_encrypted)
    title = structured_payload.get("title")
    return str(title) if title else None


def _row_to_contribution(row: Any) -> ContributionRecord:
    return ContributionRecord(
        id=row.id,
        finding_id=row.finding_id,
        finding_type=row.finding_type,
        points_contributed=float(row.points_contributed),
        is_positive=row.is_positive,
        base=float(row.base),
        influence=float(row.influence),
        criticality=float(row.criticality),
        confidence=float(row.confidence),
        magnitude=float(row.magnitude),
        recency=float(row.recency),
        damping=float(row.damping),
        rank_within_issue_factor=float(row.rank_within_issue_factor),
    )


_CONTRIBUTION_SELECT = (
    "SELECT sc.id, sc.finding_id, f.finding_type, sc.points_contributed, sc.is_positive, "
    "sc.base, sc.influence, sc.criticality, sc.confidence, sc.magnitude, sc.recency, "
    "sc.damping, sc.rank_within_issue_factor "
    "FROM score_contributions sc JOIN findings f ON f.id = sc.finding_id "
)


class SqlAlchemyClientProfileRepository(ClientProfileRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self) -> ClientProfileRecord | None:
        result = await self._session.execute(
            text(
                "SELECT client_name, renewal_date FROM client_profile_versions "
                "WHERE is_current = true"
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ClientProfileRecord(client_name=row.client_name, renewal_date=row.renewal_date)


class SqlAlchemyScoreReader(ScoreReadPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_run(self) -> ScoreRunRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT id, band, score, computed_at FROM score_runs "
                    "ORDER BY computed_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return ScoreRunRecord(
            id=row.id, band=row.band, score=float(row.score), computed_at=row.computed_at
        )

    async def trend(self, *, days: int) -> list[float]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT day, score FROM ("
                    "  SELECT DISTINCT ON (date_trunc('day', computed_at)) "
                    "    date_trunc('day', computed_at) AS day, score "
                    "  FROM score_runs "
                    "  WHERE computed_at >= now() - make_interval(days => :days) "
                    "  ORDER BY date_trunc('day', computed_at), computed_at DESC"
                    ") sub ORDER BY day ASC"
                ),
                {"days": days},
            )
        ).all()
        return [float(r.score) for r in rows]

    async def list_contributions(self, score_run_id: UUID) -> list[ContributionRecord]:
        rows = (
            await self._session.execute(
                text(_CONTRIBUTION_SELECT + "WHERE sc.score_run_id = :id"),
                {"id": score_run_id},
            )
        ).all()
        return [_row_to_contribution(r) for r in rows]

    async def get_contribution(self, score_contribution_id: UUID) -> ContributionRecord | None:
        row = (
            await self._session.execute(
                text(_CONTRIBUTION_SELECT + "WHERE sc.id = :id"),
                {"id": score_contribution_id},
            )
        ).one_or_none()
        return _row_to_contribution(row) if row is not None else None


class SqlAlchemyPulseEventReader(PulseEventPort):
    def __init__(self, session: AsyncSession, encryption: EncryptionPort) -> None:
        self._session = session
        self._encryption = encryption

    async def list_recent(self, *, since: datetime) -> list[PulseEventRecord]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT event_id, occurred_at, structured_payload, body_encrypted, "
                    "finding_type, is_positive, score_contribution_id FROM ("
                    "  SELECT DISTINCT ON (e.id) e.id AS event_id, e.occurred_at, "
                    "    e.structured_payload, e.body_encrypted, f.finding_type, "
                    "    sc.is_positive, sc.id AS score_contribution_id "
                    "  FROM score_contributions sc "
                    "  JOIN findings f ON f.id = sc.finding_id "
                    "  JOIN events e ON e.id = ANY(f.cited_event_ids) "
                    "  WHERE e.occurred_at >= :since "
                    "  ORDER BY e.id, sc.points_contributed DESC"
                    ") sub ORDER BY occurred_at DESC"
                ),
                {"since": since},
            )
        ).all()
        return [
            PulseEventRecord(
                event_id=r.event_id,
                occurred_at=r.occurred_at,
                quoted_text=_quoted_text(r.structured_payload, r.body_encrypted, self._encryption),
                finding_type=r.finding_type,
                is_positive=r.is_positive,
                score_contribution_id=r.score_contribution_id,
            )
            for r in rows
        ]


class SqlAlchemyFindingReader(FindingReadPort):
    def __init__(self, session: AsyncSession, encryption: EncryptionPort) -> None:
        self._session = session
        self._encryption = encryption

    async def get_finding(self, finding_id: UUID) -> FindingRecord | None:
        row = (
            await self._session.execute(
                text("SELECT id, finding_type, cited_event_ids FROM findings WHERE id = :id"),
                {"id": finding_id},
            )
        ).one_or_none()
        if row is None:
            return None
        return FindingRecord(
            id=row.id, finding_type=row.finding_type, cited_event_ids=tuple(row.cited_event_ids)
        )

    async def resolve_events(self, event_ids: list[UUID]) -> list[CitedEventRecord]:
        if not event_ids:
            return []
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, occurred_at, structured_payload, body_encrypted FROM events "
                    "WHERE id = ANY((:ids)::uuid[]) ORDER BY occurred_at"
                ),
                {"ids": event_ids},
            )
        ).all()
        return [
            CitedEventRecord(
                event_id=r.id,
                occurred_at=r.occurred_at,
                quoted_text=_quoted_text(r.structured_payload, r.body_encrypted, self._encryption),
                structured_payload=r.structured_payload,
            )
            for r in rows
        ]

    async def get_commitment_comparison(
        self, event_id: UUID
    ) -> CommitmentComparisonRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT rp.business_hours_elapsed, rp.state, c.threshold_business_hours "
                    "FROM response_pairs rp LEFT JOIN commitments c ON c.id = rp.commitment_id "
                    "WHERE rp.client_event_id = :event_id"
                ),
                {"event_id": event_id},
            )
        ).one_or_none()
        if (
            row is None
            or row.business_hours_elapsed is None
            or row.threshold_business_hours is None
        ):
            return None
        return CommitmentComparisonRecord(
            business_hours_elapsed=float(row.business_hours_elapsed),
            threshold_business_hours=float(row.threshold_business_hours),
            state=row.state,
        )

    async def get_usage_comparison(self, event_id: UUID) -> UsageComparisonRecord | None:
        event_row = (
            await self._session.execute(
                text(
                    "SELECT structured_payload->>'metric' AS metric, product_area_id, occurred_at "
                    "FROM events WHERE id = :event_id"
                ),
                {"event_id": event_id},
            )
        ).one_or_none()
        if event_row is None or event_row.metric is None:
            return None

        latest_row = (
            await self._session.execute(
                text(
                    "SELECT value FROM rollups WHERE subject_type = "
                    "'product_area'::rollup_subject_type AND "
                    "subject_id IS NOT DISTINCT FROM :subject_id AND metric = :metric "
                    "AND window_end = :occurred_at"
                ),
                {
                    "subject_id": event_row.product_area_id,
                    "metric": event_row.metric,
                    "occurred_at": event_row.occurred_at,
                },
            )
        ).one_or_none()
        historical_rows = (
            await self._session.execute(
                text(
                    "SELECT value FROM rollups WHERE subject_type = "
                    "'product_area'::rollup_subject_type AND "
                    "subject_id IS NOT DISTINCT FROM :subject_id AND metric = :metric "
                    "AND window_end < :occurred_at"
                ),
                {
                    "subject_id": event_row.product_area_id,
                    "metric": event_row.metric,
                    "occurred_at": event_row.occurred_at,
                },
            )
        ).all()
        if latest_row is None or not historical_rows:
            return None
        mean = sum(float(h.value) for h in historical_rows) / len(historical_rows)
        return UsageComparisonRecord(
            metric=event_row.metric, historical_mean=mean, latest_value=float(latest_row.value)
        )


class SqlAlchemyCoverageReader(CoveragePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_sources(self) -> list[SourceRecord]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT source_type, display_name, status, last_successful_sync_at "
                    "FROM sources"
                )
            )
        ).all()
        return [
            SourceRecord(
                source_type=r.source_type,
                display_name=r.display_name,
                status=r.status,
                last_successful_sync_at=r.last_successful_sync_at,
            )
            for r in rows
        ]

    async def latest_report(self) -> CoverageReportRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT sources_read, sources_expected, gap_reason, complete_to "
                    "FROM coverage_reports ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return CoverageReportRecord(
            sources_read=row.sources_read,
            sources_expected=row.sources_expected,
            gap_reason=row.gap_reason,
            complete_to=row.complete_to,
        )

    async def connected_signal_type_count(self) -> int:
        rows = (
            await self._session.execute(
                text("SELECT source_type FROM sources WHERE status IN ('connected', 'degraded')")
            )
        ).all()
        groups = {
            _SIGNAL_TYPE_GROUPS[r.source_type]
            for r in rows
            if r.source_type in _SIGNAL_TYPE_GROUPS
        }
        return len(groups)

    async def list_quarantine(self) -> list[QuarantineRecord]:
        # Real, not a stub: feature 007's ValidationGate is the only mechanism
        # that would ever set findings.status = 'quarantined', and it doesn't
        # exist yet — there is no failed_check data to read (spec.md's Note on
        # scope, contracts/coverage.md).
        return []


class SqlAlchemyStakeholderReader(StakeholderReadPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_stakeholders(self) -> list[StakeholderRecord]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT s.id, s.name, s.role, "
                    "(SELECT MAX(e.occurred_at) FROM events e WHERE e.stakeholder_id = s.id) "
                    "AS last_seen_at "
                    "FROM stakeholders s "
                    "JOIN client_profile_versions pv ON pv.id = s.profile_version_id "
                    "WHERE pv.is_current"
                )
            )
        ).all()
        return [
            StakeholderRecord(
                stakeholder_id=r.id, name=r.name, role=r.role, last_seen_at=r.last_seen_at
            )
            for r in rows
        ]


class SqlAlchemyIdentityGapReader(IdentityGapPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_unresolved(self, *, min_count: int) -> list[UnresolvedParticipantRecord]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT structured_payload->>'participant' AS participant, count(*) AS n "
                    "FROM events WHERE stakeholder_id IS NULL "
                    "AND structured_payload ? 'participant' "
                    "GROUP BY structured_payload->>'participant' "
                    "HAVING count(*) >= :min_count "
                    "ORDER BY n DESC"
                ),
                {"min_count": min_count},
            )
        ).all()
        return [UnresolvedParticipantRecord(participant=r.participant, count=r.n) for r in rows]
