"""`WarehouseCollector` — the fourth real, non-simulated `Collector`
(specs/030-real-warehouse-connector), following `GmailCollector`/`ZendeskCollector`'s
shape. `SimulatedCollector` and its JSON fixture are not touched by this file at
all — an explicit, non-negotiable requirement (spec.md User Story 2).

Unlike Gmail/Zendesk, this is a *generic* connector — a read-only SQL connection +
a client-authored query file, not a single named vendor's API (research.md
Decision 3: "the warehouse" is inherently client-specific infrastructure, matching
`client_profile_path`'s own precedent of a directly human-edited, per-deployment
file). `WarehouseClient` isolates the actual query execution behind one testable
method (research.md Decision 7).

`fetch()`:
1. Runs the configured query as-is every cycle — no connector-derived time
   window (research.md Decision 5); the query itself is responsible for scoping
   to relevant, recent data.
2. Each row's `source_native_id` is a content hash of its own fields (research.md
   Decision 4) — identical content on a later run produces the identical native
   ID, making a re-run naturally idempotent via the existing `envelope_exists()`
   check every other collector already uses.
3. A row missing a required field is logged and skipped without aborting the
   cycle (FR-008). A whole-connection failure (the query call itself raising —
   bad credentials, unreachable database, malformed SQL) is allowed to
   propagate out of `fetch()` — `RunCollectorUseCase.execute()`'s own
   try/except records it as an honest, visible coverage gap (FR-007).
"""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.ingestion.application.collector import Collector
from app.ingestion.application.ports import CollectorRunRepositoryPort
from app.ingestion.domain.envelope import Envelope, idempotency_key

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = ("occurred_at", "metric", "value_delta_pct")


class WarehouseClient(Protocol):
    """The narrow seam `WarehouseCollector` depends on — real usage runs a
    client-authored SQL query; tests inject a fake with no real database
    (research.md Decision 7)."""

    async def fetch_readings(self) -> list[dict[str, Any]]: ...


class _RealWarehouseClient:
    def __init__(self, connection_url: str, query_path: str) -> None:
        self._connection_url = connection_url
        self._query_path = query_path

    async def fetch_readings(self) -> list[dict[str, Any]]:
        query_text = Path(self._query_path).read_text()
        engine = create_async_engine(self._connection_url)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(query_text))
                return [dict(row._mapping) for row in result]
        finally:
            await engine.dispose()


def _content_hash(row: dict[str, Any]) -> str:
    # research.md Decision 4 — an arbitrary client-authored query has no
    # guaranteed unique-row identifier; identical content always hashes the
    # same, making a re-run of the same query naturally idempotent.
    raw = (
        f"{row['metric']}:{row.get('product_area')}:"
        f"{row['occurred_at']}:{row['value_delta_pct']}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _coerce_occurred_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        occurred_at = value
    elif isinstance(value, str):
        occurred_at = datetime.fromisoformat(value)
    else:
        raise TypeError(f"occurred_at has an unexpected type: {type(value)!r}")
    # Most warehouse timestamp columns are stored in UTC without an explicit
    # offset — assume UTC for a naive value rather than silently misdating it
    # against this system's own UTC-everywhere convention.
    return occurred_at if occurred_at.tzinfo is not None else occurred_at.replace(tzinfo=UTC)


class WarehouseCollector(Collector):
    source_type = "warehouse"
    # `AudioCollector`/`GmailCollector`/`ZendeskCollector`'s own precedent — a
    # dedicated, single-purpose collector's own source_type is always what's
    # expected.
    mvp_sources_always_expected = False

    def __init__(self, client: WarehouseClient, collector_runs: CollectorRunRepositoryPort) -> None:
        self._client = client
        self._collector_runs = collector_runs

    async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
        # window_start/window_end are intentionally unused — this connector has
        # no ledger-derived window (research.md Decision 5); the configured
        # query itself is responsible for scoping to relevant, recent data.
        rows = await self._client.fetch_readings()

        items: list[dict[str, Any]] = []
        for row in rows:
            try:
                missing = [c for c in _REQUIRED_COLUMNS if row.get(c) is None]
                if missing:
                    logger.warning(
                        "warehouse collector: row missing required column(s) %s, skipped",
                        missing,
                    )
                    continue

                occurred_at = _coerce_occurred_at(row["occurred_at"])
                value_delta_pct = int(row["value_delta_pct"])
                native_id = _content_hash(row)
                key = idempotency_key(self.source_type, native_id)
                if await self._collector_runs.envelope_exists(key):
                    continue

                items.append(
                    {
                        "source_native_id": native_id,
                        "occurred_at": occurred_at.isoformat(),
                        "metric": row["metric"],
                        "product_area": row.get("product_area"),
                        "value_delta_pct": value_delta_pct,
                    }
                )
            except Exception:
                logger.exception(
                    "warehouse collector: row failed, skipped (FR-008): %r", row
                )
                continue
        return items

    def normalize(self, raw_item: dict[str, Any]) -> Envelope:
        # Matches SimulatedCollector's own _normalize_warehouse field-for-field
        # (research.md Decision 4/plan.md — FR-004: zero reader changes needed).
        return Envelope(
            source_type="warehouse",
            source_native_id=raw_item["source_native_id"],
            occurred_at=datetime.fromisoformat(raw_item["occurred_at"]),
            identity_status="unresolved",
            resolved_stakeholder_id=None,
            redacted_fields=[],
            payload_text=f"{raw_item['metric']} {raw_item['value_delta_pct']:+d}%",
            structured_payload={
                "metric": raw_item["metric"],
                "product_area": raw_item["product_area"],
                "value_delta_pct": raw_item["value_delta_pct"],
            },
        )
