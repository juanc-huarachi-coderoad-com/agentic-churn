"""`ZendeskCollector` — the third real, non-simulated `Collector`
(specs/029-real-zendesk-connector), following `GmailCollector`/`AudioCollector`'s
shape exactly. `SimulatedCollector` and its JSON fixture are not touched by this
file at all — an explicit, non-negotiable requirement (spec.md User Story 2).

`ZendeskClient` isolates HTTP calls behind three testable methods (research.md
Decision 7) — real usage wraps `httpx.AsyncClient` with Basic Auth
(`{agent_email}/token` / `{api_token}`, Zendesk's own documented format); tests
inject a fake, no real network.

`fetch()`:
1. Derives its own window from the ledger's latest `zendesk`-sourced event, with
   a 10-minute overlap buffer — a 24-hour lookback on the very first run
   (research.md Decision 6, mirrors specs/028's Decision 4).
2. Lists tickets that changed in that window (Incremental Ticket Export), then
   fetches each changed ticket's audit history to classify every status
   transition within the window as `created`/`resolved`/`reopened` (research.md
   Decision 3) — never collapsing multiple reopenings of the same ticket into
   one event (FR-012).
3. Checks idempotency per *transition*, not per ticket (a ticket can have both
   an already-collected transition and a brand-new one in the same run) —
   necessarily after fetching that ticket's audits, since which specific
   transitions are new can't be known before looking.
4. A per-ticket failure is logged and skipped without aborting the cycle
   (FR-008). A whole-connection failure (`list_changed_tickets` itself raising)
   propagates out of `fetch()` — `RunCollectorUseCase.execute()`'s own
   try/except records it as an honest, visible coverage gap (FR-007).
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.application.collector import Collector
from app.ingestion.application.ports import CollectorRunRepositoryPort
from app.ingestion.domain.envelope import Envelope, idempotency_key

logger = logging.getLogger(__name__)

_OVERLAP_BUFFER = timedelta(minutes=10)
_FIRST_RUN_LOOKBACK = timedelta(hours=24)
_RESOLVED_STATUSES = {"solved", "closed"}


class ZendeskClient(Protocol):
    """The narrow seam `ZendeskCollector` depends on — real usage wraps Zendesk's
    REST API; tests inject a fake with no real network (research.md Decision 7)."""

    async def list_changed_tickets(
        self, after: datetime, before: datetime
    ) -> list[dict[str, Any]]: ...

    async def get_ticket_audits(self, ticket_id: int) -> list[dict[str, Any]]: ...

    async def get_user_email(self, user_id: int) -> str | None: ...


class _RealZendeskClient:
    def __init__(self, subdomain: str, agent_email: str, api_token: str) -> None:
        self._base_url = f"https://{subdomain}.zendesk.com/api/v2"
        self._auth = (f"{agent_email}/token", api_token)

    async def list_changed_tickets(
        self, after: datetime, before: datetime
    ) -> list[dict[str, Any]]:
        tickets: list[dict[str, Any]] = []
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            url = f"{self._base_url}/incremental/tickets/cursor"
            params: dict[str, Any] | None = {"start_time": int(after.timestamp())}
            cursor: str | None = None
            while True:
                request_params = {"cursor": cursor} if cursor else params
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                payload = response.json()
                tickets.extend(payload.get("tickets", []))
                if payload.get("end_of_stream"):
                    break
                cursor = payload.get("after_cursor") or payload.get("next_cursor")
                if not cursor:
                    break
        return tickets

    async def get_ticket_audits(self, ticket_id: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            response = await client.get(f"{self._base_url}/tickets/{ticket_id}/audits.json")
            response.raise_for_status()
            result: list[dict[str, Any]] = response.json().get("audits", [])
            return result

    async def get_user_email(self, user_id: int) -> str | None:
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            response = await client.get(f"{self._base_url}/users/{user_id}.json")
            response.raise_for_status()
            email: str | None = response.json().get("user", {}).get("email")
            return email


def _classify_transitions(
    ticket: dict[str, Any], audits: list[dict[str, Any]], window_start: datetime
) -> list[dict[str, Any]]:
    ticket_id = ticket["id"]
    transitions: list[dict[str, Any]] = []

    created_at = datetime.fromisoformat(ticket["created_at"])
    if created_at >= window_start:
        transitions.append(
            {"kind": "created", "native_id": f"{ticket_id}-created", "occurred_at": created_at}
        )

    for audit in audits:
        audit_occurred_at = datetime.fromisoformat(audit["created_at"])
        if audit_occurred_at < window_start:
            continue
        for event in audit.get("events", []):
            if event.get("type") != "Change" or event.get("field_name") != "status":
                continue
            previous = (event.get("previous_value") or "").lower()
            current = (event.get("value") or "").lower()
            native_id = f"{ticket_id}-audit-{audit['id']}"
            if current in _RESOLVED_STATUSES and previous not in _RESOLVED_STATUSES:
                transitions.append(
                    {"kind": "resolved", "native_id": native_id, "occurred_at": audit_occurred_at}
                )
            elif previous in _RESOLVED_STATUSES and current not in _RESOLVED_STATUSES:
                transitions.append(
                    {"kind": "reopened", "native_id": native_id, "occurred_at": audit_occurred_at}
                )
    return transitions


class ZendeskCollector(Collector):
    source_type = "zendesk"
    # `AudioCollector`/`GmailCollector`'s own precedent — a dedicated,
    # single-purpose collector's own source_type is always what's expected.
    mvp_sources_always_expected = False

    def __init__(
        self,
        client: ZendeskClient,
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
                    "WHERE s.source_type = 'zendesk'::source_type"
                )
            )
        ).one_or_none()
        if row is None or row.latest is None:
            return now - _FIRST_RUN_LOOKBACK, now
        return row.latest - _OVERLAP_BUFFER, now

    async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
        # window_start/window_end (caller-supplied) are unused — the real window
        # is derived from the ledger itself, matching GmailCollector's own
        # precedent (research.md Decision 6).
        after, before = await self._derive_window()
        tickets = await self._client.list_changed_tickets(after, before)

        email_cache: dict[int, str | None] = {}
        items: list[dict[str, Any]] = []
        for ticket in tickets:
            try:
                audits = await self._client.get_ticket_audits(ticket["id"])
                transitions = _classify_transitions(ticket, audits, after)
                if not transitions:
                    continue

                requester_id = ticket.get("requester_id")
                if requester_id is not None and requester_id not in email_cache:
                    email_cache[requester_id] = await self._client.get_user_email(requester_id)
                reporter = (
                    email_cache.get(requester_id) if requester_id is not None else None
                ) or f"zendesk-user-{requester_id}"

                for transition in transitions:
                    key = idempotency_key(self.source_type, transition["native_id"])
                    if await self._collector_runs.envelope_exists(key):
                        continue
                    items.append(
                        {
                            "source_native_id": transition["native_id"],
                            "occurred_at": transition["occurred_at"].isoformat(),
                            "reporter": reporter,
                            "ticket_number": ticket["id"],
                            "title": ticket.get("subject", ""),
                            "state": transition["kind"],
                        }
                    )
            except Exception:
                logger.exception(
                    "zendesk collector: ticket %s failed, skipped (FR-008)", ticket.get("id")
                )
                continue
        return items

    def normalize(self, raw_item: dict[str, Any]) -> Envelope:
        # Matches SimulatedCollector's own _normalize_zendesk field-for-field,
        # minus product_area (spec.md Assumptions — no standard mapping exists;
        # RunCollectorUseCase's own _match_product_area already handles its
        # absence gracefully via .get(), never guessing one).
        return Envelope(
            source_type="zendesk",
            source_native_id=raw_item["source_native_id"],
            occurred_at=datetime.fromisoformat(raw_item["occurred_at"]),
            identity_status="unresolved",
            resolved_stakeholder_id=None,
            redacted_fields=[],
            payload_text=raw_item["title"],
            structured_payload={
                "participant": raw_item["reporter"],
                "ticket_number": raw_item["ticket_number"],
                "title": raw_item["title"],
                "state": raw_item["state"],
            },
        )
