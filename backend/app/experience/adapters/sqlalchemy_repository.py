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
    AskIntentCoverageRecord,
    AskQueryRepositoryPort,
    ClientProfileRecord,
    ClientProfileRepositoryPort,
    CoveragePort,
    CoverageReportRecord,
    DampingDisclosurePort,
    DisclosureRecord,
    DraftMessageRecord,
    DraftMessageRepositoryPort,
    FindingReadPort,
    FindingRecord,
    IdentityGapPort,
    IssueReadPort,
    LedgerQueryPort,
    NarratorReadPort,
    PlaybookReadPort,
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
    CommitmentStatusRecord,
    ContributionRecord,
    GeneratedDraft,
    IssueEvidenceRecord,
    NarratorSummaryRecord,
    UsageComparisonRecord,
)
from app.ingestion.application.ports import EncryptionPort
from app.readers.domain.entities import ConfirmedBaselineWindow, MessageEventInfo

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
        issue_id=row.issue_id,
    )


_CONTRIBUTION_SELECT = (
    "SELECT sc.id, sc.finding_id, f.finding_type, sc.points_contributed, sc.is_positive, "
    "sc.base, sc.influence, sc.criticality, sc.confidence, sc.magnitude, sc.recency, "
    "sc.damping, sc.rank_within_issue_factor, sc.issue_id "
    "FROM score_contributions sc JOIN findings f ON f.id = sc.finding_id "
)


class SqlAlchemyClientProfileRepository(ClientProfileRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self) -> ClientProfileRecord | None:
        result = await self._session.execute(
            text(
                "SELECT client_name, renewal_date, communication_norms "
                "FROM client_profile_versions WHERE is_current = true"
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ClientProfileRecord(
            client_name=row.client_name,
            renewal_date=row.renewal_date,
            communication_norms=row.communication_norms,
        )


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
        # status = 'validated' filter added during /speckit-analyze (C1):
        # every caller of get_finding today (GetEvidenceTraceUseCase) only
        # ever passes a finding_id already reached through score_contributions
        # (validated by construction — RecomputeScoreUseCase reads
        # list_validated() only), so this filter changes nothing for that
        # caller. It's load-bearing for the Ask agent's QueryFindingsTool
        # (specs/008-narrator-and-ask-agent), which must never surface a
        # quarantined finding (FR-024) — ScoreReadPort's own queries are
        # already safe by the same construction, but this is the one path
        # that took an arbitrary finding_id with no equivalent guarantee.
        row = (
            await self._session.execute(
                text(
                    "SELECT id, finding_type, cited_event_ids, reader_type FROM findings "
                    "WHERE id = :id AND status = 'validated'"
                ),
                {"id": finding_id},
            )
        ).one_or_none()
        if row is None:
            return None
        return FindingRecord(
            id=row.id,
            finding_type=row.finding_type,
            cited_event_ids=tuple(row.cited_event_ids),
            reader_type=row.reader_type,
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

    async def list_open_commitments(self, *, limit: int = 20) -> list[CommitmentStatusRecord]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT e.id AS event_id, e.occurred_at, e.structured_payload, "
                    "e.body_encrypted, rp.state, rp.business_hours_elapsed, "
                    "c.threshold_business_hours "
                    "FROM response_pairs rp "
                    "JOIN events e ON e.id = rp.client_event_id "
                    "LEFT JOIN commitments c ON c.id = rp.commitment_id "
                    "ORDER BY e.occurred_at DESC LIMIT :limit"
                ),
                {"limit": limit},
            )
        ).all()
        return [
            CommitmentStatusRecord(
                event_id=r.event_id,
                occurred_at=r.occurred_at,
                quoted_text=_quoted_text(r.structured_payload, r.body_encrypted, self._encryption),
                state=r.state,
                business_hours_elapsed=(
                    float(r.business_hours_elapsed)
                    if r.business_hours_elapsed is not None
                    else None
                ),
                threshold_business_hours=(
                    float(r.threshold_business_hours)
                    if r.threshold_business_hours is not None
                    else None
                ),
            )
            for r in rows
        ]


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
        # Real for the first time (feature 007's ValidationGate) — feature
        # 006 shipped this hardcoded to `[]` since nothing could populate
        # `quarantine` yet (found and fixed during feature 007's own
        # verification, not just assumed correct from the plan: the route's
        # own contract/schema were already right, only this query was still
        # a placeholder).
        rows = (
            await self._session.execute(
                text("SELECT finding_id, failed_check FROM quarantine ORDER BY created_at")
            )
        ).all()
        return [
            QuarantineRecord(finding_id=r.finding_id, failed_check=r.failed_check) for r in rows
        ]

    async def ask_intent_coverage(self) -> AskIntentCoverageRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT count(*) AS total, "
                    "count(*) FILTER (WHERE matched_intent IS NULL) AS fallback "
                    "FROM ask_queries"
                )
            )
        ).one()
        if row.total == 0:
            return None
        return AskIntentCoverageRecord(total_questions=row.total, fallback_count=row.fallback)


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

    async def get(self, stakeholder_id: UUID) -> StakeholderRecord | None:
        # specs/009-draft-composer, research.md Decision 13 (/speckit-analyze
        # finding U3) — a single-ID lookup, distinct from list_stakeholders'
        # current-profile-only scan (mirrors IssueReadPort.get_issue_evidence's
        # own single-ID-lookup shape).
        row = (
            await self._session.execute(
                text(
                    "SELECT s.id, s.name, s.role, "
                    "(SELECT MAX(e.occurred_at) FROM events e WHERE e.stakeholder_id = s.id) "
                    "AS last_seen_at "
                    "FROM stakeholders s WHERE s.id = :id"
                ),
                {"id": stakeholder_id},
            )
        ).one_or_none()
        if row is None:
            return None
        return StakeholderRecord(
            stakeholder_id=row.id, name=row.name, role=row.role, last_seen_at=row.last_seen_at
        )


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


