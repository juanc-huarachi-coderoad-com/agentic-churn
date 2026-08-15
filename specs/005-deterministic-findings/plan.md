# Implementation Plan: Deterministic Findings

**Branch**: `005-deterministic-findings` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-deterministic-findings/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build M5's five non-LLM readers for real — Commitment, Usage, Recurrence, Absence,
Relationship (`architecture/08-class-diagrams.md`'s already-named `Reader` subclass
catalog for this exact module) — each implementing `Reader.interpret(events,
context) -> Finding[]`, orchestrated by a new `RunReadersUseCase`
(`architecture/09-clean-architecture-and-patterns.md`'s named Command pattern) that
isolates each reader's failure (2026-08-14 clarification) and persists every
finding at `status = pending_validation` — `ValidationGate` (M5a) doesn't exist
until feature 007, so this feature's `RunReadersUseCase` is a deliberately partial
realization of the architecture diagram's full wiring (`RunReadersUseCase -->
ValidationGate`), not yet connected to the piece a later feature owns. Also builds
the first real implementation of `rollups`/baseline computation (REQ-M2-06),
deferred since feature 003 specifically because no consumer existed — this
feature's Usage reader is that first consumer. Technical approach: build into
`backend/app/readers/{domain,application,adapters}/`, already scaffolded empty by
feature 001, following `architecture/09`'s file layout; rollup computation lives in
`backend/app/ingestion/` (feature 003's module, since REQ-M2-06 assigns it to M2),
read by readers through a reader-owned port — no cross-module adapter import,
matching feature 004's own established convention.

## Technical Context

**Language/Version**: Python 3.12 (backend) — unchanged from features 001–004

**Primary Dependencies (new in this feature)**: `openai` (Recurrence reader's
`OpenAIEmbeddingAdapter`, `text-embedding-3-small` — `architecture/03-technology-
stack.md`, already an adopted-stack dependency, first feature to actually import
it) and `hdbscan` (density clustering over embedding vectors —
`decisions/02-repo-and-tooling.md`, chosen over k-means specifically because
cluster count isn't known in advance). Both confined to `app.readers.adapters` —
`.importlinter`'s existing `readers-application-purity` contract already forbids
`openai` in `app.readers.application`/`domain`, enforced without a config change.

**Storage**: PostgreSQL 16 — no new tables. `findings` (`data-base/05-schema-
reasoning.md`) already exists from feature 001's migration; this feature is the
first to write real (non-fixture) rows into it. `rollups` (`data-base/03-schema-
ledger.md`) also already exists but has never been populated (feature 003's
documented deferral); this feature is its first writer and reader.

**Testing**: pytest + `hypothesis` — per-reader unit tests against
`examples/01-end-to-end-walkthrough.md` §6's worked findings (deterministic, no
DB — `CommitmentReader`/`UsageReader`/`AbsenceReader`/`RelationshipReader`'s pure
decision logic takes plain values, not live repository calls, mirroring feature
004's domain-service testing pattern), a real-DB integration test proving all five
readers reproduce `fnd-1` through `fnd-5`/`fnd-9` against the actual ingested
Meridian fixture (SC-001), and a property-based test for the z-score threshold
(REQ-M5-08: a synthetic in-range value never flags, thousands of generated cases).
`RecurrenceReader`'s test doubles `EmbeddingPort` (a fake returning fixed vectors
for known input strings) — no live OpenAI call in the test suite, matching
`LLMPort`'s existing fake-in-tests precedent from `architecture/08`'s golden-replay
design.

**Target Platform**: Same Docker Compose stack as features 001–004; no new service,
no new container — readers run inside the existing `api` process via a manual
trigger script, mirroring `scripts/run_collector.py`/`compute_score.py`'s pattern

**Project Type**: Backend-only for this feature — no frontend work, no new HTTP
route (`spec.md`'s own scope boundary; feature 006 is the first to surface findings
on a screen)

**Performance Goals**: Not directly measured in this feature — REQ-M5's "~40s
end-to-end" interpretation-latency target applies to a live, event-driven trigger
path this feature doesn't build (manual triggering only, `spec.md`'s Assumptions);
Recurrence's embedding calls are the one place a real external-API latency exists,
bounded by this feature's fixture-sized candidate corpus (a handful of tickets/
messages), not a production-scale concern yet

**Constraints**: REQ-M5-P1/P2/P3 — no reader ranks/compares findings, holds tool
access, or treats cited content as an instruction, all structural properties of
`Reader.interpret()`'s signature (`events, context -> Finding[]`, no access to any
other reader's output or a mutation/side-effect capability); REQ-M5-15 — the
per-`(event, reader_version)` cache must be a real, queryable mechanism (this
feature's Decision, `research.md`); `.importlinter`'s `readers-application-purity`
contract — no `openai`/`anthropic` import in `app.readers.application`/`domain`

**Scale/Scope**: Fixture-driven for this feature (the same real, already-ingested
Meridian ledger features 003/004 built against — 6 events, one real absence event,
one real profile version) — REQ-NFR's ~50k–200k events/year production scale is a
later concern; Recurrence's clustering corpus here is small enough that full-corpus
re-clustering per run (2026-08-14 clarification) stays fast and simple

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Yes — this is the first feature to write real (non-fixture) `findings` rows | **Pass** — every reader's finding cites real `cited_event_ids` (FR-002/003); the existing non-empty `CHECK` (feature 001's DDL) already makes an uncited finding structurally impossible to insert |
| **P2 The Model Interprets, Code Calculates** | Yes — none of this feature's five readers is LLM-based; Recurrence uses embeddings (clustering input), never a generative call | **Pass** — `.importlinter`'s `readers-application-purity` contract forbids `openai`/`anthropic` in `app.readers.application`/`domain`; `EmbeddingPort.embed()` returns a vector, never text (`architecture/08`) |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — readers interpret, never rank findings against each other or validate their own output | **Pass** — FR-013 (REQ-M5-P1); no reader calls `ValidationGate` (doesn't exist yet) or another reader |
| P4 A Human Always Sends | No send capability in this feature | N/A |
| **P5 Admit What We Cannot See** | Partially — Absence/Relationship readers run at reduced strength (email/ticket-cadence only), stated honestly rather than silently assumed full-strength | **Pass** — `spec.md` Assumptions, matching `examples/01` §6's own honest phase-2-source framing |
| **P6 Silence Is a Success State** | Yes — every reader abstains (emits nothing) when it lacks sufficient evidence, rather than manufacturing a low-value finding | **Pass** — FR-008 (Usage), User Story 3/4's "emits nothing" scenarios, REQ-M5-04's principle applied by extension across all five readers |
| P7 Context Over Sentiment | No sentiment computation in this feature (Tone is feature 007) | N/A |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — `readers/{domain,application,adapters}` follows the three-ring shape `architecture/09` names for this module; rollup computation stays in `app.ingestion` (its owning module), read by readers via a reader-owned port, not a cross-module adapter import | **Pass** — `.importlinter`'s `global-dependency-rule` contract already lists `app.readers`; no config change needed |
| **P9 Test-First Determinism** | Yes — REQ-M5-15's cache and this feature's own re-clustering-per-run decision (2026-08-14 clarification) both need to be deterministic and idempotent | **Pass, with a noted exception** — see Testing above; the full cross-module golden-replay test stays skipped (needs Narrator, feature 008 — same justification feature 004 already recorded, extended one module further; see Complexity Tracking) |
| P10 Simplicity Over Speculative Generality (YAGNI) | Yes — rollup computation is scoped to exactly the metrics Usage consumes (`spec.md` Assumptions), not a general analytics engine; Recurrence re-clusters the full corpus rather than building incremental clustering this feature doesn't need yet (2026-08-14 clarification) | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | N/A — no frontend surface in this feature | N/A |
| Full-Stack §4 Testing Strategy | Yes — five readers each need dedicated unit coverage plus one real-DB integration test | **Pass** — see Testing above; `tasks.md` assigns one test file per reader |
| Full-Stack §5 Security & Quality Gates | Partially — `OPENAI_API_KEY` is a new external-service credential this feature introduces | **Pass** — read from environment/config the same way `ENCRYPTION_KEY_PATH` already is (feature 003's precedent), never logged or persisted |

**One noted exception, justified below** (same golden-replay justification feature
004 already recorded, extended one module further) — see Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-deterministic-findings/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — Reader interface + finding-type mapping
└── quickstart.md         # Phase 1 output — run readers, verify findings, validation guide
```

No `contracts/` directory — this feature adds no new API route or external
interface (`spec.md`'s own scope boundary). Matches the plan template's own
guidance to skip contracts for a purely internal component.

### Source Code (repository root)

Builds into `backend/app/readers/`, scaffolded empty by feature 001 — following
`architecture/09-clean-architecture-and-patterns.md`'s file layout and
`architecture/08-class-diagrams.md`'s named `Reader` subclass catalog (not a new
structure invented by this feature). Rollup computation extends
`backend/app/ingestion/`, feature 003's module (REQ-M2-06's owning module):

