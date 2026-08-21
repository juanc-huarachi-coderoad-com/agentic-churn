---

description: "Task list for Ask Agent Default Hybrid Responses"
---

# Tasks: Ask Agent Default Hybrid Responses

**Input**: Design documents from `/specs/023-ask-agent-default-hybrid-responses/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ask.md, quickstart.md (all present)

**Tests**: Existing tests in `test_ask_agent_graph.py`/`test_ask_agent_latency.py` are extended/updated as part of this feature (matching this codebase's existing test-first convention for this file) — this is not a new test-suite addition, it is keeping an existing, actively-maintained suite in sync with an intentional behavior change.

**Organization**: Tasks are grouped by user story (spec.md's US1/US2/US3) after a Foundational phase that performs the one shared mechanism change every story depends on.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no ordering dependency)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All file paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Lock in the confirmed blast radius before editing, so no hidden consumer is missed.

- [X] T001 Re-run the word-boundary grep from research.md Decision 6 to reconfirm scope before editing: `grep -rn "response_mode\b" --include="*.py" --include="*.ts" --include="*.tsx" . | grep -v "response_model" | grep -v "/node_modules/"` — expect matches only in `backend/app/experience/adapters/ask_agent_graph.py`, `backend/app/experience/adapters/ask_router.py` (docstring only), `backend/app/experience/application/ports.py`, `backend/app/experience/adapters/sqlalchemy_repository.py`, `backend/migrations/versions/0005_ask_queries_response_mode.py`, and the two test files. If anything else matches, stop and re-scope before proceeding.

**Checkpoint**: Scope confirmed — safe to begin the Foundational change.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one shared mechanism change (`ResponseMode` collapse) that every user story's acceptance scenario depends on. All edits are to the same file and must happen in this order.

**⚠️ CRITICAL**: No user story task can be verified until this phase is complete.

- [X] T002 In `backend/app/experience/adapters/ask_agent_graph.py`, collapse the `ResponseMode` `StrEnum` (currently `COMPONENT_ONLY | TEXT_ONLY | HYBRID`, ~line 189) to just `TEXT_ONLY | HYBRID`, and change `ClassifyOutput.response_mode`'s default (~line 212) from `ResponseMode.COMPONENT_ONLY` to `ResponseMode.HYBRID`. Update both dataclasses' docstrings to match (they currently describe the 3-way default/inventory).
- [X] T003 In `backend/app/experience/adapters/ask_agent_graph.py`, rewrite `_classify_prompt`'s response_mode section (~lines 242-261): remove the `component_only` category and its "prefer it when in doubt" bias; reword so `hybrid` is presented as the default outcome for any of the 8 structured-intent questions, and `text_only` keeps its existing discriminating examples ("why does this matter", "explain in plain terms", "how should I...") as the one still-LLM-judged exception. (Depends on T002.)
- [X] T004 In `backend/app/experience/adapters/ask_agent_graph.py`, simplify `route_after_resolve_and_render` (~lines 811-819): remove the `mode in (ResponseMode.TEXT_ONLY.value, ResponseMode.HYBRID.value)` gate — return `"generate_text"` whenever `state.get("component")` is not `None`, `"log_result"` otherwise. Update the function's docstring/comment accordingly. (Depends on T002.)
- [X] T005 In `backend/app/experience/adapters/ask_agent_graph.py`, simplify `LangGraphAskAgent.answer`'s parts assembly (~lines 918-952): remove the `component_only` branch. Surviving logic: `text_only` + successful `generated_text` → one `TextPart`; successful `generated_text` (now always the `hybrid` case) → `(TextPart, ComponentPart)`; otherwise (generation failed/timed out, or no survivable text) → `(ComponentPart,)` unchanged graceful degradation. (Depends on T002.)
- [X] T006 In `backend/app/experience/adapters/ask_agent_graph.py`, update `log_result`'s default fallback (~line 832) from `(state.get("response_mode") or "component_only") if component else None` to `(state.get("response_mode") or "hybrid") if component else None`, and update its comment. (Depends on T002.)
- [X] T007 In `backend/app/experience/adapters/ask_agent_graph.py`, add a short comment on the `handoff` → `log_result` edge (~line 872, where `graph.add_edge("handoff", "log_result")` is declared) noting that `write_to_stakeholder` is intentionally exempt from the now-universal hybrid path (the draft itself is already prose; a generic blurb on top would be redundant) — so a future refactor doesn't accidentally wire it in.

**Checkpoint**: `ResponseMode` is now 2-valued, hybrid is the default, and the routing/assembly/logging all reflect it. User story verification can begin.

---

## Phase 3: User Story 1 - Getting the visual and a plain-language explanation together (Priority: P1) 🎯 MVP

**Goal**: Every structured-intent answer includes both the component and a ≤3-sentence executive explanation, by default, without special question phrasing.

**Independent Test**: `POST /api/ask` with "why is the score high?" (no special phrasing) → `parts` has 2 items, a `text` part (≤3 sentences, explaining the visual) followed by a `component` part.

### Implementation for User Story 1

- [X] T008 [US1] In `backend/app/experience/adapters/ask_agent_graph.py`, rewrite `_text_generation_prompt` (~lines 476-496): reframe from "answer this question" to explaining, in plain executive language, what the component is showing and why it matters (or the single most useful added insight if the numbers speak for themselves); explicitly instruct the model not to restate the question or narrate the data field-by-field; tighten the length instruction from "2 to 4 sentences" to "at most 3 sentences" (or an equivalently short bullet list), matching spec.md FR-002/FR-003/SC-002. Keep the existing grounding/fact-check/UUID-stripping instructions verbatim.
- [X] T009 [US1] In `backend/tests/experience/test_ask_agent_graph.py`, change `_FakeLLM.__init__`'s default `response_mode` parameter (~line 42) from `ResponseMode.COMPONENT_ONLY` to `ResponseMode.HYBRID`, updating the class docstring if it references the old default. (Depends on T002-T006.)
- [X] T010 [US1] In `backend/tests/experience/test_ask_agent_graph.py`, replace `test_component_only_stays_a_single_component_part_unchanged` (~lines 506-518 — currently constructs `ResponseMode.COMPONENT_ONLY`, which no longer exists) with a new test, e.g. `test_default_response_produces_text_then_component_with_no_special_phrasing`, that calls `_build_agent`/`agent.answer(...)` with **no** `response_mode` argument (relying on the new default) and a real `text_markdown` fixture, and asserts `result.response_mode == "hybrid"`, `len(result.parts) == 2`, `parts[0]` is a `TextPart`, `parts[1]` is a `ComponentPart` matching today's `delta_breakdown` shape. (Depends on T009.)
- [X] T011 [US1] In `backend/tests/experience/test_ask_agent_graph.py`, rename/rewrite `test_component_only_is_the_default_response_mode_logged` (~lines 582-592) to `test_hybrid_is_the_default_response_mode_logged`, asserting `ask_queries.logged[0]["response_mode"] == "hybrid"` for a `_FakeLLM(Intent.SCORE_DELTA)` call with no explicit `response_mode` (relying on the new default) and a non-empty `text_markdown` fixture. (Depends on T009.)
- [X] T012 [US1] In `backend/tests/experience/test_ask_agent_graph.py`, add a new test asserting the default hybrid behavior holds for at least 2 more structured intents beyond `SCORE_DELTA` (e.g. `Intent.TOP_RISK` → `ranked_issues`, `Intent.QUIET_STAKEHOLDERS` → `stakeholder_cards`), each via `_build_agent`/`.answer(...)` with no explicit `response_mode` and a real `text_markdown` fixture, asserting 2 parts (`TextPart` then `ComponentPart`) each time. (Depends on T009.)

**Checkpoint**: User Story 1 is independently functional and testable — `pytest backend/tests/experience/test_ask_agent_graph.py -k "default_response or hybrid_is_the_default or hybrid_response"` passes.

---

## Phase 4: User Story 2 - Purely conversational questions still get a text-only answer (Priority: P2)

**Goal**: Confirm the `text_only` path (no visual) is completely unaffected by the enum collapse — a required non-regression, not new functionality.

**Independent Test**: `POST /api/ask` with a conversational, no-visual-fit question still returns exactly one `text` part.

### Verification for User Story 2

- [X] T013 [US2] Run `pytest backend/tests/experience/test_ask_agent_graph.py -k text_only` and confirm `test_text_only_response_produces_a_single_text_part_no_component` (~lines 464-479) still passes with **no assertion changes** — it already constructs `ResponseMode.TEXT_ONLY` explicitly, which survives the collapse unchanged. (Depends on Phase 2 + T009.)
- [X] T014 [US2] Run `pytest backend/tests/experience/test_ask_agent_graph.py -k "unverifiable_claim or degrades_to_component_only or no_survivable_text"` and confirm `test_sentence_with_unverifiable_claim_is_dropped_not_shown`, `test_text_generation_failure_degrades_to_component_only`, and `test_a_response_with_no_survivable_text_also_degrades_to_component_only` (~lines 521-580) all still pass unchanged — these exercise `ResponseMode.TEXT_ONLY` plus the graceful-degradation fallback, both preserved by design (research.md Decision 1/spec.md FR-007). (Depends on Phase 2 + T009.)

**Checkpoint**: User Stories 1 AND 2 both verified working.

---

## Phase 5: User Story 3 - Drafting a message to a stakeholder stays unaffected (Priority: P3)

**Goal**: Confirm `write_to_stakeholder` never acquires an accompanying text blurb.

**Independent Test**: `POST /api/ask` requesting a draft to a stakeholder still returns exactly one `component` part (`draft_handoff`), no `text` part.

### Verification for User Story 3

- [X] T015 [US3] Run `pytest backend/tests/experience/test_ask_agent_graph.py -k write_to_stakeholder` and confirm `test_write_to_stakeholder_produces_a_handoff_not_an_inline_answer` (~lines 371-383) still passes unchanged — this path never reaches `resolve_and_render`/`route_after_resolve_and_render`/`generate_text` (confirmed structurally in research.md Decision 4; T007's comment documents why). (Depends on Phase 2 + T007.)

**Checkpoint**: All three user stories independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Latency-test cleanup, governance (constitution amendment), and full regression pass.

- [X] T016 In `backend/tests/experience/test_ask_agent_latency.py`, remove the `component_only`/`text_or_hybrid` branch (~lines 38-39, 69-73): since every structured-intent answer now always makes the second (text-generation) call, delete `_COMPONENT_ONLY_LATENCY_BUDGET_SECONDS` and the `if result.response_mode == "component_only" else ...` conditional, and assert the single `_TEXT_OR_HYBRID_LATENCY_BUDGET_SECONDS` (8.0s) budget unconditionally. Update the module docstring (~lines 7-13), which currently describes the now-retired 3s/8s split.
- [X] T017 Amend `.specify/memory/constitution.md`: bump the version header (~line 567) from `1.4.0` to `1.5.0` (MINOR) with today's date; prepend a new Sync Impact Report section (matching the existing format/style of the `1.3.0 → 1.4.0` entry) explaining this change; update AI Safety Rule 1's sentence (~line 464) from "`component_only` vs `text_only` vs `hybrid`" to "`text_only` vs `hybrid`"; rewrite the Resilience budgets paragraph (~lines 490-501) to retire the `component_only` 2.5s fast-path clause and describe the existing 15s-capped text-generation budget as applying to every structured-intent answer, not a subset — per research.md Decision 7's exact proposed wording.
- [X] T018 [P] Grep `architecture/04-ai-safety-and-model-usage.md` and `architecture/06-error-handling.md` for `component_only` and update any stale "common case"/"default" language found to match T017's amendment (quickstart.md's governance checklist).
- [X] T019 [P] In `backend/app/experience/adapters/ask_router.py`, update `AskAnsweredResponse`'s docstring (~lines 65-69, which says `response_mode == "component_only"` is "unchanged default") to reflect the new `hybrid`-by-default behavior.
- [X] T020 Run the full regression suite: `cd backend && pytest tests/experience/ && pytest tests/narrator/` — the latter must pass unmodified (imported, not changed).
- [X] T021 Execute `specs/023-ask-agent-default-hybrid-responses/quickstart.md`'s validation scenarios end-to-end against a live backend (`docker compose up`), including the governance checklist at the bottom of that document.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run first.
- **Foundational (Phase 2)**: Depends on Phase 1 (scope confirmation) — **blocks every user story**.
- **User Stories (Phases 3-5)**: All depend on Phase 2. US1 (Phase 3) must complete before US2/US3 verification tasks that depend on its test-file setup (T009); US2 and US3 are otherwise independent of each other.
- **Polish (Phase 6)**: Depends on all three user story phases being complete.

### Within Phase 2 (Foundational)

T002 → T003, T004, T005, T006 (all read the enum/default T002 establishes) → T007 (independent comment-only addition, can happen any time after T002).

### Within Phase 3 (US1)

T008 (prompt rewrite, `ask_agent_graph.py`) has no file dependency on T009-T012 (test file) but its effect is only observable once T009 lands (fake LLM ignores the real prompt text, so ordering between T008 and T009-T012 doesn't block either direction). T009 → T010, T011, T012 (all rely on the new fake default).

### Parallel Opportunities

- T018 and T019 (Phase 6) touch different files with no dependency on each other — safe to run in parallel.
- T008 (source file) and T009 (test file) touch different files and can be done in parallel by different people, though both are prerequisites for T010-T012.
- Everything else within a phase is sequential (same-file edits or direct dependency).

---

## Parallel Example: Phase 6

```bash
# Launch together — different files, no shared dependency:
Task: "Grep architecture docs for stale component_only language (T018)"
Task: "Update AskAnsweredResponse docstring in ask_router.py (T019)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational) — the enum collapse itself.
2. Complete Phase 3 (US1) — reframed prompt + updated/new tests.
3. **STOP and VALIDATE**: run `pytest backend/tests/experience/test_ask_agent_graph.py`, confirm US1's independent test passes against a live backend.
4. This alone already satisfies the user's core request (visual + short executive text by default) — US2/US3 are non-regression guarantees, not new capability.

### Incremental Delivery

1. Setup + Foundational → mechanism in place.
2. US1 → default hybrid behavior working and tested (MVP).
3. US2 → confirm conversational text-only path untouched.
4. US3 → confirm draft-only path untouched.
5. Polish → latency test cleanup, constitution amendment, full regression, quickstart sign-off.

## Notes

- This feature is a refactor of one existing, already-tested file — there is no new module, no new port, no migration, and (per research.md Decision 6) no frontend change.
- Every task in Phases 3-5 operates on the same two files already covered by the existing test suite; there is no new test infrastructure to stand up.
- Commit after each phase checkpoint, not necessarily after every individual task, since most tasks within a phase edit the same file.
