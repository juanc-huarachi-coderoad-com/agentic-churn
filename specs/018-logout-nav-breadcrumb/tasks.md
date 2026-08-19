---

description: "Task list for feature implementation"
---

# Tasks: Sidebar Logout, Nav Tooltips & Breadcrumb Trail

**Input**: Design documents from `/specs/018-logout-nav-breadcrumb/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/README.md, quickstart.md (all present)

**Tests**: Included — every new/changed frontend file gets a co-located unit/component test, matching this repo's established convention (`sidebar.test.tsx`, `dialog.test.tsx`, `profile-editor-form.test.tsx`) and constitution P11 ("every feature ships unit + component tests"); one Playwright e2e covers the logout flow specifically because it's the one business-critical, security-relevant path this feature adds (P11 "business-critical flows get end-to-end coverage").

**Organization**: Tasks are grouped by user story (spec.md P1–P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact and relative to the repository root

## Path Conventions

Web app — `frontend/src/`, per plan.md's Project Structure. This feature is frontend-only;
no `backend/` file is created or modified (it reuses the existing, unchanged
`POST /auth/logout` endpoint).

<!-- Sample tasks from the template have been replaced with this feature's actual tasks. -->

## Phase 1: Setup

**Purpose**: Confirm a clean baseline and bring in the two new dependencies before touching any feature code.

- [X] T001 Run `cd frontend && pnpm typecheck && pnpm lint && pnpm test` and confirm all green before making any change
- [X] T002 [P] Add `@radix-ui/react-tooltip` to `frontend/package.json` dependencies and run `pnpm install` (research.md Decision 1)
- [X] T003 [P] Add `@radix-ui/react-dropdown-menu` to `frontend/package.json` dependencies and run `pnpm install` (research.md Decision 2)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Make the sidebar (and, once US3 lands, the breadcrumb) appear on all three
authenticated screens instead of Dashboard-only, and stand up the two new Radix UI
primitives. FR-001 and FR-010 both say "every authenticated screen" — today that's only true
for Dashboard, so this is genuinely blocking for every story below, not just convenient setup.

**⚠️ CRITICAL**: No user story work can begin until T004–T014 are complete.

- [X] T004 [P] Create `frontend/src/components/ui/tooltip.tsx`: thin Radix Tooltip wrapper (`TooltipProvider`, `Tooltip`, `TooltipTrigger`, `TooltipContent`), matching `frontend/src/components/ui/dialog.tsx`'s existing wrapper shape (typed pass-through around the Radix primitive plus the project's own styling classes) (research.md Decision 1) (depends on T002)
- [X] T005 [P] Create `frontend/src/components/ui/dropdown-menu.tsx`: thin Radix DropdownMenu wrapper (`DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`), same pattern as T004 (research.md Decision 2) (depends on T003)
- [X] T006 Extract the inline `DESTINATIONS` array out of `frontend/src/nav/sidebar.tsx` into a new `frontend/src/nav/destinations.ts` (export the `Destination` interface and `DESTINATIONS: Destination[]` — same three entries, unchanged: Dashboard/`LayoutGrid`/`/dashboard`, Coverage/`Radar`/`/coverage`, Profile/`UserRound`/`/profile`); update `sidebar.tsx` to import `DESTINATIONS` from it instead of declaring it inline (data-model.md "Destination", research.md Decision 6)
- [X] T007 Create `frontend/src/nav/app-shell.tsx` exporting `AppShell({ children }: { children: ReactNode })`: lift the existing `<div className="flex h-screen ...">`\<Sidebar/>` + `<main>` wrapper out of `dashboard-page.tsx` into this component, rendering `<Sidebar />` beside a `<main>` that wraps `children` (research.md Decision 5). No `Breadcrumb` yet — US3 adds it in T026.
- [X] T008 [P] Create `frontend/src/nav/app-shell.test.tsx`: render `AppShell` with arbitrary `children` inside `MemoryRouter`; assert the sidebar's three destination links render and that the `children` content renders inside the main content area (depends on T007)
- [X] T009 [P] Modify `frontend/src/coverage/coverage-page.tsx`: wrap the existing `<main className="p-8">...</main>` return value in `<AppShell>` instead of returning a bare `<main>` (depends on T007)
- [X] T010 [P] Create `frontend/src/coverage/coverage-page.test.tsx` (no test file exists for this page today): render `CoveragePage` inside `MemoryRouter` + `QueryClientProvider` with `apiFetch` mocked; assert the sidebar's three destination links render and the existing "System health" heading/content still renders (depends on T009)
- [X] T011 [P] Modify `frontend/src/profile-editor/profile-editor-form.tsx`: wrap the existing `<main className="mx-auto max-w-2xl p-8">...</main>` return value in `<AppShell>` instead of returning a bare `<main>` (depends on T007)
- [X] T012 [P] Modify `frontend/src/profile-editor/profile-editor-form.test.tsx`: wrap `renderForm()`'s rendered tree in `MemoryRouter` (now required because `AppShell` renders `Sidebar`, which uses `NavLink`/`useLocation`) — no assertion changes otherwise (depends on T011)
- [X] T013 Modify `frontend/src/dashboard/dashboard-page.tsx`: replace its private `<div className="flex h-screen ...">`\<Sidebar/>` + `<main>` markup with `<AppShell>` wrapping the same `<main>` content (identical visual result, now via the shared component) (depends on T007)
- [X] T014 Modify `frontend/src/dashboard/dashboard-page.test.tsx` only if an assertion breaks against the `AppShell`-wrapped markup (existing sidebar-link and content assertions should otherwise pass unchanged) (depends on T013)

**Checkpoint**: Foundation ready — `Sidebar` (behavior unchanged) now renders on Dashboard,
Coverage, and Profile alike; all tests green. User story implementation can now begin.

---

## Phase 3: User Story 1 - Sign out from the account menu (Priority: P1) 🎯 MVP

**Goal**: A bottom-left account icon-button opens a menu whose only item is "Log out";
selecting it revokes the token server-side and returns the user to `/login` (FR-001–005).

**Independent Test**: From any of the three screens (already sidebar-equipped via Phase 2),
click the account icon-button, confirm the menu shows exactly "Log out" and nothing else,
click it, confirm you land on `/login`, and confirm the browser back button no longer shows
protected content.

### Tests for User Story 1

- [X] T015 [P] [US1] Create `frontend/src/auth/use-logout.test.ts`: assert the hook's returned function calls `apiFetch('/auth/logout', ...)` (POST), then calls `useAuthStore.getState().logout()`, then navigates to `/login`; assert it still clears state and navigates to `/login` even when the `apiFetch` call rejects (research.md Decision 3)
- [X] T016 [P] [US1] Create `frontend/src/nav/account-menu.test.tsx`: assert clicking the account icon-button opens a menu containing exactly one item, "Log out" — no others; assert clicking outside the menu or pressing Escape closes it without invoking logout; assert clicking "Log out" invokes the logout action (mock `useLogout`)

### Implementation for User Story 1

- [X] T017 [US1] Create `frontend/src/auth/use-logout.ts` exporting `useLogout()`: returns a callback that performs a best-effort `POST /auth/logout` via `apiFetch` (catch/ignore failures — never block on it), then calls `useAuthStore.getState().logout()`, then navigates to `/login` via `useNavigate()` (research.md Decision 3) (depends on T015)
- [X] T018 [US1] Create `frontend/src/nav/account-menu.tsx` exporting `AccountMenu()`: a bottom-left icon-button using a generic `lucide-react` account/user icon (Clarification 2026-08-19 — no photo, no online-status dot) as the `DropdownMenuTrigger` (T005), with a `DropdownMenuContent` containing exactly one `DropdownMenuItem`, "Log out", wired to `useLogout()` (T017) (depends on T005, T017, T016)
- [X] T019 [US1] Modify `frontend/src/nav/sidebar.tsx`: mount `<AccountMenu />` pinned to the bottom of the sidebar's flex column (`mt-auto`), below the three destination links (FR-001) (depends on T018)
- [X] T020 [US1] Modify `frontend/src/nav/sidebar.test.tsx`: assert `AccountMenu`'s trigger button renders inside `Sidebar`, after the three destination links (depends on T019)

**Checkpoint**: Logout works end-to-end from Dashboard, Coverage, and Profile — User Story 1
is independently functional and testable.

---

## Phase 4: User Story 2 - Recognize the current section in the main menu (Priority: P2)

**Goal**: Hovering or focusing any of the three main sidebar icons shows a tooltip with its
name; the currently-active destination is distinguished by more than color alone (FR-006–009).

**Independent Test**: Hover (and separately, keyboard-focus) each of the three sidebar icons
and confirm a tooltip names its destination; navigate between destinations and confirm the
"active" visual cue moves and is visible as a shape change, not only a color change.

### Tests for User Story 2

- [X] T021 [P] [US2] Modify `frontend/src/nav/sidebar.test.tsx`: assert each destination link has an accessible tooltip exposing its `label` on hover/focus (via Radix Tooltip's `role="tooltip"` content), and assert the active link carries a distinguishing class/attribute beyond its existing background-color change (e.g. an accent-bar element/class), present only on the active link

### Implementation for User Story 2

- [X] T022 [US2] Modify `frontend/src/nav/sidebar.tsx`: wrap the destination list in a single `TooltipProvider`, and wrap each destination's icon in `Tooltip`/`TooltipTrigger`/`TooltipContent` (T004) showing `destination.label` (T006), positioned so it never covers the icon (research.md Decision 1) (depends on T004, T006, T021)
- [X] T023 [US2] In the same file, add a non-color active-state cue (e.g. a small left accent-bar element rendered only when `isActive`) alongside the existing background/text color change; `aria-current="page"` is already provided automatically by `react-router`'s `NavLink` and needs no new code (research.md Decision 4, FR-008) (depends on T022)

**Checkpoint**: Tooltips and the non-color active indicator work on Dashboard, Coverage, and
Profile — User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - See a consistent location trail on every screen (Priority: P3)

**Goal**: Every screen shows a "Home > [current screen]" breadcrumb styled like
`base/mockup-client-profile.jpg`; the Home/default screen itself shows only a non-clickable
"Home" label (FR-010–014).

**Independent Test**: Visit each of the three screens and confirm the breadcrumb; on
Dashboard specifically, confirm it shows only "Home" with no second segment and no link.

### Tests for User Story 3

- [X] T024 [P] [US3] Create `frontend/src/nav/breadcrumb.test.tsx`: assert on `/coverage` it renders a clickable "Home" segment (`href="/dashboard"`) followed by a "Coverage" segment with Coverage's icon; assert the same shape on `/profile` with Profile's icon; assert on `/dashboard` it renders only a single, non-clickable "Home" label — no second segment, no link (FR-010–012, Clarification 2026-08-19) (depends on T006)

### Implementation for User Story 3

- [X] T025 [US3] Create `frontend/src/nav/breadcrumb.tsx` exporting `Breadcrumb()`: read `useLocation().pathname`; render a fixed `Home` (`lucide-react`) icon + "Home" segment (a link to `/dashboard`, unless the current path already is `/dashboard`, in which case render it as a non-clickable label and stop — no second segment); otherwise, after a separator, render the matching `DESTINATIONS` (T006) entry's icon + `label` as a non-clickable current segment — reuse the same `label` string the sidebar tooltip uses for that route (e.g. "Profile" on `/profile`), not a separate hardcoded string, so the two can never say different things for the same page; style spacing/typography/separator to match `base/mockup-client-profile.jpg` (data-model.md "Breadcrumb trail", research.md Decisions 6–7) (depends on T006, T024)
- [X] T026 [US3] Modify `frontend/src/nav/app-shell.tsx`: render `<Breadcrumb />` at the top of the main content area, above `children` (FR-010) (depends on T025)
- [X] T027 [US3] Modify `frontend/src/nav/app-shell.test.tsx`: assert `Breadcrumb` renders inside `AppShell`'s main content area, above `children` (depends on T026)

**Checkpoint**: All three user stories are independently functional — breadcrumb trail is
visible everywhere, Dashboard shows the Home-only case correctly.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge-case hardening and end-to-end confidence across all three stories.

- [X] T028 [P] In `frontend/src/nav/breadcrumb.tsx`, add truncation/wrap styling (e.g. `truncate`/`min-w-0` on the current-screen segment) so a long screen name degrades gracefully on narrow viewports without overlapping other content (FR-014)
- [X] T029 [P] Create `frontend/e2e/logout.spec.ts` (Playwright): log in, click the account icon-button, click "Log out", assert the app lands on `/login`, then assert navigating back does not show protected content (constitution P11 "business-critical flows get end-to-end coverage")
- [X] T030 Run through `specs/018-logout-nav-breadcrumb/quickstart.md`'s manual validation scenarios (all three User Story sections) and confirm each expected outcome
- [X] T031 Run `cd frontend && pnpm typecheck && pnpm lint && pnpm test && pnpm test:e2e` and confirm all green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T002/T003 for T004/T005) — BLOCKS all user
  stories, because FR-001/FR-010 require the sidebar/breadcrumb on every screen, and today
  only Dashboard has any nav chrome at all.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - US1 (T015–T020) and US2 (T021–T023) both edit `sidebar.tsx` — do them in priority order
    (US1 before US2) rather than in parallel, to avoid overlapping edits to the same file.
  - US3 (T024–T027) is independent of US1/US2's `sidebar.tsx` edits (it only touches
    `breadcrumb.tsx` and `app-shell.tsx`) and could run in parallel with either, if staffed.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependency on US2/US3.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — touches the same file as
  US1 (`sidebar.tsx`), so build after US1 if working sequentially; otherwise independent.
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — fully independent of
  US1/US2 (different files: `breadcrumb.tsx`, `app-shell.tsx`).

### Parallel Opportunities

- T002/T003 (Setup) in parallel.
- T004/T005 (Foundational) in parallel once T002/T003 land.
- T009/T010 (Coverage) and T011/T012 (Profile) in parallel once T007/T008 land — T013/T014
  (Dashboard) can also run in parallel with those two, though it edits a file none of them
  touch.
- Within US1: T015/T016 (tests) in parallel.
- Within US3: only T024 is parallelizable on its own (T025–T027 are sequential edits to two
  files); US3 as a whole can run in parallel with US1+US2 if staffed separately, since it
  shares no file with them.

---

## Parallel Example: Foundational Phase

```bash
# Once T007 (AppShell) exists, roll it out to all three pages in parallel:
Task: "Modify frontend/src/coverage/coverage-page.tsx to render through AppShell"
Task: "Modify frontend/src/profile-editor/profile-editor-form.tsx to render through AppShell"
Task: "Modify frontend/src/dashboard/dashboard-page.tsx to render through AppShell"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — makes "every screen" true for all stories).
3. Complete Phase 3: User Story 1 (logout).
4. **STOP and VALIDATE**: run `quickstart.md`'s User Story 1 scenarios independently.
5. Demo if ready — logout is the highest-value, highest-risk gap this feature closes.

### Incremental Delivery

1. Setup + Foundational → sidebar (unchanged behavior) now ubiquitous.
2. Add User Story 1 (logout) → validate → demo (MVP).
3. Add User Story 2 (tooltips + active state) → validate → demo.
4. Add User Story 3 (breadcrumb) → validate → demo.
5. Polish (Phase 6) → full `quickstart.md` pass + e2e coverage.

---

## Notes

- [P] tasks = different files, no dependency on an incomplete task.
- [Story] label maps task to specific user story for traceability.
- US1 and US2 both edit `frontend/src/nav/sidebar.tsx` — sequential by design, not a
  parallelization opportunity between those two specific tasks even though both carry [P]
  markers relative to *other* tasks within their own story.
- Verify new/changed tests fail (or are visibly absent) before implementing, then pass after.
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story independently before moving to the next.
