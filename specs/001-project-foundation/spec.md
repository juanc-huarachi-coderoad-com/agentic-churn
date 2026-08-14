# Feature Specification: Project Foundation

**Feature Branch**: `001-project-foundation` *(no `before_specify` git hook is configured in `.specify/extensions.yml`, so no dedicated branch was auto-created — this work continues on the current branch, `feature/setup-sdd`)*

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "Repo scaffold, CI pipeline, Docker Compose stack, and database provisioned from the schema — build-order Phase 1 (`base/Churn-Sentiment-Agent-Product-Specification.md` §16). Nothing else can be built, tested, or demoed without a running database and a CI gate, and the 'no model call in scoring' static check must exist before the first line of scoring code is written."

## Note on scope for this feature

This feature has no end-user-facing behavior — its "users" are the engineers who build
every subsequent phase. That is intentional: `base/Churn-Sentiment-Agent-Product-
Specification.md` §16 names this Phase 1 precisely because every later phase depends on
it existing first. Requirement content is **not** restated here — every functional
requirement below cites the `REQ-<ID>` or architecture document that is its source of
truth, per `requirements/12-traceability-matrix.md`'s discipline.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reproducible local environment (Priority: P1)

An engineer joining the project can go from a clean clone of the repository to a fully
running stack — API, background worker, database, and frontend shell — against a database
provisioned exactly as documented, without hand-configuring infrastructure or guessing at
undocumented setup steps.

**Why this priority**: Every other build-order phase (`base/...` §16) assumes this
environment already exists. Without it, no other feature in this repo can be developed,
tested, or demoed — this is the literal precondition for all subsequent work.

**Independent Test**: Clone the repository on a machine with only Docker installed, run the
documented startup command, and confirm all services report healthy and the database
contains every table from `data-base/10-ddl-appendix.md`. Delivers value on its own: an
engineer can start implementing any later-phase module against a real environment.

**Acceptance Scenarios**:

1. **Given** a clean clone of the repository, **When** an engineer runs the documented
   startup command, **Then** the `api`, `worker`, `db`, and `web` containers (topology per
   `architecture/03-technology-stack.md`) all report healthy.
2. **Given** the stack is running, **When** the engineer inspects the database, **Then**
   its schema matches `data-base/10-ddl-appendix.md` table-for-table and the seed data from
   `data-base/11-seed-data.sql` is present.
3. **Given** the stack is running, **When** the engineer stops and restarts it, **Then**
   the provisioned schema and seed data persist without any manual migration step.

---

### User Story 2 - CI blocks architectural violations automatically (Priority: P2)

A maintainer reviewing a pull request does not have to manually verify that a change
respects the project's non-negotiable architecture rules — CI catches a violation before
the PR can merge.

**Why this priority**: This is the mechanical enforcement of constitution principles P2
("the model interprets, code calculates") and P8 ("Clean Architecture: the Dependency Rule
is law") — both explicitly required to exist *before* any scoring or reader code is
written (`base/...` §16 Phase 1 rationale), not added retroactively.

**Independent Test**: Open a pull request that adds an LLM-client import reachable from
`backend/app/scoring/`, and a separate one that imports an adapters-layer module from a
domain or application layer; confirm CI fails each on the specific check responsible,
independent of any other feature's code existing yet.

**Acceptance Scenarios**:

1. **Given** a pull request that adds an import of an LLM client (directly or
   transitively) reachable from `backend/app/scoring/`, **When** CI runs, **Then** the
   build fails on the static no-LLM-in-scoring check (`REQ-NFR-33`).
2. **Given** a pull request that imports an `adapters` package from a `domain` or
   `application` package in any module, **When** CI runs, **Then** the build fails on the
   import-linter Dependency Rule contract (`architecture/09-clean-architecture-and-
   patterns.md`, `decisions/02-repo-and-tooling.md` §CI enforcement).
3. **Given** a pull request with no architecture-boundary violations, **When** CI runs,
   **Then** lint, type-check, and both layer-boundary checks all pass.

---

### User Story 3 - Test-harness scaffolding is in place before it's needed (Priority: P3)

An engineer beginning Phase 4 (scoring engine) or Phase 5 (deterministic findings) finds
the golden-replay, decimal-reconciliation, and monotonicity test locations, fixture paths,
and CI job wiring already scaffolded — they add test *content* into an existing harness
rather than first building the harness itself.

**Why this priority**: Lower priority than Stories 1–2 because no test content is due
until Phase 4/5, but still part of Phase 1's mandate (`base/...` §16: "the 'no model call
in scoring' static check must exist before the first line of scoring code is written" —
the same reasoning extends to the rest of the regression suite named in `REQ-NFR-27..32`).

**Independent Test**: Run the CI pipeline on the empty scaffold; confirm the golden-replay,
reconciliation, and monotonicity job steps execute (against placeholder/empty fixtures) and
report a clear "not yet populated" result rather than failing or silently skipping.

**Acceptance Scenarios**:

1. **Given** the repository scaffold with no scoring or reader code yet, **When** CI runs,
   **Then** the golden-replay, decimal-reconciliation, and monotonicity job steps
   (`tests/strategy.md`) execute and report their (currently empty) status explicitly,
   rather than being absent from the pipeline.
2. **Given** the fixture path referenced by `tests/strategy.md`
   (`demo/fixtures/meridian-week.json`), **When** an engineer looks for where to add
   golden-replay content in a later phase, **Then** the directory structure and naming
   already match what `tests/strategy.md` documents.

