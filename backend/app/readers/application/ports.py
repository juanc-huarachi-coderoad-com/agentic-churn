"""Ports the readers application layer depends on — implemented by
app.readers.adapters.*. Application depends on these, never on a concrete
adapter (constitution P8, Dependency Inversion), enforced mechanically by
`.importlinter`. Reader-owned ports reading the same underlying tables
`app.ingestion`'s own ports read, for a different query shape — no cross-module
adapter import (feature 004's established convention, `research.md`'s Decision).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from app.readers.domain.entities import (
    CandidateTicket,
    ConfirmedBaselineWindow,
    FailedCheck,
    MeetingTranscriptInfo,
    MessageEventInfo,
    ResponsePairInfo,
)
from app.scoring.domain.entities import Finding

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Tone / Intent readers (LLMPort, MessageEventRepositoryPort) — specs/007-model-findings
# ---------------------------------------------------------------------------


class LLMPort(ABC):
    """`architecture/09-clean-architecture-and-patterns.md`'s already-named
    single-method interface — no `tools` parameter exists, structurally
    making tool-granting impossible from a reader's side (REQ-M5-P2)."""

    @abstractmethod
    async def generate_structured(self, prompt: str, schema: type[T]) -> T: ...


class MessageEventRepositoryPort(ABC):
    @abstractmethod
    async def list_all(self) -> list[MessageEventInfo]:
        """Every message-bearing event (Gmail/Slack `message`, Zendesk
        `ticket_state_change`) — the shared candidate corpus Tone and Intent
        both self-fetch from. Cache filtering against already-interpreted
        events happens in each reader via `FindingRepositoryPort.
        already_interpreted`, not here."""
        ...


class ConfirmedBaselineRepositoryPort(ABC):
    @abstractmethod
    async def get_confirmed_window(
        self, stakeholder_id: UUID
    ) -> ConfirmedBaselineWindow | None:
        """`None` if no `baseline_confirmations` row exists yet for this
        stakeholder — the common case until `scripts/confirm_baseline.py` has
        been run (`research.md` Decision 3)."""
        ...


class FindingTypeConfigPort(ABC):
    @abstractmethod
    async def get_thresholds(self, finding_type: str) -> tuple[float, int] | None:
        """`(confidence_floor, min_evidence_count)`, or `None` if
        `finding_type` isn't a configured row — that `None` case *is* how the
        gate's schema check's `finding_type`-membership sub-check is
        implemented (`research.md` Decision 6.1), not a separate code path."""
        ...


class EventExistencePort(ABC):
    @abstractmethod
    async def existing_ids(self, ids: list[UUID]) -> set[UUID]:
        """Which of the given IDs are real rows in `events` — the gate's
        `cited_event_missing` check."""
        ...


class QuarantineRepositoryPort(ABC):
    @abstractmethod
    async def record(self, finding_id: UUID, failed_checks: list[FailedCheck]) -> None: ...


class MeetingTranscriptRepositoryPort(ABC):
    @abstractmethod
    async def list_all(self) -> list[MeetingTranscriptInfo]:
        """Every `meeting`-type event — FR-023's fetch-time consent gate
        (`SimulatedCollector.fetch`) already guarantees every row here came
        from a series with documented, all-party consent; nothing in this
        module needs to re-check `consent_documented`, there being nothing
        left to check it against."""
        ...


# ---------------------------------------------------------------------------
# Commitment reader (ResponsePairRepositoryPort)
# ---------------------------------------------------------------------------


class ResponsePairRepositoryPort(ABC):
    @abstractmethod
    async def list_all(self) -> list[ResponsePairInfo]: ...


# ---------------------------------------------------------------------------
# Usage reader (RollupRepositoryPort)
# ---------------------------------------------------------------------------


