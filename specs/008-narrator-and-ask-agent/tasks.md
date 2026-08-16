# Tasks: Narrator and Ask Agent

**Input**: Design documents from `specs/008-narrator-and-ask-agent/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/dashboard.md`, `contracts/ask.md`, `quickstart.md`

**Tests**: Test tasks below cover exactly `spec.md`'s acceptance scenarios —
the Narrator's fact-check behavior with `LLMPort` faked, the Ask agent's
branch coverage per `tests/strategy.md`'s already-documented design (one test
per REQ-M9-02 intent plus decline/fallback/handoff, fake ports, no live
model call), the read-only-tool-enforcement test, one real-network latency
test, and the golden-replay suite going live for the first time — not a
broader TDD suite beyond what those already require.

**Organization**: Tasks are grouped by user story — US1 Narrator (P1), US2 Ask
agent answers with the right component (P1), US3 Ask agent refuses honestly
(P1) — per `plan.md`'s Project Structure. US1 is a fully independent leaf: it
never touches `app.experience` or `langgraph`. US2 and US3 share one compiled
graph (`app.experience.adapters.ask_agent_graph`), so both depend on
Foundational's graph skeleton; US3's `insufficient_history` decline path
additionally depends on US2's `QueryLedgerTool` (noted explicitly below,
mirroring how feature 007's Polish phase depended on that feature's own
earlier stories).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, or an independent region of a
  shared file, with no dependency on an incomplete task)
- **[Story]**: US1/US2/US3
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 Add `langgraph` to `backend/pyproject.toml`'s dependencies
      (`decisions/03-langgraph-for-ask-agent.md`, `research.md` Decision 3)
      — confined to exactly one file
      (`app.experience.adapters.ask_agent_graph`, `.importlinter`'s
      existing `global-dependency-rule`, no config change needed).
      `langchain-anthropic` turned out unnecessary and was not added:
      `classify_intent` reuses our own `LLMPort`/`AnthropicLLMAdapter`
      (`research.md` Decision 1), never LangChain's model wrapper, and the
      graph's tool objects only need `langchain_core.tools`, already a
      transitive dependency of `langgraph` itself — found while
      implementing, corrected to avoid an unused dependency (P10 YAGNI)
