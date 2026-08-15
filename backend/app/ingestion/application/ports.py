"""Ports the ingestion application layer depends on — implemented by
app.ingestion.adapters.*. Application depends on these, never on a concrete adapter
(constitution P8, Dependency Inversion), enforced mechanically by `.importlinter`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.ingestion.domain.business_hours import WorkingCalendar


class EncryptionPort(ABC):
    @abstractmethod
    def encrypt(self, plaintext: str) -> bytes: ...

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> str: ...


# ---------------------------------------------------------------------------
# Event ledger (T018)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventRecord:
    id: UUID
    envelope_id: UUID
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    stakeholder_id: UUID | None
    product_area_id: UUID | None
    structured_payload: dict[str, Any]
    supersedes_event_id: UUID | None
    thread_key: str | None
    body_encrypted: bytes | None


@dataclass(frozen=True)
class NewEvent:
    envelope_id: UUID
    event_type: str
    occurred_at: datetime
    stakeholder_id: UUID | None = None
    product_area_id: UUID | None = None
    body_encrypted: bytes | None = None
    structured_payload: dict[str, Any] = field(default_factory=dict)
    supersedes_event_id: UUID | None = None
    thread_key: str | None = None


@dataclass(frozen=True)
class EventThreadRow:
    thread_key: str
    event_id: UUID
    stitch_confidence: float
    stitch_method: str


@dataclass(frozen=True)
class ResponsePairRow:
    client_event_id: UUID
    reply_event_id: UUID | None
    commitment_id: UUID | None
    business_hours_elapsed: float | None
    state: str
    profile_version_id: UUID | None


@dataclass(frozen=True)
class RollupRow:
    """One computed rollup sample (REQ-M2-06) — `ComputeRollupsUseCase`'s output,
    one row per source event, not a pre-aggregated summary. `research.md`'s
    Decision: `rollups.value` is a `usage_measurement` event's own
    `value_delta_pct` reading, not a separate absolute value the event schema
    doesn't carry."""

    subject_type: str
    subject_id: UUID | None
    metric: str
    window_start: datetime
    window_end: datetime
    value: float


class EventRepositoryPort(ABC):
    @abstractmethod
    async def append(self, event: NewEvent, *, data_key_ref: str) -> UUID:
        """Appends one event, chained to whichever event was most recently appended.
        Callers MUST append in `occurred_at` order across a single run — the chain's
        verification (verify_hash_chain()) walks `ORDER BY occurred_at, id`, so
        appending out of that order would desynchronize insertion order from
        verification order (see sqlalchemy_repositories.py's docstring)."""
        ...

    @abstractmethod
    async def list_all_ordered(self) -> list[EventRecord]:
        """Every event, `ORDER BY occurred_at, id` — the same order verify_hash_chain()
        and replay both use."""
        ...

    @abstractmethod
    async def truncate_projections(self) -> None:
        """TRUNCATEs `event_threads` and `response_pairs` — REQ-M2-P3, replay rebuilds
        both from `events` alone."""
        ...

    @abstractmethod
    async def bulk_rebuild_projections(
        self, threads: list[EventThreadRow], pairs: list[ResponsePairRow]
    ) -> None: ...

    @abstractmethod
    async def truncate_rollups(self) -> None:
        """TRUNCATEs `rollups` (REQ-M2-06) — a projection, rebuilt from `events`
        alone (`data-base/01-database-overview.md`'s Principle 3), the same
        shape `event_threads`/`response_pairs` already have."""
        ...

    @abstractmethod
    async def bulk_insert_rollups(self, rows: list[RollupRow]) -> None: ...

    @abstractmethod
    async def record_replay_run(
        self, *, trigger: str, events_replayed_count: int, status: str, error: str | None
    ) -> UUID: ...

    @abstractmethod
    async def latest_event_hash(self) -> str:
        """The genesis value if the ledger is empty."""
        ...


