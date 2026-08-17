# Quickstart: Validating the Main Dashboard Visual Redesign

This is a validation guide, not a setup guide — see the repo `README.md` and `docker-compose.yml` for full environment setup. It assumes a running backend + database (`docker compose up`) seeded with at least one account that has active findings and score history, per the existing dev-fixture conventions used by earlier dashboard features (specs 002/006).

## Prerequisites

- Backend + Postgres running (`docker compose up`), with a seeded account that has: active findings (non-`healthy_quiet` state), at least 2 score-history points, at least one `narrator.actions` entry, and at least one `contribution_bars` entry.
- A second seeded account (or the same account toggled) in the `healthy_quiet` state, to validate FR-010.
- Frontend dependencies installed and up to date after this feature's `recharts`/`lucide-react` additions:

```bash
cd frontend
pnpm install
```

## Run the app

```bash
pnpm dev
```

Log in and navigate to `/dashboard`.

## Validate User Story 1 — redesigned layout (P1)

1. Open `/dashboard` for the account with active findings.
2. **Expect**: sidebar (left), Signal Stream (center), Churn Risk Overview + Action & Draft Hub (right) all visible — matches SC-001 (identifiable within 5 seconds).
3. Open the browser devtools network tab; confirm no new network requests fire beyond what the pre-redesign dashboard already made (`GET /api/dashboard` and whatever the opened panels already trigger) — validates FR-011/SC-002.
4. Click the Coverage and Profile sidebar icons; confirm each existing route still loads correctly and the sidebar highlights the active one (FR-001, FR-002).
5. Switch the account to `healthy_quiet` (or load a seeded healthy account); confirm the dashboard collapses to the existing near-empty message, not the four-region layout (FR-010).

## Validate User Story 2 — Churn Risk Overview (P2)

1. On the same account, confirm the Churn Risk Overview card shows: the score, its band label, a filled area chart of the trend, and the ranked risk-driver list, all in one card (FR-004, FR-005).
2. Compare every displayed number (score, trend values, driver labels/points) against the raw `GET /api/dashboard` JSON response for that account — values must match exactly (SC-005).
3. Load an account with fewer than 2 score-history points; confirm the chart degrades gracefully rather than rendering a broken/misleading area (Edge Case, Acceptance Scenario 3).

## Validate User Story 3 — floating assistant (P3)

1. Reload `/dashboard`; confirm the assistant renders collapsed (launcher only) — never expanded on load (FR-007).
2. Scroll down within the Signal Stream, then open the assistant; confirm it opens without a page navigation and without resetting scroll position (SC-003).
3. Ask a question; confirm the existing `idle → thinking → answered` behavior is unchanged (same `postAsk` call, same response rendering via `AnswerRenderer`).
4. Collapse and reopen the assistant; confirm the last exchange is still shown, not cleared (FR-008).
5. With the assistant open, trigger an Evidence panel or Draft Composer overlay (e.g. click a Signal Stream entry); confirm both remain usable and neither is hidden behind the other (Edge Case — z-index stacking).

## Regression check — FR-009 / FR-011

Run the existing automated suites; all should pass after being updated for new markup (not new behavior):

```bash
pnpm test        # vitest — component/unit tests
pnpm test:e2e     # playwright — end-to-end
pnpm typecheck
pnpm lint
```

Specifically confirm:
- `frontend/src/dashboard/dashboard-page.test.tsx` — still asserts the same `useQuery` call and the same conditional rendering by `data.state`.
- `frontend/src/ask/ask-bar.test.tsx` — still asserts the same `useMutation`/`postAsk` call and idle/thinking/answered states, now inside the floating shell.
- `frontend/src/draft-composer/draft-composer-panel.test.tsx`, `frontend/src/evidence/evidence-panel.test.tsx` — still assert the same props and the same open/close behavior.

## Definition of Done for this feature

- All acceptance scenarios above pass manually.
- `pnpm test`, `pnpm test:e2e`, `pnpm typecheck`, `pnpm lint` all pass.
- A side-by-side screenshot comparison against `base/mockup-mainPage.jpg` shows the four regions in their specified positions (SC-005).
- No diff exists in any file under `frontend/src/dashboard/types.ts`, `ask/types.ts`, `draft-composer/types.ts`, `evidence/types.ts`, any `api.ts`, or anywhere in `backend/` (FR-011, verifiable with `git diff --stat`).
