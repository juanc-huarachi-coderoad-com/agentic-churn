"""SQLAlchemy implementations of the ingestion ports. Raw parameterized SQL against
data-base/10-ddl-appendix.md's columns, matching auth/experience's existing pattern —
no ORM declarative models, since this project's schema is DDL-first.

Hash-chain canonicalization note (`SqlAlchemyEventRepository.append`): a new event's
`event_hash` must byte-for-byte agree with `verify_hash_chain()`'s independent
recomputation once it reads the stored row back (data-base/10-ddl-appendix.md). That
function calls `::text` on the row's own TIMESTAMPTZ/UUID/JSONB columns — Postgres's
rendering of those types isn't something a Python formatter can safely reproduce, so
rather than guess, `append()` asks Postgres itself for those exact canonical casts via
one round-trip SELECT *before* inserting, then hands the resulting strings to
`hash_chain.compute_hash()` (a pure function, ingestion/domain/hash_chain.py).
"""

import json
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.application.ports import (
    ClientProfileContext,
    ClientProfileContextPort,
    CollectorRunRepositoryPort,
    CommitmentContext,
    CommitmentLookupPort,
    EventRecord,
    EventRepositoryPort,
    EventThreadRow,
    NewEvent,
    ProductAreaRecord,
    RecurringCommitment,
    ResponsePairRow,
    RetentionJobRepositoryPort,
    RollupRow,
    StakeholderIdentity,
)
from app.ingestion.domain.business_hours import WorkingCalendar
from app.ingestion.domain.hash_chain import GENESIS_HASH, compute_hash


