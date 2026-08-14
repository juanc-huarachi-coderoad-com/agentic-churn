# Implementation Plan: Dashboard Shell

**Branch**: `feature/setup-sdd` *(no dedicated `002-*` branch — see spec.md's branch note)* | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-dashboard-shell/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement full username/password authentication (`requirements/14-authentication.md`)
and a dashboard shell that proves the authenticated React → FastAPI → Postgres pipeline
works end to end, rendering only what's honestly available today — the seeded client's
name and the spec's own "Learning" state — never fabricated score data. Technical
approach: build into the module locations already named in `decisions/02-repo-and-
tooling.md` (`backend/app/auth/`, `backend/app/experience/dashboard.py`,
`frontend/src/auth/`, `frontend/src/dashboard/`), resolving the handful of
previously-undecided choices (token format, password hashing library, rate limiting,
frontend routing/state) in `research.md`.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript 5.x (frontend) — unchanged from
feature 001

**Primary Dependencies (new in this feature)**: `argon2-cffi` (password hashing),
`slowapi` (login rate limiting) on the backend; `react-router`, `@tanstack/react-query`,
`zustand` on the frontend (`research.md`)

**Storage**: PostgreSQL 16 — no schema change. Reads/writes `users` and `auth_tokens`
(`data-base/12-users-and-auth.md`) and reads `client_profile_versions`
(`data-base/04-schema-context.md`) for real, for the first time; both already provisioned
and seeded by feature 001. `data-base/11-seed-data.sql`'s `marta` row gets a real demo
password hash (`research.md` §Decision: Regenerating the seeded demo password hash) —
the only seed-data change, no DDL/migration change.

**Testing**: pytest (backend) — auth flow (login success/failure/rate-limit, token
validation/revocation) and the dashboard route's authorization gate; Vitest + React
Testing Library (frontend) — login form, protected-route redirect; Playwright — one
end-to-end flow (login → see dashboard) as the first real use of the harness feature 001
scaffolded

**Target Platform**: Same Docker Compose stack as feature 001 — no new services, no
`docker-compose.yml` change needed

**Project Type**: Web application (backend + frontend), same monorepo as feature 001

**Performance Goals**: Dashboard load < 1s (`REQ-NFR-01`); Ask agent budget (`REQ-M9-08`)
not applicable — this feature adds no ask-agent code

**Constraints**: Every route except `/auth/login` and `/health` requires a valid bearer
token, with zero exceptions (`REQ-AUTH-P1`); no per-role restriction yet (`REQ-AUTH-P3`,
constitution's Full-Stack Engineering §5 "Zero Trust Validation" — re-validated at the
Application boundary, not trusted from the frontend)

**Scale/Scope**: Single client deployment, single API instance — informs the in-process
rate-limiter decision (`research.md`), not a distributed one

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| P1 Evidence or It Does Not Exist | Not yet — no findings exist until Phase 5/7 | N/A this phase |
| P2 The Model Interprets, Code Calculates | No LLM code anywhere in this feature | N/A |
| P3 Each Component Refuses to Do the Next One's Job | Auth middleware only resolves identity, never authorizes by role (`REQ-AUTH-P3`); the dashboard route only reads precomputed data, never computes (`REQ-M8-01`, `REQ-M8-P1`) | **Pass** |
| **P4 A Human Always Sends** | Yes — no send capability is added anywhere; this feature has no email/message-sending surface at all | **Pass** — nothing to violate |
| **P5 Admit What We Cannot See** | Yes — the dashboard renders the honest "Learning" state rather than a fabricated score (`REQ-M8-07`); a malformed/missing client profile shows an explicit state, not a blank screen (spec.md Edge Cases) | **Pass** — FR-008, Edge Cases |
| **P6 Silence Is a Success State** | Yes — "Learning" and "nothing needs you" states are near-empty by design, not manufactured concern | **Pass** |
| P8 Clean Architecture: the Dependency Rule Is Law | Yes — `backend/app/auth/{domain,application,adapters}` follows the same three rings as `scoring/`; `import-linter`'s `global-dependency-rule` contract (feature 001) already covers `app.auth.*` | **Pass** — no `.importlinter` change needed, `auth` was already a listed container |
| P9 Test-First Determinism | Not applicable — no scoring/ledger code touched | N/A |
| P10 Simplicity Over Speculative Generality (YAGNI) | Yes — in-process rate limiting instead of Redis; opaque tokens instead of JWT+denylist; no role-based access control scaffolding for a system that doesn't enforce roles yet (`REQ-AUTH-P3`) | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | Yes — `frontend/src/auth/` and `frontend/src/dashboard/` are feature-oriented folders; TanStack Query for the dashboard's server state, Zustand for the auth token, matching the stack this principle already names | **Pass** |
| Full-Stack §2 Frontend Architecture (forms/validation) | Yes — the login form is this project's first real form | **Pass** — React Hook Form + Zod (`research.md` §Decision: React Hook Form + Zod for the login form) |
| Full-Stack §4 Testing Strategy | Yes — this feature has real business logic (password hashing, token lifecycle) for the first time | **Pass** — T015/T023 (backend), T026 (component), T027 (E2E) cover the hierarchy this principle requires |
| Full-Stack §5 Security & Quality Gates (Zero Trust Validation) | Yes — the backend re-validates the bearer token on every request; the frontend's "redirect if no token" is UX only, never the actual security boundary | **Pass** — FR-005 |

**No violations requiring justification.** Complexity Tracking table below is empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-dashboard-shell/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — auth token lifecycle over existing tables
├── quickstart.md         # Phase 1 output — login-to-dashboard validation guide
├── contracts/
│   ├── auth.md            # POST /auth/login, POST /auth/logout
│   └── dashboard.md       # GET /api/dashboard (shell-scoped response)
└── tasks.md               # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

Builds into the monorepo layout feature 001 scaffolded
(`decisions/02-repo-and-tooling.md` §Monorepo layout) — only the files this feature adds
or changes are shown; everything else from feature 001 is unchanged:

```text
backend/
├── app/
│   ├── auth/
│   │   ├── domain/
│   │   │   └── password.py         # Argon2id hash/verify, opaque token generation — pure, no I/O
│   │   ├── application/
│   │   │   ├── ports.py            # UserRepositoryPort, TokenRepositoryPort
│   │   │   ├── use_cases.py        # LoginUseCase, LogoutUseCase
│   │   │   └── dependencies.py     # get_current_user FastAPI dependency (REQ-AUTH-05/P1 gate)
│   │   └── adapters/
│   │       ├── sqlalchemy_repository.py
│   │       └── router.py           # POST /auth/login, POST /auth/logout
│   ├── experience/
│   │   ├── application/
│   │   │   └── use_cases.py        # GetDashboardShellUseCase
│   │   └── adapters/
│   │       └── dashboard_router.py # GET /api/dashboard
│   └── main.py                     # wires auth + dashboard routers, rate limiter (updated)
└── tests/
    └── unit/
        ├── test_auth.py            # login/logout/rate-limit/revocation
        └── test_dashboard_route.py # authorization gate + Learning-state response

frontend/
└── src/
    ├── auth/
    │   ├── login-page.tsx
    │   ├── auth-store.ts           # zustand: token, isAuthenticated
    │   ├── api-client.ts           # fetch wrapper attaching Authorization header
    │   └── protected-route.tsx     # redirects to /login when unauthenticated
    ├── dashboard/
    │   └── dashboard-page.tsx      # TanStack Query call to /api/dashboard
    ├── App.tsx                     # updated: react-router routes for /login, /dashboard
    └── e2e/
        └── login-to-dashboard.spec.ts  # first real Playwright spec (feature 001 scaffolded the harness)

data-base/
└── 11-seed-data.sql                # marta's password_hash regenerated to a real demo hash
```

**Structure Decision**: Same web-application structure as feature 001, extending the
already-scaffolded `auth/` and `experience/` (backend) and `auth/`, `dashboard/`
(frontend) module folders with real code for the first time — no new top-level
directories.

## Complexity Tracking

*No entries — Constitution Check reported no violations requiring justification.*
