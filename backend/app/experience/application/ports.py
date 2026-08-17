"""Ports the experience (M8) application layer depends on — implemented by
app.experience.adapters.*. Reader-owned, no cross-module adapter import
(`research.md`'s Decision — mirrors feature 004/005's own established
convention for reading another module's owned tables).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, TypedDict
from uuid import UUID

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
from app.readers.domain.entities import ConfirmedBaselineWindow, MessageEventInfo


@dataclass(frozen=True)
class ClientProfileRecord:
    client_name: str
    renewal_date: date | None = None
    """Added for `ClientHeader.days_to_renewal` — `research.md`'s Decision,
    `/speckit-analyze` finding CV2 (extends this existing port, not a new one)."""
    communication_norms: str | None = None
    """specs/009-draft-composer, `research.md` Decision 5 — the account-wide
    free-text communication norms REQ-M10-04 personalizes drafts against."""


class ClientProfileRepositoryPort(ABC):
    @abstractmethod
    async def get_current(self) -> ClientProfileRecord | None:
        """The current (is_current = true) client_profile_versions row, or None if the
        database has never been seeded — the `no_profile` state (contracts/
        dashboard.md, spec.md Edge Cases)."""
        ...


# ---------------------------------------------------------------------------
# ScoreReadPort
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoreRunRecord:
    id: UUID
    band: str
    score: float
    computed_at: datetime


class ScoreReadPort(ABC):
    @abstractmethod
    async def latest_run(self) -> ScoreRunRecord | None: ...

    @abstractmethod
    async def trend(self, *, days: int) -> list[float]:
        """One point per day, that day's last `score_runs.score`
        (`research.md`'s Decision) — oldest first."""
        ...

    @abstractmethod
    async def list_contributions(self, score_run_id: UUID) -> list[ContributionRecord]: ...

    @abstractmethod
    async def get_contribution(
        self, score_contribution_id: UUID
    ) -> ContributionRecord | None: ...


# ---------------------------------------------------------------------------
# FindingReadPort
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FindingRecord:
    id: UUID
    finding_type: str
    cited_event_ids: tuple[UUID, ...]
    reader_type: str


class FindingReadPort(ABC):
    @abstractmethod
    async def get_finding(self, finding_id: UUID) -> FindingRecord | None: ...

    @abstractmethod
    async def resolve_events(self, event_ids: list[UUID]) -> list[CitedEventRecord]:
        """Decrypted body where a real message exists; a `ticket_state_change`'s
        own title stands in otherwise — never fabricated (spec.md's Edge Cases)."""
        ...

    @abstractmethod
    async def get_commitment_comparison(
        self, event_id: UUID
    ) -> CommitmentComparisonRecord | None:
        """`response_pairs` joined on the cited event — the Commitment dispatch
        case's baseline/current source."""
        ...

    @abstractmethod
    async def get_usage_comparison(self, event_id: UUID) -> UsageComparisonRecord | None:
        """`rollups` for the same subject/metric as the cited event — the Usage
        dispatch case's baseline/current source."""
        ...

    @abstractmethod
    async def list_open_commitments(self, *, limit: int = 20) -> list[CommitmentStatusRecord]:
        """`response_pairs` ordered most-recent-first — the Ask agent's "what
        did we promise them?" intent (specs/008-narrator-and-ask-agent)."""
        ...


# ---------------------------------------------------------------------------
# PulseEventPort
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PulseEventRecord:
    event_id: UUID
    occurred_at: datetime
    quoted_text: str | None
    finding_type: str
    is_positive: bool
    score_contribution_id: UUID
    """Not part of `architecture/07-api-spec.md`'s originally-drafted `PulseEvent`
    schema — added so a pulse event can actually satisfy FR-007's "every ...
    pulse event ... clickable through to evidence" requirement; an additive
    extension, not a contradiction (the same kind of addition `state`/`message`
    already are on `DashboardResponse`, feature 002)."""


class PulseEventPort(ABC):
    @abstractmethod
    async def list_recent(self, *, since: datetime) -> list[PulseEventRecord]:
        """Validated `score_contributions` within the window, joined to their
        findings' cited events — never a raw, unfiltered `events` scan
        (`research.md`'s Decision)."""
        ...


# ---------------------------------------------------------------------------
# StakeholderReadPort
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StakeholderRecord:
    stakeholder_id: UUID
    name: str
    role: str
    last_seen_at: datetime | None


class StakeholderReadPort(ABC):
    @abstractmethod
    async def list_stakeholders(self) -> list[StakeholderRecord]:
        """Current profile stakeholders with their most recent real ledger
        activity — `last_seen_at is None` means never active."""
        ...

    @abstractmethod
    async def get(self, stakeholder_id: UUID) -> StakeholderRecord | None:
        """`None` if `stakeholder_id` doesn't resolve to a stakeholder on the
        current profile — the draft composer's `404` path (specs/
        009-draft-composer, `research.md` Decision 13, `/speckit-analyze`
        finding U3: the original plan had no way to validate this)."""
        ...


# ---------------------------------------------------------------------------
# CoveragePort
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceRecord:
    source_type: str
    display_name: str
    status: str
    last_successful_sync_at: datetime | None


@dataclass(frozen=True)
class CoverageReportRecord:
    sources_read: int
    sources_expected: int
    gap_reason: str | None
    complete_to: datetime


@dataclass(frozen=True)
class QuarantineRecord:
    finding_id: UUID
    failed_check: str


@dataclass(frozen=True)
class AskIntentCoverageRecord:
    """specs/008-narrator-and-ask-agent — the Ask agent's own fallback rate,
    found missing from this port during `/speckit-analyze` (SC-007)."""

    total_questions: int
    fallback_count: int

    @property
    def fallback_rate(self) -> float:
        return self.fallback_count / self.total_questions if self.total_questions else 0.0


class CoveragePort(ABC):
    @abstractmethod
    async def list_sources(self) -> list[SourceRecord]: ...

    @abstractmethod
    async def latest_report(self) -> CoverageReportRecord | None: ...

    @abstractmethod
    async def connected_signal_type_count(self) -> int:
        """How many of the six counted signal types (Tickets, Email, Chat,
        Product usage, Surveys, Meetings — `requirements/08-health-
        dashboard.md`'s own list) have at least one `connected`/`degraded`
        source, out of 6 — the Learning state's real "N of 6"."""
        ...

    @abstractmethod
    async def list_quarantine(self) -> list[QuarantineRecord]:
        """Real — feature 007's `ValidationGate` is what populates
        `quarantine`; empty only when nothing has actually been quarantined
        yet, never as a placeholder."""
        ...

    @abstractmethod
    async def ask_intent_coverage(self) -> AskIntentCoverageRecord | None:
        """`None` when no `ask_queries` rows exist yet. Closes SC-007's own
        promise that the Ask agent's fallback rate is "visible and
        measurable at any time, without querying the database directly"
        (specs/008-narrator-and-ask-agent, found during `/speckit-analyze`)."""
        ...


# ---------------------------------------------------------------------------
# IdentityGapPort
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UnresolvedParticipantRecord:
    participant: str
    count: int


class IdentityGapPort(ABC):
    @abstractmethod
    async def list_unresolved(self, *, min_count: int) -> list[UnresolvedParticipantRecord]:
        """`events.structured_payload->>'participant'` grouped where
        `stakeholder_id IS NULL`, `HAVING count(*) >= min_count`
        (`research.md`'s Decision — reuses the `participant` field every
        ingestion normalizer already writes)."""
        ...


# ---------------------------------------------------------------------------
# NarratorReadPort — specs/008-narrator-and-ask-agent
# ---------------------------------------------------------------------------


class NarratorReadPort(ABC):
    @abstractmethod
    async def get_for_score_run(self, score_run_id: UUID) -> NarratorSummaryRecord | None:
        """`None` when no `narrator_outputs` row exists yet for this run —
        the "absent, not empty" discipline REQ-M8-P2 already applies
        elsewhere on this response (`contracts/dashboard.md`)."""
        ...

    @abstractmethod
    async def get_latest(self) -> NarratorSummaryRecord | None:
        """The most recent narration, regardless of score run — backs the
        Ask agent's "what should we do?" intent, which reads the same
        playbook-personalized actions the dashboard already displays rather
        than recomputing anything (REQ-M9-03)."""
        ...


# ---------------------------------------------------------------------------
# LedgerQueryPort — specs/008-narrator-and-ask-agent
# ---------------------------------------------------------------------------


class LedgerQueryPort(ABC):
    @abstractmethod
    async def baseline_vs_current(
        self, stakeholder_id: UUID
    ) -> tuple[ConfirmedBaselineWindow, list[MessageEventInfo]] | None:
        """Reuses `app.readers.domain`'s existing value objects (feature 007)
        as its return shape. `None` when the stakeholder has fewer than 5
        confirmed-baseline messages — the Ask agent's "is this normal for
        X?" intent (REQ-M9-02), and the source of the `insufficient_history`
        decline (Clarifications, 2026-08-15)."""
        ...

    @abstractmethod
    async def timeline_for_stakeholder(
        self, stakeholder_id: UUID, *, limit: int = 20
    ) -> list[MessageEventInfo]:
        """Every message-bearing event involving this stakeholder, most
        recent first — the "show me everything about X" intent."""
        ...


# ---------------------------------------------------------------------------
# AskQueryRepositoryPort — specs/008-narrator-and-ask-agent
# ---------------------------------------------------------------------------


class AskQueryRepositoryPort(ABC):
    @abstractmethod
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
        """One `ask_queries` row per graph run, regardless of which terminal
        node fired — the dataset REQ-M9's ~90% intent-coverage measurement
        reads from (FR-023)."""
        ...


# ---------------------------------------------------------------------------
# AskAgentPort — the Ask agent's own seam, `decisions/03-langgraph-for-
# ask-agent.md`. Application-layer code (ask_router.py) depends on this,
# never on `LangGraphAskAgent` directly.
# ---------------------------------------------------------------------------


class AskAgentState(TypedDict, total=False):
    """`architecture/08-class-diagrams.md` diagram 4's state shape — every
    key but `question` is absent until the node that produces it runs;
    LangGraph's `StateGraph` reads this class's type hints to build its
    channel schema, so it must be a real `TypedDict`, not a plain dict
    subclass."""

    question: str
    asked_by_user_id: UUID
    intent: str | None
    subject_hint: str | None
    tool_results: dict[str, Any]
    component: str | None
    component_props: dict[str, Any] | None
    fallback_text: str | None
    sources: tuple[UUID, ...]
    declined_reason: str | None
    started_at: float


@dataclass(frozen=True)
class AskAgentResult:
    intent: str | None
    component: str | None
    component_props: dict[str, Any] | None
    fallback_text: str | None
    sources: tuple[UUID, ...]
    declined_reason: str | None
    response_time_ms: int


class AskAgentPort(ABC):
    @abstractmethod
    async def answer(self, question: str, *, asked_by_user_id: UUID) -> AskAgentResult: ...


# ---------------------------------------------------------------------------
# Draft composer (M10) — specs/009-draft-composer
# ---------------------------------------------------------------------------


class IssueReadPort(ABC):
    @abstractmethod
    async def get_issue_evidence(self, issue_id: UUID) -> IssueEvidenceRecord | None:
        """The requested issue's own aggregated evidence — any issue with
        cited evidence, not only the top-ranked one (Clarifications,
        2026-08-16). `None` if the issue doesn't exist or has no validated
        findings."""
        ...


class PlaybookReadPort(ABC):
    @abstractmethod
    async def finding_type_for_playbook(self, playbook_id: UUID) -> str | None:
        """`playbook_actions.applies_to_finding_type` for one template —
        used to filter the latest run's narrated actions down to the
        requested issue's own finding types (research.md Decision 4)."""
        ...


@dataclass(frozen=True)
class DraftMessageRecord:
    id: UUID
    issue_id: UUID
    stakeholder_id: UUID
    draft_text: str
    tone_variant: str
    evidence_event_ids: tuple[UUID, ...]
    checks_passed: bool
    copied_at: datetime | None
    logged_manually_at: datetime | None


class DraftMessageRepositoryPort(ABC):
    @abstractmethod
    async def persist(
        self,
        draft: GeneratedDraft,
        *,
        issue_id: UUID,
        stakeholder_id: UUID,
        requested_by_user_id: UUID,
    ) -> UUID:
        """One `INSERT` into `draft_messages` — only ever called once
        `DraftCheckResult.passed` is `True` (research.md Decision 7); a
        failing result never reaches this method."""
        ...

    @abstractmethod
    async def get(self, draft_id: UUID) -> DraftMessageRecord | None: ...

    @abstractmethod
    async def stamp_copied(self, draft_id: UUID) -> bool:
        """Sets `copied_at = now()`. Returns `False` if `draft_id` doesn't
        resolve (the route's `404` path)."""
        ...

    @abstractmethod
    async def stamp_logged_manually(self, draft_id: UUID) -> bool:
        """Sets `logged_manually_at = now()` — an internal-only flag,
        writes nowhere outside this table (REQ-M10-08). Returns `False` if
        `draft_id` doesn't resolve (the route's `404` path)."""
        ...


# ---------------------------------------------------------------------------
# DampingDisclosurePort (feature 010 — feedback memory read side)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DisclosureRecord:
    disclosure_text: str


class DampingDisclosurePort(ABC):
    @abstractmethod
    async def get_disclosure(self, pattern_signature: str) -> DisclosureRecord | None:
        """`None` whenever `weight >= 1.0` — the "only when true and
        relevant" rule (REQ-M4-04, FR-011) is enforced at the read, not
        left to the caller."""
        ...
