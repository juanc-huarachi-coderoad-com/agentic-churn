"""specs/029-real-zendesk-connector — `ZendeskCollector` unit coverage against a
fake `ZendeskClient` (no real network, `research.md` Decision 7). `SimulatedCollector`
is never imported or touched here — its own test file
(`tests/unit/test_simulated_collector.py`) is the non-regression proof for
FR-006/User Story 2, run unchanged.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import async_session_factory, engine
from app.ingestion.adapters.sqlalchemy_repositories import SqlAlchemyEventRepository
from app.ingestion.adapters.zendesk_collector import ZendeskClient, ZendeskCollector
from app.ingestion.application.ports import CollectorRunRepositoryPort, NewEvent
from app.ingestion.domain.envelope import idempotency_key
from tests.conftest import ledger_floor


async def _zendesk_anchor() -> datetime:
    """Inserts one real `zendesk`-sourced event anchored to `ledger_floor()+1s`
    (guaranteed to become the new `MAX(occurred_at)` for `source_type='zendesk'`,
    by that helper's own definition) and returns its `occurred_at`. Every fixture
    timestamp in this file is computed relative to this anchor, never a fixed or
    wall-clock-relative constant — `ZendeskCollector.fetch()` derives its real
    window from whatever this shared, cumulative test database's own
    `MAX(occurred_at)` for `zendesk` already is (`research.md` Decision 6), which
    can be arbitrarily far in the future due to *other* tests' own synthetic data
    — a known, pre-existing class of cross-test pollution
    (`tests/conftest.py`'s own "events can't be deleted" contract), the identical
    lesson `specs/028-real-gmail-connector/tests/unit/test_gmail_collector.py`
    already learned for `source_type='gmail'` first. Depends on a `zendesk`
    `sources` row already existing — true in CI/this feature's own local
    verification, both of which run `scripts/run_collector.py --source simulated`
    (which seeds it) before the test suite."""
    async with async_session_factory() as session:
        anchor = await ledger_floor(session) + timedelta(seconds=1)
    async with engine.begin() as conn:
        source = (
            await conn.execute(
                text("SELECT id FROM sources WHERE source_type = 'zendesk' LIMIT 1")
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
            {"id": run_id, "source_id": source.id, "occurred_at": anchor},
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
                "occurred_at": anchor,
                "payload": b"\x00",
            },
        )
    async with async_session_factory() as session:
        await SqlAlchemyEventRepository(session).append(
            NewEvent(
                envelope_id=envelope_id,
                event_type="ticket_state_change",
                occurred_at=anchor,
                structured_payload={"ticket_number": 0, "state": "created", "title": "anchor"},
            ),
            data_key_ref="test-key",
        )
    return anchor


def _audit(audit_id: int, occurred_at: datetime, previous: str, current: str) -> dict[str, Any]:
    return {
        "id": audit_id,
        "created_at": occurred_at.isoformat(),
        "events": [
            {
                "type": "Change",
                "field_name": "status",
                "previous_value": previous,
                "value": current,
            }
        ],
    }


class _FakeZendeskClient(ZendeskClient):
    def __init__(
        self,
        tickets: list[dict[str, Any]],
        audits: dict[int, list[dict[str, Any]]] | None = None,
        emails: dict[int, str] | None = None,
        list_error: Exception | None = None,
        audit_errors: dict[int, Exception] | None = None,
    ) -> None:
        self._tickets = tickets
        self._audits = audits or {}
        self._emails = emails or {}
        self._list_error = list_error
        self._audit_errors = audit_errors or {}
        self.list_calls = 0
        self.audit_calls: list[int] = []
        self.email_calls: list[int] = []

    async def list_changed_tickets(self, after: datetime, before: datetime) -> list[dict[str, Any]]:
        self.list_calls += 1
        if self._list_error is not None:
            raise self._list_error
        return self._tickets

    async def get_ticket_audits(self, ticket_id: int) -> list[dict[str, Any]]:
        self.audit_calls.append(ticket_id)
        if ticket_id in self._audit_errors:
            raise self._audit_errors[ticket_id]
        return self._audits.get(ticket_id, [])

    async def get_user_email(self, user_id: int) -> str | None:
        self.email_calls.append(user_id)
        return self._emails.get(user_id)


class _NoOpCollectorRuns(CollectorRunRepositoryPort):
    async def get_or_create_source(self, *, source_type, display_name, auth_scope):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def start_run(self, *, source_id, trigger, window_start, window_end):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def finish_run(self, *, run_id, envelopes_emitted, duplicates_skipped, error):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def record_coverage(  # type: ignore[no-untyped-def]
        self, *, collector_run_id, sources_expected, sources_read, gap_reason, complete_to
    ):
        raise NotImplementedError

    async def envelope_exists(self, idempotency_key: str) -> bool:
        return False

    async def insert_envelope(self, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def link_envelope_to_event(self, envelope_id, event_id) -> None:  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def resolve_identity(self, *, source_identifier, source_type):  # type: ignore[no-untyped-def]
        raise NotImplementedError


async def test_a_new_ticket_produces_a_created_transition():
    anchor = await _zendesk_anchor()
    ticket_id = int(uuid4().int % 100000)
    ticket = {
        "id": ticket_id,
        "created_at": (anchor + timedelta(minutes=1)).isoformat(),
        "subject": "Slow API response",
        "requester_id": 42,
    }
    fake = _FakeZendeskClient([ticket], audits={ticket_id: []}, emails={42: "ana@meridian.com"})

    async with async_session_factory() as session:
        collector = ZendeskCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(anchor, anchor)

    assert len(items) == 1
    item = items[0]
    assert item["state"] == "created"
    assert item["ticket_number"] == ticket_id
    assert item["reporter"] == "ana@meridian.com"
    assert item["title"] == "Slow API response"

    envelope = collector.normalize(item)
    assert envelope.source_type == "zendesk"
    assert envelope.structured_payload == {
        "participant": "ana@meridian.com",
        "ticket_number": ticket_id,
        "title": "Slow API response",
        "state": "created",
    }
    assert envelope.idempotency_key == idempotency_key("zendesk", item["source_native_id"])


async def test_status_change_to_solved_produces_a_resolved_transition():
    anchor = await _zendesk_anchor()
    ticket_id = int(uuid4().int % 100000)
    old_created = anchor - timedelta(days=10)  # outside the window — not itself a "created"
    ticket = {
        "id": ticket_id,
        "created_at": old_created.isoformat(),
        "subject": "Add CSV export",
        "requester_id": 7,
    }
    audits = [_audit(1001, anchor + timedelta(minutes=1), "open", "solved")]
    fake = _FakeZendeskClient(
        [ticket], audits={ticket_id: audits}, emails={7: "diego@meridian.com"}
    )

    async with async_session_factory() as session:
        collector = ZendeskCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(anchor, anchor)

    assert len(items) == 1
    assert items[0]["state"] == "resolved"


async def test_status_change_from_solved_back_to_open_produces_a_reopened_transition():
    anchor = await _zendesk_anchor()
    ticket_id = int(uuid4().int % 100000)
    old_created = anchor - timedelta(days=10)
    ticket = {
        "id": ticket_id,
        "created_at": old_created.isoformat(),
        "subject": "Slow API response",
        "requester_id": 42,
    }
    audits = [_audit(2001, anchor + timedelta(minutes=1), "solved", "open")]
    fake = _FakeZendeskClient([ticket], audits={ticket_id: audits}, emails={42: "ana@meridian.com"})

    async with async_session_factory() as session:
        collector = ZendeskCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(anchor, anchor)

    assert len(items) == 1
    assert items[0]["state"] == "reopened"


async def test_two_reopenings_of_the_same_ticket_produce_two_distinct_events():
    anchor = await _zendesk_anchor()
    ticket_id = int(uuid4().int % 100000)
    old_created = anchor - timedelta(days=10)
    ticket = {
        "id": ticket_id,
        "created_at": old_created.isoformat(),
        "subject": "Slow API response",
        "requester_id": 42,
    }
    audits = [
        _audit(3001, anchor + timedelta(minutes=1), "solved", "open"),
        _audit(3002, anchor + timedelta(minutes=2), "open", "closed"),
        _audit(3003, anchor + timedelta(minutes=3), "closed", "open"),
    ]
    fake = _FakeZendeskClient([ticket], audits={ticket_id: audits}, emails={42: "ana@meridian.com"})

    async with async_session_factory() as session:
        collector = ZendeskCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(anchor, anchor)

    states = sorted(item["state"] for item in items)
    assert states == ["reopened", "reopened", "resolved"]
    native_ids = {item["source_native_id"] for item in items}
    assert len(native_ids) == 3  # each transition has its own stable, distinct identifier


async def test_a_whole_connection_failure_propagates_unchanged():
    anchor = await _zendesk_anchor()
    fake = _FakeZendeskClient([], list_error=ConnectionError("zendesk api unreachable"))
    async with async_session_factory() as session:
        collector = ZendeskCollector(fake, _NoOpCollectorRuns(), session)
        raised = False
        try:
            await collector.fetch(anchor, anchor)
        except ConnectionError:
            raised = True
        assert raised


async def test_one_bad_ticket_is_skipped_without_aborting_the_rest():
    anchor = await _zendesk_anchor()
    good_id = int(uuid4().int % 100000)
    bad_id = good_id + 1
    good_ticket = {
        "id": good_id,
        "created_at": (anchor + timedelta(minutes=1)).isoformat(),
        "subject": "Good ticket",
        "requester_id": 1,
    }
    bad_ticket = {
        "id": bad_id,
        "created_at": (anchor + timedelta(minutes=1)).isoformat(),
        "subject": "Bad ticket",
        "requester_id": 2,
    }
    fake = _FakeZendeskClient(
        [bad_ticket, good_ticket],
        audits={good_id: []},
        emails={1: "user1@meridian.com"},
        audit_errors={bad_id: ValueError("malformed audit response")},
    )

    async with async_session_factory() as session:
        collector = ZendeskCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(anchor, anchor)

    assert len(items) == 1
    assert items[0]["ticket_number"] == good_id
    assert sorted(fake.audit_calls) == sorted([bad_id, good_id])


async def test_requester_email_is_looked_up_once_per_requester_per_cycle():
    anchor = await _zendesk_anchor()
    ticket_a = int(uuid4().int % 100000)
    ticket_b = ticket_a + 1
    tickets = [
        {
            "id": ticket_a,
            "created_at": (anchor + timedelta(minutes=1)).isoformat(),
            "subject": "First",
            "requester_id": 99,
        },
        {
            "id": ticket_b,
            "created_at": (anchor + timedelta(minutes=1)).isoformat(),
            "subject": "Second",
            "requester_id": 99,
        },
    ]
    fake = _FakeZendeskClient(
        tickets, audits={ticket_a: [], ticket_b: []}, emails={99: "same-customer@meridian.com"}
    )

    async with async_session_factory() as session:
        collector = ZendeskCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(anchor, anchor)

    assert len(items) == 2
    assert all(item["reporter"] == "same-customer@meridian.com" for item in items)
    assert fake.email_calls == [99]  # looked up once, reused for the second ticket