# ---------------------------------------------------------------------------
# Ask agent (M9) — specs/008-narrator-and-ask-agent
# ---------------------------------------------------------------------------


class SqlAlchemyNarratorReadRepository(NarratorReadPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_score_run(self, score_run_id: UUID) -> NarratorSummaryRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT headline, reasons, actions FROM narrator_outputs "
                    "WHERE score_run_id = :score_run_id"
                ),
                {"score_run_id": score_run_id},
            )
        ).one_or_none()
        if row is None:
            return None
        return NarratorSummaryRecord(
            headline=row.headline, reasons=tuple(row.reasons), actions=tuple(row.actions)
        )

    async def get_latest(self) -> NarratorSummaryRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT headline, reasons, actions FROM narrator_outputs "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return NarratorSummaryRecord(
            headline=row.headline, reasons=tuple(row.reasons), actions=tuple(row.actions)
        )


class SqlAlchemyLedgerQueryRepository(LedgerQueryPort):
    """Reuses `app.readers.adapters.SqlAlchemyConfirmedBaselineRepository`'s
    query shape (feature 007) — implemented independently here, not
    imported, per this codebase's established no-cross-module-adapter-import
    convention (`research.md`'s Decision)."""

    _MIN_BASELINE_SAMPLES = 5
    """REQ-M6-CAL-04's floor, mirrored from the Tone reader — the same
    threshold, applied here for the same reason (`research.md` Decision 4)."""

    def __init__(self, session: AsyncSession, encryption: EncryptionPort) -> None:
        self._session = session
        self._encryption = encryption

    async def baseline_vs_current(
        self, stakeholder_id: UUID
    ) -> tuple[ConfirmedBaselineWindow, list[MessageEventInfo]] | None:
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

        baseline_rows = (
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
        sample_texts = [
            t
            for r in baseline_rows
            if (t := _quoted_text(r.structured_payload, r.body_encrypted, self._encryption))
        ]
        if len(sample_texts) < self._MIN_BASELINE_SAMPLES:
            return None

        window = ConfirmedBaselineWindow(
            stakeholder_id=stakeholder_id,
            window_start=confirmation.window_start,
            window_end=confirmation.window_end,
            sample_texts=tuple(sample_texts),
        )
        current = await self.timeline_for_stakeholder(stakeholder_id, limit=10)
        return window, current

    async def timeline_for_stakeholder(
        self, stakeholder_id: UUID, *, limit: int = 20
    ) -> list[MessageEventInfo]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, occurred_at, structured_payload, body_encrypted FROM events "
                    "WHERE stakeholder_id = :stakeholder_id "
                    "AND event_type IN ('message'::event_type, "
                    "'ticket_state_change'::event_type) "
                    "ORDER BY occurred_at DESC LIMIT :limit"
                ),
                {"stakeholder_id": stakeholder_id, "limit": limit},
            )
        ).all()
        return [
            MessageEventInfo(
                event_id=r.id,
                occurred_at=r.occurred_at,
                stakeholder_id=stakeholder_id,
                text=_quoted_text(r.structured_payload, r.body_encrypted, self._encryption) or "",
            )
            for r in rows
        ]


class SqlAlchemyAskQueryRepository(AskQueryRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        *,
        question_text: str,
        matched_intent: str | None,
        rendered_component: str | None,
        declined_reason: str | None,
        response_time_ms: int,
        asked_by_user_id: UUID,
    ) -> None:
        await self._session.execute(
            text(
                "INSERT INTO ask_queries (question_text, matched_intent, rendered_component, "
                "declined_reason, response_time_ms, asked_by_user_id) "
                "VALUES (:question_text, :matched_intent, :rendered_component, "
                "CAST(:declined_reason AS declined_reason), :response_time_ms, "
                ":asked_by_user_id)"
            ),
            {
                "question_text": question_text,
                "matched_intent": matched_intent,
                "rendered_component": rendered_component,
                "declined_reason": declined_reason,
                "response_time_ms": response_time_ms,
                "asked_by_user_id": asked_by_user_id,
            },
        )
        await self._session.commit()


