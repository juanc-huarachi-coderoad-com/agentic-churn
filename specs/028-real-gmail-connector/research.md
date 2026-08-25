# Research: Real Gmail Connector

## Decision 1: A dedicated `GmailCollector`, following `AudioCollector`'s shape exactly — not a modification of `SimulatedCollector`

**Decision**: `GmailCollector` is a new class implementing `Collector` (`fetch`/`normalize`),
`source_type = "gmail"`, `mvp_sources_always_expected = False` (the `AudioCollector` precedent for
a dedicated, single-purpose collector — `Collector`'s own docstring: "a real gap in the original
plan... found necessary while implementing `AudioCollector`... a dedicated, single-purpose
collector has no such ambiguity: its own declared `source_type` is always what's expected"). It has
its own independent `RunCollectorUseCase.execute()` call, its own scheduled interval in
`worker.py`, and its own `--run-once` entry — `SimulatedCollector` is not touched, imported by, or
otherwise modified by this feature (`spec.md` FR-005/User Story 2).

**Rationale**: This is the exact template the codebase already established for the first real,
non-fixture connector (`specs/019-meeting-audio-ingestion`), and it is also the only shape that can
satisfy the explicit "don't remove the JSON functionality" requirement — modifying
`SimulatedCollector` itself, or replacing its `gmail` normalize function, would touch the thing the
requirement says to leave alone.

**Alternatives considered**: Adding a "real mode" flag to `SimulatedCollector` — rejected outright,
directly contradicts the explicit requirement and also violates P3 (a collector shouldn't carry a
branch for "am I real or fake").

## Decision 2: `source_type = "gmail"` is shared with `SimulatedCollector`'s fixture items — a real, accepted data-modeling consequence, not a bug to work around

**Decision**: `GmailCollector` uses the same `source_type = "gmail"` enum value
`SimulatedCollector`'s fixture already uses — not a new, parallel identifier.

**Rationale**: `sources.source_type` is a fixed Postgres enum
(`data-base/10-ddl-appendix.md`) with one canonical value per real-world source category; the
`AudioCollector` precedent for choosing a *different* value (`"transcripts"` instead of the already
-claimed `"calendar"`) applied because those two are genuinely different source categories in the
product's own model (calendar absence-monitoring events vs. meeting transcripts) — Gmail is not:
there is exactly one "gmail" in the product's mental model, and `get_or_create_source()`'s own
`SELECT ... WHERE source_type = ... LIMIT 1` logic already assumes one canonical `sources` row per
`source_type`, reused by whichever collector runs against it. In the real deployment model this
system is built for (`architecture/03-technology-stack.md`'s "one deployment = one client"), a
given client's `.env` either has real Gmail credentials configured or it doesn't — `SimulatedCollector`
is the pre-real-connector stand-in for a client that doesn't have one yet, not a permanent second
"gmail" identity meant to run forever alongside the real one. Events are never deleted or
overwritten regardless of which collector produced them (`events` is append-only at the DB level,
`tests/conftest.py`), so "coexistence without interference" (`spec.md` User Story 2, Acceptance
Scenario 2) holds at the level that actually matters — no event, finding, or score is ever
corrupted by the other collector having also run — even though the shared `sources` row's
`last_successful_sync_at`/`status` naturally reflects whichever collector most recently succeeded,
which is an honest, not a broken, representation of "is gmail connected right now."

**Alternatives considered**: A distinct enum value (e.g. a hypothetical `gmail_real`) — rejected:
invents a second identity for what the product considers one source, and would require a schema
migration to add an enum value whose only purpose is separating a demo/test path from the real one
— exactly the kind of speculative modeling P10 warns against.

## Decision 3: Polling only — no Gmail push/webhook subscription for MVP

**Decision**: `GmailCollector` polls on a scheduled interval (like every other collector in
`worker.py`); it does not set up a Gmail API push notification (Cloud Pub/Sub) subscription.

**Rationale**: REQ-M1-02 requires webhook subscription only "WHEN a source supports webhooks" —
Gmail's push mechanism requires a publicly reachable HTTPS endpoint to receive Google's push
notifications, which this system's deployment model (`docker-compose.yml`, no public ingress by
default, one Compose stack per client with no shared/exposed infrastructure) doesn't provide out of
the box. Building that endpoint, its own Pub/Sub subscription management, and the security
surface of a public webhook receiver is real, new infrastructure this feature's actual requirement
(get real Gmail signals into the system automatically) doesn't need — polling on a reasonable
interval already satisfies REQ-M1-02's polling half and this feature's own SC-001 without it.

**Alternatives considered**: Gmail push notifications via Cloud Pub/Sub — rejected above; revisit
only if a deployment's own public ingress already exists for another reason (out of this feature's
scope to build one just for this).

