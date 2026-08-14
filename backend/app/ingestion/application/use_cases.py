"""Ingestion application use cases: AppendEventUseCase, response-pair/event-thread
computation, ReplayUseCase (T020-T022); identity resolution, redaction,
RunCollectorUseCase (T031-T033, T035); DetectAbsenceUseCase (T040). One file —
tasks.md groups these together since they share ports.py/sqlalchemy_repositories.py
and read as one coherent "what happens to a signal after it's collected" pipeline.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.ingestion.application.collector import Collector
from app.ingestion.application.ports import (
    ClientProfileContext,
    ClientProfileContextPort,
    CollectorRunRepositoryPort,
    CommitmentLookupPort,
    EncryptionPort,
    EventRecord,
    EventRepositoryPort,
    EventThreadRow,
    NewEvent,
    ResponsePairRow,
)
from app.ingestion.domain.business_hours import WorkingCalendar, compute_business_hours_elapsed
from app.ingestion.domain.envelope import Envelope
from app.ingestion.domain.thread_stitching import (
    ANCHOR_CONFIDENCE,
    TICKET_REFERENCE_CONFIDENCE,
    find_ticket_references,
    thread_key_for_ticket,
)

# ---------------------------------------------------------------------------
# T020 — append
# ---------------------------------------------------------------------------


class AppendEventUseCase:
    """Builds an event's canonical fields and appends it (REQ-M2-01, REQ-M2-02,
    REQ-M2-03 for `supersedes_event_id`)."""

    def __init__(self, events: EventRepositoryPort, data_key_ref: str) -> None:
        self._events = events
        self._data_key_ref = data_key_ref

    async def execute(self, event: NewEvent) -> UUID:
        return await self._events.append(event, data_key_ref=self._data_key_ref)


# ---------------------------------------------------------------------------
# T021 / T024 — response-pair + thread-stitching computation (shared by ReplayUseCase
# and, indirectly, by RunCollectorUseCase, which triggers a replay after collection)
# ---------------------------------------------------------------------------


def _rebuild_projections(
    events: list[EventRecord],
    *,
    calendar: WorkingCalendar,
    commitment_id: UUID | None,
    threshold_business_hours: float | None,
    profile_version_id: UUID,
    as_of: datetime,
    decrypt: Callable[[bytes], str],
) -> tuple[list[EventThreadRow], list[ResponsePairRow]]:
    threads: list[EventThreadRow] = []
    pairs: list[ResponsePairRow] = []

    open_pairs: dict[int, tuple[UUID, datetime]] = {}
    ticket_threads: dict[int, str] = {}

    for record in events:
        if record.event_type == "ticket_state_change":
            ticket_number = record.structured_payload.get("ticket_number")
            state = record.structured_payload.get("state")
            if ticket_number is None:
                continue
            thread_key = thread_key_for_ticket(ticket_number)
            ticket_threads[ticket_number] = thread_key
            threads.append(
                EventThreadRow(
                    thread_key=thread_key,
                    event_id=record.id,
                    stitch_confidence=ANCHOR_CONFIDENCE,
                    stitch_method="ticket_reference",
                )
            )
            if state in ("created", "reopened"):
                open_pairs[ticket_number] = (record.id, record.occurred_at)
            elif state == "resolved" and ticket_number in open_pairs:
                client_event_id, client_occurred_at = open_pairs.pop(ticket_number)
                elapsed = compute_business_hours_elapsed(
                    client_occurred_at, record.occurred_at, calendar
                )
                pairs.append(
                    ResponsePairRow(
                        client_event_id=client_event_id,
                        reply_event_id=record.id,
                        commitment_id=commitment_id,
                        business_hours_elapsed=elapsed,
                        state="resolved",
                        profile_version_id=profile_version_id,
                    )
                )
        elif record.event_type == "message" and record.body_encrypted is not None:
            body_text = decrypt(record.body_encrypted)
            for ticket_number in find_ticket_references(body_text):
                if ticket_number in ticket_threads:
                    threads.append(
                        EventThreadRow(
                            thread_key=ticket_threads[ticket_number],
                            event_id=record.id,
                            stitch_confidence=TICKET_REFERENCE_CONFIDENCE,
                            stitch_method="ticket_reference",
                        )
                    )

    for _ticket_number, (client_event_id, client_occurred_at) in open_pairs.items():
        elapsed = compute_business_hours_elapsed(client_occurred_at, as_of, calendar)
        state = (
            "open_overdue"
            if threshold_business_hours is not None and elapsed > threshold_business_hours
            else "open"
        )
        pairs.append(
            ResponsePairRow(
                client_event_id=client_event_id,
                reply_event_id=None,
                commitment_id=commitment_id,
                business_hours_elapsed=elapsed,
                state=state,
                profile_version_id=profile_version_id,
            )
        )

    return threads, pairs


# ---------------------------------------------------------------------------
# T022 — replay
# ---------------------------------------------------------------------------


class ReplayUseCase:
    """Truncates `event_threads`/`response_pairs` and rebuilds both from the full
    `events` history (REQ-M2-07). Also what makes response_pairs/event_threads correct
    after an ordinary collection run (RunCollectorUseCase calls this too, trigger=
    "manual") — on this ledger, "replay" and "bring derived state current" are the
    same operation, so there's exactly one implementation of each, not two."""

    def __init__(
        self,
        events: EventRepositoryPort,
        profile_context: ClientProfileContextPort,
        encryption: EncryptionPort,
    ) -> None:
        self._events = events
        self._profile_context = profile_context
        self._encryption = encryption

    async def execute(self, *, trigger: str, as_of: datetime | None = None) -> UUID:
        as_of = as_of or datetime.now(UTC)
        all_events = await self._events.list_all_ordered()
        try:
            profile = await self._profile_context.get_current()
            threads, pairs = _rebuild_projections(
                all_events,
                calendar=profile.working_calendar,
                commitment_id=(
                    profile.first_response_commitment.id
                    if profile.first_response_commitment
                    else None
                ),
                threshold_business_hours=(
                    profile.first_response_commitment.threshold_business_hours
                    if profile.first_response_commitment
                    else None
                ),
                profile_version_id=profile.profile_version_id,
                as_of=as_of,
                decrypt=self._encryption.decrypt,
            )
            await self._events.truncate_projections()
            await self._events.bulk_rebuild_projections(threads, pairs)
        except Exception as exc:
            await self._events.record_replay_run(
                trigger=trigger, events_replayed_count=0, status="failed", error=str(exc)
            )
            raise
        return await self._events.record_replay_run(
            trigger=trigger,
            events_replayed_count=len(all_events),
            status="succeeded",
            error=None,
        )