class SqlAlchemyEventRepository(EventRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_event_hash(self) -> str:
        result = await self._session.execute(
            text("SELECT event_hash FROM events ORDER BY created_at DESC, id DESC LIMIT 1")
        )
        row = result.one_or_none()
        return row.event_hash if row is not None else GENESIS_HASH

    async def append(self, event: NewEvent, *, data_key_ref: str) -> UUID:
        event_id = uuid4()
        recorded_at = datetime.now(event.occurred_at.tzinfo)
        prev_event_hash = await self.latest_event_hash()

        canon = (
            await self._session.execute(
                text(
                    "SELECT "
                    "(:id)::uuid::text AS id_t, "
                    "(:envelope_id)::uuid::text AS envelope_id_t, "
                    "(:occurred_at)::timestamptz::text AS occurred_at_t, "
                    "(:recorded_at)::timestamptz::text AS recorded_at_t, "
                    "COALESCE((:stakeholder_id)::uuid::text, '') AS stakeholder_id_t, "
                    "COALESCE((:product_area_id)::uuid::text, '') AS product_area_id_t, "
                    "(:structured_payload)::jsonb::text AS payload_t, "
                    "COALESCE((:supersedes_event_id)::uuid::text, '') AS supersedes_t"
                ),
                {
                    "id": str(event_id),
                    "envelope_id": str(event.envelope_id),
                    "occurred_at": event.occurred_at,
                    "recorded_at": recorded_at,
                    "stakeholder_id": (
                        str(event.stakeholder_id) if event.stakeholder_id is not None else None
                    ),
                    "product_area_id": (
                        str(event.product_area_id) if event.product_area_id is not None else None
                    ),
                    "structured_payload": json.dumps(event.structured_payload),
                    "supersedes_event_id": (
                        str(event.supersedes_event_id)
                        if event.supersedes_event_id is not None
                        else None
                    ),
                },
            )
        ).one()

        fields = [
            canon.id_t,
            canon.envelope_id_t,
            event.event_type,
            canon.occurred_at_t,
            canon.recorded_at_t,
            canon.stakeholder_id_t,
            canon.product_area_id_t,
            canon.payload_t,
            canon.supersedes_t,
            event.thread_key,
            prev_event_hash,
        ]
        event_hash = compute_hash(fields)

        await self._session.execute(
            text(
                "INSERT INTO events (id, envelope_id, event_type, occurred_at, recorded_at, "
                "stakeholder_id, product_area_id, body_encrypted, data_key_ref, "
                "structured_payload, supersedes_event_id, thread_key, prev_event_hash, event_hash) "
                "VALUES (:id, :envelope_id, (:event_type)::event_type, :occurred_at, :recorded_at, "
                ":stakeholder_id, :product_area_id, :body_encrypted, :data_key_ref, "
                "(:structured_payload)::jsonb, :supersedes_event_id, :thread_key, "
                ":prev_event_hash, :event_hash)"
            ),
            {
                "id": event_id,
                "envelope_id": event.envelope_id,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at,
                "recorded_at": recorded_at,
                "stakeholder_id": event.stakeholder_id,
                "product_area_id": event.product_area_id,
                "body_encrypted": event.body_encrypted,
                "data_key_ref": data_key_ref,
                "structured_payload": json.dumps(event.structured_payload),
                "supersedes_event_id": event.supersedes_event_id,
                "thread_key": event.thread_key,
                "prev_event_hash": prev_event_hash,
                "event_hash": event_hash,
            },
        )
        await self._session.commit()
        return event_id

    async def list_all_ordered(self) -> list[EventRecord]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, envelope_id, event_type, occurred_at, recorded_at, stakeholder_id, "
                    "product_area_id, structured_payload, supersedes_event_id, thread_key, "
                    "body_encrypted FROM events ORDER BY occurred_at, id"
                )
            )
        ).all()
        return [
            EventRecord(
                id=r.id,
                envelope_id=r.envelope_id,
                event_type=r.event_type,
                occurred_at=r.occurred_at,
                recorded_at=r.recorded_at,
                stakeholder_id=r.stakeholder_id,
                product_area_id=r.product_area_id,
                structured_payload=r.structured_payload,
                supersedes_event_id=r.supersedes_event_id,
                thread_key=r.thread_key,
                body_encrypted=r.body_encrypted,
            )
            for r in rows
        ]

    async def truncate_projections(self) -> None:
        await self._session.execute(text("TRUNCATE event_threads, response_pairs"))
        await self._session.commit()

    async def bulk_rebuild_projections(
        self, threads: list[EventThreadRow], pairs: list[ResponsePairRow]
    ) -> None:
        for t in threads:
            await self._session.execute(
                text(
                    "INSERT INTO event_threads "
                    "(thread_key, event_id, stitch_confidence, stitch_method) "
                    "VALUES (:thread_key, :event_id, :confidence, (:method)::stitch_method)"
                ),
                {
                    "thread_key": t.thread_key,
                    "event_id": t.event_id,
                    "confidence": t.stitch_confidence,
                    "method": t.stitch_method,
                },
            )
        for p in pairs:
            await self._session.execute(
                text(
                    "INSERT INTO response_pairs (client_event_id, reply_event_id, commitment_id, "
                    "business_hours_elapsed, state, profile_version_id) "
                    "VALUES (:client_event_id, :reply_event_id, :commitment_id, :elapsed, "
                    "(:state)::response_pair_state, :profile_version_id)"
                ),
                {
                    "client_event_id": p.client_event_id,
                    "reply_event_id": p.reply_event_id,
                    "commitment_id": p.commitment_id,
                    "elapsed": p.business_hours_elapsed,
                    "state": p.state,
                    "profile_version_id": p.profile_version_id,
                },
            )
        await self._session.commit()

    async def truncate_rollups(self) -> None:
        await self._session.execute(text("TRUNCATE rollups"))
        await self._session.commit()

    async def bulk_insert_rollups(self, rows: list[RollupRow]) -> None:
        for r in rows:
            await self._session.execute(
                text(
                    "INSERT INTO rollups (subject_type, subject_id, metric, "
                    "window_start, window_end, value) "
                    "VALUES ((:subject_type)::rollup_subject_type, :subject_id, "
                    ":metric, :window_start, :window_end, :value)"
                ),
                {
                    "subject_type": r.subject_type,
                    "subject_id": r.subject_id,
                    "metric": r.metric,
                    "window_start": r.window_start,
                    "window_end": r.window_end,
                    "value": r.value,
                },
            )
        await self._session.commit()

    async def record_replay_run(
        self, *, trigger: str, events_replayed_count: int, status: str, error: str | None
    ) -> UUID:
        run_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO replay_runs (id, trigger, started_at, finished_at, "
                "events_replayed_count, status, error) "
                "VALUES (:id, (:trigger)::replay_trigger, now(), now(), :count, "
                "(:status)::replay_status, :error)"
            ),
            {
                "id": run_id,
                "trigger": trigger,
                "count": events_replayed_count,
                "status": status,
                "error": error,
            },
        )
        await self._session.commit()
        return run_id


