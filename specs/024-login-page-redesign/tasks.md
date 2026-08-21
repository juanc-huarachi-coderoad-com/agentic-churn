---

description: "Task list for feature implementation"
---

# Tasks: Login Page Redesign

**Input**: Design documents from `/specs/024-login-page-redesign/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Test tasks are included — `research.md` Decision 7 and `plan.md`'s Constitution Check
commit this feature to adding component-level test coverage for the login page (currently
zero), alongside the existing e2e suite.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent
verification of each story's acceptance scenarios, even though most tasks touch the same
single page component.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

This is the existing web app structure (`backend/` + `frontend/`); this feature touches only
`frontend/`, specifically the existing `frontend/src/auth/` feature slice and
`frontend/e2e/`.

---

## Phase 1: Setup

**Purpose**: Resolve the one open unknown before any implementation begins

- [x] T001 Verify the exact `lucide-react` export names for the icons this feature needs
      (user, lock, eye, eye-off, warning-triangle, success-check) against the installed
      version by checking `frontend/node_modules/lucide-react/dist/lucide-react.d.ts` (or
      equivalent type declarations) — confirm the real export names (e.g. `TriangleAlert` vs.
      `AlertTriangle`, `CircleCheck` vs. `CheckCircle2`) so later tasks import icons that
      actually exist (constitution: `lucide-react` is the only permitted icon library, per
      research.md Decision 3).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Replace the current single-column form shell with the two-panel, responsive
layout scaffold that every user story renders into. No story can be demonstrated until this
exists.

**⚠️ CRITICAL**: Complete this phase before starting any user story phase.

- [x] T002 Rewrite the page container in `frontend/src/auth/login-page.tsx`: replace the
      current `<main className="flex min-h-svh items-center justify-center">` single-column
      markup with a two-slot flex layout — a brand-panel slot (`hidden lg:flex`, matching the
      codebase's existing `lg` breakpoint convention per research.md Decision 5) and a
      form-panel slot that stays full-width below `lg`. Leave the existing form's fields,
      validation, and submit logic untouched inside the form-panel slot for now.
- [x] T003 [P] Create `frontend/src/auth/login-brand-panel.tsx` — a new presentational
      component rendering: the AURA orb hero (Tailwind classes for shape/layout, an inline
      `style` prop for the computed radial-gradient/box-shadow, and the existing
      `motion-safe:animate-aura-pulse` utility — following the exact pattern of
      `frontend/src/dashboard/aura-risk-orb.tsx`, per research.md Decision 4), the
      "Churn Prediction & Sentiment Agent" eyebrow label, the "AURA" wordmark, and the product
      tagline. Export a second, compact variant (or a `compact` prop) for the collapsed mobile
      lockup (small orb + "AURA" wordmark only).
- [x] T004 Wire `LoginBrandPanel` into the layout scaffold from T002: the full panel rendered
      in the desktop brand-panel slot, the compact variant rendered above the form on narrow
      viewports, in `frontend/src/auth/login-page.tsx`.

**Checkpoint**: The page renders the new two-panel/responsive shell with the brand panel in
place; the existing form still behaves exactly as before inside the new form slot.

---

## Phase 3: User Story 1 - A branded, professional first impression (Priority: P1) 🎯 MVP

**Goal**: The login page visually matches the approved AURA design — branded panel, restyled
form chrome, responsive collapse — satisfying FR-001, FR-002, FR-009, SC-001, SC-003.

**Independent Test**: Load `/login` at a desktop width and confirm the two-panel branded
layout; narrow the viewport below the `lg` breakpoint and confirm the compact lockup replaces
the brand panel with no layout breakage down to 320px.

### Tests for User Story 1

- [x] T005 [P] [US1] Create `frontend/src/auth/login-page.test.tsx` (new file) with initial
      tests asserting: the "AURA" wordmark and tagline text render, and the page heading has
      accessible name "Welcome back" (Testing Library, `render` + `screen.getByRole('heading',
      …)`, following the style of the existing `frontend/src/auth/protected-route.test.tsx`).

### Implementation for User Story 1

- [x] T006 [US1] Update the form panel's heading copy in `frontend/src/auth/login-page.tsx`
      from `<h1>Log in</h1>` to an `<h1>` reading "Welcome back" with a subtitle "Log in to
      your AURA workspace" beneath it.
- [x] T007 [US1] Restyle the username/password `<input>` elements in
      `frontend/src/auth/login-page.tsx` into the icon-led "input shell" treatment (bordered
      container, `rounded-md`, `border-neutral-300`, focus-visible ring), adding leading
      `User`/`Lock` icons from `lucide-react` through the existing `Icon` wrapper
      (`frontend/src/components/ui/icon.tsx`), using the export names confirmed in T001.
- [x] T008 [US1] Replace the current ad hoc `<button type="submit">` in
      `frontend/src/auth/login-page.tsx` with the shared `Button` component
      (`frontend/src/components/ui/button.tsx`, `variant="primary"`, full width), preserving
      the existing `disabled={isSubmitting}` and `"Logging in…"` / `"Log in"` label logic
      unchanged.
- [x] T009 [P] [US1] Update the first test in `frontend/e2e/login-to-dashboard.spec.ts` to
      assert `page.getByRole('heading', { name: 'Welcome back' })` in place of `'Log in'`
      (research.md Decision 6); leave every other assertion in that file unchanged.

**Checkpoint**: User Story 1 is independently verifiable — the page is visually redesigned per
the approved reference, and the one intentionally-changed e2e assertion matches it.

---

## Phase 4: User Story 2 - Familiar, working sign-in behavior (Priority: P1)

**Goal**: The existing authentication behavior (fields, validation, error message, redirect)
is fully preserved under the new visual treatment — FR-003 to FR-007, FR-011, SC-002.

**Independent Test**: Using only the visible UI, submit empty fields, then a rejected
username/password pair, then a valid pair, and confirm each behaves exactly as the
pre-redesign page did.

### Tests for User Story 2

- [x] T010 [US2] Add tests to `frontend/src/auth/login-page.test.tsx` (appends to the file
      created in T005): submitting with both fields empty shows "Username is required" and
      "Password is required" and makes no `fetch` call; submitting with a mocked `fetch`
      resolving to a non-OK response shows "Invalid username or password."; submitting with a
      mocked OK response calls the auth store's `login()` and triggers navigation to
      `/dashboard`; editing either field after a shown root error clears that error. Mock
      `global.fetch` with Vitest (`vi.stubGlobal('fetch', vi.fn(...))`), consistent with this
      repo's existing Vitest conventions.

### Implementation for User Story 2

- [x] T011 [US2] Carry the existing `loginSchema`, `useForm` call, and `onSubmit` handler
      (the `apiFetch('/auth/login', …)` call, `setError('root', …)`, `login(data.token)`,
      `navigate('/dashboard')`) in `frontend/src/auth/login-page.tsx` through unchanged, wiring
      them to the restyled markup: the root-error banner reads `errors.root?.message`, and the
      inline field errors read `errors.username?.message` / `errors.password?.message`.
- [x] T012 [US2] Restyle the root-error banner in `frontend/src/auth/login-page.tsx` into the
      bordered/tinted banner treatment from the approved design (red-tinted background, warning
      icon), shown/hidden exactly when `errors.root` is set/unset — no change to that
      condition.

**Checkpoint**: User Stories 1 and 2 both work independently — the page is redesigned and
every existing sign-in outcome behaves identically to before.

---

## Phase 5: User Story 3 - Comfortable, accessible interaction (Priority: P2)

**Goal**: Password visibility toggle, focus states, and accessible error wiring — FR-008,
FR-010, SC-004.

**Independent Test**: Tab through the form using only the keyboard, toggle password
visibility, and confirm focus rings, `aria-invalid`, and the toggle's accessible label all
behave correctly.

### Tests for User Story 3

- [x] T013 [US3] Add tests to `frontend/src/auth/login-page.test.tsx`: clicking the password
      visibility toggle switches the password `<input>`'s `type` attribute between
      `"password"` and `"text"` and switches the toggle button's accessible name between "Show
      password" and "Hide password"; a field with a validation error present has
      `aria-invalid="true"`.

### Implementation for User Story 3

- [x] T014 [US3] Add a local `passwordVisible` boolean (`useState`, data-model.md) and a
      visibility-toggle `<button type="button">` (lucide `Eye`/`EyeOff` via the `Icon`
      wrapper, using the names confirmed in T001) inside the password field's input shell in
      `frontend/src/auth/login-page.tsx`.
- [x] T015 [US3] Add `aria-invalid={!!errors.username}` / `aria-invalid={!!errors.password}` to
      the two `<input>` elements, and an appropriate live-region role (`role="alert"` on the
      error banner, `role="status"` if a success state is shown) in
      `frontend/src/auth/login-page.tsx`.
- [x] T016 [US3] Verify and, if needed, adjust `focus-visible:` ring styling on both inputs and
      the visibility-toggle button in `frontend/src/auth/login-page.tsx` so keyboard focus is
      clearly visible at every stop, matching the approved design's focus treatment.

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all stories, per `quickstart.md`

- [x] T017 [P] Run `pnpm --dir frontend typecheck` and `pnpm --dir frontend lint`, fixing any
      issues raised by the new/changed files in `frontend/src/auth/`.
- [x] T018 [P] Run `pnpm --dir frontend test` and confirm the full `login-page.test.tsx` suite
      (T005, T010, T013) passes.
- [x] T019 Run `pnpm --dir frontend test:e2e` against a seeded backend
      (`specs/002-dashboard-shell/quickstart.md` §3) and confirm all four scenarios in
      `frontend/e2e/login-to-dashboard.spec.ts` pass, including the updated heading assertion.
- [x] T020 [P] Execute the manual QA checklist in `specs/024-login-page-redesign/quickstart.md`
      steps 1–8 (desktop layout, responsive collapse to 320px, keyboard-only pass).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on T001 (icon names needed before T007/T014 import
  icons, though T002/T003/T004 themselves don't import icons yet) — BLOCKS all user stories.
- **User Stories (Phase 3–5)**: All depend on Foundational (Phase 2) completion. US1 and US2
  are both P1 and share the most file overlap (`login-page.tsx`) — implement sequentially in
  the order below even though they're organized as separate stories for traceability. US3
  builds on the markup both US1 and US2 leave in place (the input shells, the banner).
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational. No dependency on US2/US3, but shares
  `login-page.tsx` with both — sequence, don't parallelize, to avoid merge conflicts in the
  same file.
- **User Story 2 (P1)**: Starts after Foundational; in practice implemented after US1 since
  both edit `login-page.tsx`'s form section. Independently testable per its own acceptance
  scenarios regardless of order.
- **User Story 3 (P2)**: Starts after Foundational; builds visually on the input-shell markup
  US1 introduces and the error/success conditions US2 wires up, so implement it last.

### Within Each User Story

- Tests are written before/alongside that story's implementation tasks (append to the shared
  `login-page.test.tsx`) and should fail until that story's implementation tasks land.
- Story complete before moving to the next.

### Parallel Opportunities

- T003 (new `login-brand-panel.tsx` file) can run in parallel with T002 (edits
  `login-page.tsx`) — different files.
- T009 (edits the e2e spec file) can run in parallel with T006–T008 (edit `login-page.tsx`) —
  different files.
- T017, T018, T020 in Polish are independent commands and can run in parallel; T019 needs a
  seeded backend running and is best run on its own.

---

## Parallel Example: Foundational Phase

```bash
# T002 and T003 touch different files and can proceed together:
Task: "Rewrite the page container in frontend/src/auth/login-page.tsx"
Task: "Create frontend/src/auth/login-brand-panel.tsx"
# T004 then wires them together and must wait for both.
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 together)