# ---------------------------------------------------------------------------
# Client profile context — identity/exclusion/calendar targets (T029)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StakeholderIdentity:
    id: UUID
    identifiers: tuple[str, ...]


@dataclass(frozen=True)
class ProductAreaRecord:
    id: UUID
    key: str


@dataclass(frozen=True)
class CommitmentContext:
    id: UUID
    type: str
    threshold_business_hours: float | None


@dataclass(frozen=True)
class ClientProfileContext:
    profile_version_id: UUID
    stakeholders: tuple[StakeholderIdentity, ...]
    product_areas: tuple[ProductAreaRecord, ...]
    exclusions: tuple[str, ...]
    working_calendar: WorkingCalendar
    first_response_commitment: CommitmentContext | None


class ClientProfileContextPort(ABC):
    @abstractmethod
    async def get_current(self) -> ClientProfileContext: ...


# ---------------------------------------------------------------------------
# Collector run bookkeeping — sources/collector_runs/coverage_reports/raw_envelopes/
# identity_map (shared by RunCollectorUseCase and DetectAbsenceUseCase)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollectorRunStart:
    run_id: UUID
    source_id: UUID


class CollectorRunRepositoryPort(ABC):
    @abstractmethod
    async def get_or_create_source(
        self, *, source_type: str, display_name: str, auth_scope: str
    ) -> UUID: ...

    @abstractmethod
    async def start_run(
        self, *, source_id: UUID, trigger: str, window_start: datetime, window_end: datetime
    ) -> UUID: ...

    @abstractmethod
    async def finish_run(
        self,
        *,
        run_id: UUID,
        envelopes_emitted: int,
        duplicates_skipped: int,
        error: str | None,
    ) -> None: ...

    @abstractmethod
    async def record_coverage(
        self,
        *,
        collector_run_id: UUID,
        sources_expected: int,
        sources_read: int,
        gap_reason: str | None,
        complete_to: datetime,
    ) -> UUID: ...

    @abstractmethod
    async def envelope_exists(self, idempotency_key: str) -> bool: ...

    @abstractmethod
    async def insert_envelope(
        self,
        *,
        collector_run_id: UUID,
        source_native_id: str,
        idempotency_key: str,
        occurred_at: datetime,
        identity_status: str,
        redacted_fields: list[str],
        payload_encrypted: bytes,
        data_key_ref: str,
    ) -> UUID: ...

    @abstractmethod
    async def link_envelope_to_event(self, envelope_id: UUID, event_id: UUID) -> None: ...

    @abstractmethod
    async def resolve_identity(
        self, *, source_identifier: str, source_type: str
    ) -> UUID | None:
        """Looks up (or upserts, on first sight of a new identifier) `identity_map`,
        returning a `stakeholder_id` or `None` for `unresolved` — never a guess
        (REQ-M1-P5)."""
        ...


# ---------------------------------------------------------------------------
# Absence collector (T038)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecurringCommitment:
    id: UUID
    cadence: str


class CommitmentLookupPort(ABC):
    @abstractmethod
    async def list_recurring_commitments(self) -> list[RecurringCommitment]: ...

    @abstractmethod
    async def last_contact_at(self) -> datetime | None:
        """The most recent non-`absence` event's `occurred_at`, across the whole
        ledger — the "last time we heard from/about this client" signal a recurring-
        sync commitment's cadence is checked against."""
        ...


__all__ = [
    "ClientProfileContext",
    "ClientProfileContextPort",
    "CollectorRunRepositoryPort",
    "CollectorRunStart",
    "CommitmentContext",
    "CommitmentLookupPort",
    "EncryptionPort",
    "EventRecord",
    "EventRepositoryPort",
    "EventThreadRow",
    "NewEvent",
    "ProductAreaRecord",
    "RecurringCommitment",
    "ResponsePairRow",
    "StakeholderIdentity",
    "WorkingCalendar",
]
