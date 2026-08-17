# Implementation Plan: Production Hardening

**Branch**: `011-production-hardening` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/011-production-hardening/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build-order Phase 11 ("Hardening") — the six items the base product spec's own §16 build order
names for this phase, translated 1:1 from `spec.md`'s six user stories. Unlike every prior
feature (one working slice), this phase is deliberately six loosely-coupled hardening/breadth
items shipped together because the base spec bundles them as one phase, not because they share
one code path. Each is independently implementable and independently testable, per
`spec.md`'s own priority ordering:

1. **Retention/crypto-shredding** (P1) — `research.md` Decision 1's real, plan-time-discovered
   finding: the MVP's single deployment-wide Fernet key can't selectively shred by age at all.
   Fixed by moving to daily key-rotation buckets (`data_key_ref` = ingestion date), a new
   `KeyStorePort`/`FileKeyStore`, and a new scheduled job in `app.worker` using the
   already-provisioned, previously-unused `shredder_role` DB grant.
2. **RBAC** (P2) — one new dependency, `require_full_access`, applied to the seven existing
   write-capable routes; `TokenRecord`/`CurrentUser` gain `role` (Decision 2). Zero new routes.
3. **Observability** (P3) — a new, deliberately thin `app/observability/` adapters-only package
   (Decision 6) instrumenting the four operation types FR-009 names, at their existing call
   sites, with zero port/use-case signature changes.
4. **Weight recalibration** (P4) — one new admin-only route
   (`PATCH /api/admin/finding-types/{finding_type}`) firing the already-designed but
   never-used `score_runs.trigger = weight_edit_replay` path (Decision 3).
5. **Profile editor UI** (P5) — one new route, `POST /api/profile`, that is a second front door
   to the already-existing, unmodified `SubmitProfileUseCase` (Decision 4); the frontend fills
   in `frontend/src/profile-editor/`'s empty, feature-001-scaffolded slot.
