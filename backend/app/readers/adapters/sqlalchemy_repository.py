"""SQLAlchemy implementations of the readers' ports. Raw parameterized SQL against
data-base/03-schema-ledger.md's and data-base/05-schema-reasoning.md's columns,
matching the rest of the codebase's DDL-first pattern (no ORM declarative models).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.readers.application.ports import (
    AbsenceEventInfo,
    AbsenceEventRepositoryPort,
    CandidateCorpusPort,
    FindingRepositoryPort,
    RelationshipContextPort,
    ResponsePairRepositoryPort,
    RollupRepositoryPort,
)
from app.readers.domain.entities import CandidateTicket, ResponsePairInfo
from app.scoring.domain.entities import Finding


class SqlAlchemyResponsePairRepository(ResponsePairRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ResponsePairInfo]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT client_event_id, state, business_hours_elapsed, "
                    "commitment_id FROM response_pairs "
                    "WHERE commitment_id IS NOT NULL"
                )
            )
        ).all()
        commitment_thresholds: dict[UUID, float] = {}
        commitment_ids = {r.commitment_id for r in rows}
        if commitment_ids:
            threshold_rows = (
                await self._session.execute(
                    text(
                        "SELECT id, threshold_business_hours FROM commitments "
                        "WHERE id = ANY((:ids)::uuid[])"
                    ),
                    {"ids": list(commitment_ids)},
                )
            ).all()
            commitment_thresholds = {
                r.id: float(r.threshold_business_hours)
                for r in threshold_rows
                if r.threshold_business_hours is not None
            }
        return [
            ResponsePairInfo(
                client_event_id=r.client_event_id,
                state=r.state,
                business_hours_elapsed=(
                    float(r.business_hours_elapsed)
                    if r.business_hours_elapsed is not None
                    else None
                ),
                threshold_business_hours=commitment_thresholds.get(r.commitment_id),
            )
            for r in rows
        ]


class SqlAlchemyRollupRepository(RollupRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_subjects(self) -> list[tuple[str, UUID | None, str]]:
        rows = (
            await self._session.execute(
                text("SELECT DISTINCT subject_type, subject_id, metric FROM rollups")
            )
        ).all()
        return [(r.subject_type, r.subject_id, r.metric) for r in rows]

    async def historical_values(
        self, *, subject_type: str, subject_id: UUID | None, metric: str
    ) -> list[float]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT value FROM rollups WHERE subject_type = "
                    "(:subject_type)::rollup_subject_type AND "
                    "subject_id IS NOT DISTINCT FROM :subject_id AND metric = :metric "
                    "ORDER BY window_end DESC OFFSET 1"
                ),
                {"subject_type": subject_type, "subject_id": subject_id, "metric": metric},
            )
        ).all()
        return [float(r.value) for r in rows]

    async def latest_value(
        self, *, subject_type: str, subject_id: UUID | None, metric: str
    ) -> tuple[float, UUID] | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT value, window_end FROM rollups WHERE subject_type = "
                    "(:subject_type)::rollup_subject_type AND "
                    "subject_id IS NOT DISTINCT FROM :subject_id AND metric = :metric "
                    "ORDER BY window_end DESC LIMIT 1"
                ),
                {"subject_type": subject_type, "subject_id": subject_id, "metric": metric},
            )
        ).one_or_none()
        if row is None:
            return None

        event_row = (
            await self._session.execute(
                text(
                    "SELECT id FROM events WHERE event_type = 'usage_measurement'::event_type "
                    "AND product_area_id IS NOT DISTINCT FROM :subject_id "
                    "AND occurred_at = :window_end "
                    "AND structured_payload->>'metric' = :metric LIMIT 1"
                ),
                {"subject_id": subject_id, "window_end": row.window_end, "metric": metric},
            )
        ).one_or_none()
        if event_row is None:
            return None
        return float(row.value), event_row.id


class SqlAlchemyAbsenceEventRepository(AbsenceEventRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[AbsenceEventInfo]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, occurred_at, structured_payload FROM events "
                    "WHERE event_type = 'absence'::event_type"
                )
            )
        ).all()
        results: list[AbsenceEventInfo] = []
        for r in rows:
            payload = r.structured_payload
            window_start = datetime.fromisoformat(payload["window_start"])
            last_contact_raw = payload.get("last_contact_at")
            last_contact_at = (
                datetime.fromisoformat(last_contact_raw) if last_contact_raw else None
            )
            results.append(
                AbsenceEventInfo(
                    event_id=r.id,
                    occurred_at=r.occurred_at,
                    window_start=window_start,
                    last_contact_at=last_contact_at,
                )
            )
        return results


class SqlAlchemyRelationshipContext(RelationshipContextPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_stakeholders(self) -> list[UUID]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT s.id FROM stakeholders s "
                    "JOIN client_profile_versions pv ON pv.id = s.profile_version_id "
                    "WHERE pv.is_current"
                )
            )
        ).all()
        return [r.id for r in rows]

    async def active_stakeholder_ids(self, *, since: datetime) -> set[UUID]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT DISTINCT stakeholder_id FROM events "
                    "WHERE stakeholder_id IS NOT NULL AND occurred_at >= :since"
                ),
                {"since": since},
            )
        ).all()
        return {r.stakeholder_id for r in rows}

    async def most_recent_event_for_stakeholder(self, stakeholder_id: UUID) -> UUID | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT id FROM events WHERE stakeholder_id = :stakeholder_id "
                    "ORDER BY occurred_at DESC LIMIT 1"
                ),
                {"stakeholder_id": stakeholder_id},
            )
        ).one_or_none()
        return row.id if row is not None else None


class SqlAlchemyCandidateCorpusRepository(CandidateCorpusPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_candidates(self) -> list[CandidateTicket]:
        # Only `created`/`reopened` represent a new occurrence of a reported
        # problem worth comparing — `resolved` closes one, it doesn't report a
        # new one (research.md's Decision, found during implementation: ticket
        # #398 has both `created` and `resolved` with an identical title, which
        # would otherwise falsely cluster as a "recurrence").
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, structured_payload FROM events "
                    "WHERE event_type = 'ticket_state_change'::event_type "
                    "AND structured_payload->>'state' IN ('created', 'reopened')"
                )
            )
        ).all()
        return [
            CandidateTicket(
                event_id=r.id,
                ticket_number=r.structured_payload["ticket_number"],
                title=r.structured_payload["title"],
            )
            for r in rows
        ]


class SqlAlchemyFindingRepository(FindingRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def already_interpreted(
        self, *, reader_type: str, reader_version: str, event_id: UUID
    ) -> bool:
        row = (
            await self._session.execute(
                text(
                    "SELECT 1 FROM findings "
                    "WHERE reader_type = (:reader_type)::reader_type "
                    "AND reader_version = :reader_version "
                    "AND (:event_id)::uuid = ANY(cited_event_ids) LIMIT 1"
                ),
                {
                    "reader_type": reader_type,
                    "reader_version": reader_version,
                    "event_id": event_id,
                },
            )
        ).one_or_none()
        return row is not None

    async def persist(self, finding: Finding) -> None:
        await self._session.execute(
            text(
                "INSERT INTO findings (id, reader_type, reader_version, finding_type, "
                "magnitude, confidence, cited_event_ids, stakeholder_id, "
                "product_area_id, status) "
                "VALUES (:id, (:reader_type)::reader_type, :reader_version, "
                ":finding_type, :magnitude, :confidence, :cited_event_ids, "
                ":stakeholder_id, :product_area_id, (:status)::finding_status)"
            ),
            {
                "id": finding.id,
                "reader_type": finding.reader_type,
                "reader_version": finding.reader_version,
                "finding_type": finding.finding_type,
                "magnitude": finding.magnitude,
                "confidence": finding.confidence,
                "cited_event_ids": list(finding.cited_event_ids),
                "stakeholder_id": finding.stakeholder_id,
                "product_area_id": finding.product_area_id,
                "status": finding.status,
            },
        )
        await self._session.commit()
