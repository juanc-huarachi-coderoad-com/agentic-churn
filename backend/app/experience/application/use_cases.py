"""Application use cases for the experience (M8) read layer — dashboard,
evidence trace panel, system health. Pure reads and formatting only
(REQ-M8-01, REQ-M8-P1); `GetDashboardUseCase` supersedes feature 002's
`GetDashboardShellUseCase` now that real score/finding/coverage data exists.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.context.domain.damping_calculator import pattern_signature
from app.experience.application.ports import (
    ClientProfileRepositoryPort,
    CoveragePort,
    DampingDisclosurePort,
    DraftMessageRepositoryPort,
    FindingReadPort,
    IdentityGapPort,
    IssueReadPort,
    LedgerQueryPort,
    NarratorReadPort,
    PlaybookReadPort,
    PulseEventPort,
    ScoreReadPort,
    StakeholderReadPort,
)
from app.experience.application.prompts.draft_composer_v1 import (
    DraftModelOutput,
)
from app.experience.application.prompts.draft_composer_v1 import (
    build_prompt as build_draft_prompt,
)
from app.experience.domain.entities import (
    AgreedAction,
    ArithmeticClause,
    CitedEventRecord,
    DraftCheckResult,
    EvidenceComparison,
    GeneratedDraft,
    NarratorSummaryRecord,
    VerifiedDateSet,
)
from app.experience.domain.services import (
    build_verified_date_set,
    build_verified_fact_set,
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
    verify_dates,
    verify_facts,
    verify_no_concession,
    verify_no_invented_cause,
    verify_no_leak,
)
from app.narrator.domain.entities import VerifiedFactSet
from app.readers.application.ports import LLMPort

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
class NarratorResult:
    """specs/008-narrator-and-ask-agent — `null` on `DashboardResponse` when
    no `narrator_outputs` row exists yet for the latest run (REQ-M8-P2's
    "absent, not empty" discipline, `contracts/dashboard.md`)."""

    headline: str
    reasons: tuple[dict[str, object], ...]
    actions: tuple[dict[str, object], ...]


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
    narrator: NarratorResult | None = None


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
        narrator: NarratorReadPort,
    ) -> None:
        self._profile = profile
        self._score = score
        self._pulse = pulse
        self._stakeholders = stakeholders
        self._coverage = coverage
        self._identity_gaps = identity_gaps
        self._narrator = narrator

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
        narrator_result: NarratorResult | None = None
        if latest_run is not None:
            narrator_summary = await self._narrator.get_for_score_run(latest_run.id)
            if narrator_summary is not None:
                narrator_result = NarratorResult(
                    headline=narrator_summary.headline,
                    reasons=narrator_summary.reasons,
                    actions=narrator_summary.actions,
                )
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
            narrator=narrator_result,
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
    disclosure_text: str | None


class GetEvidenceTraceUseCase:
    """Dispatches by `finding_type` (`data-model.md`'s table,
    `app.experience.domain.services`) — falls back to
    `evaluate_generic_evidence()` for a type outside the five feature-005
    readers produce (`/speckit-analyze` finding CV1)."""

    def __init__(
        self,
        score: ScoreReadPort,
        findings: FindingReadPort,
        damping: DampingDisclosurePort | None = None,
    ) -> None:
        self._score = score
        self._findings = findings
        self._damping = damping

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

        disclosure_text = None
        if self._damping is not None:
            pattern = pattern_signature(finding.reader_type, finding.finding_type)
            disclosure = await self._damping.get_disclosure(pattern)
            if disclosure is not None:
                disclosure_text = disclosure.disclosure_text

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
            disclosure_text=disclosure_text,
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
class AskIntentCoverageResult:
    """specs/008-narrator-and-ask-agent — SC-007's own promise that the Ask
    agent's fallback rate is visible without querying the database directly
    (found missing during `/speckit-analyze`, E1)."""

    total_questions: int
    fallback_count: int
    fallback_rate: float


@dataclass(frozen=True)
class CoverageResult:
    sources: list[SourceStatusResult]
    quarantine: list[QuarantineEntryResult]
    ask_intent_coverage: AskIntentCoverageResult | None = None


class GetCoverageUseCase:
    def __init__(self, coverage: CoveragePort) -> None:
        self._coverage = coverage

    async def execute(self) -> CoverageResult:
        sources = await self._coverage.list_sources()
        quarantine = await self._coverage.list_quarantine()
        ask_intent_coverage = await self._coverage.ask_intent_coverage()
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
            ask_intent_coverage=(
                AskIntentCoverageResult(
                    total_questions=ask_intent_coverage.total_questions,
                    fallback_count=ask_intent_coverage.fallback_count,
                    fallback_rate=ask_intent_coverage.fallback_rate,
                )
                if ask_intent_coverage is not None
                else None
            ),
        )


# ---------------------------------------------------------------------------
# GenerateDraftUseCase — Draft composer (M10), specs/009-draft-composer
# ---------------------------------------------------------------------------


class IssueNotFoundError(Exception):
    """`issue_id` doesn't resolve to an issue with cited (validated)
    evidence — the route's `404` path (`contracts/drafts.md`)."""


class StakeholderNotFoundError(Exception):
    """`stakeholder_id` doesn't resolve to a stakeholder on the current
    profile — the route's `404` path (`/speckit-analyze` finding U3)."""


class DraftCheckFailedError(Exception):
    """`DraftCheckResult.passed` is `False` — the route's `422` path. Never
    carries which check failed (`research.md` Decision 7, Clarifications
    2026-08-16): the CS lead sees the same generic failure message a
    generation error/timeout already produces."""