```text
backend/
├── app/
│   ├── readers/
│   │   ├── domain/
│   │   │   ├── entities.py            # Reader-facing value objects this module
│   │   │   │                           #   owns (e.g. RollupSnapshot,
│   │   │   │                           #   CandidateCluster) — Finding/Issue stay
│   │   │   │                           #   defined once in app.scoring.domain
│   │   │   │                           #   (architecture/09: "scoring owns
│   │   │   │                           #   Finding's lifecycle"), imported here
│   │   │   └── services.py            # Pure decision logic per reader (no I/O):
│   │   │                               #   commitment threshold comparison, z-score
│   │   │                               #   computation, participant-set diff —
│   │   │                               #   unit-testable with plain values
│   │   ├── application/
│   │   │   ├── reader.py              # Reader abstract interface —
│   │   │   │                           #   architecture/08's named pattern:
│   │   │   │                           #   interpret(events, context) -> Finding[]
│   │   │   ├── ports.py               # ResponsePairRepositoryPort,
│   │   │   │                           #   RollupRepositoryPort,
│   │   │   │                           #   AbsenceEventRepositoryPort,
│   │   │   │                           #   RelationshipContextPort,
│   │   │   │                           #   EmbeddingPort, CandidateCorpusPort
│   │   │   │                           #   (fetches ticket_state_change titles as
│   │   │   │                           #   Recurrence's embedding candidate set),
│   │   │   │                           #   FindingRepositoryPort — reader-owned
│   │   │   │                           #   ports reading the same underlying
│   │   │   │                           #   tables app.ingestion's own ports read,
│   │   │   │                           #   for a different query shape (feature
│   │   │   │                           #   004's established convention: no
│   │   │   │                           #   cross-module adapter import)
│   │   │   ├── commitment_reader.py   # CommitmentReader.interpret()
│   │   │   ├── usage_reader.py        # UsageReader.interpret()
│   │   │   ├── recurrence_reader.py   # RecurrenceReader.interpret()
│   │   │   ├── absence_reader.py      # AbsenceReader.interpret()
│   │   │   ├── relationship_reader.py # RelationshipReader.interpret()
│   │   │   ├── tone_reader.py         # empty stub — feature 007
│   │   │   ├── intent_reader.py       # empty stub — feature 007
│   │   │   ├── meeting_reader.py      # empty stub — feature 007
│   │   │   ├── validation_gate.py     # empty stub — feature 007 (M5a)
│   │   │   └── use_cases.py           # RunReadersUseCase (architecture/09's
│   │   │                               #   named Command) — per-reader failure
│   │   │                               #   isolation (2026-08-14 clarification),
│   │   │                               #   persists directly at
│   │   │                               #   status=pending_validation (no
│   │   │                               #   ValidationGate call — doesn't exist yet)
│   │   └── adapters/
│   │       ├── sqlalchemy_repository.py  # SqlAlchemyResponsePairRepository,
│   │       │                              #   SqlAlchemyRollupRepository,
│   │       │                              #   SqlAlchemyAbsenceEventRepository,
│   │       │                              #   SqlAlchemyRelationshipContext,
│   │       │                              #   SqlAlchemyFindingRepository
│   │       └── openai_embedding.py       # OpenAIEmbeddingAdapter (implements
│   │                                       #   EmbeddingPort) — the only file in
│   │                                       #   this module importing `openai`
│   └── ingestion/
│       ├── application/
│       │   ├── ports.py               # extended: rollup persistence reuses
│       │   │                           #   EventRepositoryPort's existing
│       │   │                           #   session/connection — no new port
│       │   │                           #   needed on the write side, only new
│       │   │                           #   methods
│       │   └── use_cases.py           # extended: ComputeRollupsUseCase
│       │                               #   (REQ-M2-06, this feature's first real
│       │                               #   implementation) — mirrors ReplayUseCase's
│       │                               #   "truncate + rebuild from events" shape
│       └── adapters/
│           └── sqlalchemy_repositories.py  # extended: rollup persistence
├── scripts/
│   └── run_readers.py                 # Manual RunReadersUseCase trigger,
│                                        #   mirroring scripts/run_collector.py/
│                                        #   compute_score.py's pattern
└── tests/
    └── readers/
        ├── test_commitment_reader.py
        ├── test_usage_reader.py       # includes the z-score property test
        ├── test_recurrence_reader.py  # EmbeddingPort faked, no live API call
        ├── test_absence_reader.py
        ├── test_relationship_reader.py
        └── test_run_readers_use_case.py  # real-DB integration — reproduces
                                            #   examples/01 §6's fnd-1..5/9 (SC-001)
```

