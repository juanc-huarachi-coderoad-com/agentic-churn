# Quickstart: Validating the Login Page Redesign

## Prerequisites

- `frontend/` dependencies installed (`pnpm install`, already the case in this repo).
- For the **full** login flow (real API call, redirect to dashboard): the backend running
  against a migrated + seeded database, per `specs/002-dashboard-shell/quickstart.md` §3. The
  seeded demo credentials used by the existing e2e suite are `marta` /
  `agentic-demo-2026` (`frontend/e2e/login-to-dashboard.spec.ts`).
- For **visual/manual QA only** (layout, responsive collapse, client-side validation states):
  the frontend dev server alone is enough — the empty-field validation errors never reach the
  network.

## Manual validation

1. `pnpm --dir frontend dev`, open `/login`.
2. **Desktop layout (≥1024px wide)**: confirm the two-panel layout — AURA orb + product name +
   tagline on one side, the sign-in form on the other.
3. **Responsive collapse**: narrow the viewport below 1024px (Tailwind's `lg` breakpoint).
   Confirm the brand panel is replaced by a compact orb+wordmark lockup above the form, and
   the form remains fully usable with no horizontal scrolling down to 320px wide.
4. **Empty-field validation**: submit with both fields empty. Confirm inline errors
   "Username is required" / "Password is required" appear under each field, and no network
   request is made.
5. **Invalid credentials**: submit `marta` / a wrong password. Confirm the single banner
   "Invalid username or password." appears, and it disappears again as soon as either field is
   edited.
6. **Successful login**: submit `marta` / `agentic-demo-2026` (requires the seeded backend).
   Confirm the button shows a loading state, then the app redirects to `/dashboard`.
7. **Password visibility toggle**: click the toggle inside the password field. Confirm the
   field's content switches between masked and plain text, and its accessible name switches
   between "Show password" and "Hide password".
8. **Keyboard-only pass**: using only Tab/Shift+Tab/Enter, confirm every interactive element
   (username field, password field, visibility toggle, submit button) is reachable and
   operable, with a visible focus state at each stop.

## Automated validation

Run from `frontend/`:

- `pnpm typecheck` — strict TypeScript, no `any`.
- `pnpm lint` — ESLint, including the accessibility/react-hooks rules already configured.
- `pnpm test` — Vitest + Testing Library, including the new `login-page.test.tsx` covering the
  scenarios in steps 4–7 above at the component level.
- `pnpm test:e2e` — Playwright, including the updated `login-to-dashboard.spec.ts` (heading
  copy assertion updated per `research.md` Decision 6; all other assertions unchanged and must
  still pass, requires the seeded backend per the Prerequisites above).

All four commands are expected to pass with no changes anywhere outside
`frontend/src/auth/` and the one updated line in `frontend/e2e/login-to-dashboard.spec.ts`.
