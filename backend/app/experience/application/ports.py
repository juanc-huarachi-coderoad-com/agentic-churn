"""Ports the experience (M8) application layer depends on — implemented by
app.experience.adapters.*. Reader-owned, no cross-module adapter import
(`research.md`'s Decision — mirrors feature 004/005's own established
convention for reading another module's owned tables).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.experience.domain.entities import (
    CitedEventRecord,
    CommitmentComparisonRecord,
    ContributionRecord,
    UsageComparisonRecord,
)


@dataclass(frozen=True)
class ClientProfileRecord:
    client_name: str
    renewal_date: date | None = None
    """Added for `ClientHeader.days_to_renewal` — `research.md`'s Decision,
    `/speckit-analyze` finding CV2 (extends this existing port, not a new one)."""


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
        """Real, and always empty until feature 007's `ValidationGate`
        exists — `findings.status = 'quarantined'` never occurs yet
        (spec.md's Note on scope)."""
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
