"""Application use cases for the experience (M8) read layer — dashboard,
evidence trace panel, system health. Pure reads and formatting only
(REQ-M8-01, REQ-M8-P1); `GetDashboardUseCase` supersedes feature 002's
`GetDashboardShellUseCase` now that real score/finding/coverage data exists.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.experience.application.ports import (
    ClientProfileRepositoryPort,
    CoveragePort,
    FindingReadPort,
    IdentityGapPort,
    PulseEventPort,
    ScoreReadPort,
    StakeholderReadPort,
)
from app.experience.domain.entities import ArithmeticClause, CitedEventRecord, EvidenceComparison
from app.experience.domain.services import (
    evaluate_absence_evidence,
    evaluate_commitment_evidence,
    evaluate_generic_evidence,
    evaluate_recurrence_evidence,
    evaluate_relationship_evidence,
    evaluate_usage_evidence,
    format_arithmetic,
    pulse_severity,
    render_state_message,
    resolve_dashboard_state,
)

_PULSE_WINDOW_DAYS = 14
_TREND_DAYS = 14
_STAKEHOLDER_ACTIVE_WINDOW_DAYS = 28
"""Reuses `RelationshipReader`'s existing `_WINDOW_DAYS = 28` constant
(feature 005, `research.md`'s Decision) — not a new window."""
_UNRESOLVED_MIN_COUNT = 3

_COMMITMENT_FINDING_TYPES = frozenset({"broken_response_promise", "commitment_met"})


# ---------------------------------------------------------------------------
# GetDashboardUseCase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClientHeaderResult:
    client_name: str
    band: str | None
    days_to_renewal: int | None


@dataclass(frozen=True)
class ScoreBlockResult:
    score: float
    band: str
    trend: list[float]


@dataclass(frozen=True)
class ContributionBarResult:
    score_contribution_id: UUID
    label: str
    points: float
    is_positive: bool


@dataclass(frozen=True)
class PulseEventResult:
    event_id: UUID
    occurred_at: datetime
    severity: str
    quoted_text: str | None
    score_contribution_id: UUID


@dataclass(frozen=True)
class StakeholderCardResult:
    stakeholder_id: UUID | None
    """`None` for a synthetic unresolved-identity card — never a real
    stakeholder (spec.md's User Story 4, Acceptance Scenario 3)."""
    name: str
    role: str
    tone_trajectory: str
    last_seen_at: datetime | None
    status: str


@dataclass(frozen=True)
class CoverageLineResult:
    sources_read: int
    sources_expected: int
    complete_to: datetime | None
    status: str


@dataclass(frozen=True)
class DashboardResult:
    client_header: ClientHeaderResult | None
    state: str
    message: str | None
    score_block: ScoreBlockResult | None
    contribution_bars: list[ContributionBarResult]
    pulse_timeline: list[PulseEventResult]
    stakeholder_cards: list[StakeholderCardResult]
    coverage_line: CoverageLineResult | None


class GetDashboardUseCase:
    """Assembles the full `DashboardResponse` (`architecture/07-api-spec.md`)
    from real, already-computed data — no scoring/ranking/aggregation of its
    own (REQ-M8-01, REQ-M8-P1)."""

    def __init__(
        self,
        profile: ClientProfileRepositoryPort,
        score: ScoreReadPort,
        pulse: PulseEventPort,
        stakeholders: StakeholderReadPort,
        coverage: CoveragePort,
        identity_gaps: IdentityGapPort,
    ) -> None:
        self._profile = profile
        self._score = score
        self._pulse = pulse
        self._stakeholders = stakeholders
        self._coverage = coverage
        self._identity_gaps = identity_gaps

    async def execute(self) -> DashboardResult:
        profile = await self._profile.get_current()
        if profile is None:
            return DashboardResult(
                client_header=None,
                state="no_profile",
                message=None,
                score_block=None,
                contribution_bars=[],
                pulse_timeline=[],
                stakeholder_cards=[],
                coverage_line=None,
            )

        now = datetime.now(UTC)

        latest_run = await self._score.latest_run()
        sources = await self._coverage.list_sources()
        report = await self._coverage.latest_report()
        signal_types = await self._coverage.connected_signal_type_count()
        unresolved = await self._identity_gaps.list_unresolved(min_count=_UNRESOLVED_MIN_COUNT)

        disconnected = next((s for s in sources if s.status == "disconnected"), None)
        degraded = disconnected is None and (
            any(s.status == "degraded" for s in sources)
            or (report is not None and report.sources_read < report.sources_expected)
        )
        minutes_behind = (
            max(0, int((now - report.complete_to).total_seconds() // 60))
            if report is not None
            else None
        )
        top_unresolved = unresolved[0] if unresolved else None
        unresolved_domain = (
            top_unresolved.participant.split("@")[-1]
            if top_unresolved is not None and "@" in top_unresolved.participant
            else (top_unresolved.participant if top_unresolved is not None else None)
        )

        score_block = None
        contribution_bars: list[ContributionBarResult] = []
        pulse_timeline: list[PulseEventResult] = []
        if latest_run is not None:
            contributions = await self._score.list_contributions(latest_run.id)
            trend = await self._score.trend(days=_TREND_DAYS)
            score_block = ScoreBlockResult(
                score=latest_run.score, band=latest_run.band, trend=trend
            )
            contribution_bars = [
                ContributionBarResult(
                    score_contribution_id=c.id,
                    label=c.finding_type,
                    points=c.points_contributed,
                    is_positive=c.is_positive,
                )
                for c in contributions
            ]
            pulse_records = await self._pulse.list_recent(
                since=now - timedelta(days=_PULSE_WINDOW_DAYS)
            )
            pulse_timeline = [
                PulseEventResult(
                    event_id=p.event_id,
                    occurred_at=p.occurred_at,
                    severity=pulse_severity(
                        finding_type=p.finding_type, is_positive=p.is_positive
                    ),
                    quoted_text=p.quoted_text,
                    score_contribution_id=p.score_contribution_id,
                )
                for p in pulse_records
            ]

        active_cutoff = now - timedelta(days=_STAKEHOLDER_ACTIVE_WINDOW_DAYS)
        stakeholder_cards = [
            StakeholderCardResult(
                stakeholder_id=s.stakeholder_id,
                name=s.name,
                role=s.role,
                tone_trajectory="unknown",
                last_seen_at=s.last_seen_at,
                status=(
                    "active"
                    if s.last_seen_at is not None and s.last_seen_at >= active_cutoff
                    else "quiet"
                ),
            )
            for s in await self._stakeholders.list_stakeholders()
        ]
        stakeholder_cards.extend(
            StakeholderCardResult(
                stakeholder_id=None,
                name=u.participant,
                role="Unidentified",
                tone_trajectory="unknown",
                last_seen_at=None,
                status="unresolved_identity",
            )
            for u in unresolved
        )

        minutes_since_last_check = (
            int((now - latest_run.computed_at).total_seconds() // 60)
            if latest_run is not None
            else 0
        )
        state = resolve_dashboard_state(
            has_profile=True,
            disconnected_source_name=(disconnected.display_name if disconnected else None),
            disconnected_source_last_read_at=(
                disconnected.last_successful_sync_at if disconnected else None
            ),
            unresolved_domain=unresolved_domain,
            unresolved_count=(top_unresolved.count if top_unresolved else 0),
            degraded=degraded,
            minutes_behind=minutes_behind,
            connected_signal_types=signal_types,
            band=(latest_run.band if latest_run else None),
            contribution_count=len(contribution_bars),
            minutes_since_last_check=minutes_since_last_check,
        )

        client_header = ClientHeaderResult(
            client_name=profile.client_name,
            band=(latest_run.band if latest_run else None),
            days_to_renewal=(
                (profile.renewal_date - now.date()).days if profile.renewal_date else None
            ),
        )
        coverage_line = CoverageLineResult(
            sources_read=(report.sources_read if report else 0),
            sources_expected=(report.sources_expected if report else len(sources)),
            complete_to=(report.complete_to if report else None),
            status=("degraded" if degraded else "disconnected" if disconnected else "ok"),
        )

        return DashboardResult(
            client_header=client_header,
            state=state.kind,
            message=render_state_message(state),
            score_block=score_block,
            contribution_bars=contribution_bars,
            pulse_timeline=pulse_timeline,
            stakeholder_cards=stakeholder_cards,
            coverage_line=coverage_line,
        )


# ---------------------------------------------------------------------------
# GetEvidenceTraceUseCase
# ---------------------------------------------------------------------------


class EvidenceNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class QuotedMessageResult:
    event_id: UUID
    text: str | None
    occurred_at: datetime


@dataclass(frozen=True)
class EvidenceTraceResult:
    finding_id: UUID
    finding_type: str
    points: float
    comparison: EvidenceComparison
    quoted_messages: list[QuotedMessageResult]
    arithmetic: list[ArithmeticClause]


class GetEvidenceTraceUseCase:
    """Dispatches by `finding_type` (`data-model.md`'s table,
    `app.experience.domain.services`) — falls back to
    `evaluate_generic_evidence()` for a type outside the five feature-005
    readers produce (`/speckit-analyze` finding CV1)."""

    def __init__(self, score: ScoreReadPort, findings: FindingReadPort) -> None:
        self._score = score
        self._findings = findings

    async def execute(self, score_contribution_id: UUID) -> EvidenceTraceResult:
        contribution = await self._score.get_contribution(score_contribution_id)
        if contribution is None:
            raise EvidenceNotFoundError(score_contribution_id)

        finding = await self._findings.get_finding(contribution.finding_id)
        if finding is None:
            raise EvidenceNotFoundError(score_contribution_id)

        events = await self._findings.resolve_events(list(finding.cited_event_ids))
        comparison = await self._dispatch_comparison(finding.finding_type, events)
        arithmetic = format_arithmetic(contribution)

        return EvidenceTraceResult(
            finding_id=finding.id,
            finding_type=finding.finding_type,
            points=contribution.points_contributed,
            comparison=comparison,
            quoted_messages=[
                QuotedMessageResult(
                    event_id=e.event_id, text=e.quoted_text, occurred_at=e.occurred_at
                )
                for e in events
            ],
            arithmetic=list(arithmetic),
        )

    async def _dispatch_comparison(
        self, finding_type: str, events: list[CitedEventRecord]
    ) -> EvidenceComparison:
        if finding_type in _COMMITMENT_FINDING_TYPES and events:
            comparison = await self._findings.get_commitment_comparison(events[0].event_id)
            if comparison is not None:
                return evaluate_commitment_evidence(comparison)
        if finding_type == "usage_deviation" and events:
            usage = await self._findings.get_usage_comparison(events[0].event_id)
            if usage is not None:
                return evaluate_usage_evidence(usage)
        if finding_type == "contact_absence" and events:
            return evaluate_absence_evidence(events[0])
        if finding_type == "relationship_change" and events:
            return evaluate_relationship_evidence(events[0])
        if finding_type == "recurring_issue":
            return evaluate_recurrence_evidence(cited_event_count=len(events))
        return evaluate_generic_evidence()


# ---------------------------------------------------------------------------
# GetCoverageUseCase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceStatusResult:
    source_type: str
    status: str
    last_successful_sync_at: datetime | None


@dataclass(frozen=True)
class QuarantineEntryResult:
    finding_id: UUID
    failed_check: str


@dataclass(frozen=True)
class CoverageResult:
    sources: list[SourceStatusResult]
    quarantine: list[QuarantineEntryResult]


class GetCoverageUseCase:
    def __init__(self, coverage: CoveragePort) -> None:
        self._coverage = coverage

    async def execute(self) -> CoverageResult:
        sources = await self._coverage.list_sources()
        quarantine = await self._coverage.list_quarantine()
        return CoverageResult(
            sources=[
                SourceStatusResult(
                    source_type=s.source_type,
                    status=s.status,
                    last_successful_sync_at=s.last_successful_sync_at,
                )
                for s in sources
            ],
            quarantine=[
                QuarantineEntryResult(finding_id=q.finding_id, failed_check=q.failed_check)
                for q in quarantine
            ],
        )
