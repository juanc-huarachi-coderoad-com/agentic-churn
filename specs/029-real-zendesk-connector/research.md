# Research: Real Zendesk Connector

## Decision 1: A dedicated `ZendeskCollector`, `SimulatedCollector` untouched — same shape as `GmailCollector`/`AudioCollector`

**Decision**: `ZendeskCollector` implements `Collector`, `source_type = "zendesk"`,
`mvp_sources_always_expected = False`, its own independent `RunCollectorUseCase.execute()` call
and scheduled interval. `SimulatedCollector` is not touched, imported by, or modified by this
feature (`spec.md` FR-006/User Story 2) — identical reasoning to
`specs/028-real-gmail-connector/research.md` Decision 1, not re-derived here.

## Decision 2: `source_type = "zendesk"` shared with `SimulatedCollector`'s fixture items

**Decision**: Same as `specs/028-real-gmail-connector/research.md` Decision 2 — one canonical
`sources` row per `source_type`, reused by whichever collector runs against it. Not re-derived
here; identical rationale (fixed enum, one-deployment-one-client model, events are append-only so
no data is ever corrupted by the shared row).

## Decision 3: Detect ticket transitions via the Ticket Audits API, not the Incremental Ticket Event Export API

**Decision**: For each ticket the Incremental Ticket Export (cursor) endpoint reports as changed
since the last poll, fetch that ticket's audits (`GET /api/v2/tickets/{id}/audits.json`) and scan
each audit's `events` array for a `type: "Change"`, `field_name: "status"` entry — a transition
into `solved`/`closed` is a `resolved` event; a transition *out of* `solved`/`closed` back to an
active status is a `reopened` event. A ticket whose `created_at` falls inside the polling window
is additionally emitted as a `created` event (FR-004).

**Rationale**: Zendesk's own documentation (fetched live, not from training-data assumption)
explicitly notes the Ticket Audits List endpoint "is not intended for capturing continuous change
data; for that purpose, the Incremental Ticket Event Export API is recommended to avoid missing
records" — but that caveat is about completeness under *high, continuous* change volume across an
entire account, which is not this product's scale (REQ-NFR-05: 50k-200k events/year *across every
source combined*, Zendesk being one of three Phase-1 sources). At this scale, "list tickets that
changed" (cheap, one call per poll) plus "fetch full audit history for just the tickets that
changed" (one call per changed ticket, not per account) is proportionate — and the Audits API's
`events[].field_name`/`value`/`previous_value` shape for a `"Change"` event is long-stable, clearly
documented Zendesk API surface, unlike the less-clearly-documented exact shape of a `"Change"`-type
entry inside the Incremental Ticket Event Export stream (that endpoint's own documented sample
response showed a `"measure"`-type event, not a confirmed `"Change"`-type one, when checked live).

**Alternatives considered**: Incremental Ticket Event Export API for everything — rejected above
(shape uncertainty, and Zendesk's own noted use case is different from this feature's actual
scale). Polling raw ticket status only, inferring "resolved" whenever `status` is currently
`solved`/`closed` — rejected: cannot distinguish a first resolution from a second one after a
reopen (FR-012/SC-005 both require this), and cannot detect a "reopened" transition that happened
and was later resolved again within the same polling window, silently losing signal `_normalize_
zendesk`'s own fixture already treats as meaningful (`reopen_count`).

## Decision 4: A `requester_id` → email lookup, cached per `fetch()` call, not persisted

**Decision**: `ZendeskCollector` resolves each ticket's `requester_id` (a numeric Zendesk user ID)
to an email address via `GET /api/v2/users/{id}.json`, memoized in a plain `dict` for the lifetime
of one `fetch()` call — not written anywhere, not shared across cycles.

**Rationale**: `_normalize_zendesk`'s existing `structured_payload["participant"]` shape expects a
real identifier string (an email address, matching every other source's own `participant` shape),
but Zendesk's ticket objects only carry a numeric `requester_id`. A per-cycle cache is enough:
several transitions detected in the same `fetch()` call frequently share the same requester (the
same customer's ticket being created, then resolved, then reopened), so this avoids redundant
lookups within one run without inventing cross-run persisted state this feature's actual
requirement (FR-005's shape parity) doesn't need (P10) — the same "cache only what one cycle needs,
derive the rest from the source of truth each time" spirit as `research.md` Decision 4 in feature
028's own window-derivation choice.

**Alternatives considered**: Persisting a `requester_id`→email map across cycles (a new table) —
rejected, disproportionate for what a per-call `dict` already solves; the API cost of a repeat
lookup on a later, separate cycle is trivial at this product's real ticket volume.

## Decision 5: `httpx`, not an official Zendesk SDK — plain REST + Basic Auth

**Decision**: `ZendeskCollector`'s real HTTP calls use `httpx.AsyncClient` directly, with Basic
Auth credentials formatted as `f"{agent_email}/token"` / `api_token` (Zendesk's own documented
format, confirmed live). `httpx` moves from this project's dev-only dependency group to its main
dependencies (it was already present, just not available at runtime).

**Rationale**: Zendesk's REST API is simple, well-documented JSON-over-HTTPS with no OAuth
token-refresh complexity (unlike Gmail) — a full SDK would add a dependency for a handful of GET
requests this codebase can already make with `httpx`, which it already has in its dependency tree
and testing toolchain, avoiding both the new-dependency cost `research.md` decisions elsewhere in
this roadmap consistently avoid (P10) and the async/sync-wrapping complexity Gmail's collector
needed for its own synchronous official SDK (`asyncio.to_thread`) — `httpx.AsyncClient` is natively
async, no thread-wrapping needed at all.

**Alternatives considered**: An unofficial `zenpy`/similar Python Zendesk client library —
rejected, no official first-party SDK exists for Zendesk (unlike Google's), and a community
wrapper is an unnecessary dependency for REST calls this simple.

## Decision 6: Window derivation mirrors Gmail's exactly — ledger-derived, no new persisted cursor

**Decision**: Same mechanism as `specs/028-real-gmail-connector/research.md` Decision 4 — each
`fetch()` call queries the ledger for the latest `zendesk`-sourced event's `occurred_at`, subtracts
a 10-minute overlap buffer, falls back to a 24-hour lookback on the very first run (`spec.md`
FR-011).

**Rationale**: Identical to Gmail's — not re-derived here.

## Decision 7: A small `ZendeskClient` seam, mirroring `GmailClient`

**Decision**: `ZendeskClient` (a `Protocol` in `app.ingestion.adapters.zendesk_collector`) with
three async methods: `list_changed_tickets(after, before) -> list[dict]`,
`get_ticket_audits(ticket_id) -> list[dict]`, `get_user_email(user_id) -> str | None`. The real
implementation wraps `httpx.AsyncClient`; tests inject a fake — no real network, matching
`specs/028-real-gmail-connector/research.md` Decision 5's identical reasoning for testability.
`.importlinter`'s `ingestion-application-purity` contract does not yet forbid a Zendesk HTTP client
module by name (unlike Gmail's pre-anticipated `googleapiclient`/`google` entries) — no new entry
is strictly required since `httpx` itself is not a "concrete external-API SDK" the contract's
existing forbidden-module list is about (it's a generic HTTP client, already used elsewhere in this
codebase's own test tooling), but this collector's real HTTP calls still live only in
`app.ingestion.adapters`, consistent with the contract's spirit.
