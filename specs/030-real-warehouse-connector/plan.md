# Implementation Plan: Real Warehouse Connector

**Branch**: `main` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/030-real-warehouse-connector/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add `WarehouseCollector` (`backend/app/ingestion/adapters/warehouse_collector.py`) — a generic
SQL-based `Collector` (a read-only connection string + a client-authored query file, `research.md`
Decision 3), not a vendor SDK, following `GmailCollector`/`ZendeskCollector`'s established shape.
`SimulatedCollector` is not modified. Also wires the existing, already-built but never-invoked
`ComputeRollupsUseCase` into `worker.py`'s `_orchestrate_pipeline()` (`research.md` Decision 6) —
a pre-existing gap (traced to feature 007's own `specs/ROADMAP.md` log entry) this feature's own
value depends on closing, since real warehouse data would otherwise be collected but never reach
the Usage reader, exactly as no source's usage/CSAT data does today.

## Technical Context

**Language/Version**: Python 3.12 — unchanged.

**Primary Dependencies**: None new for the default (Postgres/Redshift-compatible) case — reuses
`sqlalchemy[asyncio]` + `asyncpg`, both already main dependencies. A client on a different
warehouse backend (Snowflake, BigQuery, etc.) supplies that backend's own SQLAlchemy dialect/driver
as an operator-installed extra — not preinstalled here (`research.md` Decision 3).

**Storage**: The application's own PostgreSQL 16 gets no schema change. The *target* warehouse is
an external, client-owned database this connector reads from — never written to.

**Testing**: pytest, unit-style against a fake `WarehouseClient` (no real database) — covering the
query-result → `Envelope` mapping, content-hash idempotency (Decision 4), malformed-row skipping,
and whole-connection-failure propagation. `ComputeRollupsUseCase`'s own wiring is covered by a
real-DB test proving a `usage_measurement` event actually produces a `rollups` row after
`_orchestrate_pipeline()`'s new step runs — the first time this has ever been true in this
codebase for any source. `SimulatedCollector`'s own existing test suite is the non-regression
proof for FR-005.

**Target Platform**: Same Docker Compose `worker` service. No new container.

**Project Type**: Web application backend (Python/FastAPI) — no frontend change.

**Performance Goals**: No new latency target. `ComputeRollupsUseCase`'s full-ledger rebuild cost
per cycle is a known, accepted characteristic (`research.md` Decision 6), not a new regression —
matches this project's existing `RecurrenceReader` precedent at the same P10 discipline level.

**Constraints**: Read-only warehouse access only (FR-002/REQ-M1-P4). Must never touch
`SimulatedCollector` (FR-005). `ComputeRollupsUseCase`'s own internal logic is unchanged — this
feature only adds a caller (Decision 6's own scope boundary).

**Scale/Scope**: One new adapter file, one new settings block (2 fields: connection URL, query file
path), one composition-root wiring change in `worker.py` for the collector, one additional line in
`worker.py`'s existing `_orchestrate_pipeline()` for the rollups step, new unit + real-DB tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| P1 Evidence or It Does Not Exist | No | No change to citation mechanics. |
| P2 The Model Interprets, Code Calculates | No | No scoring code touched; `ComputeRollupsUseCase` is pure arithmetic, already unchanged. |
| P3 Each Component Refuses to Do the Next One's Job | Yes | `WarehouseCollector` only reads pre-computed rows and normalizes (REQ-M1-P1/P2) — the client's own query computes the delta, not this connector. |
| **P4 A Human Always Sends** | **Yes — explicitly checked.** | FR-002/REQ-M1-P4: read-only connection only, never a write-capable one. |
| P5 Admit What We Cannot See | Yes | FR-007/User Story 3: a whole-connection failure is a visible coverage gap. |
| P6 Silence Is a Success State | No | Not a dashboard/UI feature. |
| P7 Context Over Sentiment | No | No Tone-reader logic touched. |
| P8 Clean Architecture — the Dependency Rule Is Law | Yes | `WarehouseCollector`/`WarehouseClient` live in `app.ingestion.adapters`; the new `ComputeRollupsUseCase` call site in `worker.py` uses an existing, already-correctly-layered application use case, not a new one. |
| **P9 Test-First Determinism** | **Yes — re-checked deliberately given Decision 6's scope.** | `ComputeRollupsUseCase.execute()` is itself a "truncate + rebuild from events" projection, the exact same shape `event_threads`/`response_pairs` already have and golden-replay already exercises — wiring in an *existing*, unmodified use case as a new caller does not change its own determinism properties. No golden-replay test needs to change. |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | **Yes.** | No vendor SDK (Decision 3); no query-templating placeholder system (Decision 5); no incremental-rollup redesign (Decision 6) — every alternative considered and rejected in `research.md` was rejected specifically for adding scope this feature's actual requirement doesn't need. |
| P11 Frontend | No | No frontend change. |

**Result**: PASS. No violation requires justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/030-real-warehouse-connector/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `data-model.md` — no schema change. No `contracts/` — no new API endpoint; the query-result
contract (Decision 4) is documented in `quickstart.md` instead, since it's an operator-facing
contract (what columns their SQL must return), not an internal port.

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                          # MODIFIED — warehouse_connection_url/_query_path/_poll_interval_hours
│   └── ingestion/adapters/
│       └── warehouse_collector.py         # NEW — WarehouseClient (Protocol), _RealWarehouseClient, WarehouseCollector
├── app/worker.py                          # MODIFIED — new collector job + --run-once entry; _orchestrate_pipeline() gains the ComputeRollupsUseCase step
└── tests/unit/
    ├── test_warehouse_collector.py        # NEW — fake WarehouseClient, no real network
    └── test_pipeline_orchestration.py     # MODIFIED — new real-DB test proving rollups actually gets rebuilt
```

**Structure Decision**: Mirrors `specs/028`/`specs/029`'s own structure for the collector itself;
the `ComputeRollupsUseCase` wiring lands in the same `_orchestrate_pipeline()` function feature 026
already established as the automated pipeline's single composition point for "things that must run
before readers do."

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