@dataclass(frozen=True)
class DraftResult:
    id: UUID
    draft_text: str
    tone_variant: str
    evidence_event_ids: tuple[UUID, ...]
    checks_passed: bool


class GenerateDraftUseCase:
    """A plain `LLMPort` call, no orchestration framework
    (`decisions/02-repo-and-tooling.md`'s ratified shape for M10,
    `research.md` Decision 2) — fetch inputs, generate, run all five
    pre-display checks (REQ-M10-07, `research.md` Decision 6), persist only
    on a full pass (`research.md` Decision 7)."""

    def __init__(
        self,
        issues: IssueReadPort,
        stakeholders: StakeholderReadPort,
        profile: ClientProfileRepositoryPort,
        ledger: LedgerQueryPort,
        narrator: NarratorReadPort,
        playbook: PlaybookReadPort,
        findings: FindingReadPort,
        drafts: DraftMessageRepositoryPort,
        llm: LLMPort,
    ) -> None:
        self._issues = issues
        self._stakeholders = stakeholders
        self._profile = profile
        self._ledger = ledger
        self._narrator = narrator
        self._playbook = playbook
        self._findings = findings
        self._drafts = drafts
        self._llm = llm

    async def execute(
        self,
        *,
        issue_id: UUID,
        stakeholder_id: UUID,
        tone_variant: str,
        requested_by_user_id: UUID,
    ) -> DraftResult:
        stakeholder = await self._stakeholders.get(stakeholder_id)
        if stakeholder is None:
            raise StakeholderNotFoundError(stakeholder_id)

        issue_evidence = await self._issues.get_issue_evidence(issue_id)
        if issue_evidence is None:
            raise IssueNotFoundError(issue_id)

        profile = await self._profile.get_current()
        client_name = profile.client_name if profile is not None else ""
        communication_norms = profile.communication_norms if profile is not None else None

        events = await self._findings.resolve_events(list(issue_evidence.cited_event_ids))
        evidence_texts = [e.quoted_text for e in events if e.quoted_text]

        thread_history = await self._ledger.timeline_for_stakeholder(stakeholder_id)
        thread_history_texts = [m.text for m in thread_history if m.text]

        narrator_summary = await self._narrator.get_latest()
        agreed_actions = await self._resolve_agreed_actions(
            narrator_summary, issue_evidence.finding_types
        )

        facts = build_verified_fact_set(
            evidence_texts=evidence_texts,
            thread_history_texts=thread_history_texts,
            stakeholder_name=stakeholder.name,
            client_name=client_name,
        )
        dates = build_verified_date_set(agreed_actions)

        prompt = build_draft_prompt(
            stakeholder_name=stakeholder.name,
            tone_variant=tone_variant,
            issue_label=issue_evidence.label,
            evidence_texts=evidence_texts,
            communication_norms=communication_norms,
            thread_history_texts=thread_history_texts,
            agreed_actions=[
                {"text": a.text, "owner": a.owner, "due_date": a.due_date}
                for a in agreed_actions
            ],
        )
        model_output = await self._llm.generate_structured(prompt, DraftModelOutput)

        check_result = self._run_checks(model_output.draft_text, facts, dates)
        if not check_result.passed:
            raise DraftCheckFailedError()

        generated = GeneratedDraft(
            draft_text=model_output.draft_text,
            tone_variant=model_output.tone_variant or tone_variant,
            evidence_event_ids=issue_evidence.cited_event_ids,
            check_result=check_result,
        )
        draft_id = await self._drafts.persist(
            generated,
            issue_id=issue_id,
            stakeholder_id=stakeholder_id,
            requested_by_user_id=requested_by_user_id,
        )
        return DraftResult(
            id=draft_id,
            draft_text=generated.draft_text,
            tone_variant=generated.tone_variant,
            evidence_event_ids=generated.evidence_event_ids,
            checks_passed=True,
        )

    async def _resolve_agreed_actions(
        self, narrator_summary: NarratorSummaryRecord | None, finding_types: tuple[str, ...]
    ) -> list[AgreedAction]:
        """Filters the latest run's already-narrated, already-dated actions
        down to the requested issue's own finding types (`research.md`
        Decision 4) — the only source of a "human-supplied" date."""
        if narrator_summary is None:
            return []
        finding_type_set = set(finding_types)
        resolved: list[AgreedAction] = []
        for raw_action in narrator_summary.actions:
            playbook_id_raw = raw_action.get("playbook_id")
            if not playbook_id_raw:
                continue
            try:
                playbook_id = UUID(str(playbook_id_raw))
            except ValueError:
                continue
            action_finding_type = await self._playbook.finding_type_for_playbook(playbook_id)
            if action_finding_type is not None and action_finding_type in finding_type_set:
                resolved.append(
                    AgreedAction(
                        text=str(raw_action.get("text", "")),
                        owner=str(raw_action.get("owner", "")),
                        due_date=str(raw_action.get("due_date", "")),
                        finding_type=action_finding_type,
                    )
                )
        return resolved

    def _run_checks(
        self, draft_text: str, facts: VerifiedFactSet, dates: VerifiedDateSet
    ) -> DraftCheckResult:
        fact_result = verify_facts(draft_text, facts)
        date_result = verify_dates(draft_text, dates)
        cause_result = verify_no_invented_cause(draft_text, facts)
        leak_result = verify_no_leak(draft_text)
        concession_result = verify_no_concession(draft_text)
        passed = all(
            (
                fact_result.passed,
                date_result.passed,
                cause_result.passed,
                leak_result.passed,
                concession_result.passed,
            )
        )
        return DraftCheckResult(
            passed=passed,
            fact_check=fact_result,
            date_check=date_result,
            cause_check=cause_result,
            leak_check=leak_result,
            concession_check=concession_result,
        )
