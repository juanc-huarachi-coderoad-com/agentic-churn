---

description: "Task list for Assistant Chat Conversation"
---

# Tasks: Assistant Chat Conversation

**Input**: Design documents from `/specs/017-assistant-chat-conversation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ask.md, quickstart.md (all present)

**Tests**: Included — this repo's constitution (P9, P11, Full-Stack Engineering §4) treats unit +
component tests as part of Definition of Done, and every existing file this feature touches
(`ask-bar.test.tsx`, `test_ask_agent_graph.py`) already carries a matching test file.

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P1/P2/P2/P3), so each
story can be implemented, tested, and demoed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Maps the task to US1–US5 from spec.md
- File paths are exact and relative to the repo root

## Path Conventions

Existing web-app layout, unchanged (`plan.md` Project Structure): `backend/app/experience/...`,
`backend/tests/experience/...`, `frontend/src/ask/...`.

---

## Phase 1: Setup

**Purpose**: Confirm a clean baseline before making any change — no scaffolding needed, this
feature extends existing modules only (`plan.md`: no new dependency, no migration).

- [X] T001 Run the existing baseline test suites and confirm both are green before any change:
  `cd backend && pytest tests/experience/` and `cd frontend && npx vitest run src/ask`

**Checkpoint**: Baseline confirmed green — safe to start.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The transcript data structure every one of the 5 user stories renders into. Without
this, no story can be independently demonstrated in the UI (`data-model.md` `Turn`/`Conversation`;
`research.md` Decision 1 — component-local state, no global store, no per-account keying per
Decision 0).

**⚠️ CRITICAL**: No user story's frontend work can begin until this phase is complete. (US3's
backend-only tasks do not depend on this phase and could technically start in parallel — see
Dependencies below.)

- [X] T002 [P] Add the `Turn` type (`id`, `question`, `status: 'pending' | 'answered' | 'error'`,
  `response`, `error`) to `frontend/src/ask/types.ts`, per `data-model.md`'s Turn entity
- [X] T003 Replace `AskBar`'s single `useMutation`-driven idle/thinking/answered state with a
  `turns: Turn[]` array (`useState<Turn[]>([])`) in `frontend/src/ask/ask-bar.tsx`, rendering one
  turn container per array entry (question text + a per-turn pending/answered/error indicator);
  keep the existing single-question `useMutation` call underneath for now, just fan its result out
  into the array instead of a single `mutation.data` (depends on T002)
- [X] T004 In `frontend/src/ask/ask-bar.tsx`, invoke the existing `AnswerRenderer` once per
  `answered` `Turn` in the array (not once for a single latest result), and render the existing
  fallback-text branch once per `error`-or-fallback `Turn` likewise (depends on T003)

**Checkpoint**: `AskBar` renders a growing list of turn placeholders; foundation ready for every
user story.

---

## Phase 3: User Story 1 - Ask multiple questions in one running conversation (Priority: P1) 🎯 MVP

**Goal**: Every question/answer pair stays visible, appended in order, with a visible "thinking"
indicator for the pending one, none ever discarded — including when a request itself fails
(spec.md FR-001, FR-002, FR-004, FR-005, FR-013, FR-015).

**Independent Test**: Ask a question, wait for the answer, ask a second different question — both
question/answer pairs are visible simultaneously, second appended below the first.

### Tests for User Story 1

- [X] T005 [US1] In `frontend/src/ask/ask-bar.test.tsx`, extend the existing "preserves the last
  exchange" test (and/or add a new one) to assert that sending a second question appends a new
  turn **below** the first, and both remain queryable in the DOM at the same time (today's test
  only ever checks the single latest exchange)
- [X] T006 [US1] In `frontend/src/ask/ask-bar.test.tsx`, add a test that sends 10 consecutive
  questions and asserts all 10 question/answer pairs are present with zero lost/overwritten
  (spec.md SC-001)
- [X] T007 [US1] In `frontend/src/ask/ask-bar.test.tsx`, add a test that mocks `apiFetch` to
  reject/error for one question mid-conversation (with at least one prior answered turn already
  present) and asserts: that turn shows an error state, the prior turn(s) remain untouched and
  visible, and a subsequent question can still be asked and answered normally (spec.md FR-013 and
  its Edge Cases entry — "assistant fails to respond mid-conversation")

### Implementation for User Story 1

- [X] T008 [US1] In `frontend/src/ask/ask-bar.tsx`, wire the submit handler to **append** a new
  `pending` `Turn` to `turns` on every send (never replace the array), and update that specific
  turn (by `id`) to `answered` or `error` when its request resolves/rejects (depends on
  Foundational T003/T004; T005–T007 existing and failing)
- [X] T009 [US1] In `frontend/src/ask/ask-bar.tsx`, make the transcript container scrollable and
  keep the newest turn in view (e.g., scroll-to-bottom whenever a turn is appended), without
  hiding or collapsing older turns (depends on T008)

**Checkpoint**: User Story 1 fully functional and independently testable/demoable.

---

## Phase 4: User Story 2 - Typed message moves into the conversation immediately (Priority: P1) 🎯 MVP

**Goal**: Input clears synchronously the instant a message is sent; sending is blocked (not
typing) while a turn is pending; empty/whitespace submissions are no-ops (spec.md FR-003, FR-006,
FR-014).

**Independent Test**: Type a question, submit, confirm the input is empty immediately and the
typed text appears as the newest turn, before the answer arrives.

### Tests for User Story 2

- [X] T010 [US2] In `frontend/src/ask/ask-bar.test.tsx`, add a test asserting the input value is
  empty **synchronously** right after submit (not just eventually), and that the submitted text
  appears as the newest turn's question
- [X] T011 [US2] In `frontend/src/ask/ask-bar.test.tsx`, add a test (reusing the existing
  deferred-promise `resolveFetch` pattern) asserting the send control is disabled while the
  current turn is pending, and re-enabled the instant it resolves
- [X] T012 [US2] In `frontend/src/ask/ask-bar.test.tsx`, add a test asserting an empty or
  whitespace-only submit adds no turn and leaves the input untouched

### Implementation for User Story 2

- [X] T013 [US2] In `frontend/src/ask/ask-bar.tsx`'s submit handler, clear the input state
  synchronously before the request starts, reject empty/whitespace-only submissions before
  clearing/appending anything, and disable the send control whenever any turn in `turns` has
  status `pending` (typing itself stays enabled) (depends on T008; `research.md` Decision 6;
  T010–T012 existing and failing)

**Checkpoint**: User Stories 1 AND 2 both independently functional — this is the MVP.

---

## Phase 5: User Story 3 - Assistant understands greetings and casual messages (Priority: P2)

**Goal**: Greeting/thanks/capabilities messages get one of a small set of fixed, pre-written
replies — no LLM call, no "Fallback answer" caption — while genuine declines are unaffected
(spec.md FR-007, FR-008, FR-012).

**Independent Test**: Send "hi" as the first message; confirm a friendly, non-generic reply with
no "Fallback answer" caption, and confirm a genuinely out-of-scope question ("will they cancel?")
still declines as before, caption included.

### Tests for User Story 3

- [X] T014 [US3] In `backend/tests/experience/test_ask_agent_graph.py`, add tests asserting a
  greeting ("hi"/"hello"), a thanks ("thanks"/"thank you"), and a capabilities ("what can you do")
  message each return a fallback-shaped result with `declined_reason=None` and one of the fixed
  reply strings, **without** the fake `LLMPort`'s classify call ever being invoked (assert call
  count via the existing `_FakeLLM` fixture)
- [X] T015 [US3] In `backend/tests/experience/test_ask_agent_graph.py`, add a test asserting a
  question that matches no small-talk pattern still reaches `classify_intent` unchanged (existing
  per-intent tests must keep passing as-is)
- [X] T016 [P] [US3] In `frontend/src/ask/ask-bar.test.tsx`, add a test asserting a fallback
  response with `declined_reason: null` renders **without** the "Fallback answer" caption, while
  the existing `declined_reason: "prediction"` case still shows it

### Implementation for User Story 3

- [X] T017 [US3] In `backend/app/experience/adapters/ask_agent_graph.py`, add the fixed
  greeting/thanks/capabilities pattern table and reply strings (alongside the existing
  `_DECLINE_TEXT` dict), and a `detect_smalltalk` graph node wired as the new entry point (before
  `classify_intent`) via a conditional edge: match → return `declined_reason=None` +
  fixed reply, skip straight to `log_result`; no match → proceed to `classify_intent` exactly as
  today (`research.md` Decision 4) (depends on T014/T015 existing and failing)
- [X] T018 [US3] In `frontend/src/ask/ask-bar.tsx`, suppress the "Fallback answer" caption when a
  turn's `declined_reason` is `null`; keep it for every other (non-null) `declined_reason` value
  (depends on T008; T016 existing and failing)

**Checkpoint**: User Stories 1, 2, AND 3 all independently functional.

---

## Phase 6: User Story 4 - Assistant remembers earlier turns in the same conversation (Priority: P2)

**Goal**: Follow-up questions are interpreted using up to the 5 most recent prior turns, sent by
the client and independently validated/truncated by the server; memory affects only intent/subject
resolution — never the fact-checked answer text, and never corrupts an unrelated new question
(spec.md FR-009, FR-010, FR-017; `research.md` Decisions 2–3).

**Independent Test**: Ask a question establishing a subject, then a short follow-up that only
makes sense given the first ("what caused that?") — confirm the answer reflects the earlier
context.

### Tests for User Story 4

- [X] T019 [US4] In `backend/tests/experience/test_ask_agent_graph.py`, add a test asserting
  `AskAgentState["history"]` changes what the fake `LLMPort` receives as the classify prompt
  (prior question text is present in it), but does **not** change what the `generate_text` fake
  receives (`research.md` Decision 3's boundary)
- [X] T020 [US4] In `backend/tests/experience/test_ask_agent_graph.py`, add a test asserting
  `history` longer than 5 entries is truncated to the 5 most recent before it reaches the prompt
- [X] T021 [US4] In `backend/tests/experience/test_ask_agent_graph.py`, add a test asserting that a
  new, self-contained question unrelated to the supplied `history` still has its own text intact
  and undistorted in the classify prompt, and that the fake `LLMPort`'s classify result for that
  question's own (distinct) intent is what drives `resolve_and_render` — i.e., unrelated history
  present does not corrupt or override the current question's own resolution (spec.md FR-010,
  US4 Acceptance Scenario 2)
- [X] T022 [P] [US4] In `frontend/src/ask/ask-bar.test.tsx`, add a test asserting a follow-up
  question's outgoing request body includes the prior turn's `{question, answer}` as `history`
  (mock `apiFetch`, assert on the captured request body)

### Implementation for User Story 4

- [X] T023 [US4] Add a `HistoryTurn` Pydantic model (`question: str`, `answer: dict[str, Any]`)
  and an optional `history: list[HistoryTurn] = []` field to `AskRequest` in
  `backend/app/experience/adapters/ask_router.py`; before calling `agent.answer()`, truncate to
  the 5 most recent entries and bound each entry's size (Zero Trust — never trust the client
  already enforced this), converting to plain dicts for the agent call
- [X] T024 [US4] Add `history: list[dict[str, Any]]` to `AskAgentState`
  (`backend/app/experience/application/ports.py`) and an optional `history` parameter to
  `AskAgentPort.answer()`; thread it into `LangGraphAskAgent.answer()`'s initial graph state in
  `backend/app/experience/adapters/ask_agent_graph.py` (depends on T023)
- [X] T025 [US4] Extend `_classify_prompt` in `backend/app/experience/adapters/ask_agent_graph.py`
  to append a compact, code-serialized rendering of each accepted `history` entry (question text
  plus a short representation of its answer — `fallback_text`, or its `parts`' text/component
  summary), explicitly framed as data to interpret, never as instructions (matching the existing
  framing already used for `question`/`component_props`) (depends on T024; T019–T021 existing and
  failing)
- [X] T026 [P] [US4] Add an optional `history` parameter to `postAsk` in `frontend/src/ask/api.ts`,
  included in the request body only when non-empty
- [X] T027 [US4] In `frontend/src/ask/ask-bar.tsx`, derive the last 5 `{question, answer}` pairs
  from `turns` (answered turns only) on each submit and pass them to `postAsk` as `history`
  (depends on T008, T026; T022 existing and failing)

**Checkpoint**: User Stories 1–4 all independently functional.

---

## Phase 7: User Story 5 - Answers mix plain text and rich, generative visual content (Priority: P3)

**Goal**: Every turn in the transcript (not just the latest) keeps the existing mixed text +
generative-UI rendering, correctly and independently per turn; a purely conversational reply
renders as plain text with no forced/empty visual element (spec.md FR-011, FR-012).

**Independent Test**: Ask a question with structured-data answer, then a second, different one —
both turns render their own text/visual content correctly without disturbing each other.

### Tests for User Story 5

- [X] T028 [US5] In `frontend/src/ask/ask-bar.test.tsx`, add a test with two turns present at
  once — one `component_only`, one `hybrid` (text + component) — asserting both render correctly
  and independently in the transcript
- [X] T029 [US5] In `frontend/src/ask/ask-bar.test.tsx`, add a test asserting a plain
  conversational fallback (`declined_reason: null`, from US3) renders as plain text only, with no
  empty or forced visual element

### Implementation for User Story 5

- [X] T030 [US5] Verify/adjust `frontend/src/ask/ask-bar.tsx`'s per-turn rendering from T004 so
  multiple `AnswerRenderer` instances render correctly in sequence down a growing transcript (keys,
  spacing) — this is mostly a verification pass given T004/T008 already render one
  `AnswerRenderer` per answered turn (depends on T004, T008, T018; T028–T029 existing and failing)

**Checkpoint**: All 5 user stories independently functional — feature complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify non-functional guarantees that span every story.

- [X] T031 [P] Run `backend/tests/experience/test_ask_agent_latency.py` to confirm the small-talk
  fast path (US3) and the history-augmented classify call (US4) both stay within the existing
  `component_only` 2.5s/no-retry and `text_only`/`hybrid` 15s resilience budgets
  (`architecture/06-error-handling.md`, unchanged)
- [X] T032 [P] Type-check and lint both changed packages: `cd backend && ruff check . && mypy app`,
  `cd frontend && npm run lint && npm run typecheck` (constitution Full-Stack Engineering §5
  Definition of Done)
- [X] T033 Run `specs/017-assistant-chat-conversation/quickstart.md` end to end (backend `curl`
  checks + the 5-step manual browser walkthrough) and confirm SC-001 through SC-006 — SC-004's
  "9 out of 10" accuracy bar in particular is validated only here, manually/qualitatively, not by
  an automated unit test (see Notes)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS every user story's frontend tasks (T005
  onward). US3's backend-only tests/tasks (T014–T015, T017) do not depend on Phase 2 and may start
  in parallel with it.
- **User Stories (Phase 3–7)**: All frontend tasks depend on Foundational; proceed in priority
  order (P1 → P1 → P2 → P2 → P3) or in parallel per story once Foundational is done
- **Polish (Phase 8)**: Depends on all 5 user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only
- **US2 (P1)**: Depends on Foundational + US1's T008 (the append/update-by-id submit handler it
  refines) — not independent of US1's implementation, though independently *testable* once T008
  exists
- **US3 (P2)**: Backend tasks (T014–T015, T017) depend on nothing else; frontend task T018 depends
  on Foundational + US1's T008
- **US4 (P2)**: Backend tasks depend on nothing else; frontend tasks (T026–T027) depend on US1/US2
  (T008, T013) for a submit handler to extend
- **US5 (P3)**: Depends on Foundational T004/T008 and US3's T018 (shares the same fallback-vs-text
  rendering branch)

**Note (`research.md` Decision 0)**: no task adds per-account conversation keying — this product
has exactly one account per deployment, so the single `turns` array from Foundational already
satisfies spec.md FR-016. Do not add an `accountId → Conversation` map.

**Note (`research.md` Decision 1)**: no task adds persistence (localStorage, a backend session
table, etc.) — spec.md FR-017's "resets on reload" is satisfied by the absence of any such code,
not by a task that builds one.

### Parallel Opportunities

- T002 (types) has no same-phase dependents to block
- T014/T015 (US3 backend tests) and T016 (US3 frontend test) touch different files/layers and can
  run in parallel
- T019–T021 (US4 backend tests) and T022 (US4 frontend test) touch different files/layers and can
  run in parallel
- T026 (`api.ts`) can run in parallel with backend US4 tasks (T023–T025) — different files
- T031/T032 (Polish) can run in parallel with each other

Every other same-phase pair not listed above shares a file with another task in that phase (most
often `ask-bar.tsx`, `ask-bar.test.tsx`, or `test_ask_agent_graph.py`) and is deliberately left
unmarked — see Notes.

---

## Parallel Example: User Story 4

```bash
# Backend and frontend history plumbing touch different files — run together:
Task: "Add HistoryTurn model + history field to AskRequest in backend/app/experience/adapters/ask_router.py"
Task: "Add optional history parameter to postAsk in frontend/src/ask/api.ts"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks all stories)
3. Complete Phase 3: User Story 1
4. Complete Phase 4: User Story 2
5. **STOP and VALIDATE**: run `quickstart.md` steps 1 (partially, skipping the greeting-specific
   assertion) and 3–4's input/transcript checks