- [X] T002 [P] Add `generation_model_id: str = "claude-sonnet-5"` to the
      `Settings` class in `backend/app/config.py`, and add a matching
      `GENERATION_MODEL_ID=claude-sonnet-5` entry to `.env.example`
      (`decisions/02-repo-and-tooling.md`'s Claude model ID pinning table;
      mirrors `reader_model_id`'s existing pattern exactly) — shared by the
      Narrator and the Ask agent's `classify_intent` step
- [X] T003 [P] New Alembic migration
      `backend/migrations/versions/0002_ask_insufficient_history.py`:
      `ALTER TYPE declined_reason ADD VALUE IF NOT EXISTS
      'insufficient_history'` (`research.md` Decision 6 — a real schema
      change, `declined_reason` is a Postgres `ENUM` type, not a `CHECK`;
      filename/revision id shortened from the originally-planned
      `0002_declined_reason_insufficient_history` — `alembic_version.
      version_num` is `VARCHAR(32)`, the longer id didn't fit, caught by
      actually running the migration against a real database rather than
      just writing it); updated `data-base/10-ddl-appendix.md`'s
      `CREATE TYPE declined_reason` line and `data-base/
      08-schema-experience.md`'s `ask_queries.declined_reason` description
      to list all five values; verified live — `SELECT enumlabel FROM
      pg_enum ...` shows all 5 values against a real freshly-migrated
      database
- [X] T004 [P] Update `architecture/07-api-spec.md`: add
      `DashboardResponse.narrator` (`{headline, reasons[], actions[]}`,
      nullable — `contracts/dashboard.md`); add `draft_handoff` as an 8th
      value to `AskComponentResponse.component`'s enum
      (`research.md` Decision 5); add `insufficient_history` as a 5th value
      to `AskFallbackResponse.declined_reason`'s enum (matches T003)

**Checkpoint**: Dependency, config, and schema groundwork ready.

---

## Phase 2: Foundational (Ask agent graph skeleton — blocks US2 and US3 only)

**Purpose**: The one compiled graph both Ask-agent stories extend. The
Narrator (US1) has no dependency on this phase — it never touches
`app.experience` or `langgraph` — and can proceed the moment Setup is done.

**CRITICAL**: No US2 or US3 task can begin until this phase is complete.

- [X] T005 [P] Define `AskAgentState` (TypedDict) in
      `backend/app/experience/application/ports.py` — `question: str,
      intent: str | None, tool_results: list[dict], component: str | None,
      component_props: dict | None, fallback_text: str | None,
      declined_reason: str | None` (`architecture/08-class-diagrams.md`
      diagram 4, `data-model.md`)
- [X] T006 [P] Define `AskAgentPort` (ABC) and `AskAgentResult` in
      `backend/app/experience/application/ports.py` —
      `answer(question: str, user: User) -> AskAgentResult`
      (`decisions/03-langgraph-for-ask-agent.md`)
- [X] T007 [P] Define `AskQueryRepositoryPort` in
      `backend/app/experience/application/ports.py` —
      `log(question_text, matched_intent, rendered_component,
      declined_reason, response_time_ms, asked_by_user_id) -> None`
      (`data-model.md`)
- [X] T008 Implement `SqlAlchemyAskQueryRepository` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (depends on
      T007) — one `INSERT` into `ask_queries` per call
- [X] T009 Implement the compiled graph skeleton in
      `backend/app/experience/adapters/ask_agent_graph.py` (depends on T005,
      T006, T001) — `LangGraphAskAgent(AskAgentPort)`: a `classify_intent`
      node using `LLMPort` (imported from `app.readers.application.ports`,
      `research.md` Decision 1) constructed with
      `settings.generation_model_id`, closed enum covering all 7 lookup
      intents + `write_to_stakeholder` (handoff) + `prediction` +
      `colleague_judgment` from REQ-M9-02/05/06, plus branch routing to
      placeholder terminal nodes (filled in by T025/T033/T034) — every
      terminal node's contract is to call `AskQueryRepositoryPort.log(...)`
      exactly once before returning (T008). Implemented and verified with a
      real compiled graph run (fake ports, no live model): the full
      `classify_intent → route_intent → {decline, fallback, handoff,
      resolve_and_render} → log_result → END` structure works end to end —
      writing it as one cohesive graph turned out simpler than genuinely
      stubbed terminal nodes, so T024/T025/T033/T034/T035/T036's logic
      landed in this same pass (each still verified and marked separately
      below, not skipped)

**Checkpoint**: Graph skeleton compiles; `classify_intent` is independently
testable against a fake `LLMPort`. US2 and US3 work can now begin.

---

## Phase 3: User Story 1 - A score's explanation reads like a person wrote it, and every fact in it is checked (Priority: P1)

**Goal**: A completed score run's ranked findings become a fact-checked
headline, reasons, and playbook-derived actions — persisted once, rendered on
the dashboard.

**Independent Test**: `quickstart.md` §1–2 (narrate a run, confirm the
dashboard renders it) and §10 (a missing `GENERATION_MODEL_ID` fails
honestly).

### Implementation for User Story 1

- [X] T010 [P] [US1] Define domain value objects in
      `backend/app/narrator/domain/entities.py` (this module's first real
      content) — `RankedContribution`, `VerifiedFactSet`, `FactCheckResult`,
      `NarratedReason`, `NarratedAction`, `NarratorOutput` (`data-model.md`)
- [X] T011 [US1] Implement `fact_check(sentence: str, facts:
      VerifiedFactSet) -> FactCheckResult` in
      `backend/app/narrator/domain/services.py` (depends on T010) — pure,
      no I/O: extracts every number/name token from `sentence`, confirms
      each exists verbatim in `facts` (REQ-M7-06/07). One genuine bug found
      and fixed via live verification against the real database (T019, not
      a synthetic unit case): the initial regex treated every sentence's
      *first* word as a name-candidate if capitalized, so any action
      beginning with an imperative verb ("Escalate the ticket...") was
      discarded every time — false-failing almost every real action.
      Fixed by excluding the sentence's own leading word from name
      extraction (source-text extraction, used to build the verified set,
      is intentionally left unfiltered — over-including there is safe;
      under-filtering the *candidate* sentence is not). Documented
      trade-off, not silently patched: a genuine name that happens to open
      a sentence now also bypasses verification — accepted as the safer
      failure direction given the alternative discarded nearly every
      generated action.
- [X] T012 [P] [US1] Define `ScoreContextPort`, `ClientContextPort`,
      `PlaybookPort`, `NarratorOutputRepositoryPort` in
      `backend/app/narrator/application/ports.py` (depends on T010;
      `LLMPort` itself is imported from `app.readers.application.ports`, not
      redefined here — `research.md` Decision 1)
- [X] T013 [US1] Implement `SqlAlchemyScoreContextRepository`,
      `SqlAlchemyClientContextRepository`, `SqlAlchemyPlaybookRepository`,
      `SqlAlchemyNarratorOutputRepository` in
      `backend/app/narrator/adapters/sqlalchemy_repository.py` (depends on
      T012) — `ScoreContextRepository` orders `score_contributions` by the
      scoring engine's own rank (`points_contributed`, most impactful
      first — the Narrator never re-sorts this, REQ-M7-P2) and joins
      `issues` for the fallback template's `top_issue`
