# Implementation Plan: Project Foundation

**Branch**: `feature/setup-sdd` *(no dedicated `001-*` branch — see spec.md's branch note)* | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-project-foundation/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Scaffold the repository, CI pipeline, Docker Compose stack, and database so every later
build-order phase (`base/Churn-Sentiment-Agent-Product-Specification.md` §16, Phases 2–11)
has a running, reproducible environment and a mechanically-enforced architecture gate to
build into. Technical approach: adopt the stack and repo layout already decided in
`architecture/03-technology-stack.md` and `decisions/02-repo-and-tooling.md` as-is — this
plan's job is to scaffold them, not re-decide them — and resolve the small set of
previously-undecided tooling choices (lint/type-check/test tools) in `research.md`.

## Technical Context

**Language/Version**: Python 3.12 (backend, via `uv`); TypeScript 5.x on Node 20 LTS
(frontend, via Vite/`pnpm`)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), Alembic (backend); React 18,
Vite, Tailwind CSS, Radix primitives (frontend); `import-linter` (CI layer-boundary gate,
`architecture/09-clean-architecture-and-patterns.md`)

**Storage**: PostgreSQL 16, schema provisioned from `data-base/10-ddl-appendix.md` as the
first Alembic revision (`decisions/02-repo-and-tooling.md` §ORM and migrations)

**Testing**: pytest + `hypothesis` (backend, `architecture/03-technology-stack.md`); Vitest
+ React Testing Library + Playwright (frontend, `research.md` §Decision: Frontend test
tooling) — this feature scaffolds the CI job steps and directory structure only; test
*content* is populated starting Phase 2 (frontend) and Phase 4/5 (backend golden-replay/
reconciliation/monotonicity, per spec.md User Story 3)

**Target Platform**: Docker Compose (Linux containers), one stack per client deployment —
`api`, `worker`, `db`, `web` services (`architecture/03-technology-stack.md`)

**Project Type**: Web application (backend + frontend), single monorepo, module-by-module
(M1–M10) package layout with three rings (`domain`/`application`/`adapters`) inside each
module (`decisions/02-repo-and-tooling.md` §Monorepo layout)

**Performance Goals**: N/A directly for this feature (no business-logic request paths
exist yet) — this phase's role is making the later performance targets (`REQ-NFR-01..05`)
measurable, not meeting them itself

**Constraints**: One deployment = one client, no shared infrastructure across deployments
(`REQ-NFR-21`); the static no-LLM-in-scoring check and the Dependency Rule gate must exist
in CI before any scoring/reader code is written (`base/...` §16 Phase 1 rationale;
constitution P2, P8)

**Scale/Scope**: 50k–200k events/year per deployment (`REQ-NFR-05`) — confirms a single
PostgreSQL instance with no message broker is sufficient, which is what the Compose
topology below provisions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| P1 Evidence or It Does Not Exist | Not yet — no findings exist until Phase 5/7 | N/A this phase |
| **P2 The Model Interprets, Code Calculates** | Yes — this feature builds the static no-LLM-in-scoring CI check itself | **Pass** — FR-004 delivers exactly this gate |
| P3 Each Component Refuses to Do the Next One's Job | Partially — the module-by-module scaffold (FR-007) sets up the boundary, no module logic exists yet to violate it | Pass (structural only) |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — the three-ring layout and `import-linter` contracts are this feature's core deliverable | **Pass** — FR-005, FR-007 |
| **P9 Test-First Determinism** | Partially — golden-replay/reconciliation/monotonicity *test content* is Phase 4/5 work, but the CI harness for them is scaffolded here (spec.md User Story 3) | **Pass** — FR-008 scaffolds the harness; no violation, since no scoring code exists yet to test |
| P10 Simplicity Over Speculative Generality (YAGNI) | Yes — repo layout matches `decisions/02-repo-and-tooling.md` exactly; `domain/` folders are **not** created for modules that don't have domain logic yet (e.g. `narrator/`, `experience/`), per that document's explicit note | **Pass** |
| P11 / Full-Stack §2 Frontend Architecture | Minimal — the `web` container is a shell only; no real feature code exists yet | Pass (scaffold matches feature-oriented structure, empty of features) |
| Full-Stack §3 Backend Clean Architecture | Yes | **Pass** — same as P8 |
| Full-Stack §4 Testing Strategy ("near-100% unit coverage" for domain/use cases) | N/A this phase — no domain/use-case code exists yet | N/A, applies starting Phase 3 |
| Full-Stack §5 Security & Quality Gates (CI gates on type-checks/linters; zero-trust backend validation) | Partially — CI gating on lint/type-check is FR-006; zero-trust request validation is N/A (no endpoints exist beyond the health check) | **Pass** for what applies |

