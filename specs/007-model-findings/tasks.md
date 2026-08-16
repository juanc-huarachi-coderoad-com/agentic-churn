# Tasks: Model Findings

**Input**: Design documents from `specs/007-model-findings/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`
(no `contracts/` — this feature adds no API route, `spec.md`'s own scope boundary)

**Tests**: Test tasks below cover exactly `spec.md`'s acceptance scenarios (Tone/
Intent reader behavior with `LLMPort` faked, the gate's four checks individually
and combined, the real-DB integration proving `validated`/`quarantined` outcomes)
— not a broader TDD suite beyond what those already require.

**Organization**: Tasks are grouped by user story — US1 Tone reader (P1), US2
Intent reader (P1), US3 Validation gate (P1) — per `plan.md`'s Project Structure.
All three are independent leaves: the gate (US3) operates on any `Finding` and is
fully testable against hand-constructed values without Tone/Intent existing; Tone
and Intent don't call each other or the gate directly. `RunReadersUseCase`'s
wiring — which touches all eight readers, not just this feature's two — is
genuinely cross-cutting integration work, placed in the final Polish phase,
mirroring how feature 005 placed its own `RunReadersUseCase` assembly last.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1/US2/US3
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 Add `anthropic` to `backend/pyproject.toml`'s dependencies
      (`architecture/03-technology-stack.md`'s already-adopted choice —
      this feature is the first to actually import it, mirroring how feature
      005 was the first to actually import the already-adopted `openai`)
