---

description: "Task list template for feature implementation"
---

# Tasks: Chat Component Sender Identification Redesign

**Input**: Design documents from `/specs/021-chat-component-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (all present; no `contracts/` — no external interface change)

**Tests**: Included. The project constitution (P11, "every feature ships unit + component tests") makes this an established convention for this codebase, not an ad hoc choice — tasks extend the existing `frontend/src/ask/ask-bar.test.tsx` suite rather than introducing a new test tier.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact — this is a 3-file feature: `frontend/src/ask/ask-bar.tsx`, `frontend/src/ask/types.ts`, `frontend/src/ask/ask-bar.test.tsx`

## Path Conventions

Web app (frontend/backend split, existing). This feature touches only `frontend/src/ask/` — no backend directory involved.

---

## Phase 1: Setup

**Purpose**: Confirm a clean starting point. No new dependencies, no project initialization needed — `lucide-react`, Tailwind, Vitest/Testing Library are already installed and used by this exact component (plan.md Technical Context).

- [X] T001 Run `cd frontend && npm test -- ask-bar && npm run typecheck && npm run lint` and confirm all pass before making any change, establishing the baseline `ask-bar.tsx`/`ask-bar.test.tsx` must not regress.

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites shared by all user stories.

None. This feature is small enough (one component, one type file) that there is no shared infrastructure beyond what already exists — the sender-identity row structure itself is introduced by User Story 1 and extended by User Story 2/3, not built ahead of it. Proceed directly to Phase 3.

---

## Phase 3: User Story 1 - Instantly tell who said what (Priority: P1) 🎯 MVP

**Goal**: Every completed message (human question or assistant answer) shows a distinct sender icon and label, so a reader can identify the sender without reading the text.

**Independent Test**: Open a conversation with at least one human message and one assistant message; confirm each shows a distinct icon + label ("Human" / "AURA Assistant"), consistently positioned per role, matching `base/chatComponent.jpg`. No timestamp is required yet for this story to be considered working.

### Tests for User Story 1

- [X] T002 [P] [US1] In `frontend/src/ask/ask-bar.test.tsx`, add a test asserting a human question renders a `User`-icon element and the text "Human", and an answered turn renders the text "AURA Assistant" and a `Sparkles`-icon element; add a test asserting a `pending`-status turn and an `error`-status turn render neither sender icon nor sender label (only the existing "Thinking…"/error text) — these tests must fail until the tasks below are done.

### Implementation for User Story 1

- [X] T003 [US1] In `frontend/src/ask/ask-bar.tsx`, add a small `Participant` presentation constant (or two local consts) mapping `human` → `{ icon: User, label: 'Human' }` and `assistant` → `{ icon: Sparkles, label: 'AURA Assistant' }`, importing `User` from `lucide-react` alongside the existing `Sparkles` import (research.md Decision 3).
- [X] T004 [US1] In `TurnView` (`frontend/src/ask/ask-bar.tsx:154-188`), add a left-aligned identity row above the question text: `Icon` (human, via `frontend/src/components/ui/icon.tsx`) + "Human" label, using T003's constant. (depends on T003)
- [X] T005 [US1] In `TurnView` (`frontend/src/ask/ask-bar.tsx:154-188`), add a right-aligned identity row above the answer content, rendered **only** when `turn.status === 'answered'`: "AURA Assistant" label + `Icon` (Sparkles), using T003's constant — pending/error branches are left untouched, so T002's exclusion assertions pass by construction. (depends on T003)

**Checkpoint**: `npm test -- ask-bar` passes with T002's new assertions; User Story 1 is demoable independently (icon + label identification, no timestamps yet).

---

## Phase 4: User Story 2 - See when each message was sent (Priority: P2)

**Goal**: Every completed message additionally shows a 12-hour `AM/PM` timestamp next to its sender label, mirrored to each participant's outer edge.

**Independent Test**: Open a conversation and confirm every completed message (human and assistant) shows a timestamp next to its label, positioned at that participant's outer edge; pending/error turns still show no timestamp.

### Tests for User Story 2

- [X] T006 [P] [US2] In `frontend/src/ask/ask-bar.test.tsx`, extend the human/assistant assertions from T002 to also match a 12-hour `AM/PM`-formatted time (e.g. regex `/\d{1,2}:\d{2}\s?(AM|PM)/i`) in each identity row — trailing the "Human" label, leading the "AURA Assistant" label; keep the pending/error exclusion assertions (still no timestamp shown).

### Implementation for User Story 2

- [X] T007 [P] [US2] In `frontend/src/ask/types.ts`, add `questionSentAt: string` and `respondedAt: string | null` to the `Turn` interface (data-model.md).
- [X] T008 [US2] In `handleSubmit` (`frontend/src/ask/ask-bar.tsx:57-85`), set `questionSentAt: new Date().toISOString()` and `respondedAt: null` when creating the new `Turn`. (depends on T007)
- [X] T009 [US2] In `updateTurn`'s `onSuccess`/`onError` calls inside `handleSubmit` (`frontend/src/ask/ask-bar.tsx:77-83`), set `respondedAt: new Date().toISOString()` in both patches. (depends on T007)
- [X] T010 [US2] In `frontend/src/ask/ask-bar.tsx`, add a `formatMessageTime(iso: string): string` helper using `Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', hour12: true })` to render ISO timestamps as "10:32 AM" (research.md Decision 1).
- [X] T011 [US2] In `TurnView`, render `formatMessageTime(turn.questionSentAt)` trailing the "Human" label (T004's row), and `formatMessageTime(turn.respondedAt)` leading the "AURA Assistant" label (T005's row, only rendered when `turn.respondedAt` is non-null) — mirrored per research.md Decision 2. (depends on T004, T005, T008, T009, T010)

