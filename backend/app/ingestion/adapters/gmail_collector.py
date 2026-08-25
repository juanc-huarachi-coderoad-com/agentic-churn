"""`GmailCollector` — the second real, non-simulated `Collector`
(specs/028-real-gmail-connector), following `AudioCollector`'s shape exactly
(specs/019-meeting-audio-ingestion). `SimulatedCollector` and its JSON fixture are
not touched by this file at all — an explicit, non-negotiable requirement
(spec.md User Story 2).

`GmailClient` isolates the third-party `googleapiclient` library behind two
testable methods (research.md Decision 5) — `.importlinter`'s
`ingestion-application-purity` contract already forbids `googleapiclient`/`google`
imports outside `app.ingestion.adapters`, so both this Protocol and its real
implementation live here, never in `app.ingestion.application`.

`fetch()`:
1. Derives its own window from the ledger's latest `gmail`-sourced event, with a
   10-minute overlap buffer (research.md Decision 4) — a 24-hour lookback on the
   very first run for a mailbox with no prior gmail events (spec.md FR-010: never
   the account's entire history).
2. Skips a message whose idempotency key already has a matching `raw_envelopes`
   row *before* fetching its full body (mirrors AudioCollector's own Decision 10
   precedent — the load-bearing fix for that feature's own `/speckit-analyze`
   finding F1).
3. A per-item failure (unparseable message, no readable body) is logged and
   skipped without aborting the cycle (FR-007).
4. A whole-connection failure (`list_message_ids` itself raising — bad
   credentials, unreachable service) is allowed to propagate out of `fetch()` —
   `RunCollectorUseCase.execute()`'s own try/except records it as an honest,
   visible coverage gap (FR-006), not a crash.
"""

import asyncio
import email.utils
import logging
import re
from base64 import urlsafe_b64decode
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.application.collector import Collector
from app.ingestion.application.ports import CollectorRunRepositoryPort
from app.ingestion.domain.envelope import Envelope, idempotency_key

logger = logging.getLogger(__name__)

_OVERLAP_BUFFER = timedelta(minutes=10)
_FIRST_RUN_LOOKBACK = timedelta(hours=24)
_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_HTML_TAG = re.compile(r"<[^>]+>")


class GmailClient(Protocol):
    """The narrow seam `GmailCollector` depends on — real usage wraps the Gmail
    API; tests inject a fake with no real network (research.md Decision 5)."""

    async def list_message_ids(self, after: datetime, before: datetime) -> list[str]: ...

    async def get_message(self, message_id: str) -> dict[str, Any]: ...