class RollupRepositoryPort(ABC):
    @abstractmethod
    async def list_subjects(self) -> list[tuple[str, UUID | None, str]]:
        """`(subject_type, subject_id, metric)` triples with at least one rollup
        sample — the Usage reader's candidate set, one z-score check per triple."""
        ...

    @abstractmethod
    async def historical_values(
        self, *, subject_type: str, subject_id: UUID | None, metric: str
    ) -> list[float]:
        """All but the most recent rollup sample for this subject/metric —
        "history" the newest reading is compared against, never including itself."""
        ...

    @abstractmethod
    async def latest_value(
        self, *, subject_type: str, subject_id: UUID | None, metric: str
    ) -> tuple[float, UUID] | None:
        """The most recent sample's value and the event it came from — `None` if
        no sample exists yet for this subject/metric."""
        ...


# ---------------------------------------------------------------------------
# Absence reader (AbsenceEventRepositoryPort)
# ---------------------------------------------------------------------------


class AbsenceEventRepositoryPort(ABC):
    @abstractmethod
    async def list_all(self) -> list["AbsenceEventInfo"]:
        """Every real `absence`-type event — the REQ-M5-15 cache check (via
        `FindingRepositoryPort`) is what actually filters out already-
        interpreted ones, the same pattern every other reader's port follows."""
        ...


class AbsenceEventInfo:
    """Plain container (not a dataclass — deliberately no domain re-export of
    `structured_payload`'s raw shape) for what the Absence reader's decision
    logic needs from one real `absence`-type event."""

    __slots__ = ("event_id", "occurred_at", "window_start", "last_contact_at")

    def __init__(
        self,
        event_id: UUID,
        occurred_at: datetime,
        window_start: datetime,
        last_contact_at: datetime | None,
    ) -> None:
        self.event_id = event_id
        self.occurred_at = occurred_at
        self.window_start = window_start
        self.last_contact_at = last_contact_at


# ---------------------------------------------------------------------------
# Relationship reader (RelationshipContextPort)
# ---------------------------------------------------------------------------


class RelationshipContextPort(ABC):
    @abstractmethod
    async def list_stakeholders(self) -> list[UUID]:
        """The current profile's stakeholder IDs — the set Relationship diffs
        ledger activity against."""
        ...

    @abstractmethod
    async def active_stakeholder_ids(self, *, since: datetime) -> set[UUID]:
        """Stakeholder IDs with at least one ledger event since `since` (the
        rolling-window floor, `research.md`'s Decision: 4 weeks)."""
        ...

    @abstractmethod
    async def most_recent_event_for_stakeholder(self, stakeholder_id: UUID) -> UUID | None:
        """The evidence event a `relationship_change` finding cites — the last
        time this stakeholder was actually active, `None` if never (corrected
        during implementation: `commitments` carries no `stakeholder_id` column,
        so a real `absence`-type event can never be attributed to a specific
        stakeholder — the co-citation `spec.md`'s Edge Cases originally
        described isn't representable against the real schema; this is the
        finding's only citation)."""
        ...


# ---------------------------------------------------------------------------
# Recurrence reader (EmbeddingPort, CandidateCorpusPort)
# ---------------------------------------------------------------------------


class EmbeddingPort(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


class CandidateCorpusPort(ABC):
    @abstractmethod
    async def list_candidates(self) -> list[CandidateTicket]:
        """`ticket_state_change` titles as Recurrence's embedding candidate set
        (found missing during `/speckit-analyze`)."""
        ...


# ---------------------------------------------------------------------------
# Shared (FindingRepositoryPort)
# ---------------------------------------------------------------------------


class FindingRepositoryPort(ABC):
    @abstractmethod
    async def already_interpreted(
        self, *, reader_type: str, reader_version: str, event_id: UUID
    ) -> bool:
        """The REQ-M5-15 cache check — a direct query against `findings`, not a
        new table (`research.md`'s Decision)."""
        ...

    @abstractmethod
    async def persist(self, finding: Finding) -> None: ...
