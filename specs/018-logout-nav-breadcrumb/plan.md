# Implementation Plan: Sidebar Logout, Nav Tooltips & Breadcrumb Trail

**Branch**: `018-logout-nav-breadcrumb` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-logout-nav-breadcrumb/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Three coupled frontend-only UI improvements to the existing sidebar/navigation shell: (1) a
bottom-left account icon-button that opens a single-item ("Log out") menu and performs a real
logout by calling the existing `POST /auth/logout` backend endpoint before clearing local
session state; (2) elegant hover/focus tooltips on the three main sidebar destinations plus a
non-color-only "currently selected" indicator; (3) a Home > [current screen] breadcrumb trail,
styled like the existing Client Profile mockup, applied to every authenticated screen. The
sidebar today is only rendered on the Dashboard screen — Coverage and Profile render bare
`<main>` content with no navigation chrome at all — so this feature also introduces a shared
`AppShell` layout (Sidebar + Breadcrumb) adopted by all three protected routes, which is the
mechanism that makes "every screen" (FR-001, FR-010) true rather than aspirational. No backend
changes: the feature reuses the existing, already-tested `/auth/logout` endpoint and
`useAuthStore` unchanged in shape.

## Technical Context

**Language/Version**: TypeScript ~6.0 / React 18.3 (existing `frontend/` app, Vite 8 build)

**Primary Dependencies**: React Router 7, TanStack Query 5, Zustand 5 (existing); Radix UI
primitives — `@radix-ui/react-dialog` and `@radix-ui/react-slot` already in use, this feature
adds `@radix-ui/react-tooltip` and `@radix-ui/react-dropdown-menu` (same family, same wrapper
pattern as `components/ui/dialog.tsx`, per constitution P11 "Design system" — no non-Radix
component library); `lucide-react` icons (existing, adds `Home` and `LogOut`); Tailwind CSS 4.

**Storage**: N/A — no new persisted data. Reuses the existing Zustand `persist`-backed
`useAuthStore` (`frontend/src/auth/auth-store.ts`) unchanged in shape; logout continues to end
with `token: null, isAuthenticated: false`.

**Testing**: Vitest + `@testing-library/react` for component tests (matches existing
`sidebar.test.tsx`, `profile-editor-form.test.tsx` patterns); Playwright for one end-to-end
logout flow, since logout is a business-critical, security-relevant path (constitution P11
"Testing").

**Target Platform**: Web SPA, existing `frontend/` app — no new platform.

**Project Type**: Web application (existing `backend/` + `frontend/` repo). This feature is
frontend-only; it calls one pre-existing backend endpoint (`POST /auth/logout`,
`backend/app/auth/adapters/router.py`) without modifying it.

**Performance Goals**: N/A beyond standard SPA interaction responsiveness — tooltip appears
after a short, consistent hover/focus delay (Radix Tooltip default, ~400ms) and the account
menu opens synchronously on click (Radix DropdownMenu, no network round-trip to open).

**Constraints**: No backend changes and no new API surface — must reuse `POST /auth/logout`
as-is; must not introduce a non-Radix menu/tooltip/dropdown library (constitution Full-Stack
§2 "UI & Styling"); the account menu contains exactly one item, "Log out" (Clarification
2026-08-19).

**Scale/Scope**: 3 existing authenticated screens (Dashboard, Coverage, Profile/Client
profile) gain a shared layout; ~4 new frontend files (`AppShell`, `Breadcrumb`, `AccountMenu`,
a shared destinations registry) plus 2 new `components/ui` Radix wrappers (`Tooltip`,
`DropdownMenu`) and edits to `Sidebar`, `App.tsx`, `CoveragePage`, `ProfileEditorForm`,
`DashboardPage`, and `auth-store.ts`/a small logout hook.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature touches no scoring, ledger, evidence, or LLM-facing module — P1 (Evidence),
P2 (Model Interprets/Code Calculates), P3 (component boundaries), P5 (incomplete-data
visibility), P6 (Silence Is a Success State), P7 (Context Over Sentiment), P8 (backend Clean
Architecture rings), and P9 (Test-First Determinism/golden-replay) are **not applicable** —
nothing in `backend/app/ledger/` or `backend/app/scoring/` is created or modified.

- **P4 — A Human Always Sends**: satisfied. Logout is a direct, human-initiated click; nothing
  autonomous is added.
- **P10 — Simplicity Over Speculative Generality**: satisfied. The account menu ships with
  exactly the one item the spec requires ("Log out"), per the 2026-08-19 clarification — no
  speculative "Settings"/"View profile" entries added ahead of need.
