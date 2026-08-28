# Implementation Plan: Real Zendesk Connector

**Branch**: `main` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/029-real-zendesk-connector/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add `ZendeskCollector` (`backend/app/ingestion/adapters/zendesk_collector.py`), a new, independent
`Collector` following `GmailCollector`/`AudioCollector`'s established shape — real Zendesk REST API
reads (Incremental Ticket Export for "what changed" + Ticket Audits for "what specifically
changed" on each ticket, `research.md` Decision 3), per-item failure isolation, idempotency, its
own scheduled interval, its own `--run-once` entry. `SimulatedCollector` and its JSON fixture are
not modified in any way, mirroring feature 028's own non-negotiable constraint exactly. A small
internal `ZendeskClient` seam isolates HTTP calls behind three testable methods. Uses `httpx`
(promoted from dev-only to a main dependency) rather than a new SDK — Zendesk's REST API needs
nothing more.

## Technical Context

**Language/Version**: Python 3.12 — unchanged.

**Primary Dependencies**: `httpx` moves from this project's dev dependency group to its main
dependencies (already present, just not available at runtime until now) — no brand-new package.

**Storage**: PostgreSQL 16 — no schema change. `sources.source_type = 'zendesk'` already exists
(shared with `SimulatedCollector`'s fixture items, `research.md` Decision 2); no new table.

**Testing**: pytest, unit-style against a fake `ZendeskClient` (no real network) — covering
transition classification (created/reopened/resolved, including a ticket reopened twice within one
window), windowing, idempotency, per-item failure isolation, and whole-connection-failure
propagation. `SimulatedCollector`'s own existing test suite is the non-regression proof for
FR-006/User Story 2 — it needs zero changes and must keep passing.

**Target Platform**: Same Docker Compose `worker` service. No new container — Zendesk credentials
are new environment variables in `.env`.

**Project Type**: Web application backend (Python/FastAPI) — no frontend change.

**Performance Goals**: No new latency target — Zendesk is not on the automated-pipeline's ~30-60s
path (`specs/026`); it runs on its own configurable interval (hourly default, matching
`AudioCollector`/`GmailCollector`'s own precedent).

**Constraints**: Read-only Zendesk scope only (FR-002/REQ-M1-P4). Must never touch
`SimulatedCollector` (FR-006). First-ever run per account bounded to a 24-hour lookback (FR-011). A
ticket reopened multiple times must produce one event per reopening (FR-012).

**Scale/Scope**: One new adapter file, one new settings block (4 fields: subdomain, agent email,
API token, poll interval), one composition-root wiring change in `worker.py`, new unit tests, one
`pyproject.toml` dependency-group move.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| P1 Evidence or It Does Not Exist | No | No change to citation mechanics. |
| P2 The Model Interprets, Code Calculates | No | No scoring code touched. |
| P3 Each Component Refuses to Do the Next One's Job | Yes | `ZendeskCollector` only fetches, classifies transitions, and normalizes (REQ-M1-P1/P2/P3) — no severity/importance judgment, no identity interpretation beyond the read-only requester-email lookup this shape already requires (`RunCollectorUseCase` still does the real identity resolution). |
| **P4 A Human Always Sends** | **Yes — explicitly checked.** | FR-002/REQ-M1-P4: read-only scope only, never write/modify/delete access. |
| P5 Admit What We Cannot See | Yes | FR-007/User Story 3: a whole-connection failure is a visible coverage gap, mirroring `AudioCollector`/`GmailCollector`'s established propagation discipline. |
| P6 Silence Is a Success State | No | Not a dashboard/UI feature. |
| P7 Context Over Sentiment | No | No Tone-reader baseline logic touched. |
| P8 Clean Architecture — the Dependency Rule Is Law | Yes | `ZendeskCollector`/`ZendeskClient`/`_RealZendeskClient` all live in `app.ingestion.adapters`; `.importlinter`'s `ingestion-application-purity` contract is unaffected (no new forbidden-module entry strictly required, `research.md` Decision 7). |
| P9 Test-First Determinism | No | Doesn't touch `backend/app/ledger/` or `backend/app/scoring/` — a new `Collector`, same shape as prior real connectors, which required no golden-replay changes either. |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | **Yes.** | No new SDK (Decision 5); no persisted requester-email cache (Decision 4); no attempt to map Zendesk-specific fields onto "product area" (`spec.md` Assumptions); Incremental Ticket Event Export rejected in favor of the smaller, already-well-understood Audits API for this product's actual scale (Decision 3). |
| P11 Frontend | No | No frontend change. |

**Result**: PASS. No violation requires justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/029-real-zendesk-connector/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `data-model.md` — no schema change. No `contracts/` — no new API endpoint.

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                          # MODIFIED — zendesk_subdomain/_agent_email/_api_token/_poll_interval_hours
│   └── ingestion/adapters/
│       └── zendesk_collector.py           # NEW — ZendeskClient (Protocol), _RealZendeskClient, ZendeskCollector
├── app/worker.py                          # MODIFIED — new job + --run-once entry, same shape as gmail/audio
├── pyproject.toml                         # MODIFIED — httpx moves dev -> main dependencies
└── tests/unit/
    └── test_zendesk_collector.py          # NEW — fake ZendeskClient, no real network
```

**Structure Decision**: Mirrors `specs/028-real-gmail-connector`'s own structure exactly — the
now-established, proven shape for "the next real connector" in this codebase.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
