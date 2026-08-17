# Tasks: Feedback Memory

**Input**: Design documents from `specs/010-feedback-memory/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/feedback.md`, `quickstart.md`

**Tests**: Test tasks below cover exactly `spec.md`'s acceptance scenarios —
the pure damping formula unit-tested directly (no DB, matching
`test_fact_check.py`/the draft composer's check-function precedent),
`RecordFeedbackVerdictUseCase` with its three ports faked, a real-DB/
real-route integration test proving the worked REQ-M6-CAL-03a values via
the actual API, and a re-run of feature 004's existing golden-replay/
reconciliation/monotonicity suite to confirm `research.md` Decision 2's
refactor is behavior-preserving — not a broader TDD suite beyond what those
already require.

**Organization**: Tasks are grouped by user story — US1 the core damping
write path (P1), US2 disclosure always visible across all three surfaces
(P1), US3 `correct`/`resolved` behave distinctly from `false_alarm` (P2) —
per `plan.md`'s Project Structure. US3 is the lightest story in this
feature: `RecordFeedbackVerdictUseCase` (built in US1) already handles all
three verdict types generically — a `resolved` verdict simply never
increments `false_alarm_count`/`correct_count`, so REQ-M6-CAL-03b's "never
touches weight" guarantee falls out of the same formula with no
verdict-type branch anywhere (`data-model.md`). US3 therefore adds no new
production code, only the test coverage that proves this — an honest
coupling, matching feature 009's own precedent for calling out when a
"story" is mostly proof rather than new surface area.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, or an independent region of
  a shared file, with no dependency on an incomplete task)
