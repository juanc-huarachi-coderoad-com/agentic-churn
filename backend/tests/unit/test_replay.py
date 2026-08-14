"""REQ-M2-07 — append a sequence of events, replay, snapshot the rebuilt
`event_threads`/`response_pairs` projections, replay again, and assert the result is
byte-identical (the C1 remediation: this is the test that proves `ReplayUseCase`,
previously only referenced by name, is actually built and actually deterministic)."""

import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory
from app.ingestion.adapters.encryption import FernetEncryption
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.ports import NewEvent
from app.ingestion.application.use_cases import ReplayUseCase
from tests.conftest import ledger_floor

_BOGOTA = ZoneInfo("America/Bogota")


async def _next_business_window(session) -> tuple[datetime, datetime]:
    """A (created_at, resolved_at) pair, 2 hours apart, both inside the seeded
    profile's 08:00-18:00 America/Bogota working window, on the next weekday strictly
    after the ledger's current floor — anchored, not fixed, so this test stays correct
    regardless of execution order or how many times it's run against this database
    before (see tests/conftest.py's `ledger_floor` docstring)."""
    floor_local = (await ledger_floor(session)).astimezone(_BOGOTA)
    day = floor_local.date() + timedelta(days=1)
    while day.weekday() >= 5:  # Saturday, Sunday
        day += timedelta(days=1)
    created_at = datetime.combine(day, time(10, 0), tzinfo=_BOGOTA)
    resolved_at = datetime.combine(day, time(12, 0), tzinfo=_BOGOTA)
    return created_at, resolved_at


def _without_id(rows: list[dict]) -> list[dict]:
    return [{k: v for k, v in row.items() if k != "id"} for row in rows]


async def _snapshot(session):
    threads = (
        await session.execute(text("SELECT * FROM event_threads ORDER BY event_id"))
    ).mappings().all()
    pairs = (
        await session.execute(text("SELECT * FROM response_pairs ORDER BY client_event_id"))
    ).mappings().all()
    return _without_id([dict(t) for t in threads]), _without_id([dict(p) for p in pairs])


async def test_replay_is_deterministic(make_envelope):
    ticket_number = 500000 + (uuid.uuid4().int % 100000)

    async with async_session_factory() as setup_session:
        created_at, resolved_at = await _next_business_window(setup_session)

    # The real, persistent deployment key — not a throwaway per-test one:
    # ReplayUseCase decrypts *every* message-type event in the whole ledger (not just
    # this test's own), including ones other tests appended and can't be re-generated
    # (events are permanent), so everything that ever encrypts a body must agree on
    # one key, exactly like the one real deployment this ledger models.
    encryption = FernetEncryption(settings.encryption_key_path)

    async with async_session_factory() as session:
        events = SqlAlchemyEventRepository(session)

        created_envelope = await make_envelope(created_at)
        await events.append(
            NewEvent(
                envelope_id=created_envelope,
                event_type="ticket_state_change",
                occurred_at=created_at,
                structured_payload={"ticket_number": ticket_number, "state": "created"},
            ),
            data_key_ref="test-key",
        )

        resolved_envelope = await make_envelope(resolved_at)
        await events.append(
            NewEvent(
                envelope_id=resolved_envelope,
                event_type="ticket_state_change",
                occurred_at=resolved_at,
                structured_payload={"ticket_number": ticket_number, "state": "resolved"},
            ),
            data_key_ref="test-key",
        )

        replay = ReplayUseCase(
            events=events,
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
        )
        await replay.execute(trigger="manual")
        first_threads, first_pairs = await _snapshot(session)

        await replay.execute(trigger="manual")
        second_threads, second_pairs = await _snapshot(session)

    assert first_threads == second_threads
    assert first_pairs == second_pairs

    matching_pairs = [
        p
        for p in first_pairs
        if p["state"] == "resolved" and float(p["business_hours_elapsed"]) == 2.0
    ]
    assert any(
        t["thread_key"] == f"thread-{ticket_number}" for t in first_threads
    ), "the ticket's own state-change events must anchor its thread"
    assert matching_pairs, "the created/resolved pair must compute to exactly 2.0 business hours"