# ---------------------------------------------------------------------------
# T031/T032 — identity resolution + redaction
# ---------------------------------------------------------------------------

# REQ-M1-09's exclusions are topic *labels* (e.g. "legal_threads"), not a per-word
# dictionary a human maintains — a small fixed marker-phrase list per topic is enough
# to prove the redaction path for real against this feature's fixture, without
# building a general text-classification model no reader yet needs (constitution
# P10/YAGNI; a real NLP-based exclusion matcher is a documented follow-up).
_EXCLUSION_MARKERS: dict[str, tuple[str, ...]] = {
    "legal_threads": ("legal team", "legal counsel", "lawsuit", "contract dispute"),
    "commercial_negotiation": ("discount", "renewal price", "contract terms", "negotiat"),
}


def redact(payload_text: str, exclusions: tuple[str, ...]) -> tuple[str, list[str]]:
    """Strips `payload_text` entirely and records which exclusion(s) matched, if any
    marker phrase for an excluded topic appears (REQ-M1-09)."""
    text_lower = payload_text.lower()
    matched = [
        exclusion
        for exclusion in exclusions
        if any(marker in text_lower for marker in _EXCLUSION_MARKERS.get(exclusion, ()))
    ]
    if matched:
        return "[REDACTED]", matched
    return payload_text, matched


def _match_product_area(envelope: Envelope, profile: ClientProfileContext) -> UUID | None:
    key = envelope.structured_payload.get("product_area")
    if key is None:
        return None
    for area in profile.product_areas:
        if area.key == key:
            return area.id
    return None


def _event_type_for_source(source_type: str) -> str:
    if source_type == "zendesk":
        return "ticket_state_change"
    if source_type == "warehouse":
        return "usage_measurement"
    return "message"


# ---------------------------------------------------------------------------
# T033/T035 — RunCollectorUseCase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollectorRunResult:
    envelopes_emitted: int
    duplicates_skipped: int
    coverage_report_id: UUID