Both are Priority P1 in `spec.md` — the redesign isn't a real MVP if it looks right but breaks
login, or works but still looks like the old bare form. Treat T001–T012 as the MVP slice:

1. Complete Phase 1: Setup (T001).
2. Complete Phase 2: Foundational (T002–T004).
3. Complete Phase 3: User Story 1 (T005–T009).
4. Complete Phase 4: User Story 2 (T010–T012).
5. **STOP and VALIDATE**: run the Phase 3 + Phase 4 independent tests together — redesigned
   page, unchanged sign-in behavior.

### Incremental Delivery

1. Setup + Foundational → shell ready.
2. US1 + US2 → the redesigned, functionally-identical login page (MVP).
3. US3 → accessibility/comfort polish (visibility toggle, aria wiring, focus states) on top.
4. Polish phase → full automated + manual validation pass.

---

## Notes

- Almost every implementation task touches the same file
  (`frontend/src/auth/login-page.tsx`) by design — this is a focused redesign of one existing
  page, not a multi-service feature. `[P]` is used sparingly here, only where tasks genuinely
  touch different files.
- Verify each story's tests fail before that story's implementation tasks, then pass after.
- Commit after each task or logical group.
- Stop at either checkpoint (after Phase 4, after Phase 5) to validate independently before
  continuing.