---

### Edge Cases

- What happens when a developer's machine already has a port the Compose stack needs
  (`architecture/03-technology-stack.md`'s `api`/`worker`/`db`/`web` services)? The
  documented startup instructions must surface the conflict clearly rather than failing
  silently.
- What happens when `data-base/10-ddl-appendix.md` is edited but no matching Alembic
  migration is added in the same change? Out of scope for this feature's CI to catch
  mechanically (see Assumptions) — flagged here as a known gap for a later hardening pass.
- What happens when the `.importlinter` contract file itself has a syntax error? CI MUST
  fail closed (block merge) rather than silently skip the layer-boundary check — a
  misconfigured gate must never look like a passing one, per constitution P5 ("admit what
  we cannot see") applied to the CI system itself.
- What happens when `docker compose up` is run against a database volume left over from a
  previous, differently-versioned run? The documented startup path must state how to reset
  cleanly (a documented "wipe and reprovision" step), since a stale volume producing a
  schema mismatch would silently violate `REQ-NFR-09`'s determinism guarantee before any
  feature code even runs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single documented command that starts the full
  local stack (`api`, `worker`, `db`, `web`) matching the topology decided in
  `architecture/03-technology-stack.md`, honoring the one-deployment-per-client isolation
  model (`REQ-NFR-21`).
- **FR-002**: The system MUST provision the PostgreSQL schema as the first Alembic
  migration, generated from `data-base/10-ddl-appendix.md` as the source of truth
  (`decisions/02-repo-and-tooling.md` §ORM and migrations; `data-base/01-database-
  overview.md` design principle 1).
- **FR-003**: The system MUST apply `data-base/11-seed-data.sql` via a dedicated seed
  script, kept separate from schema migrations (`decisions/02-repo-and-tooling.md` §ORM and
  migrations).
- **FR-004**: CI MUST run a check that fails the build if `backend/app/scoring/` contains
  any reachable import of an LLM client, directly or transitively (`REQ-NFR-33`;
  constitution P2).
- **FR-005**: CI MUST enforce the Dependency Rule for every module via declared
  `import-linter` contracts — not a hand-rolled script per module
  (`architecture/09-clean-architecture-and-patterns.md` §Enforcement; constitution P8).
- **FR-006**: CI MUST run lint and type-check jobs on every pull request and block merge on
  failure (`architecture/03-technology-stack.md` §Testing/CI row; constitution
  §Development Workflow & Quality Gates).
- **FR-007**: The repository MUST be scaffolded with the module-by-module, three-ring
  (`domain`/`application`/`adapters`) package layout documented in `decisions/02-repo-and-
  tooling.md` §Monorepo layout, so later phases build into existing structure rather than
  restructuring the repository.
- **FR-008**: CI MUST include job steps for the golden-replay, decimal-reconciliation, and
  monotonicity checks (`tests/strategy.md`), wired to their documented fixture/test
  locations, even though their test content is populated in later phases
  (`REQ-NFR-27..32`).
- **FR-009**: The database schema MUST already include the `users`/`auth_tokens` tables
  (`data-base/12-users-and-auth.md`) so that every "who did this" column added in later
  phases can foreign-key to `users.id` from the start (verbatim rule, `AGENTS.md` §Working
  in this repo).
- **FR-010**: The Compose stack's host-side ports (`api`, `db`, `web`) MUST be overridable
  via `.env` without editing `docker-compose.yml`, so a port conflict on a developer's
  machine has a documented fix rather than requiring a manual file edit (Edge Cases).

### Key Entities

This feature provisions the *containers* for data (schema, migration history, CI
artifacts) — it introduces no new business entities. The full entity set is defined in
`data-base/02` through `data-base/09` and is out of scope to re-describe here; this feature
is complete when that schema exists, byte-for-byte, in a running database.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer can go from cloning the repository to a fully running, healthy
  local stack in under 10 minutes, without manual troubleshooting.
- **SC-002**: 100% of pull requests introducing an LLM import reachable from the scoring
  engine are blocked before merge, with zero reliance on manual code review to catch it.
- **SC-003**: 100% of pull requests violating any module's Dependency Rule (an adapters
  package imported by a domain or application package) are blocked before merge.
- **SC-004**: The database schema can be torn down and re-provisioned from migration
  history alone, reproducing `data-base/10-ddl-appendix.md` exactly, with zero manual SQL.
- **SC-005**: Every subsequent build-order phase (2 through 11) can begin work without
  first modifying the repository's top-level structure, CI configuration, or database
  provisioning path.

## Assumptions

- The technology stack (`architecture/03-technology-stack.md`) and repository layout
  (`decisions/02-repo-and-tooling.md`) are already decided; this feature scaffolds them, it
  does not re-decide them.
- Login/authentication UI and flow (Phase 2, `requirements/14-authentication.md`) and all
  ten modules' business logic (M1–M10) are explicitly out of scope for this feature — only
  the `users`/`auth_tokens` schema exists at this stage, per FR-009.
- A single local/demo Docker Compose deployment is sufficient for this phase; multi-
  environment (staging/production) continuous deployment is out of scope until Phase 11
  (`base/...` §16, "Production Hardening").
- Detecting DDL/migration drift automatically (rather than by review discipline) is out of
  scope for this feature's CI — noted as a known gap under Edge Cases, candidate for a
  later hardening-phase check.
