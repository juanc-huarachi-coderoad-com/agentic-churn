---

description: "Task list template for feature implementation"
---

# Tasks: Aura Orb Heartbeat Redesign

**Input**: Design documents from `/specs/020-aura-orb-heartbeat/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/aura-risk-orb-component.md, quickstart.md

**Tests**: Not explicitly requested in spec.md as a TDD approach. Test-file updates below are
included only where they are *required* to keep the suite compiling/green against the new
component contract (dropped `score` prop, removed score text, new animation class) — see
contracts/aura-risk-orb-component.md "Test contract".

**Organization**: Tasks are grouped by user story (P1/P2/P3 from spec.md). All three stories
touch the same two source files (`aura-risk-orb.tsx`, `aura-risk-orb.test.tsx`), so — despite
each being independently *testable* in isolation — the phases must be implemented in P1 → P2
→ P3 order to avoid conflicting in-flight edits to the same file (see Dependencies below).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Web app, frontend-only feature — all paths are under `frontend/src/`, per plan.md's Project
Structure.

---

## Phase 1: Setup

**Purpose**: Get a live, comparable view of the component before changing it. No new
dependencies to install (plan.md Technical Context — no new npm packages).

- [ ] T001 Run `npm run dev` in `frontend/` and open the dashboard so
      `frontend/src/dashboard/aura-risk-orb.tsx` can be visually compared against
      `base/aura.png` while iterating on the tasks below (**not run this session** — the
      Chrome browser automation tool was not connected; implementation instead proceeded
      from a standalone static-CSS preview, see T011 note)

---

## Phase 2: Foundational

*None.* This feature has no shared infrastructure that multiple stories depend on beyond
the live-preview step in Phase 1 — proceed directly to Phase 3.

---

## Phase 3: User Story 1 - Polished, glowing risk indicator (Priority: P1) 🎯 MVP

**Goal**: Replace the flat gradient circle with a glossy, luminous sphere (soft highlight +
gentle outer glow) matching `base/aura.png`, with color still driven solely by `band`.

**Independent Test**: Render `<AuraRiskOrb band="healthy" />`, `band="watch"`, and
`band="at_risk"` (e.g. in the running dashboard) and confirm each shows a glossy highlight
and soft outer bloom consistent with the reference image, colored per band, with the
existing `data-testid="aura-risk-orb"` / `--orb-color` contract unchanged.

### Implementation for User Story 1

- [X] T002 [US1] In `frontend/src/dashboard/aura-risk-orb.tsx`, rebuild the orb's visual
      layers (radial-gradient body + highlight, soft outer `box-shadow`/bloom) off the
      existing `--orb-color` custom property to match the glossy-sphere look of
      `base/aura.png` (research.md Decision 3; contracts/aura-risk-orb-component.md
      "Rendered output contract")
- [X] T003 [US1] Update the file-level comment above `AuraRiskOrb` in
      `frontend/src/dashboard/aura-risk-orb.tsx` to describe the new glossy/glow treatment,
      replacing the stale "gradient-colored risk indicator" description (depends on T002)

**Checkpoint**: The orb visually matches the reference look in all three bands; existing
`aura-risk-orb.test.tsx` color assertions (`colors the orb from BAND_CHART_COLOR...`,
`changes color across different bands`) still pass unmodified, since `--orb-color` and
`BAND_CHART_COLOR[band]` are untouched.

---

## Phase 4: User Story 2 - Living, breathing pulse (Priority: P2)

**Goal**: The orb continuously animates a slow, elegant pulse, and that animation is paused
or minimized when the user prefers reduced motion.

**Independent Test**: View the orb for a few seconds and observe a smooth, slow pulse with
no interaction. In Chrome DevTools, emulate `prefers-reduced-motion: reduce` (quickstart.md)
and confirm the pulse stops or is minimized while the orb still renders correctly.

### Implementation for User Story 2

- [X] T004 [P] [US2] In `frontend/src/index.css`, add a `--animate-aura-pulse` entry to the
      `@theme` block with its `@keyframes` (slow, subtle scale and/or glow "breathing", e.g.
      ~4s ease-in-out infinite — exact timing tuned to read as elegant, not mechanical)
      (research.md Decision 1)
- [X] T005 [US2] In `frontend/src/dashboard/aura-risk-orb.tsx`, apply the
      `motion-safe:animate-aura-pulse` utility class to the orb root so the pulse runs
      continuously but is inert under `prefers-reduced-motion: reduce` (research.md
      Decision 2; contracts/aura-risk-orb-component.md) — depends on T002 (same JSX region)
      and pairs with T004 for the animation to actually render
- [X] T006 [US2] In `frontend/src/dashboard/aura-risk-orb.test.tsx`, add a test asserting
      the orb root carries the pulse animation utility class for every band (contracts/
      aura-risk-orb-component.md "New assertions this feature must add") — depends on T005

**Checkpoint**: The orb pulses continuously in the running app; the new class-presence test
passes; reduced-motion emulation stops/minimizes the pulse (manual check per quickstart.md).

---

## Phase 5: User Story 3 - Score removed from the orb face (Priority: P3)

**Goal**: No numeric score is displayed on the orb; the `score` prop is dropped entirely
since it has no remaining use once display text is removed (research.md Decision 4).

**Independent Test**: Render the orb for any band and confirm no digits appear anywhere on
it; `<AuraRiskOrb band={...} />` type-checks with only `band` passed (no `score` argument
accepted or required).

### Implementation for User Story 3

- [X] T007 [US3] In `frontend/src/dashboard/aura-risk-orb.tsx`, remove `score` from
      `AuraRiskOrbProps` and delete the `<span>{Math.round(score)}</span>` display
      (contracts/aura-risk-orb-component.md "Props") — depends on T005 (same file)
- [X] T008 [US3] In `frontend/src/dashboard/dashboard-page.tsx`, update the
      `<AuraRiskOrb score={data.score_block.score} band={data.score_block.band} />` call
      site to pass only `band` (contracts/aura-risk-orb-component.md "Consumer contract") —
      depends on T007
- [X] T009 [US3] In `frontend/src/dashboard/aura-risk-orb.test.tsx`, remove the two obsolete
      score-display tests (`renders the given score`, `rounds a fractional score for
      display`) and their now-invalid `score={...}` prop usage, and add a test asserting no
      numeric text renders on the orb for any band (contracts/aura-risk-orb-component.md
      "Test contract") — depends on T006 (same file) and T007

**Checkpoint**: All three user stories are complete — the orb is a glossy, continuously
pulsing, band-colored sphere with no numeric text, and the numeric score remains visible
elsewhere on the dashboard via `ChurnRiskOverviewCard`/`ScoreBlock` (unaffected by this
feature).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the full Definition of Done across all three stories together.

- [X] T010 [P] Run `npm run typecheck`, `npm run lint`, and `npm run test` in `frontend/`
      and fix any failures (Definition of Done, P11 / Full-Stack Engineering §1) — all
      green: `tsc -b --noEmit` clean, `eslint .` 0 errors (7 pre-existing warnings
      unrelated to this feature), 117/117 tests passing across the full suite
- [ ] T011 Walk through the remaining manual checks in
      `specs/020-aura-orb-heartbeat/quickstart.md` (visual comparison against
      `base/aura.png`, reduced-motion emulation, responsiveness across widths) — **not
      completed this session**: the Chrome browser automation tool was not connected, so
      the running dashboard could not be visually inspected. A standalone static-CSS
      preview of the exact gradient/glow/pulse values used in the component was built at
      `/private/tmp/claude-504/.../scratchpad/aura-preview.html` for a quick manual eyeball,
      but this does not substitute for checking the real component in the real app. The
      user should run through this task manually (`npm run dev` in `frontend/`, compare
      against `base/aura.png`, emulate `prefers-reduced-motion: reduce` in DevTools).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: None — skipped for this feature.
- **User Story 1 (Phase 3)**: Depends on Setup only. Establishes the visual baseline every
  later phase edits on top of.
- **User Story 2 (Phase 4)**: Depends on User Story 1 being applied first (T005 edits the
  same JSX region T002 introduced).
- **User Story 3 (Phase 5)**: Depends on User Story 2 being applied first (T007/T009 edit
  the same files T005/T006 touched).
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

Unlike a typical multi-entity feature, these three stories are **not file-independent** —
they all edit `aura-risk-orb.tsx` (and, from US2 onward, `aura-risk-orb.test.tsx`) in place,
and spec.md's own P3 rationale says the score-removal only "look[s] intentional" once P1's
redesign exists. Implement strictly in priority order: **US1 → US2 → US3**. Each phase's
Checkpoint is still independently verifiable (you can stop after any phase and have a
working, demonstrable increment), which preserves the *testability* goal even though the
*implementation* order is fixed.

### Parallel Opportunities

- T004 (`frontend/src/index.css`) can be done in parallel with T002/T003
  (`frontend/src/dashboard/aura-risk-orb.tsx`) — different files, and Tailwind's CSS-first
  `@theme` registration has no compile-time coupling to where the utility class is later
  referenced.
- T010's typecheck/lint/test commands can run in parallel with each other (independent
  processes) once all implementation tasks are done.
- Otherwise, within a story, tasks touching `aura-risk-orb.tsx` or `aura-risk-orb.test.tsx`
  are sequential (same file).

---

## Parallel Example: User Story 2

```bash
# T004 and T002/T003 touch different files and can be done in parallel:
Task: "Add --animate-aura-pulse keyframe in frontend/src/index.css"
Task: "Rebuild orb visual layers in frontend/src/dashboard/aura-risk-orb.tsx"  # (US1, T002)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (glossy/glow visual redesign)
3. **STOP and VALIDATE**: Compare against `base/aura.png` in the running dashboard for all
   three bands
4. Demo if ready — this alone is already a meaningful visual upgrade

### Incremental Delivery

1. Setup → Phase 3 (US1) → validate → demo (visual redesign only)
2. Phase 4 (US2) → validate (pulse + reduced-motion) → demo (orb now feels "alive")
3. Phase 5 (US3) → validate (score gone, type-checks) → demo (final, decluttered orb)
4. Phase 6: Polish — full typecheck/lint/test + quickstart walkthrough

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Despite the [P] labels being sparse here (small, tightly-coupled component), each story's
  Checkpoint is independently demonstrable — the constraint is implementation *order*, not
  testability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
