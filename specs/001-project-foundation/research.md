# Phase 0 Research: Project Foundation

Most of this feature's technical decisions are **already made** in `architecture/03-
technology-stack.md` and `decisions/02-repo-and-tooling.md` — this document resolves the
handful of choices those files leave open (mainly lint/type-check/test tooling), rather
than re-researching what's already decided. Each entry cites its source or states the new
decision and why.

## Already-decided (cited, not re-researched)

| Area | Decision | Source |
|---|---|---|
| Backend language/framework | Python 3.12, FastAPI | `architecture/03-technology-stack.md` |
| Backend package manager | `uv` | `decisions/02-repo-and-tooling.md` §Package managers |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic, first migration = straight import of `data-base/10-ddl-appendix.md` | `decisions/02-repo-and-tooling.md` §ORM and migrations |
| Database | PostgreSQL 16 | `architecture/03-technology-stack.md` |
| Frontend framework/tooling | React 18 + TypeScript + Vite, `pnpm` | `architecture/03-technology-stack.md`, `decisions/02-repo-and-tooling.md` §Package managers |
| Frontend styling | Tailwind CSS + Radix-based components (shadcn/ui) | `architecture/03-technology-stack.md`, constitution P11 |
| Hosting | Docker Compose, one stack per client (`api`, `worker`, `db`, `web`) | `architecture/03-technology-stack.md` |
| Backend test framework | pytest + `hypothesis` | `architecture/03-technology-stack.md` |
| CI platform | GitHub Actions | `architecture/03-technology-stack.md` |
| Layer-boundary enforcement | `import-linter`, `.importlinter` config at repo root | `architecture/09-clean-architecture-and-patterns.md`, `decisions/02-repo-and-tooling.md` |
| Repo layout | Module-by-module (M1–M10), three rings (`domain`/`application`/`adapters`) inside each | `decisions/02-repo-and-tooling.md` §Monorepo layout |

## Decision: Backend lint/format/type-check tooling

**Decision**: **Ruff** for linting and formatting, **mypy** for static type-checking.

**Rationale**: No prior document names a specific tool — `architecture/03-technology-
stack.md`'s CI row only says "lint, type-check" generically. Ruff is written in Rust,
single-binary like `uv` (same "remove the difficulty" philosophy the team already applied
when choosing `uv` over pip/poetry, `decisions/02-repo-and-tooling.md`), and replaces what
would otherwise be three separate tools (flake8, isort, black). mypy is the conventional
pairing for SQLAlchemy 2.0's typed ORM (SQLAlchemy 2.0 ships its own mypy plugin/typing
support) and FastAPI's Pydantic-based request/response models.

**Alternatives considered**: `pyright` instead of `mypy` — rejected only because it's
Node-based (an extra JS toolchain dependency in a Python CI job) whereas mypy is a pure
Python package already inside the `uv`-managed environment; either is a valid substitute if
the team disagrees.

## Decision: Frontend lint/format/type-check tooling

**Decision**: **ESLint** + **Prettier** for lint/format, `tsc --noEmit` for type-checking.

**Rationale**: The standard, unopinionated pairing for a Vite + React + TypeScript project
— no project document suggests a reason to deviate from the ecosystem default.

## Decision: Frontend test tooling

**Decision**: **Vitest** + **React Testing Library** for unit/component tests, **Playwright**
for end-to-end tests.

**Rationale**: Constitution P11 and the "Full-Stack Engineering" §4 both require a
hierarchical unit → component → E2E test structure for the frontend, but no prior document
names the tools. Vitest is Vite-native (shares the same config/transform pipeline the
frontend build already uses, no separate Jest/Babel toolchain), React Testing Library is
the conventional component-testing pairing for it, and Playwright is already a reasonable
default for the business-critical-workflow E2E coverage constitution P11 requires. No test
*content* is written in this feature (User Story 3 only scaffolds the harness) — the choice
matters now because Phase 1 is what wires the CI job steps and directory structure these
tools will fill in Phase 2 onward.

**Alternatives considered**: Cypress instead of Playwright — rejected as a close call, not
a wrong choice; Playwright was picked for first-class multi-browser support and faster CI
execution, with no strong project-specific reason to prefer either.

## Decision: Health/readiness endpoint

**Decision**: The `api` service exposes a minimal `GET /health` endpoint returning service
status, used by the Docker Compose healthcheck and by this feature's own acceptance
scenarios (spec.md User Story 1, "all containers report healthy").

**Rationale**: `architecture/07-api-spec.md` documents the product's real endpoints (M8/M9/
M10), none of which exist yet at this phase — but Docker Compose's `depends_on` +
healthcheck pattern (`architecture/03-technology-stack.md`'s Compose file sketch) needs
*something* to poll. A basic liveness/readiness endpoint is the smallest thing that
satisfies "the api container reports healthy" without anticipating any M1–M10 business
logic.

## Outcome

No `NEEDS CLARIFICATION` markers remain. All Technical Context fields in `plan.md` are
resolved either by citing an existing document or by a decision recorded above.