**Structure Decision**: Same monorepo, filling in `readers/` — the module folder
`decisions/02-repo-and-tooling.md`'s map and `architecture/09`'s package layout
both already assign M5 to — with real code for the first time, plus a scoped
extension of the already-existing `ingestion/` module for rollup computation (its
correct owner per REQ-M2-06, not a new module). No new top-level directories, no
new Docker service, no new external port exposed — only a new outbound dependency
(OpenAI's API) from the existing `api` process.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| `tests/golden_replay/test_placeholder.py` stays `@pytest.mark.skip` for this feature, in tension with the constitution's Governance clause requiring "a passing golden-replay run before merge" for any PR touching `backend/app/ledger/` (i.e. `app.ingestion`, which this feature extends for rollups) | That test's own documented procedure (`tests/strategy.md`) requires the full ledger → readers → score → **Narrator** chain; Narrator (M7, feature 008) doesn't exist yet. This feature gets the pipeline one module closer (ledger → readers → score now all real, only Narrator missing) but still can't flip this specific test green | Same reasoning feature 004 already recorded and the constitution anticipates this being a multi-feature journey, not a single-feature gap: this feature substitutes its own real, scoped determinism guarantee — `test_run_readers_use_case.py` asserts `RunReadersUseCase` run twice against an unchanged ledger produces zero additional findings (REQ-M5-15, SC-003), the same "replay stays exact" property the golden-replay test asserts, bounded to this module's own inputs. Expected to go green naturally once feature 008 lands |