## Decision 4: Window derived from the ledger itself, not a separately persisted cursor

**Decision**: Each `fetch()` call queries the ledger for the latest `gmail`-sourced event's
`occurred_at`, subtracts a fixed overlap buffer (10 minutes), and uses that as the query's lower
bound (`after:`); `now()` is the upper bound. On the very first run for a mailbox with no prior
`gmail`-sourced events at all, falls back to a fixed 24-hour lookback (`spec.md` FR-010 — never the
account's entire history).

**Rationale**: Matches REQ-M1-03 exactly ("fetch a deliberate overlap window with the previous run
and de-duplicate using an idempotency key") — the overlap is the safety margin against a message
that arrived right at the boundary of the previous window being missed; idempotency-key dedup
(`idempotency_key("gmail", message_id)`, already checked via `collector_runs.envelope_exists()`
before the expensive per-message fetch, mirroring `AudioCollector`'s own Decision 10 precedent)
makes that overlap safe rather than duplicating anything. Deriving the window from the ledger
itself — not a new persisted cursor — mirrors `specs/026-automated-pipeline-orchestration`'s own
Decision 2 reasoning: no new schema/state for a value the existing data already tells you, and a
process restart's worst case is one slightly-wider-than-usual window, made safe by the same
idempotency check either way.

**Alternatives considered**: A persisted last-poll-timestamp column/table — rejected for the same
reason feature 026 rejected persisting its own cursor: disproportionate schema surface for a value
already derivable, whose worst-case staleness is self-correcting via idempotency dedup.

## Decision 5: A small `GmailClient` seam for testability, isolating `googleapiclient` to one class

**Decision**: `GmailCollector` depends on a narrow, adapter-internal `GmailClient` (a `Protocol`
defined in the same file, not a formal `ports.py` port) with exactly two async methods:
`list_message_ids(after, before) -> list[str]` and `get_message(message_id) -> dict`. The real
implementation (`_RealGmailClient`) wraps `googleapiclient.discovery.build("gmail", "v1",
credentials=...)`, running each blocking call via `asyncio.to_thread` (the same pattern
`pyannote_diarization.py` already uses for its own blocking hosted-API call, per
`audio_collector.py`'s own docstring). Tests inject a fake implementing the same two methods —
no real network, no `googleapiclient` import needed in test code.

**Rationale**: `googleapiclient`'s dynamically-built, fluently-chained resource objects
(`service.users().messages().list(...).execute()`) are awkward to fake directly; isolating the two
actual API calls behind a two-method seam keeps `GmailCollector.fetch()`'s own logic (windowing,
idempotency-check-before-fetch, per-item error isolation, header/body parsing) fully unit-testable
without mocking a third-party library's internals. `.importlinter`'s `ingestion-application-purity`
contract already anticipates and forbids `googleapiclient`/`google` imports outside
`app.ingestion.adapters` — both `GmailClient` and `_RealGmailClient` live there, so no contract
change is needed.

**Alternatives considered**: Testing against a real (throwaway) Gmail account's live API in CI —
rejected, would require committing real credentials to CI secrets for a public-ish repository and
makes tests flaky against network/API availability; this codebase's own established pattern (every
other external-API adapter: `WhisperTranscriptionAdapter`, `AnthropicLLMAdapter`,
`OpenAIEmbeddingAdapter`) is unit tests against a fake/stub, with live verification done manually
against the real service outside the automated suite.

## Decision 6: MIME body extraction — plain text preferred, HTML stripped as fallback, no attempt at a "best" multipart resolution beyond that

**Decision**: Walk the Gmail message's `payload` (recursing into `parts` for a multipart message)
for the first `mimeType == "text/plain"` part and base64url-decode its `body.data`. If none exists,
fall back to the first `text/html` part, decoded and stripped of tags via a minimal regex/parser.
If neither exists, the item is treated as a per-item failure (`spec.md` Edge Cases — "a message
with no readable text at all is skipped").

**Rationale**: Matches `spec.md`'s own Edge Case exactly, and is the smallest implementation that
satisfies FR-004 (the same shape every existing reader already expects — plain text, matching
`_normalize_gmail`'s `payload_text = item["text"]`). No attempt at richer HTML-to-text conversion
(preserving links, formatting, etc.) — out of scope, no requirement asks for it (P10).

**Alternatives considered**: A full HTML-to-Markdown conversion library — rejected, new dependency
for a capability nothing in `spec.md` requires; the readers consuming `payload_text` (Tone/Intent)
already work on plain prose, not formatted text.
