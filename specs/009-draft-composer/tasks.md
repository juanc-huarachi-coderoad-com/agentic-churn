# Tasks: Draft Composer

**Input**: Design documents from `specs/009-draft-composer/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/drafts.md`, `quickstart.md`

**Tests**: Test tasks below cover exactly `spec.md`'s acceptance scenarios —
the five pure pre-display checks unit-tested directly (no DB, no LLM,
matching `test_fact_check.py`'s own precedent), `GenerateDraftUseCase` with
`LLMPort` faked, a real-DB/real-route integration test reproducing the
worked example plus a scripted red-team case per check, and a static
transport-import scan — not a broader TDD suite beyond what those already
require.

**Organization**: Tasks are grouped by user story — US1 generation content
(P1), US2 pre-display checks block display (P1), US3 tone variants/copy/log/
no-send + frontend (P2) — per `plan.md`'s Project Structure. Both P1 stories
extend the *same* `GenerateDraftUseCase`/`draft_router.py` (there is no
architecturally separate module to split them across, unlike features 005/
007's independent readers) — US2 is the one deliberate cross-story
dependency in this feature (extends US1's use case sequentially), called out
explicitly below, matching feature 008's own precedent for documenting real
coupling rather than presenting a falsely-clean dependency graph. US3's
`/copy`/`/log-as-sent` routes depend only on Foundational, but its
tone-variant scenario and its frontend panel need US1's `POST /api/drafts`
to exist.

**Revision note (2026-08-16)**: This task list was regenerated after
`/speckit-analyze` found nine findings (3 HIGH, 4 MEDIUM, 2 LOW, none
CRITICAL) against the original 32-task version. All are addressed here: the
pre-display check pipeline grows from three functions to five (T017/T019
are new — `verify_no_invented_cause`, `verify_no_concession`); T008 is new
(a stakeholder-existence check, closing a real 404 gap); T033 is new (a
mechanical scan replacing what would otherwise be a manual "code-level
review" for SC-004); and a Notes-section line now explicitly states why
FR-017 has no task. Task IDs below do not match any earlier draft of this
file — this is the authoritative version.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, or an independent region of a
  shared file, with no dependency on an incomplete task)
- **[Story]**: US1/US2/US3
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 Confirm no new dependency, environment variable, or migration is
      needed before starting (`research.md` Decisions 1, 11): verify
      `GENERATION_MODEL_ID` is already present in `.env`/
      `backend/app/config.py` (set by feature 008), and verify
      `draft_messages`/the `tone_variant` enum already exist via
      `docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c
      "\d draft_messages"` against the running stack — both must already be
      true; if either is missing, stop and re-run feature 001's migration
      before continuing, don't add a new one

**Checkpoint**: Environment confirmed ready — no groundwork tasks needed,
unlike every prior feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The read/write plumbing every story needs — issue evidence
lookup, playbook finding-type resolution, draft persistence, stakeholder
existence, and the profile's communication norms. No use-case assembly yet.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T002 [P] Define domain value objects in
      `backend/app/experience/domain/entities.py` (extends the existing
      file) — `IssueEvidenceRecord`, `AgreedAction`, `VerifiedDateSet`,
      `DateCheckResult`, `CauseCheckResult`, `LeakCheckResult`,
      `ConcessionCheckResult`, `DraftCheckResult`, `GeneratedDraft`
      (`data-model.md` — five-check set, revised from three per
      `/speckit-analyze` findings G1/U1). Does **not** redefine
      `VerifiedFactSet`/`FactCheckResult` — those stay imported from
      `app.narrator.domain.entities` (`research.md` Decision 2)
- [X] T003 Define `IssueReadPort`, `PlaybookReadPort`,
      `DraftMessageRepositoryPort` in
      `backend/app/experience/application/ports.py` (extends the existing
      file; depends on T002 for return types); add
      `communication_norms: str | None = None` to the existing
      `ClientProfileRecord` dataclass (`research.md` Decision 5,
      `data-model.md`)
- [X] T004 [P] Implement `SqlAlchemyIssueReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (depends on
      T003) — `get_issue_evidence(issue_id)`: `issues` ⋈
      `finding_issue_map` ⋈ `findings WHERE status = 'validated'`
      (matches `SqlAlchemyFindingReader.get_finding`'s existing
      validated-only filter, `research.md` Decision 3), aggregating
      distinct `finding_types` and `cited_event_ids` across the issue's own
      findings; `None` if the issue doesn't exist or has no validated
      findings
- [X] T005 [P] Implement `SqlAlchemyPlaybookReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (depends on
      T003) — `finding_type_for_playbook(playbook_id)`: `SELECT
      applies_to_finding_type FROM playbook_actions WHERE id = :id`
      (`research.md` Decision 4)
- [X] T006 [P] Implement `SqlAlchemyDraftMessageRepository` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (depends on
      T003) — `persist(draft, *, issue_id, stakeholder_id,
      requested_by_user_id) -> UUID` (one `INSERT` into `draft_messages`,
      `checks_passed` always `true` — a failing result never reaches this
      method, `research.md` Decision 7); `get(draft_id) ->
      DraftMessageRecord | None`; `stamp_copied(draft_id)` (sets
      `copied_at = now()`); `stamp_logged_manually(draft_id)` (sets
      `logged_manually_at = now()`)
- [X] T007 [P] Extend `SqlAlchemyClientProfileRepository.get_current()` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (depends on
      T003) — read `communication_norms` from `client_profile_versions`
      into `ClientProfileRecord`
- [X] T008 [P] Add `get(stakeholder_id: UUID) -> StakeholderRecord | None`
      to `StakeholderReadPort` (feature 008,
      `backend/app/experience/application/ports.py`, same file as T003,
      independent region; depends on T003) and implement it on the
      existing `SqlAlchemyStakeholderReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` — `SELECT
      ... FROM stakeholders WHERE id = :id`, `None` if not found
      (`research.md` Decision 13, `/speckit-analyze` finding U3: the
      original plan had no way to validate `stakeholder_id` before
      generation)

**Checkpoint**: Foundation ready — all read/write plumbing for issue
evidence, playbook lookup, draft persistence, stakeholder existence, and
communication norms exists. US1, US2, and US3 can now begin.

---

## Phase 3: User Story 1 - A draft acknowledges the specific failure first, with exactly one ask (Priority: P1)

**Goal**: Requesting a draft for an issue produces a message that opens with
a specific, evidence-backed fact, contains exactly one ask, matches the
client's communication rhythm, and — for a call-not-email issue — states
that explicitly with talking points instead.

**Independent Test**: `quickstart.md` §1 (generate a draft for the worked
example, confirm content shape and `checks_passed: true`) — **partial** at
this checkpoint: the fact-check (`verify_facts`) and the stakeholder-
existence check (T008) are real, but `verify_dates`/
`verify_no_invented_cause`/`verify_no_leak`/`verify_no_concession` (US2)
aren't wired in yet, so this checkpoint alone is not yet the full
REQ-M10-07 gate.

### Implementation for User Story 1

- [X] T009 [US1] Implement `verify_facts(draft_text, context) ->
      FactCheckResult` in `backend/app/experience/domain/services.py`
      (extends the existing file; depends on T002) — a thin wrapper: builds
      a `VerifiedFactSet` from the issue's cited evidence + thread history +
      client profile, then calls `app.narrator.domain.services.fact_check`
      verbatim (`research.md` Decision 2, 6) — no duplicated extraction
      logic
- [X] T010 [P] [US1] Write the versioned structured-output prompt template
      in `backend/app/experience/application/prompts/draft_composer_v1.py`
      (new file/directory) — schema `{draft_text: str, tone_variant:
      Literal["direct","formal","brief"]}`, instructed to: acknowledge the
      specific evidence-backed failure first (REQ-M10-02), exactly one ask
      (REQ-M10-03, prompt-enforced only — `/speckit-analyze` finding U2),
      match the supplied communication norms (REQ-M10-04), and — when the
      supplied context signals a call is the appropriate medium
      (REQ-M10-06) — state that explicitly and produce talking points
      instead of message text, never blame language (REQ-M10-P2,
      prompt-enforced only — `research.md` Decision 6) and never a
      discount/concession (REQ-M10-P4, also mechanically checked by T019)
- [X] T011 [US1] Implement `GenerateDraftUseCase` in
      `backend/app/experience/application/use_cases.py` (extends the
      existing file, alongside `GetDashboardUseCase`/
      `GetEvidenceTraceUseCase`/`GetCoverageUseCase`; depends on T003, T004,
      T005, T007, T008, T009, T010) — `execute(issue_id, stakeholder_id,
      tone_variant, requested_by_user_id) -> GeneratedDraft`: resolve the
      stakeholder first (T008's new port method; raise `StakeholderNotFoundError`
      if `None` → caller returns `404`); fetch the issue's evidence (T004;
      raise `IssueNotFoundError` if `None` → caller returns `404`), the
      profile's `communication_norms` (T007), the stakeholder's thread
      history (`LedgerQueryPort.timeline_for_stakeholder`, feature 008,
      reused unchanged), and the latest run's actions filtered to this
      issue's finding types (`NarratorReadPort.get_latest()` + T005's
      playbook lookup, `research.md` Decision 4); call
      `LLMPort.generate_structured` with T010's prompt; run `verify_facts`
      (T009) against the result — at this checkpoint, a failing fact-check
      raises `DraftCheckFailedError` (caller returns `422`); a passing
      draft is **not yet persisted** here (T006's `persist` call lands in
      T020, once US2's remaining checks are wired in — persisting before
      the full REQ-M10-07 gate exists would violate FR-008)
- [X] T012 [US1] Implement
      `backend/app/experience/adapters/draft_router.py` — `POST
      /api/drafts` (depends on T011) — the composition root: constructs
      `AnthropicLLMAdapter(settings.anthropic_api_key,
      settings.generation_model_id)`, matching `ask_router.py`'s existing
      pattern; reads `requested_by_user_id` from the bearer token, never
      the request body; catches `IssueNotFoundError`/
      `StakeholderNotFoundError` → `404` (`contracts/drafts.md`,
      `/speckit-analyze` finding U3)
- [X] T013 [US1] Register `draft_router` in `backend/app/main.py` (depends
      on T012)
- [X] T014 [P] [US1] Write `backend/tests/experience/test_draft_checks.py`
      (depends on T009) — pure, no DB, no LLM: `verify_facts` known-good
      draft text (every number/name traces to the supplied context) passes;
      text containing an unverifiable name/number fails
- [X] T015 [P] [US1] Write
      `backend/tests/experience/test_generate_draft_use_case.py` (depends
      on T011) — `LLMPort` faked: a fact-check-passing candidate produces a
      `GeneratedDraft` whose text opens with a concrete evidence fact and
      contains exactly one ask (Acceptance Scenarios 1–3); a stakeholder
      with a short/terse `communication_norms` entry receives shorter,
      more direct output than one without (Acceptance Scenario 4); a
      call-appropriate issue produces talking-points text stating the
      medium explicitly, never a written draft substituted anyway
      (Acceptance Scenario 5); a nonexistent `issue_id` raises
      `IssueNotFoundError` (Edge Cases); a nonexistent `stakeholder_id`
      raises `StakeholderNotFoundError` (Edge Cases, `/speckit-analyze`
      finding U3)

**Checkpoint**: User Story 1's generation core is functional — content
shape, fact-check, and stakeholder/issue existence validation are real. The
remaining four checks and persistence complete in User Story 2, next.

---

## Phase 4: User Story 2 - Every draft is mechanically checked before a human ever sees it (Priority: P1)

**Goal**: `verify_dates`, `verify_no_invented_cause`, `verify_no_leak`, and
`verify_no_concession` complete REQ-M10-07's five-check gate; a draft
failing any of the five is blocked from persistence and display, returning
the same generic `422` failure message already defined for a generation
error — never a partial draft, never a message naming which check failed.

**Independent Test**: `quickstart.md` §4 (trigger each of the five checks
directly against known-good/known-bad text, confirm all five behave as
expected) — extends User Story 1's `GenerateDraftUseCase` sequentially
(same file); this is the one deliberate cross-story dependency in this
feature.

**Note**: T016–T021 all touch files User Story 1 already created
(`services.py`, `use_cases.py`, `draft_router.py`) — extending them, not
creating new ones — so this story cannot start until User Story 1's T009/
T011/T012 land, even though the four new check functions are themselves
pure with no dependency on US1's *content* logic, only its *file*.

### Implementation for User Story 2

- [X] T016 [US2] Implement `verify_dates(draft_text, dates: VerifiedDateSet)
      -> DateCheckResult` in `backend/app/experience/domain/services.py`
      (same file as T009, sequential; depends on T002) — pure: extracts
      date-like tokens (weekday/month names, explicit dates — deliberately
      the same tokens `fact_check`'s own `_COMMON_WORDS` excludes from its
      name-check, `research.md` Decision 6) and confirms each matches a
      `due_date` in the supplied `VerifiedDateSet` (built from the issue's
      matched `AgreedAction`s + thread history); an unmatched date-like
      token fails the check
- [X] T017 [US2] Implement `verify_no_invented_cause(draft_text, facts:
      VerifiedFactSet) -> CauseCheckResult` in
      `backend/app/experience/domain/services.py` (same file, sequential;
      depends on T002) — pure: extracts every sentence containing a causal
      connective (`because`, `due to`, `since`, `as a result of`, `given
      that`) and, for the clause following the connective, reuses
      `app.narrator.domain.services.extract_numbers_and_names` to confirm
      every number/name in that clause exists in `facts` — the same
      `VerifiedFactSet` `verify_facts` (T009) already builds
      (`research.md` Decision 6, `/speckit-analyze` finding U1: this check
      didn't exist in the original plan, leaving REQ-M10-P3's "causes"
      half entirely unaddressed)
- [X] T018 [US2] Implement `verify_no_leak(draft_text, profile_client_name)
      -> LeakCheckResult` in
      `backend/app/experience/domain/services.py` (same file, sequential;
      depends on T002) — pure: a closed, case-insensitive denylist (`score`,
      `risk`, `monitoring`, `quarantine`, `churn`, `damping`, `band` —
      matching `requirements/10-draft-composer.md`'s own acceptance
      criterion wording verbatim, REQ-M10-P5) plus a check that no
      stakeholder/client name outside the current profile's own
      `client_name`/stakeholders appears (REQ-M10-P6)
- [X] T019 [US2] Implement `verify_no_concession(draft_text) ->
      ConcessionCheckResult` in
      `backend/app/experience/domain/services.py` (same file, sequential;
      depends on T002) — pure: a closed, case-insensitive denylist of
      commercial-concession terms (`discount`, `% off`, `waive`, `credit
      your account`, `complimentary`, `free month`, `refund` — REQ-M10-P4)
      (`research.md` Decision 6, `/speckit-analyze` finding G1: SC-003's
      discount guarantee had no mechanical check in the original plan)
- [X] T020 [US2] Extend `GenerateDraftUseCase` in
      `backend/app/experience/application/use_cases.py` (same file as
      T011, sequential; depends on T006, T016, T017, T018, T019) — compose
      `verify_facts` + `verify_dates` + `verify_no_invented_cause` +
      `verify_no_leak` + `verify_no_concession` into one `DraftCheckResult`;
      only when **all five** pass does the use case call
      `DraftMessageRepositoryPort.persist` (T006) and return the persisted
      `GeneratedDraft`; any failure raises `DraftCheckFailedError` (no
      detail about which check failed) instead of persisting anything
- [X] T021 [US2] Extend `draft_router.py` (same file as T012, sequential;
      depends on T012, T020) — catch `DraftCheckFailedError`, return `422`
      with `ErrorResponse{detail: "Couldn't generate a draft — try again"}`
      — the exact string `architecture/06-error-handling.md` already
      defines for this component's generation errors, no distinction
      between any of the failure kinds (`research.md` Decision 7,
      Clarifications 2026-08-16)
- [X] T022 [P] [US2] Extend
      `backend/tests/experience/test_draft_checks.py` (depends on T016,
      T017, T018, T019) — `verify_dates`: a due-date-matching mention
      passes, an invented date fails; `verify_no_invented_cause`: a causal
      clause naming only evidenced entities passes, one naming an
      unverified entity fails; `verify_no_leak`: clean text passes, text
      containing `"score"`/`"risk"`/`"monitoring"` or another client's name
      fails; `verify_no_concession`: clean text passes, text containing
      `"discount"`/`"% off"`/`"waive"` fails
- [X] T023 [P] [US2] Extend `test_generate_draft_use_case.py` (depends on
      T020) — a candidate containing an invented date raises
      `DraftCheckFailedError` without persisting (Acceptance Scenario 2); a
      candidate with an invented cause raises without persisting
      (Acceptance Scenario 2, `/speckit-analyze` U1); a candidate leaking
      internal content raises without persisting (Acceptance Scenario 3); a
      candidate offering a discount raises without persisting (Acceptance
      Scenario 3, `/speckit-analyze` G1); a passing candidate is persisted
      exactly once (Acceptance Scenario 1)
- [X] T024 [US2] Write
      `backend/tests/experience/test_draft_routes_real_db.py` (depends on
      T021) — real-DB integration, scripted red-team: `POST /api/drafts`
      against the worked-example fixture (issue A / Ana) returns `200`,
      `checks_passed: true`, text matching `examples/
      01-end-to-end-walkthrough.md` §13's `draft-1` in substance; five
      separate requests, each engineered (via a fake `LLMPort` response
      injected for that one test) to fail exactly one of the five checks,
      each returning `422` with the exact generic `detail` string and
      creating **no** `draft_messages` row (`quickstart.md` §4)

**Checkpoint**: User Stories 1 and 2 together are the full, five-check
REQ-M10-07 gate — fully functional and independently testable.
`quickstart.md` §1 and §4 pass.

---

## Phase 5: User Story 3 - Tone variants, then copy or log — never send (Priority: P2)

**Goal**: A checks-passed draft can be re-requested in a different tone (a
new generation call, not an edit), copied, or logged as manually sent — and
no send capability exists anywhere, structurally. The Ask agent's existing
`draft_handoff` response connects to a real screen for the first time.

**Independent Test**: `quickstart.md` §2 (tone switch), §3 (copy/log + `/send`
404 probe), §4b (stakeholder 404), §5 (Ask-handoff wiring).

### Implementation for User Story 3

- [X] T025 [US3] Extend `draft_router.py` (same file as T012/T021,
      sequential; depends on T006, T012) — `POST
      /api/drafts/{id}/copy`: `204`, calls
      `DraftMessageRepositoryPort.stamp_copied` (`404` if the ID doesn't
      resolve)
- [X] T026 [US3] Extend `draft_router.py` (same file, sequential; depends
      on T006, T012) — `POST /api/drafts/{id}/log-as-sent`: `204`, calls
      `DraftMessageRepositoryPort.stamp_logged_manually` (`404` if the ID
      doesn't resolve). No `/send` route is added anywhere in this file or
      any other (REQ-M10-P1) — confirmed mechanically by T033, not just by
      omission here
- [X] T027 [P] [US3] Extend `test_draft_routes_real_db.py` (depends on
      T025, T026) — `/copy` stamps `copied_at` and only `copied_at`;
      `/log-as-sent` stamps `logged_manually_at` and only that (order-
      independent — logging without a prior copy is allowed, Edge Cases); a
      second `POST /api/drafts` with a different `tone_variant` for the
      same issue/stakeholder produces a distinct `draft_messages` row, not
      an update, and every fact in it still traces to the same evidence
      (`research.md` Decision 9, SC-006 as softened by `/speckit-analyze`
      finding I1); `POST /api/drafts/{id}/send` returns `404` (no route
      exists to match it)
- [X] T028 [P] [US3] Write `frontend/src/draft-composer/types.ts` — `
      ToneVariant`, `DraftRequest`, `DraftResponse` (`data-model.md`)
- [X] T029 [US3] Write `frontend/src/draft-composer/api.ts` (depends on
      T028) — typed `POST /api/drafts` + `/copy` + `/log-as-sent` client,
      TanStack Query, matching `frontend/src/ask/api.ts`'s existing pattern
- [X] T030 [US3] Write `frontend/src/draft-composer/draft-composer-panel.tsx`
      (depends on T029) — opens beside the evidence trace panel (feature
      006); tone-variant tabs (`direct`/`formal`/`brief`, each triggering a
      fresh `POST /api/drafts` call — `research.md` Decision 9); "Copy
      draft" and "Log as sent (manual)" buttons only — **no edit control**
      of any kind (FR-009a, Clarifications 2026-08-16); a `422` response
      renders the exact generic failure text, never a partial draft; a
      `404` response (unresolvable issue/stakeholder) renders a clear
      "couldn't find that" message
- [X] T031 [P] [US3] Write
      `frontend/src/draft-composer/draft-composer-panel.test.tsx` (depends
      on T030) — asserts: switching tone tabs issues a new request; no
      editable text field exists anywhere in the rendered output; a `422`
      response renders the generic failure message, not a partial draft
- [X] T032 [US3] Extend `frontend/src/ask/components/answer-renderer.tsx`'s
      `DraftHandoff` component (depends on T030) — replace the static
      placeholder text with a real link/button passing
      `component_props.issue_id`/`stakeholder_id` through to
      `<DraftComposerPanel>` (`research.md` Decision 10); keep the existing
      "couldn't identify who to write to" fallback copy for a `null`
      `stakeholder_id`

**Checkpoint**: All three user stories complete and independently testable
— `quickstart.md` §1–5 pass. This feature is functionally complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Mechanically confirm the structural no-send guarantee (SC-004),
confirm the layer boundary holds with the new cross-module `domain`→
`domain` import, confirm golden-replay is genuinely untouched, and document
the feature.

- [X] T033 [P] Write
      `backend/tests/experience/test_no_external_transport.py` — statically
      scans the source of every file this feature added or extended
      (`draft_router.py`; the `use_cases.py`/`services.py`/
      `sqlalchemy_repository.py` additions; `application/prompts/
      draft_composer_v1.py`) for an import of `smtplib`, `httpx`,
      `requests`, or any SMTP/CRM/chat-SDK name, and fails if any is found
      (`research.md` Decision 14, `/speckit-analyze` finding G2 — SC-004's
      "code-level architecture review" as a real, mechanically-run task
      instead of a manual inspection step) (depends on T012, T020, T021,
      T025, T026 — the files it scans must exist)
- [X] T034 [P] Run `lint-imports --config ../.importlinter`, confirm the
      `global-dependency-rule` contract passes clean with
      `app.experience.domain.services` importing `app.narrator.domain.
      services`/`entities` (a `domain`→`domain` cross-module import,
      `research.md` Decision 2 — confirm this direction is genuinely
      unrestricted by the existing contract, not just assumed) (depends on
      all of Phases 3–5)
- [X] T035 [P] Add a "Draft Composer (Phase 9)" section to the root
      `README.md`, matching the "Narrator and Ask Agent (Phase 8)"
      section's style — how to `curl POST /api/drafts`/`/copy`/
      `/log-as-sent`, the explicit "no `/send` route, anywhere" note, and a
      link to `specs/009-draft-composer/quickstart.md`
- [X] T036 Run all of `specs/009-draft-composer/quickstart.md` end to end
      against the real, fully containerized stack (`docker compose up
      --build -d`), confirm every acceptance scenario in `spec.md` passes,
      confirm `tests/golden_replay/` still passes unchanged (§6 — `draft_
      messages` is not part of its snapshot, `research.md` Decision 12),
      and re-run features 001–008's own quickstarts to confirm nothing
      regressed (depends on every task above)

**Checkpoint**: `quickstart.md` §1–6 all pass — this feature is complete.
FR-017 (closing the response clock when a human's sent reply is later
collected) intentionally has no task anywhere above — it's M1/M2's
already-existing, already-tested machinery from feature 003, not new work
this feature builds (`spec.md`'s own "Explicitly out of scope" section;
noted here per `/speckit-analyze` finding G3 so this file alone makes that
visible, not just `spec.md`/`research.md`).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all three user
  stories.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on Foundational **and** User Story 1
  (extends the same `services.py`/`use_cases.py`/`draft_router.py` files
  sequentially) — the one deliberate cross-story dependency in this
  feature.
- **User Story 3 (Phase 5)**: Its `/copy`/`/log-as-sent` tasks (T025–T026)
  depend on Foundational and US1's `draft_router.py` existing (T012) but
  not on US2. Its tone-variant test and its entire frontend (T027–T032)
  depend on US1's `POST /api/drafts` being callable (T012) — not on US2's
  check-completeness, though in practice US2 will already be done by the
  time frontend work starts in a sequential build.
- **Polish (Phase 6)**: T033 depends on every route file existing (T012,
  T020, T021, T025, T026). T034/T035 depend on Phases 3–5 being complete;
  T036 must run last.

### Within Each User Story

- Domain (pure value objects/functions) before application (the use case)
  before adapters (routes) are wired in, as in every prior feature. Several
  tasks share one file across stories
  (`backend/app/experience/domain/services.py` across T009/T016/T017/T018/
  T019; `backend/app/experience/application/use_cases.py` across T011/T020;
  `backend/app/experience/adapters/draft_router.py` across T012/T021/T025/
  T026; `backend/app/experience/adapters/sqlalchemy_repository.py` across
  T004–T008) and are marked `[P]` only where they touch independent
  regions/classes of that shared file with no dependency on an incomplete
  sibling task.

### Parallel Opportunities

- T002 can start immediately after T001.
- T004, T005, T006, T007, T008 all depend on T003 and run in parallel with
  each other (independent classes/methods in the same file).
- T010 (the prompt template) has no code dependency on T003–T009 and can
  start in parallel with them, right after T002.
- T014 and T015 run in parallel once their respective dependencies (T009,
  T011) land.
- T016, T017, T018, T019 are four independent pure functions in the same
  file and can be written in parallel once T002 lands (each depends only on
  T002, not on each other) — though as sequential edits to one file, only
  one PR/commit at a time in practice.
- T022 and T023 run in parallel once T016–T019 and T020 land, respectively.
- T027, T028 run in parallel with each other; T031 waits on T030.
- T033, T034, and T035 in Polish are independent of each other; T036 must
  run last.

---

## Parallel Example: Foundational

```bash
# Once T003 lands, launch all five adapter tasks together:
Task: "Implement SqlAlchemyIssueReader in backend/app/experience/adapters/sqlalchemy_repository.py"
Task: "Implement SqlAlchemyPlaybookReader in backend/app/experience/adapters/sqlalchemy_repository.py"
Task: "Implement SqlAlchemyDraftMessageRepository in backend/app/experience/adapters/sqlalchemy_repository.py"
Task: "Extend SqlAlchemyClientProfileRepository for communication_norms in backend/app/experience/adapters/sqlalchemy_repository.py"
Task: "Add StakeholderReadPort.get() to SqlAlchemyStakeholderReader in backend/app/experience/adapters/sqlalchemy_repository.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 together — both P1)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1 (generation content + existence checks).
4. Complete Phase 4: User Story 2 (the full five-check REQ-M10-07 gate) —
   **required** before this feature is safe to demo; User Story 1 alone
   persists nothing (T011 defers persistence to T020), so there is no
   partially-safe intermediate state to accidentally ship.
5. **STOP and VALIDATE**: `quickstart.md` §1 and §4 — a real, checked draft
   generates and persists; each of the five red-team check-failures blocks
   with the exact generic message.

### Incremental Delivery

1. Setup + Foundational → plumbing ready.
2. Add User Story 1 → generation logic and existence checks exist but
   nothing persists yet (deliberately — the gate isn't complete).
3. Add User Story 2 → the true MVP: a fully gated, persisted draft exists
   for the first time.
4. Add User Story 3 → the CS lead can actually use it end to end (tone
   switch, copy, log) and reach it from the Ask bar — validate
   independently → demo.
5. Polish → the structural no-send guarantee is mechanically confirmed
   (not just manually reviewed), layer boundary re-confirmed, golden-replay
   confirmed untouched, full quickstart re-run, features 001–008
   re-verified.

### Parallel Team Strategy

With multiple developers:

1. One developer completes Setup + Foundational.
2. A second starts User Story 1 the moment Foundational lands.
3. Because User Story 2 sequentially extends User Story 1's own files,
   the same developer (or one who coordinates closely) should carry both
   P1 stories through — this is not a story pair that parallelizes well
   across two people, unlike Foundational's own adapter tasks.
4. Once US1+US2 land, a separate developer can build all of User Story 3
   (routes + frontend) largely independently.

---

## Notes

- `[P]` tasks touch different files, or independent regions/classes of a
  shared file, with no dependency on an incomplete task.
- This feature has a tighter cross-story coupling than features 005–008:
  US2 is not an independent leaf, it sequentially extends US1's own
  `services.py`/`use_cases.py`/`draft_router.py` — called out explicitly
  rather than presented as a falsely-clean three-way split, matching this
  repository's own standard (feature 008's T035↔T024 note).
- **FR-017 has no task in this file, intentionally** — it's satisfied by
  M1/M2's already-existing collector/response-pair machinery (feature 003),
  not new work this feature builds. Flagged explicitly here per
  `/speckit-analyze` finding G3, so this file alone doesn't read as an
  uncovered MUST requirement.
- Commit after each task or logical group; stop at any checkpoint to
  validate independently before continuing.