6. This alone fixes the two most disruptive reported defects (transcript disappearing, input not
   clearing) and is demoable on its own

### Incremental Delivery

1. Setup + Foundational → transcript scaffold ready
2. US1 + US2 → MVP: multi-turn transcript, clearing input, send-gating → demo
3. US3 → greetings/small talk no longer misfire → demo
4. US4 → follow-up questions use conversation context → demo
5. US5 → verify mixed content renders correctly across every turn, not just the latest → demo
6. Polish → budgets, types/lint, full quickstart pass

### Parallel Team Strategy

With multiple developers, after Foundational:

- Developer A: US1 → US2 (they share `ask-bar.tsx`'s submit handler, best kept sequential/same
  owner)
- Developer B: US3's backend half (T014–T015, T017) — no dependency on Foundational
- Developer C: US4's backend half (T023–T025) — no dependency on Foundational
- US3/US4's frontend halves (T018, T026–T027) land once Developer A's T008/T013 are ready

---

## Notes

- [P] tasks touch different files with no unmet dependency — same-file tasks are intentionally
  left unmarked even within one story, to avoid two edits racing the same file (this includes
  every second-or-later test task added to an already-open test file within a phase — e.g. T006,
  T007, T011, T012, T015, T020, T021, T029 are correctly plain, not `[P]`)
- Every frontend test task extends `frontend/src/ask/ask-bar.test.tsx`'s existing patterns
  (`apiFetch` mock, deferred-promise `resolveFetch`) rather than introducing a new test harness
- Every backend test task extends `backend/tests/experience/test_ask_agent_graph.py`'s existing
  `_FakeLLM`/fake-port pattern rather than introducing new test infrastructure
- SC-004's "follow-up answers reflect prior context in 9/10 conversations" is a live-model
  accuracy bar, not something the fake-`LLMPort` unit tests (which return canned, prompt-
  independent output by design) can measure. T019/T021 verify the *plumbing* (history reaches the
  right prompt, unrelated history doesn't corrupt the current question); actual accuracy is
  validated only manually, via `quickstart.md`'s step 3 (T033). This is an accepted scope
  boundary, not an oversight — building automated live-model eval infrastructure for one success
  criterion would be exactly the kind of speculative tooling constitution P10 cautions against for
  a feature this scoped.
- Commit after each task or logical group; stop at any checkpoint to validate a story
  independently
- No database migration task exists anywhere in this list — none is needed (`research.md`,
  "Data-base impact: none")
