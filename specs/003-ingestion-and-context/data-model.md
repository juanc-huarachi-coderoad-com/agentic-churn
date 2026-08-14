# Data Model: Ingestion and Context

## No new tables

Every table this feature touches already exists from feature 001's migration:
`client_profile_versions`, `stakeholders`, `product_areas`, `commitments`,
`profile_history_entries` (`data-base/04-schema-context.md`); `sources`,
`collector_runs`, `coverage_reports`, `identity_map`, `raw_envelopes`
(`data-base/02-schema-ingestion.md`); `events`, `event_threads`, `response_pairs`
(`data-base/03-schema-ledger.md`). This feature is the first to read and write them
for real — no schema restated here.

## New value objects (application/domain layer only, not persisted directly)

| Object | Purpose | Fields |
|---|---|---|
| `Envelope` | The normalized shape a `Collector` hands to the ledger, before it becomes a `raw_envelopes` row | `source_type`, `source_native_id`, `idempotency_key`, `occurred_at`, `identity_status`, `resolved_stakeholder_id`, `redacted_fields`, `payload` (plaintext, encrypted just before persistence), `structured_payload` |
| `HashChainLink` | The `(prev_event_hash, event_hash)` pair for one event, computed by `ingestion/domain/hash_chain.py` | Pure function output — not a class needing its own identity |

## The fixture: `demo/fixtures/meridian-week.json`

New in this feature. Derived from `examples/01-end-to-end-walkthrough.md`'s Phase-1
subset (sources 1–3: email, tickets, product usage — sources 4–5, chat and CSAT, are
Phase 2 per `decisions/01-mvp-scope-and-phasing.md` and excluded). Shape: one JSON array
of raw source items, tagged by `source_type`, that `SimulatedCollector.fetch()` reads
and yields one at a time — matching what a real Gmail/Zendesk/warehouse adapter's
`fetch()` would return before `normalize()` touches it.

Six items, not four: ticket #398 needs *two* raw signals (created, then resolved) to
make its response-pair business-hours arithmetic a genuine two-timestamp computation
rather than a hardcoded number; ticket #456 needs only one (reopened, still open as of
the fixture's reference time — see below); a sixth item exists solely to give the
redaction path (`REQ-M1-09`, FR-012) something real to redact — none of the other five
touch an excluded topic. All times are `America/Bogota` (Meridian's profile timezone),
business calendar `08:00–18:00`, using the real calendar week of **Monday 2026-08-10 –
Friday 2026-08-14**:

```json
[
  {
    "source_type": "gmail",
    "source_native_id": "gmail-msg-8831",
    "occurred_at": "2026-08-10T09:14:00-05:00",
    "from": "ana.reyes@meridian.com",
    "text": "Please advise on the timeline. I need to brief the board on Thursday."
  },
  {
    "source_type": "zendesk",
    "source_native_id": "zendesk-456-reopened",
    "occurred_at": "2026-08-10T07:40:00-05:00",
    "reporter": "support-desk@meridian.zendesk.com",
    "ticket_number": 456,
    "title": "Slow API response",
    "reopen_count": 2,
    "product_area": "tracking_api",
    "state": "reopened"
  },
  {
    "source_type": "zendesk",
    "source_native_id": "zendesk-398-created",
    "occurred_at": "2026-08-11T11:02:00-05:00",
    "reporter": "support-desk@meridian.zendesk.com",
    "ticket_number": 398,
    "title": "Add CSV export",
    "product_area": "reporting",
    "state": "created"
  },
  {
    "source_type": "zendesk",
    "source_native_id": "zendesk-398-resolved",
    "occurred_at": "2026-08-11T13:02:00-05:00",
    "reporter": "support-desk@meridian.zendesk.com",
    "ticket_number": 398,
    "title": "Add CSV export",
    "product_area": "reporting",
    "state": "resolved"
  },
  {
    "source_type": "warehouse",
    "source_native_id": "usage-tracking_api-w34",
    "occurred_at": "2026-08-12T00:00:00-05:00",
    "metric": "weekly_active_usage",
    "product_area": "tracking_api",
    "value_delta_pct": -22
  },
  {
    "source_type": "gmail",
    "source_native_id": "gmail-msg-8845",
    "occurred_at": "2026-08-13T14:30:00-05:00",
    "from": "ana.reyes@meridian.com",
    "text": "Separately — I'm forwarding the contract dispute thread to our legal team, please hold off on that topic until they weigh in."
  }
]
```

The sixth item's text matches the seeded client profile's `legal_threads` exclusion
(`data-base/11-seed-data.sql`'s `exclusions: [legal_threads, commercial_negotiation]`) —
`RunCollectorUseCase` must strip it before the envelope is persisted and record the
redaction in `raw_envelopes.redacted_fields` (FR-012, H1 remediation).

**Worked arithmetic**, matching `spec.md` User Story 2's acceptance scenarios exactly:

- **Ticket #398**: created Tue 11:02, resolved Tue 13:02 — both inside the 08:00–18:00
  window, no day boundary crossed → **2.0 business hours elapsed**, `state = resolved`.
- **Ticket #456**: reopened Mon 07:40 (clipped forward to the 08:00 window start) — with
  the test's fixed `as_of` reference time of **Tue 2026-08-11T17:00:00-05:00**:
  Monday contributes the full 08:00–18:00 window (10.0h), Tuesday contributes 08:00–17:00
  (9.0h) → **19.0 business hours elapsed**, `state = open_overdue` (no reply event exists
  in this fixture — matching `examples/01`, where #456 is still open).

**Weekend-boundary case** (SC-003; not drawn from the fixture above — a standalone
`compute_business_hours_elapsed` unit test case, since none of this feature's fixture
events happen to straddle a weekend): a message at **Friday 2026-08-14T16:00:00-05:00**
against an `as_of` of **Monday 2026-08-17T10:00:00-05:00** →
Friday contributes 16:00–18:00 (2.0h), Saturday and Sunday contribute nothing, Monday
contributes 08:00–10:00 (2.0h) → **4.0 business hours elapsed**. This is the case that
proves the calculator actually skips the weekend rather than counting elapsed wall-clock
hours.

## Validation

- **Profile**: `context/domain/profile_schema.py`'s Pydantic model is the acceptance
  test for FR-001/FR-002 — a value either parses and passes `signs_renewal` validation,
  or it's rejected with a specific field-level error.
- **Ledger**: hash-chain integrity is checked two ways for the same data — computed in
  Python at write time, independently re-verified by the DB's `verify_hash_chain()`
  function — per `research.md`.
- **Collectors**: `SimulatedCollector` run twice over the fixture is the acceptance test
  for FR-010's idempotency guarantee — see `quickstart.md`.