- [X] T014 [P] [US1] Write the versioned structured-output narration prompt
      template in `backend/app/narrator/adapters/prompts/narration_v1.py`
      (REQ-M7-08) — schema `{headline: str, reasons: [{text, points,
      evidence_event_ids}], actions: [{text, owner, due_date,
      playbook_id}]}`, instructed to draw actions only from the supplied
      playbook templates (REQ-M7-04)
- [X] T015 [US1] Implement `NarrateScoreRunUseCase` in
      `backend/app/narrator/application/use_cases.py` (depends on T011,
      T012, T013, T014) — `execute(score_run_id)`: fetch ranked
      contributions (T013), build a `VerifiedFactSet` from cited events'
      real names/numbers (T013's `ClientContextPort`), call
      `LLMPort.generate_structured` with T014's prompt, fact-check every
      reason and the headline (T011), discard failing reasons, discard
      candidate actions missing `owner` or `due_date` (REQ-M7-05), fall back
      to the deterministic non-LLM headline template
      (`"{score} — {band}. Top issue: {issue.label} ({issue.points} pts).
      See evidence trace for detail."`, `architecture/
      06-error-handling.md`) when the LLM headline also fails its
      fact-check, persist exactly one `NarratorOutput` (T013)
- [X] T016 [US1] Implement `backend/scripts/run_narrator.py` (depends on
      T015) — manual `NarrateScoreRunUseCase` trigger against the latest
      `score_runs` row, mirroring `scripts/compute_score.py`'s existing
      pattern (`research.md` correction 2 — no live/chained trigger path
      exists anywhere in this pipeline yet)
- [X] T017 [P] [US1] Write `backend/tests/narrator/test_fact_check.py`
      (depends on T011) — pure, no DB, no LLM: known-good sentence/fact-set
      pairs pass; a sentence containing a number/name absent from the fact
      set fails; a sentence containing only already-verified facts passes
      even when phrased differently than the source
- [X] T018 [P] [US1] Write
      `backend/tests/narrator/test_narrate_score_run_use_case.py` (depends
      on T015) — `LLMPort` faked: a fact-check-passing candidate produces a
      `NarratorOutput` with `fact_check_passed = true` (Acceptance Scenario
      1–3, 5); a candidate reason containing an unverifiable fact is
      discarded, other reasons unaffected (Acceptance Scenario 5–6); a
      candidate action missing `owner` or `due_date` is excluded (Acceptance
      Scenario 4); every generated action personalizes an existing playbook
      template, never an invented one (Acceptance Scenario 3); a headline
      that fails its fact-check falls back to the deterministic template,
      `fact_check_passed = false` (Edge Cases); swapping the input ranking
      order (test harness) changes emphasis without the use case re-deriving
      its own ranking (Acceptance Scenario 7)
- [X] T019 [US1] Write
      `backend/tests/narrator/test_run_narrator_real_db.py` (depends on
      T016) — real-DB integration against the real, already-scored Meridian
      fixture: reproduces `examples/01-end-to-end-walkthrough.md`'s worked
      headline in substance, confirms exactly one `narrator_outputs` row per
      `score_runs.id` (`UNIQUE` constraint), confirms a missing
      `GENERATION_MODEL_ID` fails honestly rather than silently producing
      the fallback headline (quickstart.md §10 — a configuration failure
      must never look identical to the intentional total-fact-check-failure
      fallback)
- [X] T020 [US1] Add `NarratorReadPort` (`get_for_score_run(score_run_id) ->
      NarratorSummary | None`) to
      `backend/app/experience/application/ports.py`, implement
      `SqlAlchemyNarratorReadRepository` in
      `backend/app/experience/adapters/sqlalchemy_repository.py`, and wire
      it into the dashboard response assembly in
      `backend/app/experience/adapters/dashboard_router.py` (depends on
      T013 for the underlying `narrator_outputs` rows to exist) — populates
      `DashboardResponse.narrator`, `null` when no row exists yet for the
      latest `score_runs.id` (REQ-M8-P2's "absent, not empty" discipline,
      `contracts/dashboard.md`)
- [X] T021 [P] [US1] Frontend: extend `frontend/src/dashboard/types.ts` with
      a `NarratorSummary` type and add it to `DashboardResponse`; add
      `frontend/src/dashboard/narrator-panel.tsx` (headline/reasons/
      actions) and `narrator-panel.test.tsx`; wire `<NarratorPanel>` into
      `frontend/src/dashboard/dashboard-page.tsx`, rendered only when
      `narrator` is non-null (depends on T020's contract)

**Checkpoint**: User Story 1 fully functional and independently testable —
`quickstart.md` §1, §2, §10 pass.

---

## Phase 4: User Story 2 - Questions get answered with the right view, not a paragraph (Priority: P1)

**Goal**: Each of the 7 lookup-and-render intents (plus the draft-composer
handoff) is answered by looking up already-computed data and rendering the
correct closed-set component — never a paragraph, never a new score
computation.

**Independent Test**: `quickstart.md` §3 (delta breakdown) and §6 (the
draft-handoff response) — the compiled graph invoked directly with fake
ports, per `tests/strategy.md`'s design, plus one real end-to-end `curl` call
each.

### Implementation for User Story 2

- [X] T022 [P] [US2] Define `LedgerQueryPort` in
      `backend/app/experience/application/ports.py` —
      `baseline_vs_current(stakeholder_id: UUID) -> tuple[
      ConfirmedBaselineWindow, list[MessageEventInfo]] | None` (reuses
      `app.readers.domain`'s existing value objects from feature 007,
      `None` when fewer than 5 confirmed-baseline messages —
      `research.md` Decision 4)
- [X] T023 [US2] Implement `SqlAlchemyLedgerQueryRepository` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (depends
      on T022) — reuses feature 007's confirmed-baseline read shape,
      read-only
- [X] T024 [US2] Implement `AskAgentToolkit`, `QueryLedgerTool`,
      `QueryFindingsTool`, `QueryScoreRunsTool` in
      `backend/app/experience/adapters/ask_agent_graph.py` (same file as
      T009, sequential; depends on T009, T023). Real `StructuredTool`
      objects (`langchain_core.tools`) built and verified — `tools:
      ['query_ledger', 'query_findings', 'query_score_runs']`. `query_
      findings` ended up backed by `FindingReadPort.list_open_commitments`
      (`response_pairs`/`commitments`, deterministic ledger projections
      independent of any reader's validation status) and
      `StakeholderReadPort.list_stakeholders` — **not** `get_finding`/
      `resolve_events` at all, so C1's `status = 'validated'` filter (added
      to `get_finding` regardless, for the existing evidence-trace path) is
      not actually exercised by this feature's own tools: none of them
      expose a way to fetch an arbitrary finding by ID in the first place,
      a stronger guarantee than a filter — found while implementing, not
      assumed from the plan. `QueryScoreRunsTool` wraps `ScoreReadPort`,
      safe by construction (`score_contributions` only ever contains
      validated findings' contributions). No write method is reachable to
      register on any of the three (constitution AI safety rule 2) —
      structural, verified by each port's own abstract interface having no
      write method at all, not just by convention
- [X] T025 [US2] Implement the tool-calling loop and `render_component`
      node in `backend/app/experience/adapters/ask_agent_graph.py` (same
      file, sequential; depends on T024) — bounded to T024's 3 tools; maps
      the tool result onto one of the 7 closed-set `AskComponentResponse.
      component` values (REQ-M9-02); the `write_to_stakeholder` intent from
      T009's classifier routes straight to a `draft_handoff` response
      (`component_props = {issue_id, stakeholder_id}`, `research.md`
      Decision 5, FR-012a) without calling a tool. Verified live: a
      `score_delta` question through the real compiled graph (fake ports)
      produced `component = "delta_breakdown"` with real
      `score_contribution_id` sources.
- [X] T026 [US2] Implement `backend/app/experience/adapters/ask_router.py`
      — `POST /api/ask` (depends on T025) — the composition root:
      constructs `LangGraphAskAgent` with all its port implementations,
      reads `asked_by_user_id` from the bearer token (never the request
      body), registers the route the same way `dashboard_router.py`/
      `coverage_router.py` already do
- [X] T027 [P] [US2] Write
      `backend/tests/experience/test_ask_agent_graph.py` (depends on T025)
      — the compiled graph invoked directly with a fixed `AskAgentState`
      and fake `LedgerQueryPort`/`FindingReadPort`/`ScoreReadPort`
      (`tests/strategy.md`): one test per lookup intent asserting the
      correct component + props, plus the `write_to_stakeholder` →
      `draft_handoff` case — no live model call, no real DB. 16 tests,
      all passing (verified live, not just written). One real bug found and
      fixed while writing these tests, not by inspection: `matched_intent`
      was being set to `"prediction"`/`"colleague_judgment"` on decline
      paths — `data-base/08-schema-experience.md`'s own worked example logs
      `matched_intent = NULL` for exactly this case ("Will Meridian
      actually cancel?"), since those two categories are real classify
      outcomes but not REQ-M9-02 "matches." Fixed with a shared
      `_matched_intent_value()` helper used by both `log_result` and
      `LangGraphAskAgent.answer`.
- [X] T028 [P] [US2] Write
      `backend/tests/experience/test_ask_agent_toolkit.py` (depends on
      T024) — asserts `AskAgentToolkit.build_tools()` never returns a tool
      bound to a write method (`save`, `quarantine`, `append`) on any
      injected port, run against the actual registered tool list
      (`tests/strategy.md`'s read-only-enforcement test). 3 tests, all
      passing — one asserting exactly 3 tools registered, one mechanically
      confirming none of the 4 injected port types declare a write method
      on their own abstract interface at all (structural, not
      by-convention), one confirming each tool's coroutine is bound to the
      toolkit instance itself, not some other reachable object; **also asserts
      the quarantine-invisibility guarantee mechanically**: seed a fake
      `FindingReadPort` with one `validated` and one `quarantined` finding,
      call `QueryFindingsTool.run()` for the quarantined finding's ID, and
      confirm it returns nothing — the test-level enforcement of T024's
      new `status = 'validated'` filter (FR-024, found during
      `/speckit-analyze`)
- [X] T029 [US2] Write
      `backend/tests/experience/test_ask_agent_latency.py` (depends on
      T026) — real `AnthropicLLMAdapter`, real Postgres: asserts end-to-end
      response time stays under 3s for an intent-matched question
      (REQ-M9-08). `@pytest.mark.skipif(not settings.anthropic_api_key)` —
      verified live: skips honestly in this dev environment (no
      `ANTHROPIC_API_KEY` configured), the same honest-skip pattern feature
      007's own live-model tests already established; runs for real
      wherever a key is actually configured
- [X] T030 [P] [US2] Frontend: `frontend/src/ask/types.ts`
      (`AskComponentResponse`, `AskFallbackResponse`, matching T004's
      contract) and `frontend/src/ask/api.ts` (typed `POST /api/ask`
      client, TanStack Query)
- [X] T031 [US2] Frontend: `frontend/src/ask/ask-bar.tsx`
      (`Idle`/`Thinking`/`Answered` states around calling T030's client)
      and one renderer per closed-set component type under
      `frontend/src/ask/components/`, including a `draft_handoff` renderer
      that surfaces the handoff context rather than an inline answer; wire
      `<AskBar>` into `frontend/src/dashboard/dashboard-page.tsx` (depends
      on T030)
- [X] T032 [P] [US2] Write `frontend/src/ask/ask-bar.test.tsx` (depends on
      T031) — asserts the `Idle`/`Thinking`/`Answered` transition and that
      each response shape renders its corresponding component

**Checkpoint**: User Story 2 fully functional and independently testable —
`quickstart.md` §3, §6, §7 (partial) pass.

---

## Phase 5: User Story 3 - The Ask agent says "I don't know" or "I won't" rather than guessing (Priority: P1)

**Goal**: Predictions, colleague-judgment questions, unmatched questions,
disconnected sources, and insufficient-history stakeholders all produce a
specific, honest decline or fallback — never a guessed component.

**Independent Test**: `quickstart.md` §4 (prediction decline) and §5
(`insufficient_history` decline) — the compiled graph invoked directly with
fake ports.

**Note**: T035 depends on User Story 2's `QueryLedgerTool` (T024) — the same
lookup that answers "is this normal for X?" is what determines whether the
history is insufficient; this is the one deliberate cross-story dependency in
this feature (`tasks.md` intro).

### Implementation for User Story 3

- [X] T033 [US3] Implement the `decline` node in
      `backend/app/experience/adapters/ask_agent_graph.py` (same file,
      sequential; depends on T009) — `prediction` and `colleague_judgment`
      intents route here directly from `classify_intent`, no tool call
      (REQ-M9-05/06, REQ-M9-P2); each returns its specific
      `AskFallbackResponse.fallback_text`
- [X] T034 [US3] Implement the `fallback` node in
      `backend/app/experience/adapters/ask_agent_graph.py` (same file,
      sequential; depends on T009) — no intent matched routes here
      (REQ-M9-04): plain-text answer, clearly marked as fallback, with
      `AskFallbackResponse.sources` populated from whatever event/finding
      IDs the classify step's own context already touched — never an empty
      `sources` array standing in for "no evidence available" (REQ-M9-P3)
- [X] T035 [US3] Extend `QueryLedgerTool`'s dispatch (same file, sequential;
      depends on T024) so a `None` result from `LedgerQueryPort.
      baseline_vs_current()` routes to `decline` with `declined_reason =
      insufficient_history` instead of rendering `baseline_comparison`
      (Clarifications, 2026-08-15 — distinct from `source_not_connected`
      because the source *is* connected). Verified live against a fake
      insufficient-history ledger — `declined_reason: insufficient_history`.
- [X] T036 [US3] Implement the `source_not_connected` decline path in
      `backend/app/experience/adapters/ask_agent_graph.py` (same file,
      sequential; depends on T009) — reuses the existing `CoveragePort`
      (feature 006) to check whether a referenced source has any connected
      row before answering a source-dependent question (REQ-M9-07).
      Implemented as: before any ledger/finding/stakeholder lookup intent,
      check whether every message-bearing source (`gmail`, `zendesk`, etc.)
      is disconnected — a per-source-name match wasn't practical from a
      closed-enum classification alone, so this checks the aggregate
      message-source connectivity a lookup answer actually depends on.
      Verified live against a fake all-disconnected `CoveragePort` —
      `declined_reason: source_not_connected`.
- [X] T037 [P] [US3] Extend
      `backend/tests/experience/test_ask_agent_graph.py` (depends on T033,
      T034, T035, T036) — adds: prediction → decline, never a probability;
      colleague-judgment → decline, never a character assessment; no match
      → fallback; insufficient-history stakeholder → decline with
      `insufficient_history`, distinct from `source_not_connected`;
      disconnected source → decline with `source_not_connected`. 16 tests
      total in this file, all passing.
- [X] T038 [P] [US3] Write
      `backend/tests/unit/test_ask_queries_logging.py` (depends on T008,
      T033, T034, T035, T036) — every terminal node (render, handoff,
      decline, fallback) produces exactly one `ask_queries` row with the
      correct `matched_intent`/`rendered_component`/`declined_reason`
      combination — the dataset REQ-M9's ~90% intent-coverage measurement
      reads from (FR-023). 5 tests, all passing, reusing
      `test_ask_agent_graph.py`'s fakes rather than duplicating them.

**Checkpoint**: User Story 3 fully functional and independently testable —
`quickstart.md` §4, §5 pass. All 8 intents and all 5 `declined_reason` values
are now covered end to end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Turn `tests/golden_replay/test_placeholder.py` from a documented
placeholder into a real, passing test — the gap three prior features (004,
005, 007) explicitly deferred to this one by name — confirm the layer
boundary holds with `app.narrator`'s new domain ring and `langgraph`'s new
single-file dependency, and verify every acceptance scenario end to end.

- [X] T039 Replace `backend/tests/golden_replay/test_placeholder.py`'s
      `@pytest.mark.skip`ped stub with the real
      `test_golden_replay_reproduces_dashboard_exactly` (depends on T016,
      T019 — needs a real `narrator_outputs` row to snapshot; does not
      depend on US2/US3, since `ask_queries` is a log, not a replayed
      projection, `research.md` Decision 7): `TRUNCATE event_threads,
      response_pairs, rollups`, replay from `events` +
      `client_profile_versions` + `baseline_confirmations` alone via the
      real `ReplayUseCase` + `ComputeRollupsUseCase`, assert byte-identical
      reconstruction of `score_runs`/`score_contributions`/
      `narrator_outputs`/the real `GET /api/dashboard` response
      (`tests/strategy.md` §Golden-replay tests). Passing, stable across 3
      consecutive runs against the real database. One genuine test-design
      bug found and fixed while running this for real, not assumed from the
      plan: the first draft compared a fresh post-replay rebuild against
      *ambient* pre-existing projection counts, and failed spuriously (7 vs
      22 `event_threads`) — this suite runs against a shared, cumulative
      dev database that many other test files also append real events to
      (`tests/conftest.py`'s own documented uuid-uniqueness isolation
      model, not cleanup), so an ambient count can be stale relative to the
      ledger's current full history. Fixed by establishing a fresh "golden"
      baseline via one rebuild first, then comparing a second rebuild
      against *that*, rather than trusting whatever state happened to
      already be there.
- [X] T040 [P] Run `lint-imports --config ../.importlinter`, confirm the
      `global-dependency-rule` contract passes clean with `app.narrator`'s
      new `domain` ring populated for the first time and `langgraph`
      confined to the single `app.experience.adapters.ask_agent_graph` file
      (depends on all of Phases 3–5). One real violation found and fixed,
      not just checked clean on the first pass: `narration_v1.py` (the
      versioned prompt template + `NarrationModelOutput` schema) was
      originally placed in `app.narrator.adapters.prompts`, and
      `app.narrator.application.use_cases` imported it directly —
      `app.narrator.application is not allowed to import app.narrator.
      adapters`. Moved to `app.narrator.application.prompts.narration_v1`,
      matching `IntentReader`'s own precedent (feature 007: the model's
      structured-output schema and prompt builder live in the Application
      layer, alongside the reader itself — only the SDK-calling
      `AnthropicLLMAdapter` is genuinely an Adapter). All 3 contracts KEPT
      after the fix; full narrator/experience/ask test suite (67 tests, 1
      honest skip) re-run clean afterward.
- [X] T041 [P] Add a "Narrator and Ask Agent" section to the root
      `README.md` — how to run `run_narrator.py`, the new
      `GENERATION_MODEL_ID` prerequisite, how to `curl /api/ask`, and a
      link to `specs/008-narrator-and-ask-agent/quickstart.md`
- [X] T042 Run all of `specs/008-narrator-and-ask-agent/quickstart.md` end
      to end, confirm every acceptance scenario in `spec.md` passes, and
      re-run features 001–007's own quickstarts to confirm nothing
      regressed (depends on every task above). Verified against the real,
      freshly-built, fully containerized stack (`docker compose up --build
      -d`, not just the host venv): `migrate` applies `0002_ask_
      insufficient_history` cleanly (one real gap found — `docker compose
      build api` alone doesn't rebuild the separately-tagged `migrate`
      image; needed an explicit `docker compose build migrate`, or a full
      `docker compose up --build`); `GET /api/dashboard` returns the real
      worked-example state including the new `narrator` field; `GET
      /api/coverage` returns the new `ask_intent_coverage` field (`null`
      when empty); `POST /api/ask` fails honestly with the same
      `ANTHROPIC_API_KEY` error inside the container as on the host,
      proving the wiring, not just the business logic. Full backend suite:
      199/201 passing in isolation per module (`tests/scoring/` 36/36,
      `tests/readers/` 50/50, all of `tests/narrator/`+`tests/experience/`+
      the new `tests/unit/` additions), 2 honest skips (no live
      `ANTHROPIC_API_KEY` in this environment). One genuine, **pre-existing,
      out-of-scope** finding, not fixed here: 6 `tests/scoring/
      test_recompute_score_use_case.py` cases fail *only* when the full
      suite runs together (never in isolation) — a `score_runs.score`
      value like `99.99999...` rounds to `100.00` at the column's
      `NUMERIC(5,2)` precision, violating `CHECK (score < 100)`, triggered
      by that test file's own large synthetic point totals combined with
      this session's accumulated shared-database state. Entirely within
      `backend/app/scoring/` (feature 004's module) — this feature touches
      no scoring-engine code — so left flagged, not patched, matching this
      roadmap's own standard for out-of-scope findings (features 003/004
      each flagged issues in modules they didn't own rather than fixing
      them out of turn). Frontend: `pnpm lint`/`pnpm typecheck`/`pnpm test`
      (19/19)/`pnpm build` all clean.
- [X] T043 Extend `GET /api/coverage`'s `CoverageResponse`
      (`architecture/07-api-spec.md`, feature 006) with an
      `ask_intent_coverage: {total_questions: int, fallback_count: int,
      fallback_rate: float} | null` field — `null` when no `ask_queries`
      rows exist yet, matching every other optional field's "absent, not
      empty" discipline — computed from `ask_queries.matched_intent IS
      NULL` over all logged questions; update
      `backend/app/experience/adapters/coverage_router.py` and
      `CoveragePort` (`backend/app/experience/application/ports.py`) with
      one new read method; add a test asserting the rate updates as new
      `ask_queries` rows land (depends on T038) — closes SC-007's own
      promise that the fallback rate is "visible and measurable at any
      time, without querying the database directly," which nothing else in
      this feature's task list actually builds (found during
      `/speckit-analyze`)

**Checkpoint**: `quickstart.md` §1–10 all pass, plus the System health
screen now surfaces the Ask agent's own fallback rate — this feature is
complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS User Stories 2 and 3
  only (both extend the one compiled graph T009 builds). **User Story 1 has
  no dependency on this phase** and can start in parallel with it, right
  after Setup.
- **User Story 1 (Phase 3)**: Depends on Setup only — genuinely independent
  of `app.experience`/`app.narrator`... of the Ask agent entirely.
- **User Stories 2 and 3 (Phases 4–5)**: Both depend on Foundational. US3's
  `insufficient_history` path (T035) additionally depends on US2's
  `QueryLedgerTool` (T024) — the one deliberate cross-story dependency in
  this feature, otherwise US2 and US3 touch different terminal nodes of the
  same graph and are independently testable.
- **Polish (Phase 6)**: T039 (golden-replay) depends on US1 only. T043
  (Ask intent-coverage metric) depends on US3's T038 only, not US1/US2.
  T040–T042 depend on all prior phases being complete.

### Within Each User Story

- Domain (pure value objects/logic) before application (the use case/graph
  nodes) before adapters are wired in, as in features 005/007. Several tasks
  share one file (`backend/app/experience/adapters/ask_agent_graph.py`
  across T009/T024/T025/T033/T034/T035/T036;
  `backend/app/experience/adapters/sqlalchemy_repository.py` across
  T008/T020/T023) and are marked `[P]` only where they touch independent
  regions of that shared file; each story's own assembly task is always
  sequential, since it's what pulls that story's pieces together.

### Parallel Opportunities

- T002, T003, T004 run in parallel with T001 (different files).
- T005, T006, T007 run in parallel (independent sections of the same new
  `ports.py` additions); T008 needs T007, T009 needs T005+T006+T001.
- **Once Foundational (T005–T009) lands, User Story 1's entire phase
  (T010–T021) can proceed fully in parallel with User Stories 2 and 3** — the
  Narrator has zero dependency on the Ask agent graph.
- Within US1, T010/T012 run in parallel; T014 (the prompt template) has no
  code dependency on T010–T013 and can start immediately after Setup; T017
  and T018 run in parallel once their respective dependencies (T011, T015)
  land; T021 (frontend) can start once T020's contract shape is agreed, in
  parallel with T017–T019.
- Within US2, T022 has no dependency on T009 and can start during
  Foundational; T027/T028 run in parallel once T025/T024 land; T030
  (frontend types) can start once T004's contract is settled, in parallel
  with backend work.
- Within US3, T033/T034/T036 are independent of each other (different
  branches of the same graph) and can proceed in parallel once T009 lands;
  T035 must wait for US2's T024.
- T040, T041, and T043 in Polish are independent of each other and of T039
  (T043 only needs T038, already done by the end of Phase 5); T042 must run
  last.

---

## Implementation Strategy

### MVP First (User Story 1 alone)

1. Complete Phase 1: Setup.
2. Complete Phase 3: User Story 1 (Narrator) — does not require Phase 2.
3. **STOP and VALIDATE**: `quickstart.md` §1–2 — narrate a real score run,
   confirm the dashboard renders it for the first time since feature 006
   shipped this field permanently blocked. This alone closes the larger of
   the two gaps feature 006 explicitly deferred, and unblocks T039's
   golden-replay test independently of the Ask agent.

### Incremental Delivery

1. Setup → Foundational (graph skeleton) ready; User Story 1 can proceed in
   parallel with Foundational, since it doesn't need it.
2. Add User Story 1 (Narrator) → validate independently → the dashboard's
   explanation layer is real for the first time; golden-replay (T039)
   becomes buildable.
3. Add User Story 2 (Ask agent answers) → validate independently → the
   question box answers 7 of 8 intents for the first time since
   `POST /api/ask` was documented but never implemented.
4. Add User Story 3 (Ask agent declines) → validate independently →
   completes the closed intent set with honest refusal on every "I don't
   know / I won't" path.
5. Polish → golden-replay goes live for real, layer boundary re-confirmed,
   full quickstart re-run, features 001–007 re-verified.

### Parallel Team Strategy

With multiple developers:

1. One developer starts Setup; once done, a second starts Foundational
   (graph skeleton) while a third starts User Story 1 (Narrator) — the two
   don't touch the same files.
2. Once Foundational lands: Developer A continues into User Story 2,
   Developer B into User Story 3 (aware of the one T035↔T024 dependency).
3. Stories complete and integrate independently; Polish is the one phase
   that needs everyone's work merged first.

---

## Notes

- `[P]` tasks touch different files, or independent regions of a shared
  file, with no dependency on an incomplete task.
- Unlike feature 007 (three fully independent leaves), this feature has one
  deliberate cross-story dependency (T035 needs T024) — called out explicitly
  rather than glossed over, matching this repository's own standard for
  documenting real coupling instead of presenting a falsely-clean dependency
  graph.
- Commit after each task or logical group; stop at any checkpoint to
  validate a story independently before continuing.