# ---------------------------------------------------------------------------
# Draft composer (M10) — specs/009-draft-composer
# ---------------------------------------------------------------------------


class SqlAlchemyIssueReader(IssueReadPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_issue_evidence(self, issue_id: UUID) -> IssueEvidenceRecord | None:
        # status = 'validated' filter, matching SqlAlchemyFindingReader.
        # get_finding's own precedent (research.md Decision 3) — an issue
        # whose only findings are pending/quarantined has no evidence a
        # draft may cite.
        rows = (
            await self._session.execute(
                text(
                    "SELECT i.label, f.finding_type, f.cited_event_ids "
                    "FROM issues i "
                    "JOIN finding_issue_map fim ON fim.issue_id = i.id "
                    "JOIN findings f ON f.id = fim.finding_id AND f.status = 'validated' "
                    "WHERE i.id = :issue_id"
                ),
                {"issue_id": issue_id},
            )
        ).all()
        if not rows:
            return None
        finding_types: dict[str, None] = {}
        cited_event_ids: dict[UUID, None] = {}
        for r in rows:
            finding_types[r.finding_type] = None
            for event_id in r.cited_event_ids:
                cited_event_ids[event_id] = None
        return IssueEvidenceRecord(
            issue_id=issue_id,
            label=rows[0].label,
            finding_types=tuple(finding_types),
            cited_event_ids=tuple(cited_event_ids),
        )


class SqlAlchemyPlaybookReader(PlaybookReadPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def finding_type_for_playbook(self, playbook_id: UUID) -> str | None:
        row = (
            await self._session.execute(
                text("SELECT applies_to_finding_type FROM playbook_actions WHERE id = :id"),
                {"id": playbook_id},
            )
        ).one_or_none()
        return row.applies_to_finding_type if row is not None else None


class SqlAlchemyDraftMessageRepository(DraftMessageRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist(
        self,
        draft: GeneratedDraft,
        *,
        issue_id: UUID,
        stakeholder_id: UUID,
        requested_by_user_id: UUID,
    ) -> UUID:
        row = (
            await self._session.execute(
                text(
                    "INSERT INTO draft_messages (issue_id, stakeholder_id, "
                    "requested_by_user_id, draft_text, tone_variant, evidence_event_ids, "
                    "checks_passed) "
                    "VALUES (:issue_id, :stakeholder_id, :requested_by_user_id, :draft_text, "
                    "CAST(:tone_variant AS tone_variant), :evidence_event_ids, "
                    ":checks_passed) "
                    "RETURNING id"
                ),
                {
                    "issue_id": issue_id,
                    "stakeholder_id": stakeholder_id,
                    "requested_by_user_id": requested_by_user_id,
                    "draft_text": draft.draft_text,
                    "tone_variant": draft.tone_variant,
                    "evidence_event_ids": list(draft.evidence_event_ids),
                    "checks_passed": draft.check_result.passed,
                },
            )
        ).one()
        await self._session.commit()
        return row.id

    async def get(self, draft_id: UUID) -> DraftMessageRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT id, issue_id, stakeholder_id, draft_text, tone_variant, "
                    "evidence_event_ids, checks_passed, copied_at, logged_manually_at "
                    "FROM draft_messages WHERE id = :id"
                ),
                {"id": draft_id},
            )
        ).one_or_none()
        if row is None:
            return None
        return DraftMessageRecord(
            id=row.id,
            issue_id=row.issue_id,
            stakeholder_id=row.stakeholder_id,
            draft_text=row.draft_text,
            tone_variant=row.tone_variant,
            evidence_event_ids=tuple(row.evidence_event_ids),
            checks_passed=row.checks_passed,
            copied_at=row.copied_at,
            logged_manually_at=row.logged_manually_at,
        )

    async def stamp_copied(self, draft_id: UUID) -> bool:
        result = await self._session.execute(
            text("UPDATE draft_messages SET copied_at = now() WHERE id = :id"),
            {"id": draft_id},
        )
        await self._session.commit()
        return result.rowcount > 0

    async def stamp_logged_manually(self, draft_id: UUID) -> bool:
        result = await self._session.execute(
            text("UPDATE draft_messages SET logged_manually_at = now() WHERE id = :id"),
            {"id": draft_id},
        )
        await self._session.commit()
        return result.rowcount > 0


class SqlAlchemyDampingDisclosureReader(DampingDisclosurePort):
    """Read-only consumer of feature 010's `damping_weights` table — the
    weight-gated filter (`AND weight < 1.000`) is the single source of
    truth for "should this ever be shown," not any logic in the caller
    (`specs/010-feedback-memory/research.md` Decision 4)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_disclosure(self, pattern_signature: str) -> DisclosureRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT disclosure_text FROM damping_weights "
                    "WHERE pattern_signature = :ps AND weight < 1.000"
                ),
                {"ps": pattern_signature},
            )
        ).one_or_none()
        if row is None or row.disclosure_text is None:
            return None
        return DisclosureRecord(disclosure_text=row.disclosure_text)
