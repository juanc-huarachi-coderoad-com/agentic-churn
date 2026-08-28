# Research: Real Warehouse Connector

## Decision 1: A dedicated `WarehouseCollector`, `SimulatedCollector` untouched — same shape as `GmailCollector`/`ZendeskCollector`

**Decision**: Same as `specs/028-real-gmail-connector/research.md` Decision 1 and
`specs/029-real-zendesk-connector/research.md` Decision 1 — `WarehouseCollector` is a dedicated,
independent `Collector`, `SimulatedCollector` is never touched. Not re-derived here.

## Decision 2: `source_type = "warehouse"` shared with `SimulatedCollector`'s fixture items

**Decision**: Same reasoning as `specs/028`/`specs/029`'s own Decision 2 — one canonical `sources`
row per `source_type`. Not re-derived here.

## Decision 3: The connector is a generic SQL connection + a client-authored query file, not a vendor SDK

**Decision**: `WarehouseCollector` connects via a plain SQLAlchemy async engine built from a
configured connection URL (`WAREHOUSE_CONNECTION_URL`), and runs one client-authored SQL query
loaded from a file (`WAREHOUSE_QUERY_PATH`) — no vendor-specific SDK (Snowflake, BigQuery,
Redshift's own client libraries, etc.).

**Rationale**: Confirmed by re-reading this repository's own architecture documents (not assumed):
every one of them — `architecture/02-component-catalog.md`, `architecture/03-technology-stack.md`,
`architecture/08-class-diagrams.md`, the base product spec — names "warehouse read connector"
generically and never names a specific vendor product, unlike Gmail and Zendesk, which are both
named as specific, single SaaS products with one real API each. This is not an oversight; it
reflects that "the client's product-usage warehouse" is inherently client-specific
infrastructure (a client might run Snowflake, BigQuery, a Postgres analytics replica, or something
else entirely) in a way Gmail/Zendesk are not. Confirmed with the user directly (a genuine,
resolved ambiguity, not assumed): a generic SQL connector, matching the already-established
`CLIENT_PROFILE_PATH` precedent — "the client profile is inherently client-specific, so a human
directly edits a per-deployment file" (`decisions/00-open-questions-resolved.md` Q2) — applied to
the same underlying problem shape here. The connection URL's scheme determines which SQLAlchemy
dialect/driver handles it; this deployment ships `asyncpg` by default (already a dependency),
covering plain PostgreSQL and Redshift (which is wire-compatible with PostgreSQL) out of the box —
a client on Snowflake/BigQuery/another backend would need that backend's own SQLAlchemy-compatible
driver installed, which is the operator's own deployment-specific concern, not something this
feature preinstalls for every possible vendor (P10).

**Alternatives considered**: A specific vendor SDK (e.g. Snowflake) — rejected, narrows this
feature to clients using exactly that vendor, contradicting the architecture's own consistently
generic framing of this connector.

## Decision 4: The query result contract — four required columns, content-hash-derived idempotency

**Decision**: The configured query MUST return rows with columns `occurred_at`, `metric`,
`product_area` (nullable), `value_delta_pct` — matching `_normalize_warehouse`'s existing fixture
shape field-for-field (FR-004). Since an arbitrary client-authored query has no guaranteed natural
unique-row identifier (unlike a Gmail message ID or a Zendesk audit ID), each row's
`source_native_id` is derived as `sha256(f"{metric}:{product_area}:{occurred_at.isoformat()}:
{value_delta_pct}")` — identical content on a later run produces the identical native ID, making
re-running the same query naturally idempotent via the existing `envelope_exists()` check every
other collector already uses, with no special-casing.

**Rationale**: Requiring the client's own query to invent and return a stable ID column would be
an unusual, hard-to-explain convention for whoever writes that SQL; content-based hashing needs
nothing extra from the query and reuses this codebase's own precedent for exactly this shape of
problem (`specs/027-pgvector-embedding-store/research.md` Decision 1's identical content-hash
reasoning, applied here to a different content shape).

**Alternatives considered**: Requiring the query to return an explicit `id`/`reading_id` column —
rejected, adds a real authoring burden to every client's own SQL for a problem content-hashing
already solves without it.

## Decision 5: No connector-derived time window — the client's own query is responsible for scoping itself

**Decision**: Unlike `GmailCollector`/`ZendeskCollector`, `WarehouseCollector` does not derive a
"since last run" window from the ledger — the configured query runs as-is every cycle, and
idempotency (Decision 4) is what actually prevents duplicate collection of rows the query happens
to return again.

**Rationale**: `GmailCollector`/`ZendeskCollector`'s ledger-derived windowing works because both
APIs accept a real `after`/`start_time` parameter this codebase's own code controls. A
client-authored SQL query has no such standard parameter this connector could inject without
knowing the target warehouse's own schema (what column name means "when this happened," what time
zone, etc.) — inventing a placeholder-substitution convention for this would be real, speculative
complexity for a problem the query author is already in the best position to solve directly (e.g.
`WHERE measured_at >= now() - interval '7 days'` baked into their own query, matching
`ComputeRollupsUseCase`'s own existing `_ROLLUP_SAMPLE_WINDOW_DAYS = 7` convention). Documented as
operator guidance in `quickstart.md`, not enforced in code (`spec.md` Edge Cases).

**Alternatives considered**: A templated query with a `{since}` placeholder this connector
substitutes — rejected, real speculative complexity (a mini query-templating convention) for a
problem idempotency + query-author discipline already solves without it (P10).

## Decision 6: Wiring `ComputeRollupsUseCase` into the automated pipeline — a pre-existing gap this feature closes, not new scope invented here

**Decision**: `worker.py`'s `_orchestrate_pipeline()` (`specs/026-automated-pipeline-orchestration`)
gains one new step — `ComputeRollupsUseCase(SqlAlchemyEventRepository(session)).execute()` — called
*before* `RunReadersUseCase.execute()`, so the Usage reader (one of the eight readers already run
in that same step) sees freshly-rebuilt `rollups` reflecting any new `usage_measurement`/
`survey_response` events from *any* source, not only the new warehouse connector.

**Rationale**: Confirmed by direct code search, not assumed: `ComputeRollupsUseCase` (built in
feature 005, `REQ-M2-06`) has no caller anywhere in `app/` or `scripts/` today — a real,
already-documented gap (`specs/ROADMAP.md`'s feature-007 log entry: "`ComputeRollupsUseCase`...
has no caller anywhere in the actual pipeline... `usage_deviation` will not appear from a real
`scripts/run_readers.py` run against a freshly provisioned database until that use case is wired
into the collector/readers flow itself"). This means, today, in production, the Usage reader's
`SqlAlchemyRollupRepository` always reads an empty `rollups` table regardless of source — real or
simulated warehouse/CSAT data is collected into the ledger but never reaches the reader meant to
interpret it. This feature's own value (SC-003: real warehouse data actually reaches the Usage
reader) is impossible to deliver honestly without closing this gap — it is a required part of this
feature's scope, not scope creep, and it benefits every existing source that feeds `rollups`
(warehouse and CSAT alike), not only the one this feature adds.

**Cost characteristic, noted not solved**: `ComputeRollupsUseCase.execute()` rebuilds `rollups`
from *every* event in the ledger each time it runs (`list_all_ordered()`), not just new ones —
matching the exact same "full re-process every cycle" shape `RecurrenceReader` already has for
clustering (`specs/027-pgvector-embedding-store/research.md`'s own scope boundary: caching the
*embedding*, never redesigning the *clustering* to be incremental). Wiring this in as-is, unchanged,
matches that established precedent and this project's P10 discipline — not a new problem this
feature introduces, and not something this feature's own scope should solve by inventing
incremental rollup computation the actual requirement doesn't ask for.

**Alternatives considered**: Building an incremental version of `ComputeRollupsUseCase` — rejected,
real scope beyond "wire in the existing, already-built use case," and no requirement asks for it;
follows the same reasoning that kept `RecurrenceReader`'s own clustering full-corpus in feature 027.

## Decision 7: A small `WarehouseClient` seam, mirroring `GmailClient`/`ZendeskClient`

**Decision**: `WarehouseClient` (a `Protocol`) with one method, `async def fetch_readings() ->
list[dict[str, Any]]`. The real implementation wraps a SQLAlchemy async engine built from
`WAREHOUSE_CONNECTION_URL`, executing the query loaded from `WAREHOUSE_QUERY_PATH`; tests inject a
fake — no real database, matching `specs/028`/`specs/029`'s identical testability reasoning.