class _RealGmailClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._service: Any = None

    def _build_service(self) -> Any:
        # Imported lazily, inside the one method that needs them, so importing
        # this module alone never requires real credentials to exist — mirrors
        # OpenAIEmbeddingAdapter's own lazy-client-construction precedent.
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        credentials = Credentials(  # type: ignore[no-untyped-call]  # google-auth ships no stubs
            token=None,
            refresh_token=self._refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=_SCOPES,
        )
        return build("gmail", "v1", credentials=credentials)

    def _service_or_build(self) -> Any:
        if self._service is None:
            self._service = self._build_service()
        return self._service

    async def list_message_ids(self, after: datetime, before: datetime) -> list[str]:
        def _list_sync() -> list[str]:
            service = self._service_or_build()
            query = f"after:{int(after.timestamp())} before:{int(before.timestamp())}"
            ids: list[str] = []
            page_token: str | None = None
            while True:
                response = (
                    service.users()
                    .messages()
                    .list(userId="me", q=query, pageToken=page_token, maxResults=100)
                    .execute()
                )
                ids.extend(m["id"] for m in response.get("messages", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
            return ids

        return await asyncio.to_thread(_list_sync)

    async def get_message(self, message_id: str) -> dict[str, Any]:
        def _get_sync() -> dict[str, Any]:
            service = self._service_or_build()
            result: dict[str, Any] = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            return result

        return await asyncio.to_thread(_get_sync)


def _extract_header(payload: dict[str, Any], name: str) -> str | None:
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == name.lower():
            value: str = header["value"]
            return value
    return None


def _decode_part_body(part: dict[str, Any]) -> str | None:
    data = part.get("body", {}).get("data")
    if not data:
        return None
    return urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _extract_body_text(payload: dict[str, Any]) -> str | None:
    # research.md Decision 6 — text/plain preferred, text/html stripped as
    # fallback, no attempt at richer conversion beyond that.
    parts = payload.get("parts")
    if not parts:
        if payload.get("mimeType") == "text/plain":
            return _decode_part_body(payload)
        if payload.get("mimeType") == "text/html":
            html = _decode_part_body(payload)
            return _HTML_TAG.sub("", html) if html else None
        return None

    for part in parts:
        if part.get("mimeType") == "text/plain":
            text_body = _decode_part_body(part)
            if text_body:
                return text_body
    for part in parts:
        if part.get("mimeType") == "text/html":
            html = _decode_part_body(part)
            if html:
                return _HTML_TAG.sub("", html)
    for part in parts:
        nested = _extract_body_text(part)
        if nested:
            return nested
    return None


class GmailCollector(Collector):
    source_type = "gmail"
    # `AudioCollector`'s own precedent (specs/019-meeting-audio-ingestion) — a
    # dedicated, single-purpose collector's own source_type is always what's
    # expected, never inferred from a fixture's contents.
    mvp_sources_always_expected = False

    def __init__(
        self,
        client: GmailClient,
        collector_runs: CollectorRunRepositoryPort,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._collector_runs = collector_runs
        self._session = session

    async def _derive_window(self) -> tuple[datetime, datetime]:
        now = datetime.now(UTC)
        row = (
            await self._session.execute(
                text(
                    "SELECT MAX(e.occurred_at) AS latest FROM events e "
                    "JOIN raw_envelopes re ON re.id = e.envelope_id "
                    "JOIN collector_runs cr ON cr.id = re.collector_run_id "
                    "JOIN sources s ON s.id = cr.source_id "
                    "WHERE s.source_type = 'gmail'::source_type"
                )
            )
        ).one_or_none()
        if row is None or row.latest is None:
            return now - _FIRST_RUN_LOOKBACK, now
        return row.latest - _OVERLAP_BUFFER, now

    async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
        # window_start/window_end (the caller-supplied args) are intentionally
        # unused — the real window is derived from the ledger itself
        # (research.md Decision 4), the same way AudioCollector's own fetch()
        # already ignores these two params in favor of its own logic.
        after, before = await self._derive_window()
        message_ids = await self._client.list_message_ids(after, before)

        items: list[dict[str, Any]] = []
        for message_id in message_ids:
            key = idempotency_key(self.source_type, message_id)
            if await self._collector_runs.envelope_exists(key):
                continue

            try:
                message = await self._client.get_message(message_id)
                payload = message.get("payload", {})
                from_header = _extract_header(payload, "From")
                body_text = _extract_body_text(payload)
                if from_header is None or not body_text:
                    logger.warning(
                        "gmail collector: message %s has no usable From/body, skipped",
                        message_id,
                    )
                    continue
                _, from_address = email.utils.parseaddr(from_header)
                occurred_at = datetime.fromtimestamp(
                    int(message["internalDate"]) / 1000, tz=UTC
                )
            except Exception:
                logger.exception(
                    "gmail collector: message %s failed, skipped (FR-007)", message_id
                )
                continue

            items.append(
                {
                    "source_native_id": message_id,
                    "occurred_at": occurred_at.isoformat(),
                    "from": from_address or from_header,
                    "text": body_text,
                }
            )
        return items

    def normalize(self, raw_item: dict[str, Any]) -> Envelope:
        # Matches SimulatedCollector's own _normalize_gmail field-for-field
        # (research.md/plan.md — FR-004: zero reader changes needed).
        return Envelope(
            source_type="gmail",
            source_native_id=raw_item["source_native_id"],
            occurred_at=datetime.fromisoformat(raw_item["occurred_at"]),
            identity_status="unresolved",
            resolved_stakeholder_id=None,
            redacted_fields=[],
            payload_text=raw_item["text"],
            structured_payload={"participant": raw_item["from"]},
        )
