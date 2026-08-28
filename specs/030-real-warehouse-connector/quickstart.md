# Quickstart: Real Warehouse Connector

## Prerequisites

- A read-only database connection to the client's product-usage warehouse (or an analytics
  replica) — `WAREHOUSE_CONNECTION_URL` in `backend/.env`, a standard SQLAlchemy-style connection
  string (e.g. `postgresql+asyncpg://readonly_user:...@warehouse-host:5432/analytics`).
- A SQL query file at the path configured by `WAREHOUSE_QUERY_PATH` (default:
  `./demo/warehouse-query.sql`), written by whoever operates this deployment against their own
  warehouse's actual schema. The query MUST return these columns (any additional columns are
  ignored):

  | Column | Type | Notes |
  |---|---|---|
  | `occurred_at` | timestamp | When this reading was measured |
  | `metric` | text | e.g. `weekly_active_usage` — free text, matches the Usage reader's existing expectations |
  | `product_area` | text, nullable | Matched against the client profile's own product areas; `NULL` if not applicable |
  | `value_delta_pct` | integer | Already-computed percentage change — this connector never computes it itself (REQ-M1-P1/P2) |

  The query is responsible for scoping itself to relevant, recent data (e.g. `WHERE measured_at >=
  now() - interval '7 days'`) — this connector does not derive a window itself (`research.md`
  Decision 5).

## Setup

1. No migration needed — no schema change to this application's own database.
2. `docker compose exec worker python -m app.worker --run-once warehouse` runs one collection
   cycle immediately.

## Validation

**Story 1 (real usage data becomes real signals, and reaches the Usage reader)**:
1. Point `WAREHOUSE_QUERY_PATH` at a query returning at least one row.
2. Run `--run-once warehouse`.
3. Confirm via `GET /api/coverage` that `warehouse` shows connected, and that a `usage_measurement`
   event now exists in the ledger for each returned row.
4. Run `--run-once pipeline` (or wait for the automated cycle) and confirm — for the first time in
   this system's history for *any* source — that a `rollups` row now exists reflecting that data
   (query the `rollups` table directly, or confirm the Usage reader can now produce a
   `usage_deviation` finding where one wouldn't have existed before this feature).
5. Run the same query/cycle again with no new underlying data — confirm no duplicate events
   (SC-002).

**Story 2 (simulated sources are unaffected)**:
1. With the real warehouse connector present and configured, run `scripts/run_collector.py
   --source simulated` exactly as documented before this feature.
2. Confirm identical output to before this feature existed.
3. Run `tests/unit/test_simulated_collector.py` unchanged — confirm it still passes.

**Story 3 (a connection failure is visible)**:
1. Temporarily set `WAREHOUSE_CONNECTION_URL` to an invalid value and run `--run-once warehouse`.
2. Confirm the run fails visibly (a coverage gap for `warehouse`, logged), not a silent
   zero-events success.

## Expected outcome

Real, already-interpreted usage readings become real, citable ledger events on the warehouse's own
schedule, with zero duplicate collection; the rollup projection the Usage reader actually depends
on is rebuilt as part of the regular automated pipeline for the first time; every existing
simulated-source flow continues to work completely unmodified.