- [X] T002 [P] Add `anthropic_api_key: str = ""` and
      `reader_model_id: str = "claude-haiku-4-5-20251001"` fields to the
      `Settings` class in `backend/app/config.py`, and add matching
      `ANTHROPIC_API_KEY=`/`READER_MODEL_ID=claude-haiku-4-5-20251001` entries
      to `.env.example` (`plan.md`'s Technical Context — no `docker-
      compose.yml` change needed, every service already loads `env_file: .env`)
- [X] T003 [P] Add two rows to `data-base/11-seed-data.sql`'s existing
      `finding_type_config` `INSERT` — `competitive_mention` and
      `contractual_reference`, each `(14.00, 0.60, 1, 14, 'v1')`, mirroring
      `escalation_language`'s existing row exactly (`spec.md` Clarifications,
      `research.md` Decision 7) — apply directly against the running dev DB
      too (`quickstart.md` §1), not just the seed file, since the DB already
      exists from feature 001's provisioning

**Checkpoint**: Dependency, config, and seed-data groundwork ready.

---

## Phase 2: Foundational

**Purpose**: The one interface (`LLMPort`) and one shared read port
(`MessageEventRepositoryPort`) both Tone and Intent depend on — the genuinely
shared prerequisites, kept minimal (feature 005's own `Reader`/
`FindingRepositoryPort` already exist and need no change).

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T004 [P] Define `LLMPort` in `backend/app/readers/application/ports.py`
      — `generate_structured(prompt: str, schema: type[T]) -> T`, one method,
      no `tools` parameter (`architecture/09-clean-architecture-and-
      patterns.md`'s already-named interface; REQ-M5-P2 — no method exists
      that could attach a tool)
- [X] T005 Implement `AnthropicLLMAdapter` in
      `backend/app/readers/adapters/anthropic_llm.py` (depends on T004) —
      the only file in this module importing `anthropic`
      (`.importlinter`'s `readers-application-purity` contract, already
      enforced without a config change); uses `client.messages.parse(
      output_format=schema)`, the SDK's native structured-output mechanism —
      no `tools`/`tool_choice` parameter is ever passed at all (`research.md`
      Decision 4, corrected from an earlier forced-tool-call design once the
      simpler native mechanism was confirmed against current SDK docs); reads
      `settings.anthropic_api_key`/`settings.reader_model_id` (T002)
- [X] T006 [P] Define `MessageEventRepositoryPort` in
      `backend/app/readers/application/ports.py` — `list_all() ->
      list[MessageEventInfo]`, one row per message-bearing event (Gmail body,
      Zendesk ticket title/description, Slack message) with decrypted text,
      `stakeholder_id`, and `occurred_at` — the shared candidate corpus both
      Tone and Intent iterate over (both cite the same real event,
      `gmail-msg-8831`, in `examples/01-end-to-end-walkthrough.md` §6's
      `fnd-6`/`fnd-7`, proving they read the same underlying data)
- [X] T007 Implement `SqlAlchemyMessageEventRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (depends on
      T006) — implements `MessageEventRepositoryPort`, decrypting message
      bodies the same way feature 003's ledger read path already does
      (`pgcrypto` column-level decryption, `architecture/03`)

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 - Tone deviation is judged against the person, not a generic scale (Priority: P1)

**Goal**: A stakeholder's genuinely different-sounding message becomes a real
`tone_deterioration` finding, compared against that specific person's own
human-confirmed baseline — and the reader abstains honestly below 5 samples.

**Independent Test**: `quickstart.md` §2–3 (abstain against the real, too-
small Meridian fixture; emit against the synthetic sufficient-baseline
fixture).

### Implementation for User Story 1

- [X] T008 [P] [US1] Define `ConfirmedBaselineWindow` in
      `backend/app/readers/domain/entities.py` — `stakeholder_id`,
      `window_start`, `window_end`, `sample_texts: list[str]`,
      `sample_count: int` (`data-model.md`)
- [X] T009 [P] [US1] Define `ConfirmedBaselineRepositoryPort` in
      `backend/app/readers/application/ports.py` —
      `get_confirmed_window(stakeholder_id: UUID) ->
      ConfirmedBaselineWindow | None`, joining `baseline_confirmations` →
      matching message-bearing `events` for that stakeholder/window
      (depends on T008)
- [X] T010 [US1] Implement `SqlAlchemyConfirmedBaselineRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (same file as
      T007, sequential; depends on T009) — implements
      `ConfirmedBaselineRepositoryPort`, returns `None` when no
      `baseline_confirmations` row exists for that stakeholder (the common
      case until `scripts/confirm_baseline.py`, T012, has been run)
- [X] T011 [US1] Implement `ToneReader` in
      `backend/app/readers/application/tone_reader.py` (depends on T004/T005
      LLMPort, T006/T007 `MessageEventRepositoryPort`, T010) — `interpret()`:
      for each stakeholder with a confirmed baseline, abstain if
      `sample_count < 5` (REQ-M6-CAL-04) without calling the model at all;
      otherwise, for each of that stakeholder's messages occurring after the
      baseline window not yet interpreted by this `reader_version` (REQ-M5-15
      cache, `FindingRepositoryPort.already_interpreted`), call
      `LLMPort.generate_structured` with the baseline's `sample_texts` plus
      the new message, schema `{deviation, magnitude, confidence,
      cited_event_ids}`; emit `tone_deterioration` citing the new message's
      event ID, `stakeholder_id` set, `status = pending_validation`
- [X] T012 [US1] Implement `backend/scripts/confirm_baseline.py` (depends on
      T009/T010) — manual trigger writing one row to `baseline_confirmations`
      for a given `--stakeholder`/`--metric`/`--window-days`, mirroring
      `scripts/run_readers.py`/`compute_score.py`'s existing pattern
      (`research.md` Decision 3 — no Profile Editor UI exists yet to build
      this into, Post-MVP per `decisions/01-mvp-scope-and-phasing.md`)
- [X] T013 [P] [US1] Add
      `backend/tests/fixtures/tone_baseline_sufficient.json` (a stakeholder
      with 5+ synthetic prior messages plus one genuinely different-sounding
      new message) and
      `backend/tests/fixtures/tone_low_confidence.json` (a case producing a
      confidence below `tone_deterioration`'s `0.65` floor, mirroring
      `examples/01` §7's `fnd-10`/Diego-in-Slack shape) — the real Meridian
      fixture is deliberately too small to clear REQ-M6-CAL-04's floor
      (`quickstart.md` §2's honest abstain)
- [X] T014 [P] [US1] Write `backend/tests/readers/test_tone_reader.py` —
      `LLMPort` faked (fixed structured responses, no live Anthropic call);
      covers: emits `tone_deterioration` with separate `magnitude`/
      `confidence` when baseline sufficient and message deviates (Acceptance
      Scenario 1); abstains below 5 samples without calling the model at all
      (Acceptance Scenario 2, assert the fake was never invoked); no finding
      when message reads consistent with baseline (Acceptance Scenario 3);
      `LLMPort` call uses the closed schema, never free prose (Acceptance
      Scenario 4); re-interpreting the same event with the same
      `reader_version` returns the cached result, zero additional model calls
      (Acceptance Scenario 5, SC-005) (depends on T011, T013)

**Checkpoint**: Tone reader complete and independently tested.

---

## Phase 4: User Story 2 - Escalation, competitive, and contractual language is caught without ever being trusted as free text (Priority: P1)

**Goal**: A message containing escalation, competitive, or contractual
language becomes a real, closed-enum-classified finding — never open text,
never actionable as an instruction.

**Independent Test**: `quickstart.md` §4 (Ana's real "brief the board" email
→ `escalation_language`, citing `gmail-msg-8831`).

### Implementation for User Story 2

- [X] T015 [US2] Implement `IntentReader` in
      `backend/app/readers/application/intent_reader.py` (depends on T004/
      T005 LLMPort, T006/T007 `MessageEventRepositoryPort`) — `interpret()`:
      for each message not yet interpreted by this `reader_version` (REQ-M5-15
      cache), call `LLMPort.generate_structured` with schema `{category:
      enum[escalation, competitive_mention, contractual_reference, none],
      confidence, cited_event_ids}`; on `category = none`, emit nothing; on
      any other category, map directly to `finding_type`
      (`escalation → escalation_language`, `competitive_mention →
      competitive_mention`, `contractual_reference → contractual_reference`
      — `data-model.md`'s table, FR-003/REQ-M5-13), citing the source event,
      `stakeholder_id` set from the message's sender when resolvable,
      `status = pending_validation`
- [X] T016 [P] [US2] Write `backend/tests/readers/test_intent_reader.py` —
      `LLMPort` faked; covers: emits a finding classified into exactly one
      closed category with confidence and citation (Acceptance Scenario 1);
      no finding for neutral text / `category = none` (Acceptance Scenario
      2); the reader's request to `LLMPort` only ever accepts the closed
      enum, an out-of-enum fake response is rejected before a `Finding` is
      even constructed (Acceptance Scenario 3); a message containing
      instruction-like phrasing produces, at most, a classification finding
      — never a tool call, since `IntentReader` holds no tool-capable
      dependency at all (Acceptance Scenario 4, REQ-M5-P2/P3); re-
      interpreting the same event with the same `reader_version` returns the
      cached result, zero additional model calls (Acceptance Scenario 5,
      SC-005 — parity with `test_tone_reader.py`'s equivalent case, added
      during `/speckit-analyze`) (depends on T015)

**Checkpoint**: Intent reader complete and independently tested.

---

## Phase 5: User Story 3 - Nothing unproven reaches the score, from any reader (Priority: P1)

**Goal**: Every finding — from any of the eight readers, not just Tone/Intent
— passes through one consistent, four-check gate before scoring; a finding
that fails is quarantined honestly, tagged with its specific failure reason,
and never repaired or resubmitted.

**Independent Test**: `quickstart.md` §5 (a hand-constructed low-confidence
finding is quarantined with `failed_check = confidence_below_floor`,
reproducing `examples/01` §7's `fnd-10`/`q-1`) — runnable against directly-
constructed `Finding` values, no dependency on `ToneReader`/`IntentReader`
existing.

### Implementation for User Story 3

- [X] T017 [P] [US3] Define `ValidationGateResult` and `FailedCheck` in
      `backend/app/readers/domain/entities.py` (same file as T008,
      sequential) — `data-model.md`'s value objects; `FailedCheck.check_name`
      restricted to `schema_invalid`/`cited_event_missing`/
      `insufficient_evidence`/`confidence_below_floor`, matching
      `quarantine.failed_check`'s existing DB enum exactly
- [X] T018 [P] [US3] Implement the gate's four pure check functions in
      `backend/app/readers/domain/services.py` (same file feature 005's
      reader decision logic already lives in, sequential) — each takes plain
      values, no I/O: `finding_schema_valid(finding, thresholds:
      tuple[float, int] | None) -> bool` (magnitude/confidence in `[0, 1]`,
      non-empty `cited_event_ids`, **and** `thresholds is not None`  — a
      `None` `thresholds` means `finding_type` wasn't a configured type,
      itself a schema failure, `research.md` Decision 6.1); `cited_events_
      exist(cited_ids, existing_ids) -> bool`; `sufficient_evidence(cited_
      ids, min_evidence_count) -> bool`; `confidence_at_floor(confidence,
      confidence_floor) -> bool` (inclusive — `spec.md`'s Edge Cases); a
      combining function returning `ValidationGateResult` with one
      `FailedCheck` per failed check (`research.md` Decision 6) — when
      `thresholds is None`, only `schema_invalid` is evaluated (evidence-
      count/confidence-floor checks have nothing to check against)
- [X] T019 [P] [US3] Define `FindingTypeConfigPort` (`get_thresholds
      (finding_type: str) -> tuple[float, int] | None` — `(confidence_floor,
      min_evidence_count)`, `None` if `finding_type` isn't a configured row —
      this `None` case is how the schema check's `finding_type`-membership
      sub-check is actually implemented, T018) and `EventExistencePort`
      (`existing_ids(ids: list[UUID]) -> set[UUID]`) in
      `backend/app/readers/application/ports.py` — reader-owned, reading the
      same `finding_type_config`/`events` tables `app.scoring`'s own ports
      read for a different shape (no `confidence_floor`/`min_evidence_count`
      exists on `app.scoring`'s existing `FindingTypeConfig`, so this is a
      new port, not a cross-module import, `research.md`'s established
      convention)
- [X] T020 [P] [US3] Define `QuarantineRepositoryPort` in
      `backend/app/readers/application/ports.py` — `record(finding_id: UUID,
      failed_checks: list[FailedCheck]) -> None` (depends on T017)
- [X] T021 [US3] Implement `SqlAlchemyFindingTypeConfigRepository`,
      `SqlAlchemyEventExistenceRepository`, and
      `SqlAlchemyQuarantineRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (same file as
      T007/T010, sequential; depends on T019, T020) — the quarantine
      repository inserts one `quarantine` row (`UNIQUE(finding_id)`,
      REQ-M5A-03) plus one `quarantine_reasons` row per failed check
- [X] T022 [US3] Implement `ValidationGate` in
      `backend/app/readers/application/validation_gate.py` (depends on T018,
      T019, T020, T021) — `evaluate(finding: Finding) ->
      ValidationGateResult`: fetches that finding's type's thresholds
      (T019/T021, possibly `None`) and which of its `cited_event_ids`
      actually exist (T019/T021), runs T018's four pure checks, returns the
      combined result — no LLM call, no ranking, purely orchestration
      (REQ-M5A-01, Chain of Responsibility per `architecture/09`); never
      raises for an unconfigured `finding_type` (that's the `None`/
      `schema_invalid` path, T018) — only genuine infrastructure failures
      (a dropped DB connection) propagate, which is exactly what T024's
      widened `try`/`except` around this call exists to contain
- [X] T023 [P] [US3] Write `backend/tests/readers/test_validation_gate.py`
      — pure, no live DB (fakes for `FindingTypeConfigPort`/
      `EventExistencePort`): each of the four checks fails independently and
      produces the correct `failed_check` value (Acceptance Scenario 1); an
      unconfigured `finding_type` (`FindingTypeConfigPort` fake returns
      `None`) produces `schema_invalid`, not an exception; a finding failing
      two checks at once produces two distinct `FailedCheck` entries, not
      one collapsed label (Acceptance Scenario 3); confidence exactly equal
      to the floor passes (`spec.md`'s Edge Cases, inclusive floor); a
      finding passing all four returns `passed = True` (Acceptance Scenario
      5) (depends on T022)

**Checkpoint**: Validation gate complete and independently tested against
hand-constructed findings — no dependency on US1/US2.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Wire Tone, Intent, and the gate into the one real trigger
(`RunReadersUseCase`, extended, not replaced) so the gate applies to **all
eight** reader types, prove `spec.md`'s SC-001 through SC-005 against the
real, already-ingested Meridian fixture, confirm feature 006's `GET
/api/coverage` now returns real quarantine data, and document the feature.

- [X] T024 Extend `RunReadersUseCase` in
      `backend/app/readers/application/use_cases.py` (depends on T011 Tone,
      T015 Intent, T022 Gate) — after each reader's `interpret()` returns,
      pass every emitted finding through `ValidationGate.evaluate()`
      (T022), construct the final `Finding` via `dataclasses.replace(finding,
      status="validated" if result.passed else "quarantined")`, call
      `FindingRepositoryPort.persist()` exactly once with the final version,
      and on failure call `QuarantineRepositoryPort.record()` (T020/T021) —
      replaces the current unconditional `pending_validation` persist
      (`research.md` Decision 5); per-reader failure isolation (FR-014,
      feature 005's existing behavior) is unchanged — one reader raising
      still lets the others' findings reach the gate normally. Wrap the
      gate-evaluate-then-persist step for **each finding** in its own
      `try`/`except` too, not just each reader's `interpret()` call (gap
      found during `/speckit-analyze`: the original design only guarded
      `interpret()`, so an unexpected exception during evaluation/persist —
      not the expected `None`-thresholds/`schema_invalid` path, which never
      raises, T022 — would have propagated out of the whole `execute()` loop
      and silently skipped every reader still queued after the failing one)
      — record the error against that finding and continue to the next one,
      `data-model.md`'s pseudocode
- [X] T025 [P] Register `ToneReader`/`IntentReader` instances and
      `ValidationGate` at the composition root that constructs
      `RunReadersUseCase` for `scripts/run_readers.py` (depends on T011,
      T015, T022, T024) — all eight readers now registered, not five
- [X] T026 Extend `backend/tests/readers/test_run_readers_use_case.py` —
      real-DB integration test: asserts `validated`/`quarantined` outcomes
      instead of feature 005's blanket `pending_validation` assertion
      (`specs/ROADMAP.md`'s feature 006 log entry already flagged this
      exact assertion as needing to change); runs against the real,
      already-ingested Meridian ledger plus the synthetic fixtures (T013),
      confirms Ana's real "brief the board" email produces a validated
      `escalation_language` finding (SC-002), confirms a deliberately bad
      finding lands in `quarantine` with the correct `failed_check` (SC-003),
      re-runs and asserts zero additional model calls (REQ-M5-15, SC-005)
      (depends on T024, T025)
- [X] T027 [P] Extend `backend/tests/unit/test_coverage_route.py`
      (feature 006's existing test) — confirms `GET /api/coverage`'s
      `quarantine` field now returns real rows once a finding has been
      quarantined, replacing feature 006's own "always empty" assertion
      (REQ-M5A-04) — no route code change needed, feature 006 already reads
      real data; this task only extends the test's fixture setup and
      assertion (depends on T026)
- [X] T028 [P] Write `backend/tests/unit/test_readers_purity.py` extension
      (or confirm the existing static-check pattern from feature 005 already
      covers it) — confirms no `anthropic` import exists anywhere in
      `app.readers.domain`/`app.readers.application` beyond `LLMPort`'s
      interface declaration; `lint-imports --config ../.importlinter` passes
      clean with the `readers-application-purity` contract unchanged
- [X] T029 [P] Add a "Model Findings" section to the root `README.md` — how
      to run `confirm_baseline.py` then `run_readers.py`, the new
      `ANTHROPIC_API_KEY`/`READER_MODEL_ID` prerequisites, and a link to
      `specs/007-model-findings/quickstart.md`
- [X] T030 Run all of `specs/007-model-findings/quickstart.md` end to end,
      confirm every acceptance scenario in `spec.md` passes, and re-run
      features 001–006's own quickstarts to confirm nothing regressed
      (depends on every task above)

**Checkpoint**: `quickstart.md` §1–8 all pass — this feature is complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
  (Tone and Intent both need `LLMPort`/`AnthropicLLMAdapter` and the shared
  `MessageEventRepositoryPort` to exist first).
- **User Stories 1–3 (Phases 3–5)**: All depend on Foundational only —
  genuinely independent of each other. Tone and Intent don't call each
  other; the gate operates on any `Finding` value and needs neither reader's
  code to exist, only a `Finding` instance to evaluate.
- **Polish (Phase 6)**: Depends on all three user stories being complete —
  `RunReadersUseCase`'s extension is the one piece of real cross-cutting
  integration this feature needs (it must know about Tone, Intent, *and* the
  gate simultaneously), deliberately placed last, matching feature 005's own
  precedent.

### Within Each User Story

- Domain (pure value objects/logic) before application (the reader/gate
  itself) before adapters are wired in — as in feature 005, several tasks
  share one file (`backend/app/readers/domain/entities.py` across T008/T017;
  `backend/app/readers/adapters/sqlalchemy_repository.py` across T007/T010/
  T021) and are marked `[P]` only where they touch independent regions of
  that shared file; each story's own assembly task (T011 Tone, T015 Intent,
  T022 Gate) is always sequential, since it's what pulls that story's domain
  + port pieces together.

### Parallel Opportunities

- T002 and T003 run in parallel with T001 (different files).
- T004 and T006 run in parallel (different sections of the same new
  `ports.py` additions, no dependency between `LLMPort` and
  `MessageEventRepositoryPort`); T005 needs T004, T007 needs T006.
- Once Foundational (T004–T007) lands, **User Story 3's entire phase
  (T017–T023) can proceed fully in parallel with User Story 1 (T008–T014)
  and User Story 2 (T015–T016)** — the gate has zero dependency on either
  reader's code.
- Within US1, T008/T009 run in parallel with each other; T013 (fixtures) has
  no code dependency and can start immediately after Setup.
- Within US3, T017/T018/T019/T020 all touch independent files/regions and
  run in parallel; T021 needs T019+T020 first, T022 needs T018+T021.
- T027, T028, and T029 in Polish are independent of each other and can run
  in parallel once T026 lands.

---

## Implementation Strategy

### MVP First (User Story 1 alone)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3 (User Story 1 — Tone).
4. **STOP and VALIDATE**: `quickstart.md` §2–3 — the honest abstain against
   the real fixture, then a real finding against the synthetic sufficient-
   baseline fixture. This is the smallest real, demonstrable slice: the
   product's own named differentiator (P7, baseline-relative tone) working
   end to end, even before Intent or the gate exist.

### Incremental Delivery

1. Setup + Foundational → `LLMPort` and the shared message-read port ready.
2. Add User Story 1 (Tone) → validate independently → P7's baseline-relative
   judgment proven real.
3. Add User Story 2 (Intent) → validate independently → closed-enum
   escalation/competitive/contractual classification proven real.
4. Add User Story 3 (Validation gate) → validate independently against
   hand-constructed findings → the four-check gate proven correct without
   needing any live reader.
5. Polish (Phase 6) → wire all three (plus the five existing deterministic
   readers) behind one gated `RunReadersUseCase`, prove SC-001 through
   SC-005 against the real fixture, confirm feature 006's dashboard now
   shows real quarantine data, re-verify features 001–006 still pass.

---

## Notes

- `[P]` tasks touch different files, or independent regions of a shared
  file, with no dependency on an incomplete task.
- Like feature 005, this feature's three stories are independent leaves plus
  one final assembly phase — noted explicitly rather than glossed over.
- Commit after each task or logical group; stop at any checkpoint to
  validate a story independently before continuing.
