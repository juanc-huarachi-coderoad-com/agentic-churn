"""Shared test fixtures — DATABASE_URL points at a real, already-migrated and seeded
database (workflows/ci.yml / quickstart.md), same pattern as tests/unit/test_auth.py.

No transactional rollback/isolation: `events` is append-only at the DB level (a
BEFORE UPDATE OR DELETE trigger, data-base/10-ddl-appendix.md), so once a test appends
a real event, the (source, collector_run, raw_envelope) row chain behind it becomes
permanently un-deletable too (`events.envelope_id` FKs to `raw_envelopes.id` with no
cascade) — the same guarantee a real ledger gives production data. Tests that append
events therefore rely on uuid-uniqueness to stay isolated across runs, not cleanup.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.db import engine


async def ledger_floor(conn: AsyncConnection | AsyncSession) -> datetime:
    """The ledger's current `MAX(occurred_at)` (or "now" if the ledger is empty,
    whichever is later). `EventRepositoryPort.append`'s docstring requires appends to
    happen in `occurred_at` order globally — not just within one test — since
    `verify_hash_chain()` walks `ORDER BY occurred_at, id`. Tests that append real
    events anchor their synthetic timelines to this rather than fixed calendar dates,
    so the suite stays correct regardless of execution order or how many times it's
    been run against this database before (events can never be deleted)."""
    row = (await conn.execute(text("SELECT MAX(occurred_at) AS floor FROM events"))).one()
    now = datetime.now(UTC)
    return max(row.floor, now) if row.floor is not None else now


@pytest.fixture
def floor():
    return ledger_floor


@pytest.fixture
def make_envelope():
    """Factory fixture: creates the minimum (collector_runs, raw_envelopes) row pair a
    synthetic test event needs to satisfy `events.envelope_id`'s FK, reusing the
    seeded 'gmail' source row."""

    async def _make(occurred_at: datetime | None = None) -> UUID:
        occurred_at = occurred_at or datetime.now(UTC)
        async with engine.begin() as conn:
            source = (
                await conn.execute(
                    text("SELECT id FROM sources WHERE source_type = 'gmail' LIMIT 1")
                )
            ).one()
            run_id = uuid4()
            envelope_id = uuid4()
            await conn.execute(
                text(
                    "INSERT INTO collector_runs "
                    "(id, source_id, trigger, window_start, window_end) "
                    "VALUES (:id, :source_id, 'manual'::collector_trigger, "
                    ":occurred_at, :occurred_at)"
                ),
                {"id": run_id, "source_id": source.id, "occurred_at": occurred_at},
            )
            await conn.execute(
                text(
                    "INSERT INTO raw_envelopes (id, collector_run_id, source_native_id, "
                    "idempotency_key, occurred_at, identity_status, payload_encrypted, "
                    "data_key_ref) "
                    "VALUES (:id, :run_id, :native_id, :native_id, :occurred_at, "
                    "'unresolved'::identity_status, :payload, 'test-key')"
                ),
                {
                    "id": envelope_id,
                    "run_id": run_id,
                    "native_id": str(envelope_id),
                    "occurred_at": occurred_at,
                    "payload": b"\x00",
                },
            )
        return envelope_id

    return _make
