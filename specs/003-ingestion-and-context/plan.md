# Implementation Plan: Ingestion and Context

**Branch**: `feature/setup-sdd` *(no dedicated `003-*` branch — see spec.md's branch note)* | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-ingestion-and-context/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement the client profile (M3), event ledger (M2), and signal collectors (M1) for
real — versioned, multiplier-bearing profile context; an append-only, hash-chained,
business-hours-aware event ledger; and a `Collector` interface proven end to end by a
`SimulatedCollector` reading a new fixture derived from `examples/01-end-to-end-
walkthrough.md`. Technical approach: build into `backend/app/ingestion/` (M1+M2) and
`backend/app/context/` (M3) — both already scaffolded empty by feature 001 — resolving
encryption, hash-chain, business-hours, and identity-resolution decisions in
`research.md`.

## Technical Context

**Language/Version**: Python 3.12 (backend) — unchanged from features 001–002

**Primary Dependencies (new in this feature)**: `cryptography` (Fernet encryption,
`research.md`), `PyYAML` (client profile parsing) — no new frontend dependencies, this
feature has no UI surface

**Storage**: PostgreSQL 16 — no schema change; every table this feature touches
(`client_profile_versions`, `stakeholders`, `product_areas`, `commitments`,
`profile_history_entries`, `sources`, `collector_runs`, `coverage_reports`,
`identity_map`, `raw_envelopes`, `events`, `event_threads`, `response_pairs`) already
exists from feature 001's migration and is read/written for real for the first time

**Testing**: pytest — hash-chain round-trip (write in Python, verify via the DB's own
`verify_hash_chain()` function), business-hours arithmetic against `examples/01`'s exact
worked numbers, profile validation (accept/reject cases), `SimulatedCollector`
idempotency (run twice, assert zero duplicates), identity resolution (resolved vs.
unresolved), redaction, coverage reporting, absence detection

**Target Platform**: Same Docker Compose stack as features 001–002, plus a new
`./secrets:/app/secrets:ro` volume mount on `api`/`worker` for the encryption key file
(`research.md`)

**Project Type**: Backend-only for this feature — no frontend work; same monorepo

**Performance Goals**: Not directly applicable — this feature has no user-facing
request path yet (M8 dashboard doesn't consume ledger data until feature 006)

**Constraints**: `REQ-M2-P1`/`REQ-M2-P2` — the ledger never stores a judgment and is
never mutated outside the crypto-shredding exception already enforced by feature 001's
DB trigger; `REQ-M1-P4` — message bodies are encrypted before storage, no exception;
`REQ-M3-P1`/`REQ-M3-P2` — the profile carries multiplier *values* only, never scoring
logic, and multipliers are always human-authored, never inferred

**Scale/Scope**: Fixture-driven for this feature (one week of Meridian's Phase-1
data, ~6 events, including one exercising redaction) — the 50k–200k events/year target
(`REQ-NFR-05`) is a production concern for real adapters, not something this feature's
fixture needs to demonstrate at scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Not yet — no findings exist until Phase 5/7; this feature produces the events findings will eventually cite | N/A this phase (forward dependency, not a violation) |
| P2 The Model Interprets, Code Calculates | No LLM code anywhere in this feature | N/A |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — collectors never assign severity (`REQ-M1-P1`), the ledger never stores a judgment (`REQ-M2-P1`), the profile never contains scoring logic (`REQ-M3-P1`) | **Pass** — FR-005 (ledger facts only), profile schema has no formula fields |
| P4 A Human Always Sends | No send capability anywhere in this feature | N/A — nothing to violate |
| **P5 Admit What We Cannot See** | Yes — coverage reports exist for every run including failed ones (`REQ-M1-07/08`); unresolved identity is a first-class, honestly-reported state, never a guess | **Pass** — FR-011, FR-014 |
| P6 Silence Is a Success State | Partially — the absence collector is the mechanism that eventually powers this at the UI layer; this feature only detects and records absence, doesn't render it | N/A this phase (no UI in this feature) |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — `ingestion/{domain,application,adapters}` and `context/{domain,application,adapters}` follow the same three rings as `auth`/`scoring`; both containers already listed in `.importlinter`'s `global-dependency-rule` contract from feature 001 | **Pass** — no `.importlinter` change needed |
| **P9 Test-First Determinism** | Yes — this is the first feature to write real code into the module the golden-replay test (feature 001's placeholder) will eventually exercise; hash-chain and response-pair arithmetic must be exactly reproducible | **Pass** — hash chain verified against the DB's own independent function; business-hours arithmetic tested against `examples/01`'s exact hand-checkable numbers |
| P10 Simplicity Over Speculative Generality (YAGNI) | Yes — deferred rollups (no consumer yet), deferred fuzzy-match identity suggestion (no UI yet), minimal thread stitching (one heuristic, not exhaustive) — all explicit in spec.md's scope notes | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | N/A — this feature has no frontend surface | N/A |
| Full-Stack §4 Testing Strategy | Yes — real business logic (domain services) for the first time | **Pass** — hash-chain, business-hours (including a weekend-boundary case), profile validation, replay, redaction, and encryption each have a dedicated test task; see `tasks.md` |
| Full-Stack §5 Security & Quality Gates | Yes — message-body encryption, the exclusions-based redaction, and fail-loud-on-missing-key are exactly this section's "actionable error normalization without exposing secrets" applied to data at rest | **Pass** — FR-012, FR-013 |

**No violations requiring justification.** Complexity Tracking table below is empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-ingestion-and-context/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — entity/relationship notes beyond the schema docs
├── quickstart.md         # Phase 1 output — profile submission + collector run validation guide
├── contracts/
│   └── profile-reload.md # POST /api/profile/reload (architecture/07-api-spec.md's existing contract)
└── tasks.md               # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

Builds into `backend/app/ingestion/` and `backend/app/context/`, both scaffolded empty
by feature 001 — only new/changed files shown:

```text
backend/
├── app/
│   ├── ingestion/
│   │   ├── domain/
│   │   │   ├── hash_chain.py         # Canonical serialization + SHA-256 (data-base/03)
│   │   │   ├── business_hours.py     # Elapsed-business-hours calculator
│   │   │   └── envelope.py           # Envelope value object, idempotency key derivation
│   │   ├── application/
│   │   │   ├── ports.py              # EventRepositoryPort, CoverageRepositoryPort,
│   │   │   │                          #   ClientProfileContextPort (identifiers + exclusions),
│   │   │   │                          #   CommitmentLookupPort
│   │   │   ├── collector.py          # Collector ABC — fetch/normalize/resolve_identity/
│   │   │   │                          #   emit_envelope (Template Method, architecture/09)
│   │   │   └── use_cases.py          # RunCollectorUseCase, AppendEventUseCase,
│   │   │                              #   DetectAbsenceUseCase
│   │   └── adapters/
│   │       ├── simulated_collector.py
│   │       ├── encryption.py         # Fernet load/encrypt/decrypt (research.md)
│   │       └── sqlalchemy_repositories.py
│   ├── context/
│   │   ├── domain/
│   │   │   └── profile_schema.py     # Pydantic model + signs_renewal validator (REQ-M3-07)
│   │   ├── application/
│   │   │   ├── ports.py              # ClientProfileRepositoryPort (write side)
│   │   │   └── use_cases.py          # SubmitProfileUseCase
│   │   └── adapters/
│   │       ├── yaml_profile_loader.py
│   │       ├── profile_router.py     # POST /api/profile/reload
│   │       └── sqlalchemy_repository.py
│   ├── worker.py                     # updated: absence-collector heartbeat job registered
│   └── main.py                       # updated: profile router included, encryption key
│                                      #   loaded at startup (fail loud if missing)
├── scripts/
│   └── run_collector.py              # Manual SimulatedCollector trigger (research.md)
└── tests/
    └── unit/
        ├── test_hash_chain.py
        ├── test_business_hours.py
        ├── test_profile_validation.py
        ├── test_simulated_collector.py
        └── test_absence_collector.py

demo/
└── fixtures/
    └── meridian-week.json            # New — Phase-1 subset of examples/01's scenario

docker-compose.yml                    # updated: ./secrets:/app/secrets:ro mount
.env.example                          # updated: ENCRYPTION_KEY_ID
```

**Structure Decision**: Same monorepo, extending `ingestion/` and `context/` — the two
module folders decisions/02-repo-and-tooling.md's map assigns M1+M2 and M3 to,
respectively — with real code for the first time. No new top-level directories.

## Complexity Tracking

*No entries — Constitution Check reported no violations requiring justification.*
