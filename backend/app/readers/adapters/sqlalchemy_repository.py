"""SQLAlchemy implementations of the readers' ports. Raw parameterized SQL against
data-base/03-schema-ledger.md's and data-base/05-schema-reasoning.md's columns,
matching the rest of the codebase's DDL-first pattern (no ORM declarative models).
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.application.ports import EncryptionPort
from app.readers.application.ports import (
    AbsenceEventInfo,
    AbsenceEventRepositoryPort,
    CandidateCorpusPort,
    ConfirmedBaselineRepositoryPort,
    EventExistencePort,
    FindingRepositoryPort,
    FindingTypeConfigPort,
    MeetingTranscriptRepositoryPort,
    MessageEventRepositoryPort,
    QuarantineRepositoryPort,
    RelationshipContextPort,
    ResponsePairRepositoryPort,
    RollupRepositoryPort,
)
from app.readers.domain.entities import (
    CandidateTicket,
    ConfirmedBaselineWindow,
    FailedCheck,
    MeetingTranscriptInfo,
    MessageEventInfo,
    ResponsePairInfo,
)
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
        # `.get(...)`, not `[...]` — a malformed row missing `title`/
        # `ticket_number` is skipped, not a `KeyError` that would crash this
        # reader's entire run (the defensive hardening `specs/ROADMAP.md`'s
        # feature 005 log entry already flagged as worth doing before this
        # feature builds on top of this repository; RunReadersUseCase's own
        # per-reader failure isolation, FR-014, contains this exact class of
        # failure, but a fully-skipped malformed row is strictly better than
        # an isolated-but-total Recurrence failure over one bad row).
        return [
            CandidateTicket(
                event_id=r.id,
                ticket_number=r.structured_payload["ticket_number"],
                title=r.structured_payload["title"],
            )
            for r in rows
            if "title" in r.structured_payload and "ticket_number" in r.structured_payload
        ]


class SqlAlchemyMessageEventRepository(MessageEventRepositoryPort):
    """The shared candidate corpus Tone and Intent both self-fetch from
    (`data-model.md`) — `message`-type events (Gmail/Slack, encrypted body),
    `ticket_state_change`-type events (Zendesk, plain-JSONB title), and (FR-022)
    `survey_response`-type events that actually carry a written comment
    (`has_comment` is a plaintext `structured_payload` marker set at collection
    time — `simulated_collector._normalize_csat`'s docstring — so a score-only
    CSAT response never needs decrypting just to discover it has nothing to
    read), matching `app.experience.adapters.sqlalchemy_repository._quoted_text`'s
    already-established dual-path extraction pattern (feature 006), not
    reimported cross-module — this module gets its own copy for the same
    reason `research.md`'s "no cross-module adapter import" convention
    applies everywhere else in this file."""

    def __init__(self, session: AsyncSession, encryption: EncryptionPort) -> None:
        self._session = session
        self._encryption = encryption

    async def list_all(self) -> list[MessageEventInfo]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, occurred_at, stakeholder_id, structured_payload, "
                    "body_encrypted FROM events "
                    "WHERE event_type IN ('message'::event_type, "
                    "'ticket_state_change'::event_type) "
                    "OR (event_type = 'survey_response'::event_type "
                    "AND (structured_payload->>'has_comment')::boolean IS TRUE)"
                )
            )
        ).all()
        results: list[MessageEventInfo] = []
        for r in rows:
            event_text: str | None
            if r.body_encrypted is not None:
                event_text = self._encryption.decrypt(r.body_encrypted)
            else:
                title = r.structured_payload.get("title")
                event_text = str(title) if title else None
            if event_text is None:
                continue
            results.append(
                MessageEventInfo(
                    event_id=r.id,
                    occurred_at=r.occurred_at,
                    stakeholder_id=r.stakeholder_id,
                    text=event_text,
                )
            )
        return results


class SqlAlchemyMeetingTranscriptRepository(MeetingTranscriptRepositoryPort):
    """`meeting`-type events only — kept separate from
    `SqlAlchemyMessageEventRepository` (see `MeetingTranscriptInfo`'s
    docstring for why)."""

    def __init__(self, session: AsyncSession, encryption: EncryptionPort) -> None:
        self._session = session
        self._encryption = encryption

    async def list_all(self) -> list[MeetingTranscriptInfo]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, occurred_at, stakeholder_id, structured_payload, "
                    "body_encrypted FROM events WHERE event_type = 'meeting'::event_type"
                )
            )
        ).all()
        results: list[MeetingTranscriptInfo] = []
        for r in rows:
            if r.body_encrypted is None:
                continue
            results.append(
                MeetingTranscriptInfo(
                    event_id=r.id,
                    occurred_at=r.occurred_at,
                    stakeholder_id=r.stakeholder_id,
                    series_id=r.structured_payload.get("series_id"),
                    text=self._encryption.decrypt(r.body_encrypted),
                )
            )
        return results


class SqlAlchemyConfirmedBaselineRepository(ConfirmedBaselineRepositoryPort):
    """Joins `baseline_confirmations` -> matching message-bearing `events` for
    a stakeholder. Deliberately doesn't filter by `baseline_confirmations.
    metric` (`data-model.md`'s note) — takes the most recently confirmed
    window for that stakeholder, at most one expected in Phase 1."""

    def __init__(self, session: AsyncSession, encryption: EncryptionPort) -> None:
        self._session = session
        self._encryption = encryption

    async def get_confirmed_window(
        self, stakeholder_id: UUID
    ) -> ConfirmedBaselineWindow | None:
        confirmation = (
            await self._session.execute(
                text(
                    "SELECT window_start, window_end FROM baseline_confirmations "
                    "WHERE subject_type = 'stakeholder'::rollup_subject_type "
                    "AND subject_id = :stakeholder_id "
                    "ORDER BY confirmed_at DESC LIMIT 1"
                ),
                {"stakeholder_id": stakeholder_id},
            )
        ).one_or_none()
        if confirmation is None:
            return None

        rows = (
            await self._session.execute(
                text(
                    "SELECT structured_payload, body_encrypted FROM events "
                    "WHERE stakeholder_id = :stakeholder_id "
                    "AND event_type IN ('message'::event_type, "
                    "'ticket_state_change'::event_type) "
                    "AND occurred_at >= :window_start AND occurred_at <= :window_end"
                ),
                {
                    "stakeholder_id": stakeholder_id,
                    "window_start": confirmation.window_start,
                    "window_end": confirmation.window_end,
                },
            )
        ).all()
        sample_texts: list[str] = []
        for r in rows:
            if r.body_encrypted is not None:
                sample_texts.append(self._encryption.decrypt(r.body_encrypted))
            else:
                title = r.structured_payload.get("title")
                if title:
                    sample_texts.append(str(title))

        return ConfirmedBaselineWindow(
            stakeholder_id=stakeholder_id,
            window_start=confirmation.window_start,
            window_end=confirmation.window_end,
            sample_texts=tuple(sample_texts),
        )


class SqlAlchemyFindingTypeConfigRepository(FindingTypeConfigPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_thresholds(self, finding_type: str) -> tuple[float, int] | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT confidence_floor, min_evidence_count FROM finding_type_config "
                    "WHERE finding_type = :finding_type"
                ),
                {"finding_type": finding_type},
            )
        ).one_or_none()
        if row is None:
            return None
        return float(row.confidence_floor), int(row.min_evidence_count)


class SqlAlchemyEventExistenceRepository(EventExistencePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def existing_ids(self, ids: list[UUID]) -> set[UUID]:
        if not ids:
            return set()
        rows = (
            await self._session.execute(
                text("SELECT id FROM events WHERE id = ANY((:ids)::uuid[])"),
                {"ids": ids},
            )
        ).all()
        return {r.id for r in rows}


class SqlAlchemyQuarantineRepository(QuarantineRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, finding_id: UUID, failed_checks: list[FailedCheck]) -> None:
        # `failed_checks` is never empty when `record()` is called (the gate
        # only calls this on a failed evaluation) — the *first* failed check
        # becomes `quarantine.failed_check` (one column, one value, REQ-M5A-02);
        # every failed check, including that first one, gets its own
        # `validation_failures` row (fine-grained log, `data-base/05`).
        quarantine_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO quarantine (id, finding_id, failed_check, detail) "
                "VALUES (:id, :finding_id, (:failed_check)::validation_check, :detail)"
            ),
            {
                "id": quarantine_id,
                "finding_id": finding_id,
                "failed_check": failed_checks[0].check_name,
                "detail": failed_checks[0].actual,
            },
        )
        for check in failed_checks:
            await self._session.execute(
                text(
                    "INSERT INTO validation_failures "
                    "(id, quarantine_id, check_name, expected, actual) "
                    "VALUES (:id, :quarantine_id, :check_name, :expected, :actual)"
                ),
                {
                    "id": uuid4(),
                    "quarantine_id": quarantine_id,
                    "check_name": check.check_name,
                    "expected": check.expected,
                    "actual": check.actual,
                },
            )
        await self._session.commit()


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
