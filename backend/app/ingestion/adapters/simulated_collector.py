"""`SimulatedCollector` (FR-009) — the one concrete `Collector` this feature ships,
reading a committed fixture file instead of a live source API. Stands in for a real
Gmail/Zendesk/warehouse adapter, proving the same interface end to end
(demo/03-environment-and-fixtures-checklist.md's documented approach).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.ingestion.adapters.meeting_envelope import (
    MEETING_SOURCE_DISPLAY_NAME,
    MEETING_SOURCE_TYPE,
    build_meeting_envelope,
)
from app.ingestion.application.collector import Collector
from app.ingestion.application.ports import MeetingSeriesConsentRepositoryPort
from app.ingestion.domain.envelope import Envelope

_SOURCE_DISPLAY_NAMES = {
    "gmail": "Meridian — Email",
    "zendesk": "Meridian — Support",
    "warehouse": "Meridian — Product usage",
    "slack": "Meridian — Chat",
    "csat": "Meridian — CSAT/NPS",
    MEETING_SOURCE_TYPE: MEETING_SOURCE_DISPLAY_NAME,
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


def _normalize_slack(item: dict[str, Any]) -> Envelope:
    # `_event_type_for_source` has no "slack" branch — Slack messages fall
    # through to its "message" default, the same event_type Gmail already
    # produces, so Absence/Relationship (and, incidentally, Tone/Intent) pick
    # up Slack activity via the exact same source-agnostic `events` queries
    # they already run for email (FR-021, confirmed during implementation to
    # need zero reader-code changes — see research.md Decision 5).
    return Envelope(
        source_type="slack",
        source_native_id=item["source_native_id"],
        occurred_at=datetime.fromisoformat(item["occurred_at"]),
        identity_status="unresolved",
        resolved_stakeholder_id=None,
        redacted_fields=[],
        payload_text=item["text"],
        structured_payload={"participant": item["from"]},
    )


def _normalize_csat(item: dict[str, Any]) -> Envelope:
    # The written comment (if any) is the only sensitive text here — it goes
    # through the same encrypted `payload_text` path every other source's
    # body uses. The numeric score is not sensitive and lives in
    # `structured_payload` (plaintext JSONB) alongside `has_comment`, a
    # boolean marker `SqlAlchemyMessageEventRepository` uses to decide
    # whether a survey_response row is worth decrypting as a Tone candidate,
    # without ever needing to decrypt score-only responses just to check.
    comment = item.get("comment")
    return Envelope(
        source_type="csat",
        source_native_id=item["source_native_id"],
        occurred_at=datetime.fromisoformat(item["occurred_at"]),
        identity_status="unresolved",
        resolved_stakeholder_id=None,
        redacted_fields=[],
        payload_text=comment if comment else f"CSAT score: {item['score']}",
        structured_payload={
            "participant": item["respondent"],
            "score": item["score"],
            "has_comment": bool(comment),
        },
    )


def _normalize_calendar(item: dict[str, Any]) -> Envelope:
    return build_meeting_envelope(
        source_native_id=item["source_native_id"],
        occurred_at=datetime.fromisoformat(item["occurred_at"]),
        transcript=item["transcript"],
        attendee=item["attendee"],
        series_id=item["series_id"],
        consent_documented=item["consent_documented"],
    )


_NORMALIZERS = {
    "gmail": _normalize_gmail,
    "zendesk": _normalize_zendesk,
    "warehouse": _normalize_warehouse,
    "slack": _normalize_slack,
    "csat": _normalize_csat,
    "calendar": _normalize_calendar,
}


class SimulatedCollector(Collector):
    source_type = "simulated"
    mvp_sources_always_expected = True

    def __init__(self, fixture_path: Path, consent: MeetingSeriesConsentRepositoryPort) -> None:
        self._fixture_path = fixture_path
        self._consent = consent

    async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = json.loads(self._fixture_path.read_text())
        # FR-023/FR-003: "THE SYSTEM SHALL NEVER collect a transcript for a
        # series lacking [documented, all-party] consent" — stronger than
        # "the Meeting reader abstains on it" (confirmed against
        # tests/ingestion/test_post_mvp_sources_real_db.py's own assertion of
        # zero `raw_envelopes` rows for a non-consented series): a
        # non-consented calendar item is dropped here, before normalize()
        # ever builds an Envelope for it, so it never reaches insert_envelope
        # at all — not merely a MeetingReader-side abstention.
        #
        # specs/019-meeting-audio-ingestion, research.md Decision 3: this gate
        # now checks the real, auditable `meeting_series_consent` table via
        # `self._consent.is_active()` — the same port `AudioCollector` checks
        # — instead of trusting the fixture's own `consent_documented`
        # boolean directly. That field stays in the fixture and in
        # `structured_payload` (`build_meeting_envelope`) as descriptive
        # metadata only; it is never the enforcement point. This means the
        # demo's own `SimulatedCollector` path now exercises the real
        # consent-then-collect flow end to end, not a second, parallel
        # trust-the-fixture mechanism.
        filtered: list[dict[str, Any]] = []
        for item in items:
            if item["source_type"] == "calendar" and not await self._consent.is_active(
                item["series_id"]
            ):
                continue
            filtered.append(item)
        # Chronological order is a hard requirement of the hash chain (see
        # EventRepositoryPort.append's docstring) — the fixture's own array order
        # deliberately isn't sorted (item 2 occurs before item 1), to prove this sort
        # is load-bearing rather than an accident of fixture authoring.
        return sorted(filtered, key=lambda item: item["occurred_at"])

    def normalize(self, raw_item: dict[str, Any]) -> Envelope:
        return _NORMALIZERS[raw_item["source_type"]](raw_item)

    @staticmethod
    def display_name(source_type: str) -> str:
        return _SOURCE_DISPLAY_NAMES.get(source_type, source_type)
