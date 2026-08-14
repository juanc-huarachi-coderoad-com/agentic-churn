# Tasks: Dashboard Shell

**Input**: Design documents from `specs/002-dashboard-shell/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/auth.md`, `contracts/dashboard.md`, `quickstart.md`

**Tests**: Not separately requested beyond what `spec.md`'s acceptance scenarios already
imply — test tasks below cover exactly those scenarios (login/logout/rate-limit/
revocation, the dashboard's authorization gate, the frontend redirect), not a broader
TDD suite.

**Organization**: Tasks are grouped by user story (`spec.md`) — US1 (P1, login/logout),
US2 (P2, the authenticated dashboard shell) — per `plan.md`'s Project Structure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 (P1) or US2 (P2)
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

**Purpose**: New dependencies and the one seed-data fix both stories need before any code
is written.

- [X] T001 [P] Add `argon2-cffi` and `slowapi` to `backend/pyproject.toml` via
      `uv add` (`research.md` §Decision: `argon2-cffi`, §Decision: In-process rate
      limiting)
- [X] T002 [P] Add `react-router`, `@tanstack/react-query`, `zustand`,
      `react-hook-form`, `zod`, and `@hookform/resolvers` to `frontend/package.json`
      via `pnpm add` (`research.md` §Decision: Frontend state, §Decision: React Hook
      Form + Zod for the login form) — pinned `react-router@^7` (not the default
      latest `@8`, which requires React 19; this project deliberately stays on React 18)
- [X] T003 Regenerate the seeded `marta` row's `password_hash` in
      `data-base/11-seed-data.sql` to a real Argon2id hash of the demo password
      `agentic-demo-2026` (`research.md` §Decision: Regenerating the seeded demo
      password hash) — seed-data edit only, no DDL/migration change

**Checkpoint**: Dependencies installed, seed data has a real, loggable-in demo user.

---

## Phase 2: Foundational

**Purpose**: Shared plumbing both user stories build into.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T004 Configure CORS middleware in `backend/app/main.py` allowing the `web` origin
      (`docker-compose.yml`'s `WEB_PORT`) — without this, no frontend-to-backend request
      in either story can succeed (browsers enforce CORS; curl-based backend testing does
      not need it, but the real frontend flow does)
- [X] T005 [P] Set up the React Router route shell in `frontend/src/App.tsx`: a public
      `/login` route and a bare (not yet gated) `/dashboard` route — T024 adds the
      `ProtectedRoute` wrapper once it exists, so the app compiles at every checkpoint
      in between (depends on T002) — placeholder elements added so the app renders
      meaningfully before T016/T025 replace them
- [X] T006 [P] Wrap the app in a `QueryClientProvider` in `frontend/src/main.tsx`
      (depends on T002)

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 - Log in and out with a real, revocable token (Priority: P1) — MVP

**Goal**: A user can obtain a bearer token via username/password, have it revoked via
logout, and have every failure mode (wrong password, unknown username, deactivated user,
rate limit) behave exactly per `requirements/14-authentication.md`.

**Independent Test**: `quickstart.md` §1 — a curl-only sequence, no frontend or dashboard
route required.

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement Argon2id hash/verify and opaque token generation
      (`secrets.token_urlsafe(32)` + SHA-256 for storage) in
      `backend/app/auth/domain/password.py` — pure functions, no I/O (depends on T001)
- [X] T008 [P] [US1] Define `UserRepositoryPort` and `TokenRepositoryPort` in
      `backend/app/auth/application/ports.py`
- [X] T009 [US1] Implement `SqlAlchemyUserRepository` and `SqlAlchemyTokenRepository` in
      `backend/app/auth/adapters/sqlalchemy_repository.py` (depends on T008)
- [X] T010 [US1] Implement `LoginUseCase` — verifies `password_hash` and `is_active`
      (`FR-010`), issues a token with a hard expiry — in
      `backend/app/auth/application/use_cases.py` (depends on T007, T008)
- [X] T011 [US1] Implement `LogoutUseCase` — sets `auth_tokens.revoked_at` for the
      presented token, idempotently — in `backend/app/auth/application/use_cases.py`
      (same file as T010, sequential; depends on T008)
- [X] T012 [US1] Implement the `get_current_user` FastAPI dependency — rejects missing,
      expired, or revoked tokens with an identical `401` — in
      `backend/app/auth/application/dependencies.py` (depends on T008) — depends only on
      `TokenRepositoryPort`, wired to the concrete adapter via `dependency_overrides` at
      the composition root (`main.py`), so Application never imports Adapters
- [X] T013 [US1] Implement `POST /auth/login` and `POST /auth/logout` with `slowapi`
      rate limiting on login, per `contracts/auth.md`, in
      `backend/app/auth/adapters/router.py` (depends on T009, T010, T011) — two
      adaptations from the original design, both documented in `research.md`: rate
      limiting is keyed by source IP rather than username (`slowapi`'s key_func is
      synchronous, can't safely read the async request body), and counts only *failed*
      attempts (driven manually via `limiter.limiter.test()`/`.hit()`, not the
      `@limiter.limit(...)` decorator, which would also count — and block — successful
      logins)
- [X] T014 [US1] Wire the auth router into `backend/app/main.py`, confirming `/health`
      remains the only other unauthenticated route (`REQ-AUTH-P1`) (depends on T013, T004)
- [X] T015 [P] [US1] Write `backend/tests/unit/test_auth.py` covering: valid login,
      wrong-password/unknown-username/deactivated-user (identical `401`), third-attempt
      rate limit, logout-then-rejected-on-next-use, and a direct assertion that
      `get_current_user` resolves to the correct `user_id` for a valid token (FR-006)
      (depends on T013, T014) — 7/7 tests passing against a real migrated Postgres;
      required adding `pythonpath = ["."]` and a session-scoped asyncio event loop to
      `pyproject.toml`'s pytest config (the module-level async engine singleton
      otherwise breaks under pytest-asyncio's default per-test event loop)
- [X] T016 [P] [US1] Build the login form in `frontend/src/auth/login-page.tsx` using
      `react-hook-form` with a `zod` schema validating non-empty username/password
      before submit (constitution P11 / Full-Stack §2) (depends on T005)
- [X] T017 [P] [US1] Create the auth Zustand store (`token`, `isAuthenticated`, `login`/
      `logout` actions, `localStorage`-backed) in `frontend/src/auth/auth-store.ts`
      (depends on T002)
- [X] T018 [US1] Create the API client wrapper attaching
      `Authorization: Bearer <token>` and clearing the store on a `401` response, in
      `frontend/src/auth/api-client.ts` (depends on T017)
- [X] T019 [US1] Wire `login-page.tsx`'s `react-hook-form` submit handler to call
      `POST /auth/login` via the API client and populate the auth store on success,
      redirecting to `/dashboard` (depends on T016, T017, T018) — lint/typecheck/build
      all pass; full interactive verification happens in T027's Playwright spec once
      the dashboard page exists to navigate to

**Checkpoint**: `quickstart.md` §1 passes end to end — User Story 1 is independently
functional and testable.

---

## Phase 4: User Story 2 - Authenticated dashboard shell renders real seeded data (Priority: P2)

**Goal**: An authenticated request to `/api/dashboard` returns the seeded client's name
and the Learning state; an unauthenticated one is rejected; the frontend renders this
through a real login-to-dashboard flow.

**Independent Test**: `quickstart.md` §2 (API) and §3 (frontend) — requires User Story 1
complete (the token it produces gates this route).

### Implementation for User Story 2

- [X] T020 [US2] Implement `GetDashboardShellUseCase` — reads the current
      `client_profile_versions` row and returns `client_header` + `learning` state, or
      the `no_profile` state if none exists — in
      `backend/app/experience/application/use_cases.py` (depends on T012) — added a
      `ClientProfileRepositoryPort` in `experience/application/ports.py`, matching the
      auth module's pattern
- [X] T021 [US2] Implement `GET /api/dashboard`, gated by `get_current_user`, per
      `contracts/dashboard.md`, in `backend/app/experience/adapters/dashboard_router.py`
      (depends on T020, T012)
- [X] T022 [US2] Wire the dashboard router into `backend/app/main.py` (depends on T021,
      T014)
- [X] T023 [P] [US2] Write `backend/tests/unit/test_dashboard_route.py` covering the
      `401`-without-token case, the `200`-with-token Learning-state response, and the
      `no_profile` state when no current `client_profile_versions` row exists (depends
      on T021) — 3/3 passing against real Postgres, including a live curl verification
      of the exact contracts/dashboard.md response shape
- [X] T024 [US2] Build `ProtectedRoute` — redirects to `/login` when `isAuthenticated`
      is false — in `frontend/src/auth/protected-route.tsx`, and wrap the bare
      `/dashboard` route from T005 with it in `frontend/src/App.tsx` (depends on T005,
      T017; no longer [P] since it now also edits App.tsx alongside T005's earlier edit)
- [X] T025 [US2] Build the dashboard page — calls `/api/dashboard` via TanStack Query,
      renders `client_header.client_name` and `learning_message` — in
      `frontend/src/dashboard/dashboard-page.tsx` (depends on T006, T018, T024)
- [X] T026 [P] [US2] Write `frontend/src/auth/protected-route.test.tsx` (Vitest)
      confirming the redirect-when-unauthenticated behavior (depends on T024) — 2/2
      passing (redirect when unauthenticated, renders content when authenticated)
- [X] T027 [US2] Write `frontend/e2e/login-to-dashboard.spec.ts` — the first real content
      in the Playwright harness feature 001 scaffolded — covering the full login →
      dashboard flow (depends on T019, T025) — 4/4 passing against the real backend +
      Postgres + Vite dev server: unauthenticated redirect, successful login to
      dashboard, invalid-credentials error message, and session persistence across a
      page reload

**Checkpoint**: `quickstart.md` §1–3 all pass — User Stories 1 AND 2 both work; this is
the full vertical slice the build order names.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T028 [P] Add a "Login" section to the root `README.md` documenting the demo
      credential (`marta` / `agentic-demo-2026`) and linking to
      `specs/002-dashboard-shell/quickstart.md` — also updated the stale "Project
      Foundation only" overview paragraph to mention this feature
- [X] T029 Run all of `specs/002-dashboard-shell/quickstart.md` end to end and confirm
      every acceptance scenario in `spec.md` passes, and time the login-to-dashboard
      path against SC-001's under-5-seconds threshold (depends on every task above) —
      verified against the real, fully containerized stack (`docker compose up
      --build`, all 4 services healthy): login/logout/rate-limit/revocation via curl,
      the dashboard API contract, AND a real browser hitting the nginx-served
      production build end to end (screenshotted: login form → "Meridian Logistics" /
      "Still learning — 0 of 6 signal types available."). Login-to-dashboard round
      trip: 0.61s, well under SC-001's 5s threshold.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS both user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on US2.
- **User Story 2 (Phase 4)**: Depends on Foundational **and** on User Story 1 being
  complete — `get_current_user` (T012) and the auth store (T017)/API client (T018) it
  reuses are built in Phase 3, not duplicated in Phase 4. This is a real dependency, not
  just a sequencing convenience: the dashboard route has nothing to gate against until
  the token it validates can actually be issued.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### Within Each User Story

- Domain (pure logic) before application (use cases) before adapters (routes/repos).
- Backend route wiring (`main.py`) after the router itself exists.
- Frontend: store before API client before the page that uses both.

### Parallel Opportunities

- T001 and T002 run in parallel (different files/languages).
- T005 and T006 run in parallel once T002 is done.
- US1's T007 and T008 run in parallel (no shared file, both only need T001/nothing).
- US1's T015, T016, T017 run in parallel once their respective dependencies land.
- US2's T023 runs in parallel with T024 and T025 (different files) — T024 itself is
  sequential with T005 (both touch `frontend/src/App.tsx`).
- **US2 cannot start until US1 is functionally complete** (see Phase Dependencies above)
  — unlike feature 001's three independent stories, this feature's two stories are
  genuinely sequential, not just conventionally ordered.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run `quickstart.md` §1 — a working login/logout API is itself a
   legitimate, demoable increment, independent of any dashboard existing yet.

### Incremental Delivery

1. Setup + Foundational → shared plumbing ready.
2. Add US1 → validate independently (`quickstart.md` §1) → the auth backbone every later
   feature depends on is now real, not just scaffolded.
3. Add US2 → validate (`quickstart.md` §2–3) → the full vertical slice the build order
   names is complete: an integration bug here can no longer be confused with a
   scoring-logic bug later, because no scoring logic exists yet to confuse it with.

---

## Notes

- `[P]` tasks touch different files with no dependency on an incomplete task.
- Unlike feature 001, US2 has a genuine functional dependency on US1 (not just a shared
  Foundational phase) — noted explicitly above rather than glossed over.
- Commit after each task or logical group; stop at either checkpoint to validate
  independently before continuing.