class RunCollectorUseCase:
    """Orchestrates fetch -> normalize -> resolve_identity -> redact -> encrypt ->
    persist, per source, plus coverage reporting including the degraded/source-failure
    path (REQ-M1-07, REQ-M1-08). One `collector_runs` row per real source_type
    present in the batch (matching data-base/02-schema-ingestion.md's per-source
    design) even though `SimulatedCollector` is a single Python object standing in for
    all of them — coverage reporting is about provenance, which stays real regardless
    of how many source-specific classes exist yet.
    """

    _MVP_SOURCE_TYPES = ("gmail", "zendesk", "warehouse")

    def __init__(
        self,
        collector_runs: CollectorRunRepositoryPort,
        events: EventRepositoryPort,
        profile_context: ClientProfileContextPort,
        encryption: EncryptionPort,
        data_key_ref: str,
    ) -> None:
        self._runs = collector_runs
        self._events = events
        self._profile_context = profile_context
        self._encryption = encryption
        self._data_key_ref = data_key_ref

    async def execute(
        self,
        collector: Collector,
        *,
        window_start: datetime,
        window_end: datetime,
        fail_sources: frozenset[str] = frozenset(),
    ) -> CollectorRunResult:
        raw_items = await collector.fetch(window_start, window_end)
        # `fetch()` returns items in occurred_at order (Collector's docstring) — that
        # global order MUST be preserved all the way to `events.append()`, since the
        # hash chain requires appends in occurred_at order across the WHOLE run, not
        # just within one source. Grouping by source_type and processing each group to
        # completion (the earlier version of this method) silently reorders envelopes
        # across sources — e.g. a day-4 gmail item would get appended before a day-1
        # zendesk item — which corrupts the chain even though each source's own items
        # stay individually ordered. `envelopes` below stays in `fetch()`'s original
        # order; only the per-source bookkeeping (collector_runs rows, counts) groups
        # by source, not the actual event-append sequence.
        envelopes = [collector.normalize(item) for item in raw_items]
        profile = await self._profile_context.get_current()

        run_id_by_source: dict[str, UUID] = {}
        emitted_by_source: dict[str, int] = dict.fromkeys(self._MVP_SOURCE_TYPES, 0)
        duplicates_by_source: dict[str, int] = dict.fromkeys(self._MVP_SOURCE_TYPES, 0)
        sources_read = 0
        gap_reasons: list[str] = []

        for source_type in self._MVP_SOURCE_TYPES:
            source_id = await self._runs.get_or_create_source(
                source_type=source_type,
                display_name=f"Meridian — {source_type}",
                auth_scope=f"{source_type}.readonly",
            )
            run_id = await self._runs.start_run(
                source_id=source_id,
                trigger="manual",
                window_start=window_start,
                window_end=window_end,
            )
            run_id_by_source[source_type] = run_id

            if source_type in fail_sources:
                await self._runs.finish_run(
                    run_id=run_id,
                    envelopes_emitted=0,
                    duplicates_skipped=0,
                    error=f"{source_type} source unreachable (simulated failure)",
                )
                gap_reasons.append(f"{source_type} unreachable")
            else:
                sources_read += 1

        latest_occurred_at = window_start
        for envelope in envelopes:
            source_type = envelope.source_type
            if source_type in fail_sources or source_type not in run_id_by_source:
                continue
            run_id = run_id_by_source[source_type]

            if await self._runs.envelope_exists(envelope.idempotency_key):
                duplicates_by_source[source_type] += 1
                continue

            participant = envelope.structured_payload.get("participant")
            stakeholder_id = (
                await self._runs.resolve_identity(
                    source_identifier=participant, source_type=source_type
                )
                if participant
                else None
            )

            redacted_text, redacted_fields = redact(envelope.payload_text, profile.exclusions)
            payload_encrypted = self._encryption.encrypt(redacted_text)

            envelope_id = await self._runs.insert_envelope(
                collector_run_id=run_id,
                source_native_id=envelope.source_native_id,
                idempotency_key=envelope.idempotency_key,
                occurred_at=envelope.occurred_at,
                identity_status="resolved" if stakeholder_id else "unresolved",
                redacted_fields=redacted_fields,
                payload_encrypted=payload_encrypted,
                data_key_ref=self._data_key_ref,
            )

            event_id = await self._events.append(
                NewEvent(
                    envelope_id=envelope_id,
                    event_type=_event_type_for_source(source_type),
                    occurred_at=envelope.occurred_at,
                    stakeholder_id=stakeholder_id,
                    product_area_id=_match_product_area(envelope, profile),
                    body_encrypted=payload_encrypted,
                    structured_payload=envelope.structured_payload,
                ),
                data_key_ref=self._data_key_ref,
            )
            await self._runs.link_envelope_to_event(envelope_id, event_id)
            emitted_by_source[source_type] += 1
            latest_occurred_at = max(latest_occurred_at, envelope.occurred_at)

        latest_run_id: UUID | None = None
        for source_type in self._MVP_SOURCE_TYPES:
            if source_type in fail_sources:
                continue
            run_id = run_id_by_source[source_type]
            latest_run_id = run_id
            await self._runs.finish_run(
                run_id=run_id,
                envelopes_emitted=emitted_by_source[source_type],
                duplicates_skipped=duplicates_by_source[source_type],
                error=None,
            )

        # Every source failed — no non-failed run to attach coverage to; fall back to
        # whichever run was created last (still a real row, still an honest report).
        if latest_run_id is None:
            latest_run_id = run_id_by_source[self._MVP_SOURCE_TYPES[-1]]

        coverage_report_id = await self._runs.record_coverage(
            collector_run_id=latest_run_id,
            sources_expected=len(self._MVP_SOURCE_TYPES),
            sources_read=sources_read,
            gap_reason="; ".join(gap_reasons) or None,
            complete_to=latest_occurred_at,
        )

        return CollectorRunResult(
            envelopes_emitted=sum(emitted_by_source.values()),
            duplicates_skipped=sum(duplicates_by_source.values()),
            coverage_report_id=coverage_report_id,
        )