class SqlAlchemyClientProfileContext(ClientProfileContextPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self) -> ClientProfileContext:
        profile = (
            await self._session.execute(
                text(
                    "SELECT id, working_hours_start, working_hours_end, timezone, exclusions "
                    "FROM client_profile_versions WHERE is_current LIMIT 1"
                )
            )
        ).one()

        stakeholder_rows = (
            await self._session.execute(
                text("SELECT id, identifiers FROM stakeholders WHERE profile_version_id = :pv"),
                {"pv": profile.id},
            )
        ).all()

        product_area_rows = (
            await self._session.execute(
                text("SELECT id, key FROM product_areas WHERE profile_version_id = :pv"),
                {"pv": profile.id},
            )
        ).all()

        commitment = (
            await self._session.execute(
                text(
                    "SELECT id, type, threshold_business_hours FROM commitments "
                    "WHERE profile_version_id = :pv AND type = 'first_response' LIMIT 1"
                ),
                {"pv": profile.id},
            )
        ).one_or_none()

        return ClientProfileContext(
            profile_version_id=profile.id,
            stakeholders=tuple(
                StakeholderIdentity(id=r.id, identifiers=tuple(r.identifiers))
                for r in stakeholder_rows
            ),
            product_areas=tuple(
                ProductAreaRecord(id=r.id, key=r.key) for r in product_area_rows
            ),
            exclusions=tuple(profile.exclusions),
            working_calendar=WorkingCalendar(
                working_hours_start=profile.working_hours_start,
                working_hours_end=profile.working_hours_end,
                timezone=ZoneInfo(profile.timezone),
            ),
            first_response_commitment=(
                CommitmentContext(
                    id=commitment.id,
                    type=commitment.type,
                    threshold_business_hours=(
                        float(commitment.threshold_business_hours)
                        if commitment.threshold_business_hours is not None
                        else None
                    ),
                )
                if commitment is not None
                else None
            ),
        )


class SqlAlchemyCollectorRunRepository(CollectorRunRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_source(
        self, *, source_type: str, display_name: str, auth_scope: str
    ) -> UUID:
        existing = (
            await self._session.execute(
                text(
                    "SELECT id FROM sources "
                    "WHERE source_type = (:source_type)::source_type LIMIT 1"
                ),
                {"source_type": source_type},
            )
        ).one_or_none()
        if existing is not None:
            return cast(UUID, existing.id)

        new_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO sources (id, source_type, display_name, auth_scope, status) "
                "VALUES (:id, (:source_type)::source_type, :display_name, :auth_scope, "
                "'connected'::source_status)"
            ),
            {
                "id": new_id,
                "source_type": source_type,
                "display_name": display_name,
                "auth_scope": auth_scope,
            },
        )
        await self._session.commit()
        return new_id

    async def start_run(
        self, *, source_id: UUID, trigger: str, window_start: datetime, window_end: datetime
    ) -> UUID:
        run_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO collector_runs "
                "(id, source_id, trigger, window_start, window_end) "
                "VALUES (:id, :source_id, (:trigger)::collector_trigger, "
                ":window_start, :window_end)"
            ),
            {
                "id": run_id,
                "source_id": source_id,
                "trigger": trigger,
                "window_start": window_start,
                "window_end": window_end,
            },
        )
        await self._session.commit()
        return run_id

    async def finish_run(
        self, *, run_id: UUID, envelopes_emitted: int, duplicates_skipped: int, error: str | None
    ) -> None:
        await self._session.execute(
            text(
                "UPDATE collector_runs SET envelopes_emitted = :emitted, "
                "duplicates_skipped = :dup, error = :error, finished_at = now() WHERE id = :id"
            ),
            {"emitted": envelopes_emitted, "dup": duplicates_skipped, "error": error, "id": run_id},
        )
        await self._session.commit()

    async def record_coverage(
        self,
        *,
        collector_run_id: UUID,
        sources_expected: int,
        sources_read: int,
        gap_reason: str | None,
        complete_to: datetime,
    ) -> UUID:
        report_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO coverage_reports (id, collector_run_id, sources_expected, "
                "sources_read, gap_reason, complete_to) "
                "VALUES (:id, :run_id, :expected, :read, :gap_reason, :complete_to)"
            ),
            {
                "id": report_id,
                "run_id": collector_run_id,
                "expected": sources_expected,
                "read": sources_read,
                "gap_reason": gap_reason,
                "complete_to": complete_to,
            },
        )
        await self._session.commit()
        return report_id

    async def envelope_exists(self, idempotency_key: str) -> bool:
        result = await self._session.execute(
            text("SELECT 1 FROM raw_envelopes WHERE idempotency_key = :key"),
            {"key": idempotency_key},
        )
        return result.one_or_none() is not None

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
    ) -> UUID:
        envelope_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO raw_envelopes (id, collector_run_id, source_native_id, "
                "idempotency_key, occurred_at, identity_status, redacted_fields, "
                "payload_encrypted, data_key_ref) "
                "VALUES (:id, :run_id, :native_id, :key, :occurred_at, "
                "(:status)::identity_status, :redacted, :payload, :data_key_ref)"
            ),
            {
                "id": envelope_id,
                "run_id": collector_run_id,
                "native_id": source_native_id,
                "key": idempotency_key,
                "occurred_at": occurred_at,
                "status": identity_status,
                "redacted": redacted_fields,
                "payload": payload_encrypted,
                "data_key_ref": data_key_ref,
            },
        )
        await self._session.commit()
        return envelope_id

    async def link_envelope_to_event(self, envelope_id: UUID, event_id: UUID) -> None:
        await self._session.execute(
            text("UPDATE raw_envelopes SET ledger_event_id = :event_id WHERE id = :envelope_id"),
            {"event_id": event_id, "envelope_id": envelope_id},
        )
        await self._session.commit()

    async def resolve_identity(self, *, source_identifier: str, source_type: str) -> UUID | None:
        existing = (
            await self._session.execute(
                text(
                    "SELECT stakeholder_id FROM identity_map "
                    "WHERE source_identifier = :ident AND source_type = (:source_type)::source_type"
                ),
                {"ident": source_identifier, "source_type": source_type},
            )
        ).one_or_none()
        if existing is not None:
            return cast(UUID | None, existing.stakeholder_id)

        match = (
            await self._session.execute(
                text(
                    "SELECT s.id FROM stakeholders s "
                    "JOIN client_profile_versions pv ON pv.id = s.profile_version_id "
                    "WHERE pv.is_current AND :ident = ANY(s.identifiers) LIMIT 1"
                ),
                {"ident": source_identifier},
            )
        ).one_or_none()
        stakeholder_id = match.id if match is not None else None
        resolved_by = "exact_match" if stakeholder_id is not None else "unresolved"

        await self._session.execute(
            text(
                "INSERT INTO identity_map "
                "(source_identifier, source_type, stakeholder_id, resolved_by) "
                "VALUES (:ident, (:source_type)::source_type, :stakeholder_id, "
                "(:resolved_by)::identity_resolution) "
                "ON CONFLICT (source_identifier, source_type) DO NOTHING"
            ),
            {
                "ident": source_identifier,
                "source_type": source_type,
                "stakeholder_id": stakeholder_id,
                "resolved_by": resolved_by,
            },
        )
        await self._session.commit()
        return stakeholder_id