**Checkpoint**: `npm test -- ask-bar` passes with T006's timestamp assertions; User Stories 1 and 2 both work independently and together.

---

## Phase 5: User Story 3 - Perceive the chat as polished and trustworthy (Priority: P3)

**Goal**: The chat surface reads as elegant and professional — consistent spacing, typography, and bubble styling across short and long messages, matching `base/chatComponent.jpg` and the existing AURA visual identity.

**Independent Test**: Visually compare the rendered chat against `base/chatComponent.jpg` across a short and a long conversation; confirm consistent spacing/typography/bubble shape with no layout glitches.

### Tests for User Story 3

- [X] T012 [P] [US3] In `frontend/src/ask/ask-bar.test.tsx`, add a regression test rendering a transcript with one short human question and one long multi-paragraph assistant answer, asserting both identity rows and both message bodies render without error (guards the "very long responses" edge case from spec.md).

### Implementation for User Story 3

- [X] T013 [US3] In `TurnView` (`frontend/src/ask/ask-bar.tsx`), refine Tailwind spacing/typography/border classes on the identity rows and message bubbles (gap between identity row and bubble, rounded corners, subtle background) to match `base/chatComponent.jpg` and the existing purple/neutral AURA palette used elsewhere in the app.
- [X] T014 [US3] Review the `AskBar` header (`frontend/src/ask/ask-bar.tsx:93-103` — sparkle icon, "Aura Assistant" title, online status) against `base/chatComponent.jpg`; adjust spacing/typography only if inconsistent with the redesigned message rows.
- [X] T015 [US3] Manually validate against `base/chatComponent.jpg` following `specs/021-chat-component-redesign/quickstart.md`'s manual validation steps (short conversation, long conversation, narrow viewport). (depends on T013, T014)

**Checkpoint**: All three user stories are independently functional and visually consistent together.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final regression check across the whole feature.

- [X] T016 Run `cd frontend && npm test && npm run typecheck && npm run lint` (full suite, not just `ask-bar`) to confirm no regression elsewhere in the app (FR-008).
- [X] T017 Run `specs/021-chat-component-redesign/quickstart.md` end-to-end (automated section + manual section) and confirm every expected outcome listed there. (depends on T016)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: None — skipped for this feature (see above).
- **User Story 1 (Phase 3)**: Depends on Setup (T001) only.
- **User Story 2 (Phase 4)**: Depends on Setup; its rendering task (T011) also depends on User Story 1's T004/T005 (same identity rows it extends) — so in practice, do Phase 3 before Phase 4.
- **User Story 3 (Phase 5)**: Depends on Setup; its tasks style the rows/bubbles introduced by Phase 3/4 — so in practice, do Phase 3 and 4 before Phase 5.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories — independently testable as-is (icon + label, no timestamp).
- **User Story 2 (P2)**: Extends the identity rows User Story 1 creates (T004/T005) with a timestamp; still independently verifiable via its own acceptance scenarios once implemented.
- **User Story 3 (P3)**: Polishes what User Story 1/2 already render; has no new data/behavior of its own.

### Within Each User Story

- Tests are written alongside/just before the implementation tasks they cover (T002 before T003-T005; T006 before T007-T011; T012 before T013-T015) and must fail first.
- Same-file tasks within a story (all editing `ask-bar.tsx`) are sequential, not parallel, to avoid diff conflicts.

### Parallel Opportunities

- T002 (test file) can be written in parallel with nothing else in Phase 3 — it's the only task touching `ask-bar.test.tsx` in that phase.
- T006 (Phase 4) and T007 (Phase 4, `types.ts`) touch different files and have no dependency on each other — parallelizable.
- T012 (Phase 5 test file) is independent of T013/T014 (implementation) until it needs to pass.

---

## Parallel Example: User Story 2

```bash
# T006 and T007 touch different files and share no dependency — launch together:
Task: "Extend ask-bar.test.tsx with timestamp-format assertions"
Task: "Add questionSentAt/respondedAt fields to Turn in types.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001).
2. Complete Phase 3: User Story 1 (T002-T005).
3. **STOP and VALIDATE**: run `npm test -- ask-bar`; confirm sender icon/label distinction works standalone.
4. Demo if ready — this alone already resolves the core "who said what" ambiguity from the original request.

### Incremental Delivery

1. Setup → User Story 1 (icon + label) → validate → demo.
2. Add User Story 2 (timestamps) → validate → demo.
3. Add User Story 3 (visual polish) → validate against `base/chatComponent.jpg` → demo.
4. Phase 6 final regression check.

---

## Notes

- [P] tasks touch different files and have no unmet dependency.
- [Story] label maps every implementation/test task to its user story for traceability.
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story independently before moving on.
- No backend, no API contract, no other dashboard component is touched by any task above (FR-007/FR-008).