# ---------------------------------------------------------------------------
# T040 — absence collector
# ---------------------------------------------------------------------------

_CADENCE_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}


def _parse_cadence_days(cadence: str) -> int | None:
    return _CADENCE_DAYS.get(cadence.strip().lower())


class DetectAbsenceUseCase:
    """Compares each recurring commitment's cadence against the ledger's latest
    contact; appends an `absence` event when overdue (REQ-M1-06). Still goes through
    the standard envelope pipeline — `events.envelope_id` is `NOT NULL` — so the
    absence collector needs a `sources` row too; `calendar` is the closest-fitting
    existing `source_type` value for "the scheduler itself noticed silence" (the enum
    has no generic/internal option, data-base/10-ddl-appendix.md)."""

    ABSENCE_SOURCE_TYPE = "calendar"

    def __init__(
        self,
        commitments: CommitmentLookupPort,
        collector_runs: CollectorRunRepositoryPort,
        events: EventRepositoryPort,
        encryption: EncryptionPort,
        data_key_ref: str,
    ) -> None:
        self._commitments = commitments
        self._runs = collector_runs
        self._events = events
        self._encryption = encryption
        self._data_key_ref = data_key_ref

    async def execute(self, *, as_of: datetime | None = None) -> list[UUID]:
        as_of = as_of or datetime.now(UTC)
        appended: list[UUID] = []
        last_contact = await self._commitments.last_contact_at()

        for commitment in await self._commitments.list_recurring_commitments():
            cadence_days = _parse_cadence_days(commitment.cadence)
            if cadence_days is None:
                continue
            window_start = as_of - timedelta(days=cadence_days)
            if last_contact is not None and last_contact >= window_start:
                continue  # cadence satisfied — no absence event

            idempotency_key = f"absence:{commitment.id}:{window_start.date().isoformat()}"

            source_id = await self._runs.get_or_create_source(
                source_type=self.ABSENCE_SOURCE_TYPE,
                display_name="Internal — Absence monitor",
                auth_scope="internal",
            )
            run_id = await self._runs.start_run(
                source_id=source_id, trigger="poll", window_start=window_start, window_end=as_of
            )

            if await self._runs.envelope_exists(idempotency_key):
                await self._runs.finish_run(
                    run_id=run_id, envelopes_emitted=0, duplicates_skipped=1, error=None
                )
                continue

            payload_encrypted = self._encryption.encrypt(
                f"No contact matching commitment {commitment.id} since {last_contact}"
            )
            envelope_id = await self._runs.insert_envelope(
                collector_run_id=run_id,
                source_native_id=idempotency_key,
                idempotency_key=idempotency_key,
                occurred_at=as_of,
                identity_status="unresolved",
                redacted_fields=[],
                payload_encrypted=payload_encrypted,
                data_key_ref=self._data_key_ref,
            )
            event_id = await self._events.append(
                NewEvent(
                    envelope_id=envelope_id,
                    event_type="absence",
                    occurred_at=as_of,
                    body_encrypted=payload_encrypted,
                    structured_payload={
                        "commitment_id": str(commitment.id),
                        "cadence": commitment.cadence,
                        "window_start": window_start.isoformat(),
                        "last_contact_at": last_contact.isoformat() if last_contact else None,
                    },
                ),
                data_key_ref=self._data_key_ref,
            )
            await self._runs.link_envelope_to_event(envelope_id, event_id)
            await self._runs.finish_run(
                run_id=run_id, envelopes_emitted=1, duplicates_skipped=0, error=None
            )
            appended.append(event_id)

        return appended
