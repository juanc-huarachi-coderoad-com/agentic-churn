# Tasks: Project Foundation

**Input**: Design documents from `specs/001-project-foundation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/health-check.md`, `quickstart.md`

**Tests**: Not separately requested in `spec.md` for this feature — User Story 3 *is* the
test-harness scaffolding itself (placeholder tests proving the CI wiring works), so no
additional TDD-style test tasks are generated on top of it.

**Organization**: Tasks are grouped by user story (`spec.md`) to enable independent
implementation and testing of each story, per `plan.md`'s Project Structure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Maps to `spec.md`'s user stories — US1 (P1), US2 (P2), US3 (P3)
- Every task names an exact file path from `plan.md`'s Project Structure

## Relevant implementation skills

Not invoked during task generation, but worth loading during `/speckit-implement` for the
tasks noted: **fastapi-python** (T008, T014), **sqlalchemy-alembic-expert-best-practices-
code-review** (T009, T011, T012), **multi-stage-dockerfile** (T016, T017),
**vercel-react-best-practices** (T003, T016), **python-design-patterns** (T001, T007's
module-boundary scaffolding).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository scaffold and per-language project initialization — nothing else
can start until these exist.

- [X] T001 Create the monorepo directory structure from `plan.md`'s Project Structure:
      `backend/app/{ingestion,readers,context,scoring,narrator,experience,auth}/`,
      `backend/migrations/`, `backend/tests/{unit,golden_replay,scoring}/`,
      `frontend/src/{dashboard,ask,draft-composer,profile-editor}/` (module folders created
      empty per P10/YAGNI — no `domain/`/`application`/`adapters` subfolders until a module
      has code to put in them)