6. **Post-MVP source connectors** (P6) — three new `_normalize_*` functions extending the
   already-proven `SimulatedCollector` fixture pattern (Decision 5, a deliberate rejection of
   building this codebase's first live external API integration), plus a new `MeetingReader`
   and Absence/Relationship reading the newly-available Slack-sourced events.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript + React 18 (frontend) — unchanged from
every prior feature. Touches both sides of the stack, like 006/008/009/010.

**Primary Dependencies (new in this feature)**: `opentelemetry-sdk` +
`opentelemetry-exporter-otlp` (backend, User Story 3 only — `architecture/03-technology-stack.
md`'s already-named Phase 2 addition, adopted now for the first time). No new frontend
package — the profile editor reuses React Hook Form + Zod, already adopted per constitution
P11.

**Storage**: PostgreSQL 16. One migration, three new tables (`retention_job_runs`,
`finding_type_config_changes`) plus the `shredder_role` grant already present in the DDL since
feature 001 (unused until now) — see `data-model.md`. No existing table's column shape changes;
`data_key_ref`'s *semantics* change (Decision 1) without a type change.

**Testing**: pytest + `hypothesis` (backend), Vitest (frontend). `KeyStorePort`'s bucket-
resolution logic and `compute_weight`-adjacent config-version bump are pure and unit-tested
with plain asserts, matching every prior feature's precedent for domain-pure logic. A real-DB
test seeds an aged event, runs the retention job, and asserts `body_encrypted IS NULL` plus
`retention_job_runs` state — the same "assert against the real, running Postgres" discipline
`tests/strategy.md` already establishes, not a mocked key store. RBAC gets one parametrized
test per route in `contracts/rbac.md`'s table (403 for `account_executive`, 200/204 for every
other existing role, no regression). The static no-LLM-import scan
(`test_no_llm_imports.py`, feature 010's precedent) is re-run to confirm `app.observability`
and `app.scoring`'s new weight-change code introduce no LLM import into scoring's domain/
application rings.

**Target Platform**: Same Docker Compose stack as features 001–010, plus one new optional
service for the OTel collector/exporter backend (User Story 3) — `docker-compose.yml` gains
one service, no existing service's image or port changes.

**Project Type**: Web application — backend (Python/FastAPI) and frontend (React/TypeScript)
both change, like every full-stack feature since 002.

**Performance Goals**: FR-001's daily retention job has no latency budget of its own (an
overnight batch job, not a request-path operation) but must complete well inside its 24-hour
recurrence window even at REQ-NFR-05's upper bound (200k events/year ≈ 550/day) — trivial at
that volume for a single-column `UPDATE ... WHERE data_key_ref = ANY(...)`. FR-010's
observability goal is diagnostic, not a new latency target — `REQ-NFR-01…03`'s existing targets
are what's being measured, not raised or lowered.

**Constraints**: FR-015 (weight changes never retroactively alter an already-computed
`score_run`) is structural, not a convention — enforced by `score_runs` already being
insert-only (existing `app_role` grant, unchanged) and `finding_type_config_changes` never
being read by `RecomputeScoreUseCase`, only by the admin audit view. FR-024 (zero behavior
change for a client with no Post-MVP source connected) is verified by re-running feature 010's
existing quickstart unchanged, not a new assertion invented for this feature.

**Scale/Scope**: Same fixture-driven Meridian deployment every prior feature validates against
— `demo/fixtures/meridian-week.json` gains three new arrays (Decision 5) but the existing
`gmail`/`zendesk`/`warehouse` arrays are untouched, so every prior feature's own quickstart
continues to reproduce unchanged (the FR-024 regression check above).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Yes, indirectly — a crypto-shredded event's citation metadata (source, timestamp, participants) survives shredding; only the message body itself becomes unrecoverable, so a finding never loses its evidence *link*, only the underlying text a human could re-read (FR-004) | **Pass** |
| **P2 The Model Interprets, Code Calculates** | Yes — `UpdateFindingTypeWeightUseCase` and the retention job are both plain arithmetic/I-O, zero LLM calls; the new `MeetingReader` (User Story 6) is the sixth LLM-backed reader, following `ToneReader`/`IntentReader`'s existing precedent exactly, still zero LLM import in `app.scoring` | **Pass** — `test_no_llm_imports.py` re-run, `.importlinter`'s `scoring-domain-purity` contract untouched |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — the retention job only destroys keys and nulls ciphertext, never judges *what* to keep; RBAC only gates route access, never alters response content; the weight-change route only writes config, never recomputes scoring math itself (delegates to the existing `RecomputeScoreUseCase`, unchanged) | **Pass** |
| **P4 A Human Always Sends** | N/A — no messaging capability touched by this feature | **N/A** |
| **P5 Admit What We Cannot See** | Yes — a shredded message body is visibly marked unavailable in the evidence trace (FR-004), never silently blank or fabricated; a Post-MVP source that isn't connected leaves the dashboard exactly as honest as Phase 1's "reduced"/"still learning" states already are (FR-024) | **Pass** |
| **P6 Silence Is a Success State** | Yes — connecting zero Post-MVP sources produces zero new dashboard noise (FR-024); an account executive's read-only dashboard shows the same near-empty healthy state a CS lead sees, never a synthesized "AE-specific" concern | **Pass** |
| **P7 Context Over Sentiment** | Yes, for the new Meeting reader only — it compares against baseline the same way Tone already does, no universal sentiment scale introduced | **Pass** |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — every new class lands in its module's existing ring structure (`app.ingestion.application.ports.KeyStorePort`, `app.scoring.application.use_cases.UpdateFindingTypeWeightUseCase`, `app.auth.application.dependencies.require_full_access`, `app.readers.application.meeting_reader`); `app.observability` is deliberately adapters-only (Decision 6), never imported by any other module's domain/application ring, only by composition-root/adapter call sites. **`/speckit-analyze` finding C1, resolved**: `EncryptionKeyError` (defined in `app.ingestion.adapters.encryption`) is caught at the adapter layer only — the evidence-read repository implementation translates it to a plain `body_available: bool` field before it ever reaches `GetEvidenceTraceUseCase`; the application layer never imports the adapter's exception type, avoiding the exact class of violation feature 008's `narration_v1.py` incident already hit once (`tasks.md` T017) | **Pass** — `.importlinter`'s `global-dependency-rule` contract needs one new `source_modules` line for `app.observability` if it's given its own contract entry (see Complexity Tracking); no existing contract weakens |
| **P9 Test-First Determinism** | Yes — FR-015's determinism guarantee is tested explicitly (quickstart.md User Story 4 step 5): a `score_run` computed before a weight change is fetched again after the change and asserted byte-identical. Golden-replay/reconciliation/monotonicity suites are re-run unchanged to confirm none of the six user stories touch `backend/app/scoring/domain/` or `backend/app/ingestion/domain/hash_chain.py`'s hashed fields (Decision 1 explicitly keeps `data_key_ref`/`body_encrypted` outside the hash chain's canonical input, unchanged from `data-base/03-schema-ledger.md`) | **Pass — no Complexity Tracking exception** |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | Yes — Decision 5 explicitly rejects building this codebase's first live external API integration in favor of extending the already-proven fixture pattern; Decision 6 explicitly rejects a full three-ring `app.observability` module for a concern with no business rule to isolate; the weight-recalibration route (Decision 3) is deliberately scoped to `base_points` only, not a general config editor (`contracts/weight-recalibration.md`'s "Note on scope") | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | Yes — `frontend/src/profile-editor/` follows the same feature-oriented structure `frontend/src/evidence/` established in feature 010 (React Hook Form + Zod, TanStack Query, no scattered fetches) | **Pass** |
| Full-Stack §4 Testing Strategy | Yes — pure-function unit coverage (key-bucket resolution, weight-change validation) plus real-DB/real-route integration tests per story, matching every prior feature's shape | **Pass** — see Testing above |
| Full-Stack §5 Security & Quality Gates | Yes — `changed_by_user_id`/every new ownership column sourced from the bearer token, never the request body; the `403` for a blocked account executive is a generic, non-technical message (`contracts/rbac.md`), never a raw permission-system detail; every role-gated authorization decision (`require_full_access`, `require_admin`) emits a structured `access_decision` log line satisfying FR-008 (`/speckit-analyze` finding G1, resolved — `tasks.md` T021/T031), never a silent allow/deny | **Pass** |

**No violations requiring justification.** The one design choice worth flagging for visibility
(not because it needs justifying against a principle) is `app.observability`'s deliberately
incomplete ring structure — documented in Complexity Tracking below as a *reduction* in
structure relative to every other module, not an addition of complexity.

**Post-`/speckit-clarify` note (2026-08-16)**: Three questions resolved during clarification
(retention job cadence → daily; weight-change authorization → `admin` role only; retention job
failure handling → alert + auto-retry) — see spec.md's Clarifications section. All three are
reflected in this plan's Technical Context/Constitution Check without further correction needed
during this planning pass — unlike feature 010, no clarified answer needed revision once the
real shipped code was read.

**Post-`/speckit-analyze` note (2026-08-16)**: 9 findings (3 HIGH, 2 MEDIUM, 1 LOW-MEDIUM, 2 LOW,
plus one LOW terminology nit), all fixed before implementation — no CRITICAL findings, so this
was a remediation pass, not a blocker. Two real, previously-undiscovered gaps: FR-008 (record
role at authorization time) had zero task coverage (G1, fixed by adding a structured
`access_decision` log line to `require_full_access`/`require_admin`, `tasks.md` T021/T031); the
"collector run" and "dashboard-load" operations FR-009/FR-010/FR-011/SC-003 explicitly name were
never actually wrapped by any US3 tracing task (G2, fixed by new tasks T027a/T029a). One design
correction: FR-004a originally made US1 depend on US3's tracing to satisfy its own "alert"
requirement, contradicting US1's independent-MVP claim (I1) — fixed by having US1's `T015` log
the failure independently via standard `logging`, with US3's `T027` demoted to a strict
enhancement layered on top, not a prerequisite (this also fixed I2, T027's now-correct removal of
its `[P]` marker). See the analysis session's full report for C1 (an `EncryptionKeyError`
layer-boundary risk, fixed in `tasks.md` T017) and the remaining lower-severity wording fixes
(U1, U2, L1) applied directly to `spec.md`/`plan.md`.

## Project Structure

### Documentation (this feature)

```text
specs/011-production-hardening/
├── plan.md                        # This file
├── research.md                    # Phase 0 output — 6 decisions, one per user story,
│                                    #  3 of which correct real gaps between shipped code
│                                    #  and the schema/architecture docs' stated design
│                                    #  intent (Decisions 1, 2, 5)
├── data-model.md                   # Phase 1 output — 2 new tables, 1 changed-semantics
│                                    #  column, 1 application-layer shape change, fixture
│                                    #  additions; zero existing-table shape changes
├── contracts/
│   ├── profile-editor.md           # POST /api/profile (new)
│   ├── weight-recalibration.md     # PATCH /api/admin/finding-types/{finding_type} (new)
│   └── rbac.md                     # require_full_access applied to 7 existing routes
│                                    #  (no new route)
└── quickstart.md                   # Phase 1 output — one validation sequence per user
                                     #  story, all against the real containerized stack
```

### Source Code (repository root)

Touches six of the eight existing backend modules (`ingestion`, `auth`, `scoring`, `context`,
`readers`, plus the new `observability` package) and one frontend feature directory. No module
is created from scratch except `app/observability/` (deliberately adapters-only, Decision 6).

```text
backend/
├── app/
│   ├── observability/               # NEW package — adapters-only, no domain/application
│   │   └── adapters/
│   │       └── tracing.py           # NEW: OTel SDK setup (composition-root call),
│   │                                 #   traced() context-manager helper
│   ├── ingestion/
│   │   ├── application/
│   │   │   ├── ports.py             # extended: KeyStorePort
│   │   │   └── use_cases.py         # NEW: RunRetentionUseCase (FR-001/002/003/004a)
│   │   └── adapters/
│   │       ├── key_store.py         # NEW: FileKeyStore (daily-bucket Fernet keys),
│   │       │                         #   implements KeyStorePort
│   │       ├── encryption.py        # NEW class: BucketedFernetEncryption (same
│   │       │                         #   EncryptionPort interface, zero signature
│   │       │                         #   change at any call site — Decision 1);
│   │       │                         #   existing FernetEncryption class kept, unused
│   │       │                         #   after the swap, not deleted this feature
│   │       ├── simulated_collector.py  # extended: _normalize_slack, _normalize_csat,
│   │       │                             #   _normalize_calendar (Decision 5)
│   │       └── sqlalchemy_repositories.py  # extended: retention_job_runs read/write
│   ├── db.py                        # extended: shredder_session_factory (Decision 1) —
│   │                                  #   connects as shredder_role, the retention job's
│   │                                  #   only writer of body_encrypted/payload_encrypted
│   ├── auth/
│   │   ├── application/
│   │   │   ├── ports.py             # extended: TokenRecord.role
│   │   │   └── dependencies.py      # extended: get_current_user threads role through;
│   │   │                             #   NEW: require_full_access
│   │   └── adapters/
│   │       └── sqlalchemy_repository.py  # extended: get_by_hash query gains
│   │                                       #   JOIN users ON users.role
│   ├── scoring/
│   │   ├── application/
│   │   │   ├── ports.py             # extended: FindingTypeConfigWritePort
│   │   │   └── use_cases.py         # NEW: UpdateFindingTypeWeightUseCase
│   │   └── adapters/
│   │       ├── sqlalchemy_repository.py  # extended: finding_type_config UPDATE,
│   │       │                               #   finding_type_config_changes INSERT
│   │       └── weight_router.py     # NEW: PATCH /api/admin/finding-types/{finding_type}
│   ├── readers/
│   │   └── application/
│   │       └── meeting_reader.py    # FILLED IN — an empty stub since feature 005,
│   │                                  #   not a new file (`/speckit-analyze` finding
│   │                                  #   L1): MeetingReader (Decision 5) mirrors
│   │                                  #   tone_reader.py/intent_reader.py's shape;
│   │                                  #   consent-gated per FR-023
│   ├── context/
│   │   └── adapters/
│   │       └── profile_router.py    # extended: POST /api/profile (Decision 4) —
│   │                                  #   reuses SubmitProfileUseCase unmodified
│   ├── worker.py                    # extended: registers the retention job on the
│   │                                  #   existing APScheduler instance, alongside
│   │                                  #   absence detection / hourly score recompute
│   └── main.py                      # extended: registers weight_router; wires
│                                      #   app.observability's tracing setup;
│                                      #   swaps get_current_user → require_full_access
│                                      #   on the 7 routes contracts/rbac.md names
└── tests/
    ├── unit/
    │   ├── test_key_store.py                    # NEW — pure bucket-resolution logic
    │   ├── test_update_finding_type_weight_use_case.py  # NEW — ports faked
    │   ├── test_meeting_reader.py                # NEW — consent-gating, LLMPort faked
    │   └── test_no_llm_imports.py                # extended: scans app.observability,
    │                                               #   app.scoring's new weight-change
    │                                               #   code path too
    ├── ingestion/
    │   └── test_retention_real_db.py             # NEW — real-DB: seed aged event,
    │                                               #   run job, assert body_encrypted
    │                                               #   IS NULL + retention_job_runs state
    ├── auth/
    │   └── test_rbac_real_db.py                  # NEW — parametrized over
    │                                               #   contracts/rbac.md's route table
    └── scoring/
        └── test_weight_recalibration_real_db.py  # NEW — real-DB: weight change →
                                                     #   weight_edit_replay → prior run
                                                     #   unchanged (FR-015)

frontend/
└── src/
    └── profile-editor/               # FIRST REAL CONTENT — was .gitkeep since feature 001
        ├── profile-editor-form.tsx   # NEW: React Hook Form + Zod
        ├── profile-editor-form.test.tsx  # NEW
        ├── use-profile.ts            # NEW: GET/POST /api/profile, TanStack Query
        └── schema.ts                 # NEW: Zod schema matching contracts/profile-editor.md

architecture/07-api-spec.md           # extended: POST /api/profile marked implemented
                                        #   (was "Post-MVP" placeholder text);
                                        #   PATCH /api/admin/finding-types/{finding_type}
                                        #   added to the route table
data-base/03-schema-ledger.md         # extended: data_key_ref's "permanent reference"
                                        #   note gains the daily-bucket scheme (Decision 1)
data-base/12-users-and-auth.md        # extended: "No role-based access control" Post-MVP
                                        #   note removed — this feature is that Post-MVP
architecture/03-technology-stack.md   # extended: Observability row's "Phase 2 addition"
                                        #   marked adopted, this feature
```

**Structure Decision**: Same monorepo, six modules extended in place plus one new
deliberately-thin `app/observability/` package (Decision 6) — no new top-level directory
beyond it, no service consolidation or split. `docker-compose.yml` gains one optional service
(an OTel collector/exporter backend for User Story 3); every other service's image/port is
unchanged. `frontend/src/profile-editor/` — scaffolded empty since feature 001 specifically
for this moment (`.gitkeep`'s own comment names "when this module's own phase starts") — gets
its first real content, following `frontend/src/evidence/`'s feature-010 precedent for the same
kind of long-reserved slot.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified — none do. The one item
> below is flagged for reviewer visibility, not because it needs justifying against a
> principle.

| Item | Why it looks unusual | Why it's not a violation |
|---|---|---|
| `app/observability/` has no `domain/` or `application/` ring | Every other module in this codebase follows the full three-ring structure `decisions/02-repo-and-tooling.md` describes | That same document explicitly notes "not every module needs all three rings on day one," citing `narrator/`/`experience/` as existing thin examples — tracing has no business rule to isolate behind a port, so adding one would be the "speculative abstraction layer" P10 already tells this codebase not to build. If a future feature ever needs to unit-test tracing *decisions* (e.g. sampling policy as a business rule), that's the moment to add the missing rings, not before |
