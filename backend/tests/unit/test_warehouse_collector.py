"""specs/030-real-warehouse-connector — `WarehouseCollector` unit coverage against
a fake `WarehouseClient` (no real database, `research.md` Decision 7). Unlike
`GmailCollector`/`ZendeskCollector`, this connector has no ledger-derived window
(`research.md` Decision 5), so no real DB session or anchor event is needed here.
`SimulatedCollector` is never imported or touched here — its own test file
(`tests/unit/test_simulated_collector.py`) is the non-regression proof for
FR-005/User Story 2, run unchanged.
"""

from datetime import UTC, datetime
from typing import Any

from app.ingestion.adapters.warehouse_collector import WarehouseClient, WarehouseCollector
from app.ingestion.application.ports import CollectorRunRepositoryPort

_NOW = datetime.now(UTC)


class _FakeWarehouseClient(WarehouseClient):
    def __init__(
        self, rows: list[dict[str, Any]] | None = None, error: Exception | None = None
    ) -> None:
        self._rows = rows or []
        self._error = error
        self.calls = 0

    async def fetch_readings(self) -> list[dict[str, Any]]:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._rows


class _FakeCollectorRuns(CollectorRunRepositoryPort):
    def __init__(self, existing: set[str] | None = None) -> None:
        self._existing = existing or set()

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
        return idempotency_key in self._existing

    async def insert_envelope(self, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def link_envelope_to_event(self, envelope_id, event_id) -> None:  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def resolve_identity(self, *, source_identifier, source_type):  # type: ignore[no-untyped-def]
        raise NotImplementedError


def _row(
    metric: str = "weekly_active_users",
    product_area: str | None = "billing",
    value_delta_pct: int = -12,
    occurred_at: datetime = _NOW,
) -> dict[str, Any]:
    return {
        "occurred_at": occurred_at,
        "metric": metric,
        "product_area": product_area,
        "value_delta_pct": value_delta_pct,
    }


async def test_fetch_maps_rows_and_normalize_matches_expected_shape():
    fake = _FakeWarehouseClient([_row()])
    collector = WarehouseCollector(fake, _FakeCollectorRuns())

    items = await collector.fetch(_NOW, _NOW)

    assert len(items) == 1
    item = items[0]
    assert item["metric"] == "weekly_active_users"
    assert item["product_area"] == "billing"
    assert item["value_delta_pct"] == -12
    assert item["occurred_at"] == _NOW.isoformat()

    envelope = collector.normalize(item)
    assert envelope.source_type == "warehouse"
    assert envelope.identity_status == "unresolved"
    assert envelope.resolved_stakeholder_id is None
    assert envelope.redacted_fields == []
    assert envelope.payload_text == "weekly_active_users -12%"
    assert envelope.structured_payload == {
        "metric": "weekly_active_users",
        "product_area": "billing",
        "value_delta_pct": -12,
    }


async def test_identical_row_content_produces_identical_native_id_across_fetch_calls():
    fake = _FakeWarehouseClient([_row()])
    collector = WarehouseCollector(fake, _FakeCollectorRuns())

    first = await collector.fetch(_NOW, _NOW)
    second = await collector.fetch(_NOW, _NOW)

    assert first[0]["source_native_id"] == second[0]["source_native_id"]


async def test_a_row_missing_a_required_column_is_skipped_without_raising():
    good_row = _row(metric="nps_score")
    bad_row = _row(metric="churn_risk")
    del bad_row["value_delta_pct"]
    fake = _FakeWarehouseClient([bad_row, good_row])
    collector = WarehouseCollector(fake, _FakeCollectorRuns())

    items = await collector.fetch(_NOW, _NOW)

    assert len(items) == 1
    assert items[0]["metric"] == "nps_score"


async def test_a_row_already_seen_is_skipped_via_envelope_exists():
    fake = _FakeWarehouseClient([_row()])
    collector = WarehouseCollector(fake, _FakeCollectorRuns())
    first = await collector.fetch(_NOW, _NOW)
    seen_key = collector.normalize(first[0]).idempotency_key

    collector_again = WarehouseCollector(fake, _FakeCollectorRuns(existing={seen_key}))
    items = await collector_again.fetch(_NOW, _NOW)

    assert items == []


async def test_a_whole_connection_failure_propagates_unchanged():
    fake = _FakeWarehouseClient(error=ConnectionError("warehouse unreachable"))
    collector = WarehouseCollector(fake, _FakeCollectorRuns())

    raised = False
    try:
        await collector.fetch(_NOW, _NOW)
    except ConnectionError:
        raised = True
    assert raised