- **[Story]**: US1/US2/US3
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 Confirm no new dependency, environment variable, or migration is
      needed before starting (`research.md`): verify `feedback_verdicts`
      and `damping_weights` already exist via
      `docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c
      "\d feedback_verdicts" -c "\d damping_weights"` against the running
      stack — both must already be true (feature 001's initial migration);
      if either is missing, stop and re-run that migration before
      continuing, don't add a new one

**Checkpoint**: Environment confirmed ready — no groundwork tasks needed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The pure domain formula, the ports, and the read/write
plumbing every story needs — resolving a finding's pattern, reading/
upserting a damping weight. No use-case assembly yet.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T002 [P] Define `DampingWeight` and `FindingPatternComponents` in
      `backend/app/context/domain/entities.py` (new file) —
      `data-model.md`'s domain shapes
- [X] T003 [P] Implement `pattern_signature(reader_type, finding_type) ->
      str`, `compute_weight(false_alarm_count, correct_count) -> float`
      (REQ-M6-CAL-03a: `clamp(0.5^fa × 1.15^c, 0, 1)`), and
      `build_disclosure_text(false_alarm_count, correct_count,
      resolved_count) -> str | None` (REQ-M4-04, `None` when the pattern
      has never received a `false_alarm`/`correct` verdict) in
      `backend/app/context/domain/damping_calculator.py` (new file — the
      exact file `decisions/02-repo-and-tooling.md`'s module→package
      mapping table already names for M4) — all pure, no I/O.
      `pattern_signature`'s output **MUST** be byte-identical to
      `app.scoring.application.use_cases.RecomputeScoreUseCase`'s existing
      inline `f"{reader_type}+{finding_type}"` (`research.md` Decision 1) —
      assert this equality directly in T008's test, not just by inspection
- [X] T004 Define `FeedbackFindingReadPort`, `IssueTopFindingReadPort`,
      `FeedbackVerdictRepositoryPort` in
      `backend/app/context/application/ports.py` (extends the existing
      file; depends on T002 for return types)
- [X] T005 [P] Implement `SqlAlchemyFeedbackFindingReader` in
      `backend/app/context/adapters/sqlalchemy_repository.py` (new
      classes in the existing file; depends on T004) —
      `get_pattern_components(finding_id)`: `SELECT reader_type,
      finding_type FROM findings WHERE id = :id AND status = 'validated'`
      (matches `SqlAlchemyFindingReader.get_finding`'s existing
      validated-only filter precedent), `None` if no match
- [X] T006 [P] Implement `SqlAlchemyIssueTopFindingReader` in
      `backend/app/context/adapters/sqlalchemy_repository.py` (same file,
      independent class; depends on T004) — `get_top_finding_id(issue_id)`:
      `SELECT finding_id FROM finding_issue_map WHERE issue_id = :id ORDER
      BY rank_within_issue ASC LIMIT 1`, `None` if no match
- [X] T007 [P] Implement `SqlAlchemyFeedbackVerdictRepository` in
      `backend/app/context/adapters/sqlalchemy_repository.py` (same file,
      independent class; depends on T002, T004) — `get_damping(pattern_
      signature)`: reads the current `damping_weights` row, or a zeroed
      `DampingWeight(weight=1.0, ...)` default if none exists (FR-008);
      `record(...)`: one transaction — `INSERT INTO feedback_verdicts` then
      `INSERT INTO damping_weights ... ON CONFLICT (pattern_signature) DO
      UPDATE ...` (`research.md` Decision 5: read-then-upsert, not a
      locking transaction, at this scale)
- [X] T008 [P] Write `backend/tests/unit/test_damping_calculator.py`
      (depends on T003) — pure, no DB: `compute_weight(1, 0) == 0.500`,
      `compute_weight(2, 0) == 0.250`, `compute_weight(2, 1) == 0.2875`
      (REQ-M6-CAL-03a's three worked values, exactly); clamp bounds at `0`
      and `1.0` for extreme counts; `build_disclosure_text` returns `None`
      for `(0, 0, 0)` and a non-empty string once `false_alarm_count > 0`
      or `correct_count > 0`; `pattern_signature("relationship",
      "relationship_change") == "relationship+relationship_change"`,
      matching `data-base/07-schema-feedback.md`'s own worked example and
      literally equal to `app.scoring.application.use_cases`'s own inline
      construction for the same inputs (import both, assert equality —
      `research.md` Decision 1's guarantee, mechanically checked)

**Checkpoint**: Foundation ready — the formula, the ports, and all
read/write plumbing exist. US1, US2, and US3 can now begin.

---

## Phase 3: User Story 1 - Marking a finding false alarm measurably reduces future occurrences of that pattern (Priority: P1)

**Goal**: A single-click `false_alarm` verdict is recorded, matched to its
pattern, and measurably reduces that pattern's damping weight for every
future matching finding — without altering any already-computed score.

**Independent Test**: `quickstart.md` §1–2, §4, §6 (submit `false_alarm`
once → `weight = 0.500`; twice → `weight = 0.250`; the already-computed
`score_run` is byte-identical after; a fresh scoring run reads the new
weight).

### Implementation for User Story 1

- [X] T009 [US1] Implement `RecordFeedbackVerdictUseCase`,
      `VerdictRequiresFindingError`, `FindingNotFoundError`,
      `IssueNotFoundError` in
      `backend/app/context/application/use_cases.py` (extends the existing
      file, alongside `SubmitProfileUseCase`; depends on T003, T004, T005,
      T006, T007) — `execute(finding_id, issue_id, verdict,
      submitted_by_user_id)`: FR-005a check first (`false_alarm`/`correct`
      with only `issue_id` → `VerdictRequiresFindingError`); resolve the
      target finding (`finding_id` directly, or — `resolved` + `issue_id`
      only — T006's top-ranked lookup, `IssueNotFoundError` if empty);
      resolve `reader_type`/`finding_type` via T005
      (`FindingNotFoundError` if `None`); build `pattern_signature` (T003);
      read current `DampingWeight` (T007); increment exactly the one
      counter the verdict names; recompute `weight`/`disclosure_text`
      (T003); call T007's `record(...)` (`data-model.md`'s full sequence)
- [X] T010 [US1] Implement `backend/app/context/adapters/feedback_router.py`
      (new file) — `POST /api/feedback` (depends on T009): reads
      `submitted_by_user_id` from the bearer token, never the request
      body; validates at least one of `finding_id`/`issue_id` is set →
      `422` otherwise (FR-003); catches `VerdictRequiresFindingError` →
      `422`; catches `FindingNotFoundError`/`IssueNotFoundError` → `404`;
      returns `204` on success (`contracts/feedback.md`)
- [X] T011 [US1] Register `feedback_router` in `backend/app/main.py`
      (depends on T010)
- [X] T012 [P] [US1] Write
      `backend/tests/unit/test_record_feedback_verdict_use_case.py`
      (depends on T009) — all three ports faked: one `false_alarm` on a
      fresh pattern → `weight == 0.500`; a second `false_alarm` on the
      same pattern → `weight == 0.250` (Acceptance Scenario 2); a
      `false_alarm`/`correct` verdict with only `issue_id` raises
      `VerdictRequiresFindingError` (FR-005a); an unknown `finding_id`
      raises `FindingNotFoundError`; an unknown/finding-less `issue_id`
      raises `IssueNotFoundError`
- [X] T013 [US1] Write
      `backend/tests/unit/test_feedback_routes_real_db.py` (depends on
      T011) — real-DB integration against the worked-example fixture:
      `POST /api/feedback` with a real `finding_id` and `verdict:
      false_alarm` returns `204`; `damping_weights` shows `weight ==
      0.500`, `false_alarm_count == 1`; a second identical call →
      `weight == 0.250`; the `score_run` row that existed before either
      call is byte-identical after both (Acceptance Scenario 4); a fresh
      `RecomputeScoreUseCase` run afterward produces a
      `score_contributions.damping == 0.250` for a new matching-pattern
      finding (Acceptance Scenario 3); an `issue_id`-only `false_alarm`
      request returns `422` and writes no row anywhere (FR-005a)

**Checkpoint**: User Story 1 is fully functional and independently
testable — `false_alarm` verdicts measurably damp future matching
findings, single-click, no modal, past scores untouched.
`quickstart.md` §1–2, §4, §6 pass.

---

## Phase 4: User Story 2 - The team can always see why a card's weight was reduced (Priority: P1)

**Goal**: Wherever a damped finding (`damping_weights.weight < 1.0`) is
displayed — the evidence trace panel, reached from the dashboard's
contribution bar or an Ask-agent `delta_breakdown`/`ranked_issues` answer —
the pattern's current, plain-language `disclosure_text` is shown. A damped
finding is never hidden, only labeled.

**Independent Test**: `quickstart.md` §3, §5. The backend half
(`disclosure_text` on `GET /api/evidence/{id}`) is independently testable
by seeding a `damping_weights` row directly via SQL, with no dependency on
User Story 1's route. The frontend verdict buttons need US1's
`POST /api/feedback` to exist for genuine end-to-end interaction — the one
real cross-story dependency in this feature, matching feature 009's own
precedent for stating real coupling explicitly rather than presenting a
falsely-clean split.

### Implementation for User Story 2

- [X] T014 [P] [US2] Define `DampingDisclosurePort`, `DisclosureRecord` in
      `backend/app/experience/application/ports.py` (extends the existing
      file, independent region)
- [X] T015 [P] [US2] Implement `SqlAlchemyDampingDisclosureReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (extends
      the existing file; depends on T014) —
      `get_disclosure(pattern_signature)`: `SELECT disclosure_text FROM
      damping_weights WHERE pattern_signature = :ps AND weight < 1.000`,
      `None` otherwise (FR-011's "only when true and relevant" enforced at
      the read); extend `FindingRecord`
      (`backend/app/experience/application/ports.py`) and
      `SqlAlchemyFindingReader.get_finding`'s query (same adapters file)
      to also read/return `reader_type` — needed to build
      `pattern_signature` for a finding this module didn't previously
      need that field for
- [X] T016 [US2] Extend `GetEvidenceTraceUseCase` in
      `backend/app/experience/application/use_cases.py` (depends on T003,
      T015) — after resolving the finding, compute
      `pattern_signature(finding.reader_type, finding.finding_type)`
      (imported from `app.context.domain.damping_calculator`, `research.md`
      Decision 2/4) and call `DampingDisclosurePort.get_disclosure`;
      attach the result to `EvidenceTraceResult.disclosure_text`
- [X] T017 [US2] Add `disclosure_text: str | None` to
      `EvidenceTraceResponse` in
      `backend/app/experience/adapters/evidence_router.py` (depends on
      T016); update `architecture/07-api-spec.md`'s
      `EvidenceTraceResponse` schema to match (`contracts/feedback.md`)
- [X] T018 [P] [US2] Extend `backend/tests/unit/test_evidence_route.py`
      (the real-DB HTTP-level evidence-trace test file — corrected during
      implementation from the originally-planned
      `test_state_and_evidence_services.py`, which only tests pure domain
      services with no ports/DB, not the full `GetEvidenceTraceUseCase`
      wiring `disclosure_text` needs; depends on T016, T017) — a finding
      whose pattern has `damping_weights.weight < 1.0` produces a
      non-empty `disclosure_text`; a finding whose pattern has never
      received a verdict (no row, or `weight == 1.0`) produces `None`
      (Acceptance Scenario 2)
- [X] T019 [P] [US2] Extend `frontend/src/evidence/types.ts` —
      `EvidenceTraceResponse` gains `disclosure_text: string | null`
- [X] T020 [US2] Write `frontend/src/evidence/use-feedback.ts` (new file,
      depends on T011, T019) — `POST /api/feedback` mutation, TanStack
      Query, matching `use-evidence.ts`'s existing fetch-wrapper pattern;
      invalidates the `['evidence', scoreContributionId]` query on success
      so the panel re-fetches and picks up the new `disclosure_text`
- [X] T021 [US2] Extend `frontend/src/evidence/evidence-panel.tsx`
      (depends on T019, T020) — remove the existing "no feedback controls
      here — feature 010's job" comment; add three verdict buttons
      (Correct / False alarm / Resolved), each a single click with no
      modal/confirmation (FR-002), calling `use-feedback.ts`'s mutation
      with the panel's own `data.finding_id`; render `data.disclosure_text`
      when non-null, render nothing when `null` (P6 — no manufactured
      "learning happened" signal where none occurred)
- [X] T022 [P] [US2] Extend `frontend/src/evidence/evidence-panel.test.tsx`
      (depends on T021) — clicking each verdict button calls the mutation
      with the correct `{finding_id, verdict}` payload and no confirmation
      dialog renders; `disclosure_text` renders when present in the fetched
      data, nothing renders when it's `null`
- [X] T023 [US2] Extend `frontend/src/ask/components/answer-renderer.tsx`
      (depends on T021) — add `score_contribution_id: string` to the local
      `Cause` interface (already present in the backend response,
      `research.md` Decision 3 — no backend change needed here); make each
      `DeltaBreakdown`/`RankedIssues` row a button opening the same
      `EvidencePanel` via a new `onOpenEvidence?: (scoreContributionId:
      string) => void` prop threaded through `AnswerRenderer`, mirroring
      `onOpenDraftComposer`'s existing threading pattern from feature 009

**Checkpoint**: User Story 2 is functional — a damped finding's disclosure
is visible from all three named surfaces (dashboard → evidence panel;
evidence panel directly; Ask-agent `delta_breakdown`/`ranked_issues` →
evidence panel), and remains visible (never hidden) regardless of how many
times its pattern has been dismissed — proven structurally: no query
anywhere added by this feature filters on `damping_weights.weight`, only
ever displays it (REQ-M4-P1, no task needed — an absence, not a feature).
Likewise, REQ-M4-P2's "no blanket reader-type suppression" has no task of
its own: no control or route exists anywhere that accepts anything less
specific than a single `finding_id`/`issue_id`-scoped verdict — proven by
FR-005a's restriction (T009) plus the fact that `feedback_router.py`
(T010) exposes exactly one route, shaped exactly like `contracts/
feedback.md`, with no reader-type parameter anywhere in it.
`quickstart.md` §3, §5 pass.

---

## Phase 5: User Story 3 - Correct and resolved verdicts behave differently from false alarm (Priority: P2)

**Goal**: `correct` partially recovers a pattern's weight after prior
`false_alarm`s (never in one step); `resolved` increments its own count and
feeds the disclosure text but never touches `weight` at all.

**Independent Test**: `quickstart.md` §5 (a `correct` verdict on a pattern
already damped by two `false_alarm`s recovers to exactly `0.2875`, never
`1.0`; a `resolved` verdict on any pattern increments `resolved_count`
while `weight` stays unchanged).

**Note**: `RecordFeedbackVerdictUseCase` (T009) already handles `correct`
and `resolved` generically — REQ-M6-CAL-03b's guarantee is a property of
the formula itself (`resolved_count` never enters `compute_weight`'s
inputs), not a branch this use case needs. This story adds test coverage
only, no new production code — see this file's header note.

### Implementation for User Story 3

- [X] T024 [US3] Extend
      `backend/tests/unit/test_record_feedback_verdict_use_case.py`
      (same file as T012, sequential; depends on T012) — two
      `false_alarm` verdicts followed by one `correct` verdict on the same
      pattern → `weight == 0.2875` (Acceptance Scenario 1, REQ-M6-CAL-03a's
      worked recovery value); a `resolved` verdict on a fresh pattern →
      `resolved_count == 1`, `weight == 1.0` unchanged (Acceptance
      Scenario 2); a `resolved` verdict on an already-damped pattern
      leaves `false_alarm_count`/`correct_count`/`weight` exactly as they
      were (REQ-M6-CAL-03b)
- [X] T025 [P] [US3] Extend
      `backend/tests/unit/test_feedback_routes_real_db.py` (same file
      as T013, independent test function; depends on T013) — the same
      two-`false_alarm`-then-`correct` sequence as T024, driven through
      the real `POST /api/feedback` route end to end, confirming
      `weight == 0.2875` in `damping_weights`; a `resolved` verdict via the
      route confirms `resolved_count` incremented and `weight` untouched
      in the database

**Checkpoint**: All three user stories complete and independently testable
— `quickstart.md` §1–7 pass. This feature is functionally complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Remove the one piece of duplication this feature's design
deliberately deferred (`research.md` Decision 2), confirm the layer
boundary and golden-replay/reconciliation/monotonicity guarantees still
hold, confirm the no-LLM-import guarantee (REQ-M4-05/SC-005), and document
the feature.

- [X] T026 [P] Refactor `RecomputeScoreUseCase.execute` in
      `backend/app/scoring/application/use_cases.py` (depends on T003) —
      replace the inline `f"{finding.reader_type}+{finding.finding_type}"`
      with an import of `app.context.domain.damping_calculator.
      pattern_signature`, a behavior-preserving change (identical output
      for identical input, `research.md` Decision 2) — one canonical
      implementation instead of two independently-typed copies
- [X] T027 Re-run `backend/tests/scoring/` in full (depends on T026) —
      confirmed behavior-preserving via a stash-based A/B comparison: the
      same 6 `test_recompute_score_use_case.py` cases fail identically
      with T026's change completely reverted (`git stash`) — a
      pre-existing, database-state-dependent issue
      (`score_runs.score` rounds to exactly `100.00` at column precision
      once this long-lived shared dev database's accumulated point totals
      cross a threshold), already documented in `specs/ROADMAP.md` for
      features 008/009 as out-of-scope for any feature that doesn't touch
      `backend/app/scoring/`'s own arithmetic — not a regression T026
      introduces. All 29 other scoring tests (ageing, band, damping,
      issue-grouping, monotonicity, reconciliation, scoring-calculator)
      pass clean
- [X] T028 [P] Run `lint-imports --config ../.importlinter` (depends on
      T016, T026) — confirm the `global-dependency-rule` contract passes
      clean with `app.scoring.application` → `app.context.domain` and
      `app.experience.application`/`adapters` → `app.context.domain` (both
      cross-module `domain`-importing edges this feature adds), matching
      feature 009's own precedent that this direction is unrestricted, not
      just assumed
- [X] T029 [P] Write `backend/tests/unit/test_no_llm_imports.py` —
      statically scans **every** file this feature added or extended, not
      only `backend/app/context/`: also
      `backend/app/experience/application/ports.py`,
      `backend/app/experience/adapters/sqlalchemy_repository.py`,
      `backend/app/experience/application/use_cases.py`,
      `backend/app/experience/adapters/evidence_router.py`, and
      `backend/app/scoring/application/use_cases.py` (`plan.md`'s Project
      Structure — the disclosure-read extension and the `pattern_signature`
      refactor are as much "this feature" as `app/context/` is) — fails if
      any imports `anthropic` or `openai` (REQ-M4-05, SC-005 — a structural
      guarantee across the feature's full footprint, not just its newest
      module; `/speckit-analyze` finding C1, 2026-08-16)
- [X] T030 [P] Add a "Feedback Memory (Phase 10)" section to the root
      `README.md`, matching the "Draft Composer (Phase 9)" section's
      style — how to `curl POST /api/feedback`, the worked
      `false_alarm`/`false_alarm`/`correct` → `0.500`/`0.250`/`0.2875`
      sequence, and a link to `specs/010-feedback-memory/quickstart.md`
- [X] T031 **Fully re-run end to end** against a completely fresh,
      rebuilt stack: `docker compose down -v` (wiped the volume) →
      `docker compose up --build -d` → `scripts/seed.py` →
      `scripts/run_collector.py --source simulated` →
      `scripts/seed_score_fixture.py` → `scripts/compute_score.py` (the
      same bootstrap sequence `specs/004-score-engine/quickstart.md`
      documents). Every one of `quickstart.md`'s §1–7 steps executed live
      via `curl` against the real running `api` container and confirmed
      exactly as specified: §1 a real finding's `disclosure_text` starts
      `null`; §2 one `false_alarm` → `weight = 0.500`; §3 the evidence
      endpoint immediately shows the new `disclosure_text`; §4 a second
      `false_alarm` → `weight = 0.250`; §5 a `correct` verdict →
      `weight = 0.287` (`0.2875` at the DB's `NUMERIC(4,3)` precision);
      §6 the pre-existing `score_run` row stayed **byte-identical**
      after a fresh `compute_score.py` run, while that same fresh run's
      `score_contributions.damping` for the finding read `0.287` and the
      dashboard score dropped `91.82 → 71.60` as a direct, live
      consequence; §7 `false_alarm`/`resolved` with only an `issue_id`
      correctly returns `422`/`204` respectively (FR-005a). §8 (no
      LLM-reachable code path) reconfirmed via `grep`. §9 the full backend
      suite (`tests/unit/`, `tests/scoring/`, `tests/experience/`) — 148
      passed, 1 skipped, re-run a second time including
      `test_feedback_routes_real_db.py` — 8/8 passed against this freshly
      seeded database. Frontend: 25/25 Vitest, `tsc`/`eslint` clean.
      **Two corrections made during this final pass**: (1)
      `quickstart.md` §9's command referenced the same nonexistent
      `tests/context/` directory `research.md`/`plan.md` already caught
      and fixed elsewhere — fixed here too, and updated to pass
      `ENCRYPTION_KEY_PATH`/`CLIENT_PROFILE_PATH`/`COLLECTOR_FIXTURE_PATH`
      explicitly, matching feature 004's own quickstart precedent for
      running pytest from a host checkout; (2) the `FileNotFoundError` in
      `test_worked_example.py` originally attributed to T027/an earlier
      pass as a "pre-existing issue" was actually just this missing env
      var on the local host-checkout invocation — with it set, that test
      passes cleanly, so it was never a real bug, just an incomplete
      earlier repro. One genuinely pre-existing, already-roadmap-documented
      artifact reconfirmed, not introduced by this feature:
      `tests/readers/test_run_readers_use_case.py` fails
      (`recurring_issue` citing 1 event instead of 2+) only when run in
      the same session *after* `tests/scoring/test_worked_example.py` has
      mutated the shared dev database — feature 009's roadmap entry
      documents this exact failure mode verbatim; every acceptance
      scenario in `spec.md` is independently
      proven by the 31 automated tests above (unit, real-DB integration,
      frontend) plus `lint-imports` (3/3 kept)

**Checkpoint**: `quickstart.md` §1–9 all pass — this feature is complete.
`data-base/07-schema-feedback.md`'s `pattern_signature` field-description
correction (`research.md` Decision 1) was already applied during
`/speckit-plan`, before this task list existed — no task for it here,
flagged so this file alone doesn't read as if that inconsistency is still
open.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all three user
  stories.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on Foundational directly for its
  backend half (T014–T018 need only `damping_weights` to exist, seedable
  directly via SQL); its frontend half (T020–T023) additionally depends on
  User Story 1's `POST /api/feedback` (T010/T011) existing for genuine
  end-to-end interaction — the one real cross-story dependency in this
  feature.
- **User Story 3 (Phase 5)**: Depends on Foundational **and** User Story 1
  (T024/T025 extend US1's own test files sequentially, and exercise
  `RecordFeedbackVerdictUseCase`/`POST /api/feedback`, both built in US1)
  — adds no new production code of its own.
- **Polish (Phase 6)**: T026 depends on T003; T027 depends on T026; T028
  depends on T016 and T026; T029 depends on T015, T016, T017, T023, and
  T026 (it scans files each of those tasks creates/extends —
  `/speckit-analyze` finding C1, 2026-08-16, broadened its scope beyond
  `app/context/` alone); T031 must run last.

### Within Each User Story

- Domain (pure functions/entities) before application (ports, use cases)
  before adapters (repositories, routers), as in every prior feature.
  Several tasks share one file across stories
  (`backend/app/context/adapters/sqlalchemy_repository.py` across
  T005–T007; `backend/tests/unit/test_record_feedback_verdict_use_case.py`
  across T012/T024; `backend/tests/unit/test_feedback_routes_real_db.py`
  across T013/T025) and are marked `[P]` only where they touch independent
  regions/classes with no dependency on an incomplete sibling task.

### Parallel Opportunities

- T002 and T003 can start immediately after T001, in parallel (different
  files).
- T005, T006, T007 all depend on T004 (and T002/T003 for T007) and run in
  parallel with each other (independent classes in the same file).
- T008 depends only on T003 and can run in parallel with T004–T007.
- T012 and T013 run in parallel once their respective dependencies (T009,
  T011) land.
- T014 and T019 have no dependency on each other and can start in parallel
  once Foundational lands; T015 depends on T014.
- T018 and T019 run in parallel once their dependencies land.
- T022 waits on T021; T023 waits on T021 (shared component file,
  sequential).
- T025 runs in parallel with T024 once both their dependencies (T012/T013)
  land — independent test files.
- T026 and T030 in Polish are independent of everything else; T027 waits on
  T026; T028 waits on T016 and T026; T029 waits on T015, T016, T017, T023,
  and T026 (its now-broadened scan target — `/speckit-analyze` finding C1);
  T031 must run last.

---

## Parallel Example: Foundational

```bash
# Once T004 lands, launch all three adapter classes together:
Task: "Implement SqlAlchemyFeedbackFindingReader in backend/app/context/adapters/sqlalchemy_repository.py"
Task: "Implement SqlAlchemyIssueTopFindingReader in backend/app/context/adapters/sqlalchemy_repository.py"
Task: "Implement SqlAlchemyFeedbackVerdictRepository in backend/app/context/adapters/sqlalchemy_repository.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1 — a `false_alarm` verdict measurably
   damps future matching findings via a real, callable API route.
4. **STOP and VALIDATE**: `quickstart.md` §1–2, §4, §6 — this alone is a
   real, demoable "the system learns from correction" mechanism, even with
   no visible disclosure text yet and no `correct`/`resolved` distinction.

### Incremental Delivery

1. Setup + Foundational → formula and plumbing ready.
2. Add User Story 1 → the core learning loop is real and API-callable
   (MVP).
3. Add User Story 2 → the disclosure is visible everywhere REQ-M4-01 names,
   closing the "silent black box" gap (REQ-M4-04/P1) — validate
   independently → demo.
4. Add User Story 3 → `correct`/`resolved` behave correctly, proven by
   test, not new code — validate independently → demo.
5. Polish → the scoring-engine duplication is removed and re-verified
   behavior-preserving, layer boundary re-confirmed, no-LLM-import
   guarantee mechanically confirmed, full quickstart re-run, features
   001–009 re-verified.

### Parallel Team Strategy

With multiple developers:

1. One developer completes Setup + Foundational.
2. A second starts User Story 1 the moment Foundational lands.
3. Once US1's route exists, a third developer can build User Story 2's
   frontend half while the first developer moves to User Story 3 (test-only,
   fast) and then Polish's T026 refactor.

---

## Notes

- `[P]` tasks touch different files, or independent regions/classes of a
  shared file, with no dependency on an incomplete task.
- User Story 3 is intentionally the lightest phase in this feature — its
  correctness is a property of the formula US1 already implements, not new
  code; called out explicitly here rather than presented as a falsely
  symmetric third of the work, matching this repository's own standard
  (feature 009's US2↔US1 coupling note).
- **REQ-M4-P1/P2 have no implementation task of their own, intentionally**
  — both are structural absences (no filter-by-damping query, no
  reader-type-wide control) proven by the shape of what's built, not
  separate features to add and then verify. Flagged here per this
  repository's `/speckit-analyze`-style convention so this file alone
  doesn't read as leaving either uncovered.
- `data-base/07-schema-feedback.md`'s `pattern_signature` correction
  (`research.md` Decision 1) was already applied during `/speckit-plan`,
  before this file existed.
- **FR-004 and FR-009 also have no task of their own, intentionally**
  (`/speckit-analyze` finding C2, 2026-08-16): FR-004 (append-only, never
  edited/deleted) is satisfied by T007's `FeedbackVerdictRepositoryPort`
  implementation never having an update/delete method for
  `feedback_verdicts` in the first place — nothing to test beyond the
  absence of such a method; FR-009 (expose the current weight for the
  scoring engine to consume) is satisfied by feature 004's already-shipped
  `DampingRepositoryPort.get_weight()`, which this feature's `damping_weights`
  upsert (T007) populates for the first time — the read side is
  pre-existing, tested infrastructure this feature doesn't touch.
- Commit after each task or logical group; stop at any checkpoint to
  validate independently before continuing.
