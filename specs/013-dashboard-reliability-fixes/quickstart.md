# Quickstart: Validating the Dashboard Reliability Fixes

## Prerequisites

- `frontend/` dependencies installed (`pnpm install`).
- Backend + Postgres running (`docker compose up`) for the e2e checks (US2/US3); not required for the US1 unit/component test.

## Validate User Story 1 — no duplicate-key warnings (P1)

```bash
cd frontend
pnpm test src/ask/components/answer-renderer.test.tsx
```

Expect: the new test renders a `delta_breakdown` (or `ranked_issues`) answer with two causes sharing the same `finding_type` but different `score_contribution_id`s, asserts both rows render with their own point values, asserts clicking each opens evidence for its own `score_contribution_id`, and asserts no React console warning fires during the render.

## Validate User Story 2 — evidence e2e survives duplicate quoted text (P2)

```bash
docker compose up -d
pnpm test:e2e e2e/dashboard-to-evidence.spec.ts
```

Expect: all three tests in this file pass, including "clicking a pulse event opens the evidence panel with the real quoted message," regardless of how many seeded events currently share the quoted text `"Slow API response"`.

## Validate User Story 3 — login e2e survives dashboard-state drift (P3)

```bash
pnpm test:e2e e2e/login-to-dashboard.spec.ts
```

Expect: "logging in with valid credentials reaches the dashboard shell" passes regardless of whether the seeded `marta` / Meridian Logistics account is currently in `learning`, `catching_up`, `normal`, or any other non-`no_profile`/`healthy_quiet` state.

## Regression check

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm test:e2e
```

All must pass, with zero changes to any file outside `frontend/src/ask/components/answer-renderer.tsx`, the new `answer-renderer.test.tsx`, `frontend/e2e/dashboard-to-evidence.spec.ts`, and `frontend/e2e/login-to-dashboard.spec.ts` — verifiable with `git diff --stat` (FR-007).

## Definition of Done

- All three acceptance-scenario sets above pass.
- `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm test:e2e` all pass.
- No dashboard visual/layout, business-logic, scoring, or backend diff exists (FR-007).
