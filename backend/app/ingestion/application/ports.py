"""Ports the ingestion application layer depends on — implemented by
app.ingestion.adapters.*. Application depends on these, never on a concrete adapter
(constitution P8, Dependency Inversion), enforced mechanically by `.importlinter`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet

from app.ingestion.domain.business_hours import WorkingCalendar


class EncryptionPort(ABC):
    @abstractmethod
    def encrypt(self, plaintext: str) -> bytes: ...

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> str: ...


class KeyStorePort(ABC):
    """Daily key-rotation buckets for crypto-shredding (specs/011-production-
    hardening, research.md Decision 1). `EncryptionPort`'s signature never
    changes — a `BucketedFernetEncryption` adapter holds one of these and uses
    it internally; the retention job (`RunRetentionUseCase`) is this port's other,
    independent caller, driving `destroy()` directly."""

    @abstractmethod
    def current_bucket_id(self) -> str:
        """Today's UTC calendar date, `YYYY-MM-DD` — the bucket every new
        encryption uses."""
        ...

    @abstractmethod
    def resolve(self, bucket_id: str) -> Fernet:
        """Returns the Fernet key material for `bucket_id`, creating it lazily on
        first use if it doesn't exist yet."""
        ...

    @abstractmethod
    def list_active_buckets(self) -> list[str]:
        """Every bucket id with a key that still exists — a destroyed bucket
        never appears here again."""
        ...

    @abstractmethod
    def destroy(self, bucket_id: str) -> None:
        """Permanently deletes `bucket_id`'s key. Idempotent — destroying an
        already-destroyed (or never-created) bucket is not an error."""
        ...


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
    # specs/019-meeting-audio-ingestion — `AudioCollector`/
    # `WhisperTranscriptionAdapter` need a real, human-readable name (not an
    # `identifiers` entry, which is an email/username string meant for exact
    # lookup) to match against conversational context when attributing a
    # diarized speaker segment. Added here rather than a second port, since
    # `stakeholders.name` already exists and every other `ClientProfileContext`
    # consumer can simply ignore the field (additive, non-breaking).
    name: str = ""


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


# ---------------------------------------------------------------------------
# Retention job (specs/011-production-hardening, FR-001/002)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetentionJobRunResult:
    id: UUID
    buckets_evaluated: int
    buckets_shredded: int
    status: str


class RetentionJobRepositoryPort(ABC):
    @abstractmethod
    async def shred_bucket(self, bucket_id: str) -> None:
        """Nulls `events.body_encrypted` and `raw_envelopes.payload_encrypted` for
        every row whose `data_key_ref` matches `bucket_id` — via the narrowly-scoped
        `shredder_role` connection, never the unrestricted default one."""
        ...

    @abstractmethod
    async def record_run(
        self,
        *,
        started_at: datetime,
        completed_at: datetime | None,
        buckets_evaluated: int,
        buckets_shredded: int,
        status: str,
        error_detail: str | None,
    ) -> UUID:
        """Writes one `retention_job_runs` row (FR-002) — durable, queryable
        independent of application logs."""
        ...


# ---------------------------------------------------------------------------
# Backup job (specs/031-production-deployment-hardening-ii, FR-001..004)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BackupResult:
    destination_path: str
    file_size_bytes: int


class BackupDestinationPort(ABC):
    """A real, verifiable `pg_dump` run against this deployment's own database, plus
    pruning files older than the configured retention window (`research.md` Decision
    1/2) — a real, provider-agnostic filesystem implementation today
    (`FilesystemBackupDestination`), with a cloud object-storage adapter deferred until
    a concrete provider is chosen (FR-014), matching `KeyStorePort`'s own "port now,
    cloud adapter later" precedent exactly."""

    @abstractmethod
    async def create_backup(self) -> BackupResult:
        """Runs the backup and prunes old files; raises on any failure (a `pg_dump`
        non-zero exit, an unwritable destination) rather than returning a partial or
        sentinel result — `RunBackupUseCase` is the only caller and always wraps this
        in a try/except that records the outcome either way."""
        ...


class BackupJobRepositoryPort(ABC):
    @abstractmethod
    async def record_run(
        self,
        *,
        started_at: datetime,
        completed_at: datetime | None,
        destination_path: str | None,
        file_size_bytes: int | None,
        status: str,
        error_detail: str | None,
    ) -> UUID:
        """Writes one `backup_job_runs` row (FR-004) — durable, queryable
        independent of application logs, mirroring `RetentionJobRepositoryPort.
        record_run`'s own shape."""
        ...


# ---------------------------------------------------------------------------
# Meeting series consent (specs/019-meeting-audio-ingestion, FR-004/FR-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MeetingSeriesConsentRecord:
    id: UUID
    series_id: str
    status: str
    all_parties_confirmed: bool
    documented_by_user_id: UUID
    documented_at: datetime
    note: str | None


class MeetingSeriesConsentRepositoryPort(ABC):
    """Gates meeting audio collection (`AudioCollector`/`SimulatedCollector`,
    research.md Decision 3) and backs the consent audit-trail endpoints
    (`consent_router.py`). Insert-only — "current status" is always the
    latest row per `series_id` (data-model.md's query pattern)."""

    @abstractmethod
    async def is_active(self, series_id: str) -> bool:
        """True only if `series_id`'s latest consent row has `status ==
        'granted'` — false for a series with no consent decision at all,
        exactly the same outcome as a series whose latest decision was a
        revocation (spec.md's Edge Cases: "no decision" and "revoked" are
        treated identically)."""
        ...

    @abstractmethod
    async def record(
        self,
        *,
        series_id: str,
        status: str,
        all_parties_confirmed: bool,
        documented_by_user_id: UUID,
        note: str | None,
    ) -> MeetingSeriesConsentRecord:
        """Inserts one new consent-decision row. Never updates an existing
        row — a revocation or re-grant is always a new row (research.md
        Decision 4)."""
        ...

    @abstractmethod
    async def list_current(self) -> list[MeetingSeriesConsentRecord]:
        """One row per `series_id` that has ever had a consent decision —
        each one's latest row, per data-model.md's query pattern. A series
        with no decision ever recorded does not appear here."""
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
    "KeyStorePort",
    "MeetingSeriesConsentRecord",
    "MeetingSeriesConsentRepositoryPort",
    "NewEvent",
    "ProductAreaRecord",
    "RecurringCommitment",
    "ResponsePairRow",
    "RetentionJobRepositoryPort",
    "RetentionJobRunResult",
    "StakeholderIdentity",
    "WorkingCalendar",
]
