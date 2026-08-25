# Implementation Plan: Real Gmail Connector

**Branch**: `main` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/028-real-gmail-connector/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add `GmailCollector` (`backend/app/ingestion/adapters/gmail_collector.py`), a new, independent
`Collector` implementation following `AudioCollector`'s exact shape — real OAuth-authenticated
Gmail API reads, per-item failure isolation, idempotency, its own scheduled interval in
`worker.py`, its own `--run-once` entry. `SimulatedCollector` and its JSON fixture are **not
modified in any way** — this is the feature's explicit, non-negotiable constraint (User Story 2).
A small internal `GmailClient` seam isolates the third-party `googleapiclient` library behind two
testable methods (`research.md` Decision 5). The window each cycle reads is derived from the
ledger's own latest `gmail`-sourced event, not a new persisted cursor (Decision 4). No webhook/push
subscription — polling only (Decision 3), consistent with this deployment model having no public
ingress by default.

## Technical Context

**Language/Version**: Python 3.12 — unchanged.

**Primary Dependencies**: `google-api-python-client`, `google-auth`, `google-auth-httplib2` (new,
runtime) — the real Gmail API client and OAuth credential/token-refresh handling.
`google-auth-oauthlib` (new, one-time-script only) — powers the interactive local-server consent
flow in `scripts/generate_gmail_token.py`, which an operator runs once to obtain a refresh token;
not imported by any runtime `app/` code.

**Storage**: PostgreSQL 16 — no schema change. `sources.source_type = 'gmail'` already exists
(shared with `SimulatedCollector`'s fixture items, `research.md` Decision 2); no new table.

**Testing**: pytest, unit-style against a fake `GmailClient` (no real network) — covering
windowing, idempotency-skip-before-fetch, per-item failure isolation, header/body parsing, and the
whole-connection-failure propagation path. `SimulatedCollector`'s own existing test suite
(`tests/unit/test_simulated_collector.py`) is the non-regression proof for FR-005/User Story 2 — it
needs zero changes and must keep passing exactly as-is.

**Target Platform**: Same Docker Compose `worker` service. No new container/service — Gmail
credentials are new environment variables in `.env`, consistent with every other per-deployment
secret already handled this way (`openai_api_key`, `anthropic_api_key`, etc.).

**Project Type**: Web application backend (Python/FastAPI) — no frontend change.

**Performance Goals**: No new latency target — Gmail is not on the ~30-60s automated-pipeline path
(`specs/026`); it runs on its own slower, configurable interval (hourly default, matching
`AudioCollector`'s own configurable-interval precedent), since new email is not the kind of signal
that needs sub-minute freshness.

**Constraints**: Read-only Gmail scope only (FR-002/REQ-M1-P4) — never a scope permitting send,
modify, or delete. Must never touch `SimulatedCollector` (FR-005). First-ever run per mailbox
bounded to a 24-hour lookback, never full history (FR-010).

**Scale/Scope**: One new adapter file, one new settings block (4 fields), one new migration-free
composition-root wiring change in `worker.py`, one new one-time operator script
(`scripts/generate_gmail_token.py`), new unit tests. No `data-model.md` — no schema change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| P1 Evidence or It Does Not Exist | No | No change to citation mechanics — a real Gmail-sourced event cites itself exactly like a simulated one already does. |
| P2 The Model Interprets, Code Calculates | No | No scoring code touched. |
| P3 Each Component Refuses to Do the Next One's Job | Yes | `GmailCollector` only fetches and normalizes (REQ-M1-P1/P2/P3) — no severity/importance judgment, no identity interpretation (that stays `RunCollectorUseCase`'s job, unchanged). |
| **P4 A Human Always Sends** | **Yes — explicitly checked.** | FR-002/REQ-M1-P4: read-only Gmail scope only (`gmail.readonly`), never a scope permitting send/modify/delete — this connector cannot become a covert send capability. |
| P5 Admit What We Cannot See | Yes | FR-006/User Story 3: a whole-connection failure is a visible coverage gap, never indistinguishable from a quiet mailbox — same discipline `AudioCollector`'s `LocalStorageAccessError` propagation already established. |
| P6 Silence Is a Success State | No | Not a dashboard/UI feature. |
| P7 Context Over Sentiment | No | No Tone-reader baseline logic touched. |
| P8 Clean Architecture — the Dependency Rule Is Law | Yes | `GmailCollector`/`GmailClient`/`_RealGmailClient` all live in `app.ingestion.adapters`; `.importlinter`'s `ingestion-application-purity` contract already forbids `googleapiclient`/`google` outside that ring — confirmed still satisfied, no contract change needed. |
| P9 Test-First Determinism | No | Doesn't touch `backend/app/ledger/` or `backend/app/scoring/` — a new `Collector`, same shape as `AudioCollector`, which required no golden-replay changes either. |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | **Yes.** | No webhook/Pub/Sub infra (Decision 3); no new persisted cursor state (Decision 4); no HTML-to-Markdown conversion (Decision 6); no new `source_type` enum value (Decision 2) — every alternative considered and rejected in `research.md` was rejected specifically for adding scope this feature's actual requirement doesn't need. |
| P11 Frontend | No | No frontend change. |

**Result**: PASS. No violation requires justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/028-real-gmail-connector/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `data-model.md` — no schema change. No `contracts/` — no new API endpoint; the only "contract"
is the `Collector` interface, already defined and unchanged.

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                          # MODIFIED — gmail_client_id/secret/refresh_token/poll_interval_hours
│   └── ingestion/adapters/
│       └── gmail_collector.py             # NEW — GmailClient (Protocol), _RealGmailClient, GmailCollector
├── app/worker.py                          # MODIFIED — new job + --run-once entry, same shape as _collect_audio
├── scripts/
│   └── generate_gmail_token.py            # NEW — one-time, interactive, operator-run OAuth consent flow
└── tests/unit/
    └── test_gmail_collector.py            # NEW — fake GmailClient, no real network
```

**Structure Decision**: Mirrors `specs/019-meeting-audio-ingestion`'s own structure exactly (one
new adapter file implementing `Collector`, one `worker.py` wiring change, one settings block) — the
established, proven shape for "the first real connector for source X" in this codebase.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