class SqlAlchemyCommitmentLookup(CommitmentLookupPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recurring_commitments(self) -> list[RecurringCommitment]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT c.id, c.cadence FROM commitments c "
                    "JOIN client_profile_versions pv ON pv.id = c.profile_version_id "
                    "WHERE pv.is_current AND c.type = 'recurring_sync' AND c.cadence IS NOT NULL"
                )
            )
        ).all()
        return [RecurringCommitment(id=r.id, cadence=r.cadence) for r in rows]

    async def last_contact_at(self) -> datetime | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT MAX(occurred_at) AS last FROM events "
                    "WHERE event_type != 'absence'::event_type"
                )
            )
        ).one_or_none()
        return row.last if row is not None else None


class SqlAlchemyRetentionJobRepository(RetentionJobRepositoryPort):
    """Two sessions, deliberately: `shred_bucket` runs through `shredder_session`
    (`app.db.shredder_session_factory`, authenticated as the narrowly-scoped
    `shredder_role`), the only writer of `body_encrypted` anywhere in this
    codebase; `record_run` runs through the normal, unrestricted `session`,
    exactly like every other bookkeeping table in this module.

    `shred_bucket` only ever nulls `events.body_encrypted` — **not**
    `raw_envelopes.payload_encrypted`, a real correction found while
    implementing this class: `raw_envelopes.payload_encrypted` is `NOT NULL`
    in the schema, and `data-base/10-ddl-appendix.md`'s own crypto-shredding
    design note already says destroying the key alone is sufficient for that
    table ("once destroyed, payload_encrypted is cryptographically
    unrecoverable even though this row and its data_key_ref value are
    untouched") — only `events.body_encrypted` was ever designed to be
    explicitly nulled by the retention job (that column's own comment: "nulled
    by the retention job once the key is destroyed"). No row-level touch is
    needed or possible for `raw_envelopes`.
    """

    def __init__(self, session: AsyncSession, shredder_session: AsyncSession) -> None:
        self._session = session
        self._shredder_session = shredder_session

    async def shred_bucket(self, bucket_id: str) -> None:
        await self._shredder_session.execute(
            text(
                "UPDATE events SET body_encrypted = NULL "
                "WHERE data_key_ref = :bucket_id AND body_encrypted IS NOT NULL"
            ),
            {"bucket_id": bucket_id},
        )
        await self._shredder_session.commit()

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
        run_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO retention_job_runs "
                "(id, started_at, completed_at, buckets_evaluated, buckets_shredded, "
                "status, error_detail) "
                "VALUES (:id, :started_at, :completed_at, :buckets_evaluated, "
                ":buckets_shredded, (:status)::retention_job_status, :error_detail)"
            ),
            {
                "id": run_id,
                "started_at": started_at,
                "completed_at": completed_at,
                "buckets_evaluated": buckets_evaluated,
                "buckets_shredded": buckets_shredded,
                "status": status,
                "error_detail": error_detail,
            },
        )
        await self._session.commit()
        return run_id
