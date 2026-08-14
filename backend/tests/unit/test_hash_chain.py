"""REQ-M2-08 — appends a sequence of events, then verifies the chain via the
database's own `verify_hash_chain()` function (research.md's independent cross-check:
two implementations of the same algorithm agreeing is stronger than one implementation
checking itself)."""

from datetime import timedelta

from sqlalchemy import text

from app.db import async_session_factory
from app.ingestion.adapters.sqlalchemy_repositories import SqlAlchemyEventRepository
from app.ingestion.application.ports import NewEvent
from tests.conftest import ledger_floor


async def test_appended_sequence_has_no_broken_links(make_envelope):
    async with async_session_factory() as session:
        repo = SqlAlchemyEventRepository(session)
        start = await ledger_floor(session) + timedelta(seconds=1)
        for i in range(3):
            occurred_at = start + timedelta(seconds=i)
            envelope_id = await make_envelope(occurred_at)
            await repo.append(
                NewEvent(
                    envelope_id=envelope_id,
                    event_type="message",
                    occurred_at=occurred_at,
                    structured_payload={"seq": i},
                ),
                data_key_ref="test-key",
            )

        broken = (await session.execute(text("SELECT * FROM verify_hash_chain()"))).all()

    assert broken == []


async def test_first_event_ever_chains_to_genesis_or_a_real_prior_hash(make_envelope):
    """Whatever the true latest event's hash is at insert time (genesis if the ledger
    happens to be empty, otherwise a real prior event_hash) — either way,
    `prev_event_hash` must match it exactly, which is exactly what
    verify_hash_chain() re-derives and checks."""
    async with async_session_factory() as session:
        occurred_at = await ledger_floor(session) + timedelta(seconds=1)
        envelope_id = await make_envelope(occurred_at)
        repo = SqlAlchemyEventRepository(session)
        expected_prev_hash = await repo.latest_event_hash()
        event_id = await repo.append(
            NewEvent(envelope_id=envelope_id, event_type="message", occurred_at=occurred_at),
            data_key_ref="test-key",
        )

        row = (
            await session.execute(
                text("SELECT prev_event_hash FROM events WHERE id = :id"), {"id": event_id}
            )
        ).one()

    assert row.prev_event_hash == expected_prev_hash
