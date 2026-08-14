"""`SimulatedCollector` (FR-009) — the one concrete `Collector` this feature ships,
reading a committed fixture file instead of a live source API. Stands in for a real
Gmail/Zendesk/warehouse adapter, proving the same interface end to end
(demo/03-environment-and-fixtures-checklist.md's documented approach).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.ingestion.application.collector import Collector
from app.ingestion.domain.envelope import Envelope

_SOURCE_DISPLAY_NAMES = {
    "gmail": "Meridian — Email",
    "zendesk": "Meridian — Support",
    "warehouse": "Meridian — Product usage",
}


def _normalize_gmail(item: dict[str, Any]) -> Envelope:
    return Envelope(
        source_type="gmail",
        source_native_id=item["source_native_id"],
        occurred_at=datetime.fromisoformat(item["occurred_at"]),
        identity_status="unresolved",  # resolved later, by RunCollectorUseCase
        resolved_stakeholder_id=None,
        redacted_fields=[],
        payload_text=item["text"],
        structured_payload={"participant": item["from"]},
    )


def _normalize_zendesk(item: dict[str, Any]) -> Envelope:
    return Envelope(
        source_type="zendesk",
        source_native_id=item["source_native_id"],
        occurred_at=datetime.fromisoformat(item["occurred_at"]),
        identity_status="unresolved",
        resolved_stakeholder_id=None,
        redacted_fields=[],
        payload_text=item["title"],
        structured_payload={
            "participant": item["reporter"],
            "ticket_number": item["ticket_number"],
            "title": item["title"],
            "state": item["state"],
            "product_area": item.get("product_area"),
        },
    )


def _normalize_warehouse(item: dict[str, Any]) -> Envelope:
    return Envelope(
        source_type="warehouse",
        source_native_id=item["source_native_id"],
        occurred_at=datetime.fromisoformat(item["occurred_at"]),
        identity_status="unresolved",
        resolved_stakeholder_id=None,
        redacted_fields=[],
        payload_text=f"{item['metric']} {item['value_delta_pct']:+d}%",
        structured_payload={
            "metric": item["metric"],
            "product_area": item.get("product_area"),
            "value_delta_pct": item["value_delta_pct"],
        },
    )


_NORMALIZERS = {
    "gmail": _normalize_gmail,
    "zendesk": _normalize_zendesk,
    "warehouse": _normalize_warehouse,
}


class SimulatedCollector(Collector):
    source_type = "simulated"

    def __init__(self, fixture_path: Path) -> None:
        self._fixture_path = fixture_path

    async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = json.loads(self._fixture_path.read_text())
        # Chronological order is a hard requirement of the hash chain (see
        # EventRepositoryPort.append's docstring) — the fixture's own array order
        # deliberately isn't sorted (item 2 occurs before item 1), to prove this sort
        # is load-bearing rather than an accident of fixture authoring.
        return sorted(items, key=lambda item: item["occurred_at"])

    def normalize(self, raw_item: dict[str, Any]) -> Envelope:
        return _NORMALIZERS[raw_item["source_type"]](raw_item)

    @staticmethod
    def display_name(source_type: str) -> str:
        return _SOURCE_DISPLAY_NAMES.get(source_type, source_type)