- **P11 — Frontend: Feature-Oriented, Typed, Spec-Driven**: governs this feature directly.
  - Feature-oriented structure: new components live in `frontend/src/nav/` (where `Sidebar`
    already lives), not a generic `components/` dump.
  - Separation of concerns: the logout network call lives in a small hook/module in
    `frontend/src/auth/`, never inline inside a UI component's JSX.
  - Design system: `Tooltip` and `DropdownMenu` are added as thin Radix wrappers under
    `components/ui/`, matching the existing `Dialog` wrapper's exact pattern — no ad hoc
    popover/menu implementation, no non-Radix library.
  - Accessibility: tooltips are available on keyboard focus (not hover-only), the active nav
    item is marked with `aria-current="page"` plus a non-color visual cue, and the account
    menu/dropdown gets Radix's built-in focus trap, Escape-to-close, and click-outside
    handling for free (satisfies FR-005 without hand-rolled event listeners).
  - Testing: component tests for `AccountMenu`, `Sidebar` (tooltip + active state), and
    `Breadcrumb`; one Playwright e2e for the logout flow.

**Result**: PASS. No violations to record in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/018-logout-nav-breadcrumb/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md               # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/src/
├── nav/
│   ├── destinations.ts          # NEW — single source of truth: {to, label, icon} for
│   │                             #   Dashboard/Coverage/Profile, consumed by Sidebar
│   │                             #   (tooltips + active state) and Breadcrumb (per-page
│   │                             #   icon), so the two can never drift (FR-011).
│   ├── sidebar.tsx               # EDIT — wrap each destination icon in Tooltip; add a
│   │                             #   non-color-only active indicator + aria-current; mount
│   │                             #   AccountMenu pinned to the bottom (mt-auto).
│   ├── sidebar.test.tsx          # EDIT — cover tooltip visibility + active-state cases.
│   ├── account-menu.tsx          # NEW — bottom-left icon-button + Radix DropdownMenu with
│   │                             #   the single "Log out" item (FR-001/002/005).
│   ├── account-menu.test.tsx     # NEW.
│   ├── breadcrumb.tsx            # NEW — Home icon/link + current-screen icon/name, styled
│   │                             #   per base/mockup-client-profile.jpg (FR-010–014).
│   ├── breadcrumb.test.tsx       # NEW.
│   ├── app-shell.tsx             # NEW — composes Sidebar + Breadcrumb + page content;
│   │                             #   adopted by all three protected routes so navigation
│   │                             #   chrome stops being Dashboard-only.
│   └── app-shell.test.tsx        # NEW.
├── auth/
│   ├── auth-store.ts             # UNCHANGED shape — logout() still just clears local state
│   │                             #   (kept as the 401-interceptor's fast path).
│   ├── use-logout.ts             # NEW — the intentional-logout action: best-effort
│   │                             #   POST /auth/logout, then auth-store.logout(), then
│   │                             #   navigate('/login').
│   └── use-logout.test.ts        # NEW.
├── components/ui/
│   ├── tooltip.tsx                # NEW — thin @radix-ui/react-tooltip wrapper, same shape
│   │                             #   as dialog.tsx.
│   └── dropdown-menu.tsx          # NEW — thin @radix-ui/react-dropdown-menu wrapper.
├── dashboard/dashboard-page.tsx   # EDIT — render via AppShell instead of its own <Sidebar/>.
├── coverage/coverage-page.tsx     # EDIT — render via AppShell (currently has no nav chrome
│                                 #   at all).
├── profile-editor/
│   └── profile-editor-form.tsx   # EDIT — render via AppShell (currently has no nav chrome
│                                 #   at all); this is the screen the Breadcrumb style is
│                                 #   modeled on (base/mockup-client-profile.jpg).
└── App.tsx                        # Unchanged routing; AppShell is used inside each page,
                                    #   not as a route-level wrapper, since each page already
                                    #   owns its own data-loading/error states.

backend/                           # UNCHANGED — POST /auth/logout already exists
                                    #   (backend/app/auth/adapters/router.py) and is reused
                                    #   as-is.
```

**Structure Decision**: Existing `backend/` + `frontend/` web application layout is unchanged.
All new code lives in the existing `frontend/src/nav/` (feature-oriented, per P11) and
`frontend/src/components/ui/` (design-system primitives), plus one small addition to
`frontend/src/auth/` for the logout side effect. No new top-level directories, no backend
changes.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
