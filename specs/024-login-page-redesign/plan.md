# Implementation Plan: Login Page Redesign

**Branch**: `024-login-page-redesign` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/024-login-page-redesign/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Apply the already-approved "AURA Login" design (a two-panel branded login screen — an AURA-orb hero panel plus a polished sign-in form) to the real `frontend/src/auth/login-page.tsx`, with zero change to the existing authentication behavior (fields, validation messages, error message, redirect-on-success). The approved reference was authored as a standalone `.dc.html` design-canvas prototype (plain CSS, hand-drawn inline SVGs, custom class-based state) because that tool has no access to this app's real stack; the technical approach here is a faithful **translation** of that approved visual design onto this codebase's actual primitives — Tailwind utility classes, `lucide-react` icons via the existing `Icon` wrapper, and React Hook Form + Zod for the form itself — not a port of the prototype's raw markup.

## Technical Context

**Language/Version**: TypeScript 6.0 / React 18.3, matching the existing `frontend/` Vite app (no version change)

**Primary Dependencies**: React Hook Form + `@hookform/resolvers` + Zod (already used by `login-page.tsx`, unchanged), `lucide-react` (icons), Tailwind CSS v4 (styling) — all already-adopted dependencies; **no new npm packages**

**Storage**: N/A — no persistence change; the session token continues to be handled by the existing `useAuthStore` (Zustand)

**Testing**: Vitest + Testing Library (new component test for the login page), Playwright (`frontend/e2e/login-to-dashboard.spec.ts`, one assertion updated for the new heading copy — see research.md Decision 6)

**Target Platform**: Web (browser), responsive from 320px to desktop widths

**Project Type**: Web application — this feature touches only the existing `frontend/` app, specifically the existing `auth` feature slice; no backend change

**Performance Goals**: N/A beyond standard page-load expectations already met by the rest of the app; the only animation (the orb's pulse) reuses the existing, already-optimized `animate-aura-pulse` Tailwind utility

**Constraints**: No new dependencies; no change to the `POST /auth/login` contract (`specs/002-dashboard-shell/contracts/auth.md`, unchanged); must not regress any of the three existing e2e login scenarios; must follow the closed UI/icon/styling choices Full-Stack Engineering §2 already mandates (Tailwind + Radix/shadcn conventions, `lucide-react` only, no standard-CSS/other icon library)

**Scale/Scope**: One existing page component rewritten, one new small presentational component (the brand panel), one new component test file, one updated e2e assertion — no new routes, no new backend surface

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Applicability | Status |
|---|---|---|
| P1–P7, P9 (evidence, scoring, ledger, tone, etc.) | Not applicable — this feature has no scoring, findings, or evidence surface | ✅ N/A |
| P4 (a human always sends) | Not applicable — login has no send capability of any kind | ✅ N/A |
| P8 (Clean Architecture, backend rings) | Not applicable — no backend code touched | ✅ N/A |
| P10 (YAGNI / simplicity) | New surface area is deliberately minimal: one new presentational component (the brand panel) justified because it's a visually distinct, reusable-in-shape concern; the password-visibility toggle stays local `useState` inside the page rather than a new hook/store | ✅ Pass |
| P11 (Frontend: feature-oriented, typed, spec-driven) | Directly governs this feature — see rows below | ✅ Pass, with explicit translation decisions (research.md) |
| UI & Styling (Full-Stack §2): Tailwind + Radix/shadcn only, `lucide-react` icons only, no standard CSS / other icon libs without approval | The approved design reference used raw `<style>` CSS and hand-drawn inline SVG icons because the design-canvas tool cannot import this app's real stack. **This plan does not port that markup** — it re-expresses the same visual result in Tailwind utility classes and `lucide-react` icons (research.md Decisions 1–4) | ✅ Pass (translation, not violation) |
| Forms & Validation (P11 / Full-Stack §2): React Hook Form + Zod | The existing `loginSchema` (Zod) and `useForm` call in `login-page.tsx` are kept as-is; only a local, non-form `useState` is added for password visibility (research.md Decision 2) | ✅ Pass |
| Zero Trust Validation (Full-Stack §5) | Unchanged — the backend already re-validates independently; this feature does not touch that boundary | ✅ N/A (no change) |
| Accessibility (P11 / Full-Stack §2) | New requirements FR-010 (aria-invalid, live-region roles, accessible toggle label) are additive accessibility improvements over the current page, not a regression | ✅ Pass |
| Testing hierarchy (Full-Stack §4) | Login currently has zero component-level test coverage (only e2e). This feature adds a component test file (research.md Decision 7) and updates the one e2e assertion whose expected text intentionally changes (research.md Decision 6) | ✅ Pass |

No violations requiring justification — Complexity Tracking table is not needed for this feature.

## Project Structure

### Documentation (this feature)

```text
specs/024-login-page-redesign/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory for this feature: it makes no change to any interface. The one existing contract this page depends on (`POST /auth/login`) is already documented at `specs/002-dashboard-shell/contracts/auth.md` and is unchanged by this work.

### Source Code (repository root)

```text
frontend/
├── src/
│   └── auth/
│       ├── login-page.tsx          # Rewritten: two-panel layout, same form logic
│       ├── login-brand-panel.tsx   # New: presentational AURA hero panel + compact mobile lockup
│       ├── login-page.test.tsx     # New: component tests (validation, error, success, a11y states)
│       ├── api-client.ts           # Unchanged
│       └── auth-store.ts           # Unchanged
└── e2e/
    └── login-to-dashboard.spec.ts  # One assertion updated (heading copy), rest unchanged
```

No backend directory is touched. No new routes, dependencies, or database changes.

**Structure Decision**: Existing web application structure (`frontend/` + `backend/`), feature-oriented per P11. This work stays entirely inside the already-established `frontend/src/auth/` feature slice, adding one small presentational component alongside the existing page rather than introducing a new top-level folder or a shared/generic component, consistent with P10 (no abstraction beyond what today's single-page need justifies).

## Complexity Tracking

> No Constitution Check violations were found for this feature — this table is intentionally empty.
