---

description: "Task list for feature implementation"
---

# Tasks: Ask Agent Flexible Response Formats

**Input**: Design documents from `/specs/014-ask-agent-response-formats/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ask.md, quickstart.md (all present)

**Tests**: Included — this feature touches AI-safety-critical fact-checking logic and a real API contract change; this repo's own testing culture (property/golden tests on every prior safety-relevant feature) and constitution Full-Stack §4 both call for it.

**Organization**: Tasks are grouped by user story (spec.md P1/P2/P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact and relative to the repository root

## Path Conventions

Web app — `backend/app/experience/` (+ a read-only import from `backend/app/narrator/domain/`), `backend/tests/experience/` + `backend/tests/unit/`, one Alembic migration, `frontend/src/ask/`, and four governance documents. `backend/app/scoring/`, `backend/app/ledger/`, and `backend/app/narrator/`'s own files (imported, never modified) must never appear in any task below.

<!-- Sample tasks from the template have been replaced with this feature's actual tasks. -->

## Phase 1: Setup

**Purpose**: The two pieces of infrastructure every later phase needs — the new frontend dependency and the schema column.

- [X] T001 Add `react-markdown` to `frontend/package.json` dependencies (`pnpm add react-markdown` from `frontend/`) — no `rehype-raw`/`rehype-sanitize` plugin (research.md Decision 7)
- [X] T002 [P] Author a new Alembic migration under `backend/alembic/versions/` adding a nullable `response_mode` text column to `ask_queries` (research.md Decision 6, data-model.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Land the new `parts`-based response shape end to end, with `response_mode` hardcoded to `component_only` everywhere — this is a pure refactor of the existing, working response, provable as zero-regression before any new capability is added.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Append `TextPart`, `ComponentPart`, and the `ResponsePart` union to the existing `backend/app/experience/domain/entities.py` (data-model.md) — the file already holds dashboard/evidence/draft-composer entities
- [X] T004 In `backend/app/experience/application/ports.py`, extend `AskAgentState` with `response_mode: str | None` and `generated_text: str | None`; replace `AskAgentResult`'s `component`/`component_props` fields with `parts: tuple[ResponsePart, ...]` and add `response_mode: str | None` (data-model.md)
- [X] T005 In `backend/app/experience/application/ports.py`, extend `AskQueryRepositoryPort.log()`'s signature with a `response_mode: str | None` parameter
- [X] T006 In `backend/app/experience/adapters/sqlalchemy_repository.py`, update `SqlAlchemyAskQueryRepository.log()` to accept and persist `response_mode` (depends on T002, T005)
- [X] T007 In `backend/app/experience/adapters/ask_agent_graph.py`, update `LangGraphAskAgent.answer()`'s terminal-state assembly to build `parts` as a single `ComponentPart` from the existing `component`/`component_props` state (unchanged data), with `response_mode` hardcoded to `"component_only"` for every answered result (depends on T003, T004)
- [X] T008 In `backend/app/experience/adapters/ask_router.py`, replace `AskComponentResponse` with `AskAnsweredResponse`/`ResponsePartSchema` (parts-based, contracts/ask.md) and pass `result.response_mode` through to the `.log()` call site; `AskFallbackResponse` stays untouched (depends on T006, T007)
- [X] T009 [P] In `frontend/src/ask/types.ts`, add `ResponsePart`/`TextPart`/`ComponentPart` types and `AskAnsweredResponse` (replacing `AskComponentResponse`); update the `isComponentResponse`-equivalent type guard to discriminate on `parts` vs. `fallback_text`
- [X] T010 In `frontend/src/ask/components/answer-renderer.tsx`, accept the new `AskAnsweredResponse` shape and iterate `parts`: component parts render via the existing 8-type switch (moved into an unchanged sub-branch); text parts render via a temporary placeholder (real Markdown rendering lands in US1) (depends on T009)
- [X] T011 In `frontend/src/ask/ask-bar.tsx`, pass the new `AskAnsweredResponse` shape through unchanged in behavior (idle/thinking/answered states untouched) (depends on T010)
- [X] T012 [P] Update the existing fixtures/assertions in `backend/tests/experience/test_ask_agent_graph.py` and the frontend Ask-agent tests (`frontend/src/ask/ask-bar.test.tsx`) for the new parts-wrapped shape — a mechanical wrap of the same data, zero behavior change (depends on T007, T008, T011)

**Checkpoint**: All existing tests pass against the new `parts`-based shape with zero behavior change — this phase alone already satisfies most of US2's independent test.

---

## Phase 3: User Story 1 - Getting a conversational, explanatory answer instead of a forced component (Priority: P1) 🎯 MVP

**Goal**: The classify step can decide `response_mode: text_only`, grounded text generation runs against the same already-fetched data, every claim is mechanically fact-checked (dropping failures), and the frontend renders it as real formatted Markdown.

**Independent Test**: Ask a question with no matching structured-component intent but a clear, answerable conversational shape; confirm the response is `parts: [{"type": "text", ...}]` with real prose, and every claim in it is traceable to real account data.

### Tests for User Story 1

- [X] T013 [P] [US1] Add fake-LLM-backed test cases to `backend/tests/experience/test_ask_agent_graph.py`: `response_mode: text_only` produces `parts = [TextPart(...)]` only (no component); a sentence with an unverifiable claim is dropped from `generated_text`, never shown; a text-generation failure/timeout degrades to `parts = [ComponentPart(...)]` (research.md Decisions 3–4)
- [X] T014 [P] [US1] Create `frontend/src/ask/components/markdown-text.test.tsx`: renders headings/emphasis/lists/code blocks correctly; content containing embedded HTML (e.g. a client-message quote with a `<script>`-like string) renders as inert literal text, never executed (FR-007, research.md Decision 7)

### Implementation for User Story 1

- [X] T015 [US1] In `backend/app/experience/adapters/ask_agent_graph.py`, add a `ResponseMode` `StrEnum` (`component_only | text_only | hybrid`) and extend `ClassifyOutput` with a `response_mode: ResponseMode` field; update `_classify_prompt` with guidance and examples so it decides response format from the question's phrasing, tuned so existing fixture questions ("why did the score go up?", "why is the score high?") continue to classify `component_only` (research.md Decisions 1–2)
- [X] T016 [US1] In `backend/app/experience/adapters/ask_agent_graph.py`, add `_build_verified_facts_from_tool_results(component_props: dict) -> VerifiedFactSet`, importing `VerifiedFactSet` from `app.narrator.domain.entities` (domain-to-domain import, constitution P8) — mirrors the Narrator's own `_build_verified_facts`, including its "every point value is itself a citable number" extension (research.md Decision 4)
- [X] T017 [US1] In `backend/app/experience/adapters/ask_agent_graph.py`, add a `TextGenerationOutput` schema (single `markdown: str` field) and `_text_generation_prompt(question, component_props)` (depends on T015)
- [X] T018 [US1] In `backend/app/experience/adapters/ask_agent_graph.py`, add a helper that splits generated Markdown into fact-checkable prose sentences while excluding fenced code-block content entirely (research.md Decision 4)
- [X] T019 [US1] In `backend/app/experience/adapters/ask_agent_graph.py`, add the `generate_text` graph node: calls `llm.generate_structured` with T017's schema/prompt, splits the result via T018, fact-checks each prose sentence with `app.narrator.domain.services.fact_check` (imported, not modified) against T016's `VerifiedFactSet`, drops failing sentences, reassembles `generated_text`; any LLM error/timeout leaves `generated_text` as `None` rather than raising (depends on T016, T017, T018)
- [X] T020 [US1] In `backend/app/experience/adapters/ask_agent_graph.py`, wire `generate_text` into `build_ask_agent_graph`: a new edge from `resolve_and_render` to `generate_text` to `log_result`, gated so `generate_text` only runs when `response_mode != component_only` (depends on T019)
- [X] T021 [US1] Update `LangGraphAskAgent.answer()`'s terminal assembly (`backend/app/experience/adapters/ask_agent_graph.py`): for `text_only`, `parts = [TextPart(generated_text)]` (the component is never included in the response for this mode, even though it was fetched for grounding); if `generated_text` is `None`, degrade to `parts = [ComponentPart(...)]` instead of ever returning an empty `parts` list (depends on T020)
- [X] T022 [US1] Update `backend/tests/experience/test_ask_agent_latency.py`: branch the budget assertion on `result.response_mode` — `component_only` keeps the existing 3s/REQ-M9-08 assertion unchanged; `text_only`/`hybrid` assert against the new 8s budget (research.md Decision 3) (depends on T021)
- [X] T023 [P] [US1] Implement `frontend/src/ask/components/markdown-text.tsx` using `react-markdown` (no raw-HTML plugin) with monospace, non-reflowed code-block styling (research.md Decisions 7–8)
- [X] T024 [US1] Wire `markdown-text.tsx` into `answer-renderer.tsx`'s text-part branch, replacing Foundational's placeholder (depends on T010, T023)

**Checkpoint**: User Story 1 is independently functional — text-only answers work end to end, fact-checked, degrading gracefully on failure.

---

## Phase 4: User Story 2 - Structured visual data still renders as a component by default (Priority: P2)

**Goal**: Prove, concretely, that nothing about today's component-only experience changed.

**Independent Test**: Ask a question matching an existing structured-data intent; confirm the response still renders as the same visual component, with identical data and identical click-through behavior.

### Implementation for User Story 2

- [X] T025 [P] [US2] Add a regression test to `backend/tests/experience/test_ask_agent_graph.py` asserting `component_only` responses' `parts[0].component_props` are byte-identical to this file's pre-existing component-only fixtures (SC-002)
- [X] T026 [P] [US2] Verify `frontend/src/ask/ask-bar.test.tsx`'s existing `delta_breakdown` assertion (from `"why did the score go up?"`) still passes unmodified against the new parts-wrapped response shape; extend it if the wrap needs a one-line adjustment

**Checkpoint**: Zero-regression proven by passing pre-existing assertions plus T025/T026, not just claimed.

---

## Phase 5: User Story 3 - A single answer can combine an explanation with a visual component (Priority: P3)

**Goal**: `response_mode: hybrid` produces both a text part and a component part together, in order, from one consistent data snapshot.

**Independent Test**: Ask a question whose best answer needs both; confirm the response includes both a rendered component and formatted text, and that both agree with each other.

### Implementation for User Story 3

- [X] T027 [P] [US3] Add a hybrid-mode test case to `backend/tests/experience/test_ask_agent_graph.py`: `response_mode: hybrid` produces `parts = [TextPart(...), ComponentPart(...)]` in that order, both derived from the same fetched `component_props` (FR-008)
- [X] T028 [US3] Extend T021's terminal assembly in `backend/app/experience/adapters/ask_agent_graph.py` for the `hybrid` case: `parts = [TextPart(generated_text), ComponentPart(...)]`, text first (contracts/ask.md's documented ordering) (depends on T021)

**Checkpoint**: All three user stories independently functional — the assistant now genuinely supports component, text, and hybrid responses.

---

## Phase 6: Polish & Cross-Cutting Concerns (Governance + Regression)

**Purpose**: This feature's own Complexity Tracking made these non-optional, not an afterthought.

- [X] T029 [P] Amend `.specify/memory/constitution.md`'s AI Safety Rule 1 to name the Ask agent as a third prose-generating component (alongside Narrator/Draft composer), governed by the same Rule 4 discipline — full amendment procedure: version bump, fresh Sync Impact Report
- [X] T030 [P] Amend `architecture/04-ai-safety-and-model-usage.md`'s model-call inventory table with the Ask agent's new third output shape (`{intent, response_mode, parts}` alongside the existing component/fallback rows)
- [X] T031 [P] Amend `architecture/06-error-handling.md` with the new `text_only`/`hybrid` resilience-budget row (research.md Decision 3), keeping the existing `component_only` row unchanged
- [X] T032 [P] Add a pointer in `specs/008-narrator-and-ask-agent/contracts/ask.md` to `specs/014-ask-agent-response-formats/contracts/ask.md` as the current source of truth for the answered-response shape
- [X] T033 Apply the Alembic migration (T002) against the dev database; confirm `ask_queries.response_mode` exists and is nullable
- [X] T034 [P] Run backend regression: `pytest tests/experience/ tests/narrator/ tests/unit/test_ask_queries_logging.py` from `backend/`
- [X] T035 [P] Run frontend regression: `pnpm typecheck && pnpm lint && pnpm test` from `frontend/`
- [X] T036 Execute every step in `specs/014-ask-agent-response-formats/quickstart.md` against a live backend with a real `ANTHROPIC_API_KEY`
- [X] T037 Run `git diff --stat` and confirm the diff is confined to `backend/app/experience/`, the one new `backend/app/experience/domain/entities.py`, the one migration, `frontend/src/ask/`, and the four governance documents (T029–T032) — no changes to `backend/app/scoring/`, `backend/app/ledger/`, or any file inside `backend/app/narrator/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001–T002 (the migration and dependency both land here) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion — the real new capability
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion only — genuinely independent of US1/US3 (it's a regression proof, not new code)
- **User Story 3 (Phase 5)**: Depends on Phase 2 **and** US1's T021 (hybrid extends the same terminal-assembly function text_only builds) — the one real cross-story dependency in this feature
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Parallel Opportunities

- T001 and T002 (Setup) run in parallel
- T003 and T009 (Foundational, backend domain entities vs. frontend types) run in parallel — different files, no shared dependency
- T012 can run in parallel with nothing else in Foundational (it depends on everything before it)
- T013 and T014 (US1 tests) run in parallel
- T023 (markdown-text.tsx implementation) can run in parallel with T015–T020 (backend classify/generate/fact-check chain) — different files, no shared dependency, only converging at T024
- T025 and T026 (US2) run in parallel with each other and with all of US1/US3, once Phase 2 is done
- T029–T032 (governance amendments) and T034–T035 (regression runs) all run in parallel with each other

---

## Parallel Example: User Story 1

```bash
# Launch both US1 tests together:
Task: "Add text_only/fact-check test cases to backend/tests/experience/test_ask_agent_graph.py"
Task: "Create frontend/src/ask/components/markdown-text.test.tsx"

# Launch the frontend Markdown renderer in parallel with the backend generation chain:
Task: "Implement frontend/src/ask/components/markdown-text.tsx"
Task: "Add generate_text graph node in backend/app/experience/adapters/ask_agent_graph.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T012) — CRITICAL, proves zero regression before new capability
3. Complete Phase 3: User Story 1 (T013–T024)
4. **STOP and VALIDATE**: run quickstart.md's User Story 1 section against a live backend
5. This alone delivers the feature's actual headline capability — genuine conversational text answers

### Incremental Delivery

1. Setup + Foundational → parts-based shape live, zero regression
2. User Story 1 → validate independently → the core new capability ships
3. User Story 2 → validate independently → zero-regression formally proven
4. User Story 3 → validate independently → hybrid responses ship
5. Polish → governance amendments (non-optional per this feature's own Complexity Tracking) + full regression

### Parallel Team Strategy

With two developers, after Phase 2 completes:
- Developer A: Phase 3 (US1's backend classify/generate/fact-check chain, T015–T022)
- Developer B: Phase 3's frontend half (T023–T024) in parallel, converging only at T024; then Phase 4 (US2) solo, since it's pure verification

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps each task to its spec.md user story for traceability
- Every task names the exact file, and cross-references the exact research.md Decision it implements — there is no ambiguity left to resolve during implementation
- T029–T032 are not optional cleanup — they are this feature's own Complexity Tracking's stated condition for the Constitution Check to actually pass, not just be provisionally waved through
- Commit after each phase checkpoint
