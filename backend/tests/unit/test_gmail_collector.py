"""specs/028-real-gmail-connector — `GmailCollector` unit coverage against a fake
`GmailClient` (no real network, `research.md` Decision 5). `SimulatedCollector` is
never imported or touched here — its own test file
(`tests/unit/test_simulated_collector.py`) is the non-regression proof for
FR-005/User Story 2, run unchanged.
"""

from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.db import async_session_factory
from app.ingestion.adapters.gmail_collector import GmailClient, GmailCollector
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.ports import CollectorRunRepositoryPort, NewEvent
from app.ingestion.domain.envelope import idempotency_key
from tests.conftest import ledger_floor


def _b64(text: str) -> str:
    return urlsafe_b64encode(text.encode()).decode()


def _plain_message(message_id: str, from_header: str, body: str) -> dict[str, Any]:
    return {
        "id": message_id,
        "internalDate": str(int(datetime(2026, 8, 24, tzinfo=UTC).timestamp() * 1000)),
        "payload": {
            "headers": [{"name": "From", "value": from_header}],
            "mimeType": "text/plain",
            "body": {"data": _b64(body)},
        },
    }


class _FakeGmailClient(GmailClient):
    def __init__(
        self,
        ids: list[str],
        messages: dict[str, dict[str, Any]],
        list_error: Exception | None = None,
        get_errors: dict[str, Exception] | None = None,
    ) -> None:
        self._ids = ids
        self._messages = messages
        self._list_error = list_error
        self._get_errors = get_errors or {}
        self.list_calls = 0
        self.get_calls: list[str] = []

    async def list_message_ids(self, after: datetime, before: datetime) -> list[str]:
        self.list_calls += 1
        if self._list_error is not None:
            raise self._list_error
        return self._ids

    async def get_message(self, message_id: str) -> dict[str, Any]:
        self.get_calls.append(message_id)
        if message_id in self._get_errors:
            raise self._get_errors[message_id]
        return self._messages[message_id]


class _NoOpCollectorRuns(CollectorRunRepositoryPort):
    """Every message is treated as new — this test file exercises GmailCollector's
    own logic, not the real idempotency-persistence path (that's `test_hash_chain.py`/
    `test_simulated_collector.py`'s job for the shared `RunCollectorUseCase` machinery)."""

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


async def test_fetch_normalizes_a_new_message():
    message_id = f"msg-{uuid4().hex[:8]}"
    fake = _FakeGmailClient(
        [message_id],
        {message_id: _plain_message(message_id, "ana.reyes@meridian.com", "Please advise.")},
    )
    async with async_session_factory() as session:
        collector = GmailCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert len(items) == 1
    item = items[0]
    assert item["source_native_id"] == message_id
    assert item["from"] == "ana.reyes@meridian.com"
    assert item["text"] == "Please advise."

    envelope = collector.normalize(item)
    assert envelope.source_type == "gmail"
    assert envelope.identity_status == "unresolved"
    assert envelope.resolved_stakeholder_id is None
    assert envelope.redacted_fields == []
    assert envelope.payload_text == "Please advise."
    assert envelope.structured_payload == {"participant": "ana.reyes@meridian.com"}
    assert envelope.idempotency_key == idempotency_key("gmail", message_id)


async def test_from_header_with_display_name_is_reduced_to_the_bare_address():
    message_id = f"msg-{uuid4().hex[:8]}"
    fake = _FakeGmailClient(
        [message_id],
        {message_id: _plain_message(message_id, "Ana Reyes <ana.reyes@meridian.com>", "Hi.")},
    )
    async with async_session_factory() as session:
        collector = GmailCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items[0]["from"] == "ana.reyes@meridian.com"


async def test_a_whole_connection_failure_propagates_unchanged():
    fake = _FakeGmailClient([], {}, list_error=ConnectionError("gmail api unreachable"))
    async with async_session_factory() as session:
        collector = GmailCollector(fake, _NoOpCollectorRuns(), session)
        raised = False
        try:
            await collector.fetch(datetime.now(UTC), datetime.now(UTC))
        except ConnectionError:
            raised = True
        assert raised