**No violations requiring justification.** This feature is intentionally minimal — it
scaffolds structure the later phases will fill, and adds nothing beyond what
`decisions/02-repo-and-tooling.md` already specifies, consistent with P10/YAGNI. Complexity
Tracking table below is empty for that reason.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-foundation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — tooling decisions not already fixed elsewhere
├── data-model.md         # Phase 1 output — states explicitly that no new entities exist yet
├── quickstart.md         # Phase 1 output — clone-to-running-stack validation guide
├── contracts/
│   └── health-check.md   # Phase 1 output — the one interface this phase exposes
└── tasks.md               # Phase 2 output (/speckit-tasks command — not created by /speckit-plan)
```

### Source Code (repository root)

This is a **web application** (backend + frontend), using the monorepo layout already
decided in `decisions/02-repo-and-tooling.md` §Monorepo layout — reproduced here as the
concrete structure this feature scaffolds (module subfolders beyond `auth/` are created
empty or omitted until their own build-order phase needs them, per P10/YAGNI):

```text
backend/
├── app/
│   ├── ingestion/                # M1 — created empty; Phase 3
│   ├── readers/                  # M5, M5a — created empty; Phase 5/7
│   ├── context/                  # M3, M4 — created empty; Phase 3/10
│   ├── scoring/                  # M6 — created empty; Phase 4 (the module the CI
│   │                              #   no-LLM check targets from day one, FR-004)
│   ├── narrator/                 # M7 — created empty; Phase 8
│   ├── experience/               # M8, M9, M10 — created empty; Phase 6/8/9
│   ├── auth/                     # requirements/14-authentication.md — Phase 2
│   ├── main.py                   # FastAPI app entrypoint; exposes GET /health (contracts/health-check.md)
│   └── worker.py                 # APScheduler heartbeat stub — real triggers land Phase 3+
├── migrations/                   # Alembic; first revision imports data-base/10-ddl-appendix.md
├── scripts/
│   └── seed.py                   # Applies data-base/11-seed-data.sql; kept separate from migrations (FR-003)
├── Dockerfile                    # Multi-stage: uv dependency install → runtime; shared by api/worker services
└── tests/
    ├── unit/                     # pytest — empty until Phase 3+
    ├── golden_replay/            # tests/strategy.md — scaffolded, fixture wired Phase 4
    ├── scoring/                  # test_reconciliation.py, test_monotonicity.py — scaffolded, content Phase 4
    └── fixtures/                 # README.md pointing at the future demo/fixtures/meridian-week.json path

frontend/
├── Dockerfile                    # Multi-stage: Vite build → static serve
└── src/
    ├── dashboard/                # M8 — created empty; Phase 2 (shell)/6 (full)
    ├── ask/                      # M9 — created empty; Phase 8
    ├── draft-composer/           # M10 — created empty; Phase 9
    └── profile-editor/           # M3, Post-MVP

workflows/
└── ci.yml                        # lint, type-check, import-linter, no-LLM-in-scoring, golden-replay/
                                   #   reconciliation/monotonicity job steps (empty-safe until Phase 4/5)

.importlinter                     # layer-boundary contracts (decisions/02-repo-and-tooling.md)
docker-compose.yml                # api, worker, db, web services
.env.example
README.md                         # Startup command + schema/seed verification (T019), project overview (T030)
CONTRIBUTING.md                   # Summary of AGENTS.md's non-negotiable rules for new contributors (T031)
```

**Structure Decision**: Option 2 (web application: backend + frontend) from the plan
template, made concrete using the exact module map from `decisions/02-repo-and-tooling.md`
rather than the template's generic `models/services/api` placeholders — this repo's own
module vocabulary (M1–M10) already exists and is used consistently across every other
document, so the plan follows it instead of introducing a second naming scheme.

## Complexity Tracking

*No entries — Constitution Check reported no violations requiring justification.*