- [X] T002 Initialize the backend Python project with `uv` in `backend/pyproject.toml`:
      `fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `ruff`,
      `mypy`, `pytest`, `hypothesis` (`research.md` §Decision: Backend lint/format/type-
      check tooling)
- [X] T003 [P] Initialize the frontend project with `pnpm` in `frontend/package.json`:
      Vite + React 18 + TypeScript template, Tailwind CSS, Radix primitives, ESLint,
      Prettier, Vitest, React Testing Library, Playwright (`research.md` §Decision:
      Frontend lint/format/type-check tooling, §Decision: Frontend test tooling)
- [X] T004 [P] Configure Ruff + mypy in `backend/pyproject.toml` (strict mode per
      constitution's Full-Stack Engineering §5 "Code Quality")
- [X] T005 [P] Configure ESLint + Prettier + `tsconfig.json` (strict mode) in `frontend/`

**Checkpoint**: Both projects install their dependencies cleanly; no application code
exists yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infrastructure every user story below depends on.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T006 Create `docker-compose.yml` at the repo root defining the `api`, `worker`, `db`,
      `web` services and their network, per `architecture/03-technology-stack.md`'s Compose
      sketch, with host-side ports for `api`/`db`/`web` read from `.env`-sourced variables
      (default values baked in, no required edits for the non-conflicting case) — FR-010
      (service definitions only — Dockerfiles and healthcheck wiring land in US1)
- [X] T007 [P] Create `.env.example` at the repo root with placeholders for DB credentials
      and the per-deployment encryption key path (`architecture/03-technology-stack.md`
      §Encryption (Phase 1)), plus `API_PORT`/`DB_PORT`/`WEB_PORT` overrides for T006 (FR-010)
- [X] T008 Create the FastAPI app entrypoint in `backend/app/main.py` with a stub
      `GET /health` route returning `{"status": "ok"}` (database check wired in T014,
      `contracts/health-check.md`)
- [X] T009 Initialize Alembic in `backend/migrations/` (`alembic.ini`, `env.py`) wired to an
      async SQLAlchemy engine (`decisions/02-repo-and-tooling.md` §ORM and migrations) —
      no revisions yet
- [X] T010 Create the `workflows/ci.yml` skeleton with job stages (`lint`, `type-check`,
      `test`) and no steps populated yet — US2 and US3 tasks below add the actual gates
      into this file

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 - Reproducible local environment (Priority: P1) — MVP

**Goal**: An engineer can go from `git clone` to a fully running, healthy stack with the
database schema and seed data provisioned exactly as documented.

**Independent Test**: Clone the repo, run the documented startup command, confirm all four
containers report healthy and the database matches `data-base/10-ddl-appendix.md`
table-for-table (`spec.md` User Story 1 Acceptance Scenarios).

### Implementation for User Story 1

- [X] T011 [US1] Write the initial Alembic revision in
      `backend/migrations/versions/0001_initial_schema.py`, importing
      `data-base/10-ddl-appendix.md`'s DDL verbatim as the source of truth
      (`data-model.md` §What this feature is responsible for)
- [X] T012 [US1] Create the SQLAlchemy 2.0 async engine/session setup in
      `backend/app/db.py`, wired into `backend/migrations/env.py` (depends on T009)
- [X] T013 [P] [US1] Create the seed script in `backend/scripts/seed.py`, applying
      `data-base/11-seed-data.sql` — kept separate from the schema migration
      (`decisions/02-repo-and-tooling.md` §ORM and migrations, FR-003)
- [X] T014 [US1] Wire the `SELECT 1` database check into `GET /health` in
      `backend/app/main.py`, returning 503 when unreachable (depends on T008, T012;
      `contracts/health-check.md`)
- [X] T015 [P] [US1] Create the worker service entrypoint stub in `backend/app/worker.py`
      (APScheduler process that starts and stays healthy; real triggers land Phase 3+ of
      the build order)
- [X] T016 [P] [US1] Write a multi-stage `frontend/Dockerfile` (Vite build stage → static
      serve stage)
- [X] T017 [P] [US1] Write a multi-stage `backend/Dockerfile` (uv-based dependency install
      stage → runtime stage) shared by the `api` and `worker` services
- [X] T018 [US1] Wire `api`/`worker`/`db`/`web` build contexts, healthcheck (polling
      `GET /health`), and the `db` data volume into `docker-compose.yml` (depends on T006,
      T016, T017) — also added a one-off `migrate` service running `alembic upgrade head`
      before `api`/`worker` start (spec.md's acceptance scenarios require the schema to
      already be provisioned when the stack reports healthy, not as a separate manual
      step), and a read-only `./data-base:/data-base:ro` mount on `api` so `scripts/seed.py`
      can reach `data-base/11-seed-data.sql` without baking it into the image
- [X] T019 [US1] Document the startup command and the schema/seed verification steps in
      `README.md`, mirroring `quickstart.md` §1 (depends on T011–T018)

**Checkpoint**: `docker compose up` yields a healthy stack with the schema and seed data
provisioned — User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - CI blocks architectural violations automatically (Priority: P2)

**Goal**: A pull request that violates the no-LLM-in-scoring rule or any module's
Dependency Rule fails CI automatically, before a human reviewer has to catch it.

**Independent Test**: Open a PR adding an LLM-client import reachable from
`backend/app/scoring/`, and a separate one importing an adapters module from a domain/
application layer; confirm CI fails each on its specific check (`spec.md` User Story 2
Acceptance Scenarios).

### Implementation for User Story 2

- [X] T020 [P] [US2] Populate `.importlinter` at the repo root with the
      `scoring-domain-purity`, `readers-application-purity`, and `global-dependency-rule`
      contracts from `decisions/02-repo-and-tooling.md` §CI enforcement of the layer
      boundary — the doc's `app.*.adapters` glob sketch isn't literal import-linter
      syntax; used `containers` + an optional `(domain)` layer instead, verified against
      both a clean run and a deliberately-injected `import anthropic` violation
- [X] T021 [US2] Add a `lint-imports` job step to `workflows/ci.yml` running the
      `.importlinter` contracts (depends on T010, T020) — this job's
      `scoring-domain-purity` contract is the mechanical no-LLM-in-scoring check
      (`REQ-NFR-33`; constitution P2)
- [X] T022 [P] [US2] Add `ruff check` and `mypy` job steps for the backend to
      `workflows/ci.yml` (depends on T010, T004) — both verified clean locally
- [X] T023 [P] [US2] Add `eslint` and `tsc --noEmit` job steps for the frontend to
      `workflows/ci.yml` (depends on T010, T005) — both verified clean locally
- [X] T024 [US2] Configure `workflows/ci.yml` to fail the whole pipeline (block merge) if
      any of T021–T023's steps fail — no soft-fail/continue-on-error on any of them
      (depends on T021, T022, T023)

**Checkpoint**: A PR with an architecture-boundary violation is blocked by CI — User
Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Test-harness scaffolding is in place before it's needed (Priority: P3)

**Goal**: The golden-replay, decimal-reconciliation, and monotonicity test locations,
fixture paths, and CI job wiring exist and report status explicitly, even though their
real content is Phase 4/5-of-the-build-order work.

**Independent Test**: Run CI on the empty scaffold; confirm the three job steps execute
against placeholder fixtures and report an explicit "not yet populated" result rather than
being absent or silently skipped (`spec.md` User Story 3 Acceptance Scenarios).

### Implementation for User Story 3

- [X] T025 [P] [US3] Create `backend/tests/golden_replay/test_placeholder.py` — a
      collectable, explicitly-skipped test documenting that golden-replay content lands in
      build-order Phase 4 (`tests/strategy.md`)
- [X] T026 [P] [US3] Create `backend/tests/scoring/test_reconciliation.py` — a collectable,
      explicitly-skipped placeholder for the future `hypothesis`-based decimal-
      reconciliation property tests
- [X] T027 [P] [US3] Create `backend/tests/scoring/test_monotonicity.py` — a collectable,
      explicitly-skipped placeholder for the future `hypothesis`-based monotonicity
      property tests
- [X] T028 [US3] Add a `pytest tests/golden_replay/ tests/scoring/` job step to
      `workflows/ci.yml` that reports the (currently skipped) results explicitly rather
      than omitting these directories from the pipeline — included in the same block-merge
      gate as T024 (a skipped test reports pytest exit 0, so this cannot block merge until
      Phase 4/5 populates real content) (depends on T010, T024, T025–T027) — verified
      locally: `pytest tests/golden_replay/ tests/scoring/` collects and skips all 3
      explicitly, exit code 0
- [X] T029 [P] [US3] Create `backend/tests/fixtures/README.md` pointing at the future
      `demo/fixtures/meridian-week.json` fixture path documented in `tests/strategy.md`,
      noting it is populated in build-order Phase 4

**Checkpoint**: All three user stories are independently functional — Project Foundation
is feature-complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Repo-wide documentation and a final end-to-end validation pass.

- [X] T030 [P] Expand `README.md` with a project overview linking to `AGENTS.md`,
      `requirements/`, and `architecture/` (beyond T019's startup-command section)
- [X] T031 [P] Create `CONTRIBUTING.md` summarizing `AGENTS.md`'s non-negotiable rules for
      new contributors
- [X] T032 Verify the `docker compose down -v` / `up` reprovision path documented in
      `quickstart.md`'s Troubleshooting section actually reproduces a clean schema —
      verified: post-wipe the schema is reprovisioned (migration reapplies automatically)
      but seed data correctly does not persist (0 rows), confirming a genuinely clean
      reprovision rather than a partial one
- [X] T033 Run all of `quickstart.md` end to end, confirm every acceptance scenario in
      `spec.md` passes, and time the clone-to-healthy-stack path against SC-001's
      under-10-minutes threshold (depends on every task above) — all three user stories'
      acceptance scenarios verified against real containers; warm-cache all-healthy time
      was 21s, comfortably inside the 10-minute threshold even accounting for a cold
      base-image pull on a genuinely fresh clone

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phase 3–5)**: All depend on Foundational completing.
  - US1 has no dependency on US2 or US3.
  - US2 has no dependency on US1 or US3 (it only needs T010's CI skeleton).
  - US3 has no dependency on US1 or US2, beyond sharing `workflows/ci.yml` as a file (see
    Parallel Opportunities below).
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Independent — the MVP. Delivers a running, provisioned stack on its own.
- **US2 (P2)**: Independent of US1's *content*, but both eventually run inside the same
  `docker compose`/CI environment — no code dependency either way.
- **US3 (P3)**: Independent of US1/US2's content; shares `workflows/ci.yml` as a file with
  US2 (see below), which is a sequencing note, not a functional dependency.

### Within Each User Story

- Infrastructure/config before the code that depends on it (e.g., T009 Alembic init before
  T011's first revision).
- Docker/CI wiring tasks come after the artifacts they wire together exist.
- Story complete before moving to the next priority, if working sequentially.

### Parallel Opportunities

- All Phase 1 `[P]` tasks (T003–T005) run in parallel once T001–T002 exist.
- Phase 2's T007 runs in parallel with T006/T008/T009/T010.
- US1's T013, T015, T016, T017 run in parallel (different files, no shared dependency
  besides the already-complete Foundational phase).
- US2's T022 and T023 run in parallel (backend vs. frontend CI jobs, different tools).
- US3's T025–T027 and T029 all run in parallel (independent placeholder files).
- **US1, US2, and US3 can be staffed to three different people once Phase 2 is done** —
  the only shared-file friction is `workflows/ci.yml`, which US2's T021–T024 and US3's T028
  both append job steps to; treat that file as a merge point, not a blocking dependency.

---

## Parallel Example: User Story 1

```bash
# Launch these US1 tasks together once Phase 2 is done:
Task: "Create the seed script in backend/scripts/seed.py"
Task: "Create the worker service entrypoint stub in backend/app/worker.py"
Task: "Write a multi-stage frontend/Dockerfile"
Task: "Write a multi-stage backend/Dockerfile"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks everything else).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run `quickstart.md` §1 — a healthy, schema-provisioned stack
   from a clean clone is itself a legitimate, demoable increment (it is literally what the
   rest of the build order, `base/...` §16 Phases 2–11, needs to exist).

### Incremental Delivery

1. Setup + Foundational → environment ready to build into.
2. Add US1 → validate independently → this is the MVP the build order depends on.
3. Add US2 → validate independently → architecture is now mechanically self-enforcing.
4. Add US3 → validate independently → Phase 4/5 of the build order has a harness to write
   real tests into, instead of building one from scratch then.
5. Polish (Phase 6) → repo is ready to hand to the next build-order phase.

### Parallel Team Strategy

With three engineers: one on US1 (environment), one on US2 (CI gates), one on US3 (test
harness) — all three can start the moment Phase 2 (Foundational) is merged, coordinating
only around `workflows/ci.yml`'s shared edits (US2 and US3 both append job steps to it).

---

## Notes

- `[P]` tasks touch different files with no dependency on an incomplete task.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability —
  Setup, Foundational, and Polish tasks carry no story label by design.
- No task in this feature introduces business logic (M1–M10) — anything that looks like it
  might (e.g. module folders in T001) is explicitly scaffolding-only, per the Constitution
  Check in `plan.md` (P10/YAGNI: empty folders, no premature `domain/` subfolders).
- Commit after each task or logical group; stop at any checkpoint to validate a story
  independently before continuing.