async def test_one_bad_message_is_skipped_without_aborting_the_rest():
    good_id = f"msg-good-{uuid4().hex[:8]}"
    bad_id = f"msg-bad-{uuid4().hex[:8]}"
    fake = _FakeGmailClient(
        [bad_id, good_id],
        {good_id: _plain_message(good_id, "ana.reyes@meridian.com", "Still here.")},
        get_errors={bad_id: ValueError("malformed message")},
    )
    async with async_session_factory() as session:
        collector = GmailCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert len(items) == 1
    assert items[0]["source_native_id"] == good_id
    assert sorted(fake.get_calls) == sorted([bad_id, good_id])


async def test_a_message_with_no_readable_body_is_skipped():
    message_id = f"msg-{uuid4().hex[:8]}"
    empty_message = {
        "id": message_id,
        "internalDate": "0",
        "payload": {"headers": [{"name": "From", "value": "ana@meridian.com"}], "parts": []},
    }
    fake = _FakeGmailClient([message_id], {message_id: empty_message})
    async with async_session_factory() as session:
        collector = GmailCollector(fake, _NoOpCollectorRuns(), session)
        items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []


async def test_already_processed_messages_are_skipped_before_the_expensive_fetch():
    message_id = f"msg-{uuid4().hex[:8]}"
    fake = _FakeGmailClient(
        [message_id],
        {message_id: _plain_message(message_id, "ana@meridian.com", "Body")},
    )

    class _AlwaysExists(_NoOpCollectorRuns):
        async def envelope_exists(self, idempotency_key: str) -> bool:
            return True

    async with async_session_factory() as session:
        collector = GmailCollector(fake, _AlwaysExists(), session)
        items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []
    assert fake.get_calls == []  # never fetched the full message for an already-seen id


async def test_window_derivation_overlaps_the_latest_known_gmail_event(make_envelope):
    # `sources.source_type = 'gmail'` is shared with SimulatedCollector's own
    # fixture items *and* with `make_envelope` (tests/conftest.py's own fixture,
    # hardcoded to source_type='gmail') — many other unrelated tests in this
    # shared, cumulative, append-only database (tests/conftest.py's documented
    # contract) may already have inserted gmail-sourced events at arbitrary
    # timestamps, including synthetic future dates. Neither "no prior gmail
    # event exists" nor "the latest one is recent" can be assumed here — so
    # this test inserts a real event anchored to `ledger_floor()` (guaranteed
    # to be at or after the true current maximum, by that helper's own
    # definition) and asserts the window overlaps *that* event specifically,
    # which is the one thing always true regardless of ambient state.
    async with async_session_factory() as session:
        anchor = await ledger_floor(session) + timedelta(seconds=1)
    envelope_id = await make_envelope(anchor)
    async with async_session_factory() as session:
        await SqlAlchemyEventRepository(session).append(
            NewEvent(envelope_id=envelope_id, event_type="message", occurred_at=anchor),
            data_key_ref="test-key",
        )

    fake = _FakeGmailClient([], {})
    before_call = datetime.now(UTC)
    async with async_session_factory() as session:
        collector = GmailCollector(fake, _NoOpCollectorRuns(), session)
        after, before = await collector._derive_window()

    # `after` is exactly the overlap-adjusted anchor — the actual behavior this
    # test exists to prove. `before` is real wall-clock "now" (not DB-derived),
    # so it's checked against a real timestamp taken just before the call —
    # immune to whatever synthetic, possibly future-dated `ledger_floor()` other
    # tests have already pushed into this shared database (a known, pre-existing
    # class of cross-test pollution, not something this feature caused or fixes).
    assert after == anchor - timedelta(minutes=10)
    assert before >= before_call
    assert fake.list_calls == 0


async def test_real_collector_uses_gmail_collector_backed_by_real_repository():
    # Confirms GmailCollector also works against the real
    # SqlAlchemyCollectorRunRepository (not just the test-only fake above) for its
    # one real method call this file exercises directly, envelope_exists — the same
    # repository AudioCollector/SimulatedCollector already depend on.
    message_id = f"msg-{uuid4().hex[:8]}"
    fake = _FakeGmailClient(
        [message_id], {message_id: _plain_message(message_id, "ana@meridian.com", "Body")}
    )
    async with async_session_factory() as session:
        collector = GmailCollector(fake, SqlAlchemyCollectorRunRepository(session), session)
        items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert len(items) == 1
