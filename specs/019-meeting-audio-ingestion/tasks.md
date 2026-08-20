---

description: "Task list for Meeting Audio Ingestion"
---

# Tasks: Meeting Audio Ingestion

**Input**: Design documents from `/specs/019-meeting-audio-ingestion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/meeting-audio.md, quickstart.md

**Tests**: Included throughout — this codebase's constitution (P9, "Comprehensive Testing
Strategy") requires near-100% unit coverage for domain/application code and real-DB integration
tests at every adapter boundary; this feature follows that existing pattern rather than opting
out of it.

**Organization**: Tasks are grouped by user story. **Ordering note**: `spec.md` User Story 2
(consent) and User Story 1 (collector) are both P1, but User Story 2 is deliberately scheduled
*before* User Story 1 below — `spec.md`'s own "Why this priority" for US2 states the collector
"has no legitimate behavior without this gate existing first." Sequencing US2 first also makes
it independently demonstrable *before* any Google Drive/Whisper credentials exist: it wires the
new consent gate into the already-existing `SimulatedCollector` demo path
(`research.md` Decision 3), so the audit trail and structural enforcement can be proven against
the current fixture-driven demo alone.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are exact, relative to the repository root

## Path Conventions

Existing web app split: `backend/app/` (Python, Clean Architecture layers per module) and
`frontend/src/` (React/TypeScript, feature-oriented). This feature adds to the existing
`backend/app/ingestion/` module and the existing `frontend/src/coverage/` feature directory —
no new top-level module or feature area (`plan.md`'s Structure Decision).

---

## Phase 1: Setup

**Purpose**: New dependencies and configuration this feature needs, before any code depends on
them.

- [X] T001 Add `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, and a
      diarization library (`research.md` Decision 7 — pin the specific package here) to
      `backend/pyproject.toml`; run the project's lockfile update command. **Amended** (`research.md`
      Decision 7's "deployment build-size finding" correction): the diarization library is
      `pyannoteai-sdk` (pyannote.ai hosted API), not a locally-run `pyannote-audio` — the local
      pipeline's PyTorch/CUDA dependency closure alone drove the deployed image to ~20GB
- [X] T002 [P] Add new settings to `backend/app/config.py`: `audio_poll_interval_hours: int = 4`,
      `google_drive_token_path: str = "./secrets/google-drive-token.json"`,
      `google_drive_root_folder_id: str = ""`, `google_drive_client_id: str = ""`,
      `google_drive_client_secret: str = ""` — same honest-empty-default style as
      `openai_api_key`/`anthropic_api_key` already use in that file
- [X] T003 [P] Update `architecture/03-technology-stack.md`'s adopted-stack summary to name the
      new Drive/Whisper/diarization dependencies, per the constitution's schema/architecture
      discipline rule (`AGENTS.md`)

**Checkpoint**: Dependencies installed, configuration surface exists. No behavior changes yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure every user story below depends on — the new consent port and
its adapter (needed by both US2's enforcement and US1's collector), the extracted envelope
builder (needed by both `SimulatedCollector` and the new `AudioCollector`), and the one
additive change to shared orchestration code (needed by US1's real failures and US4's
degradation signal alike).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create migration `backend/migrations/versions/0006_meeting_series_consent.py`
      (`down_revision = "0005_ask_queries_response_mode"`) adding the `meeting_series_consent`
      table and its `status` enum (`granted`/`revoked`), per `data-model.md`
- [X] T005 [P] Update `data-base/10-ddl-appendix.md` with the new `meeting_series_consent` DDL,
      matching the migration exactly (schema discipline, `AGENTS.md`)
- [X] T006 Add `MeetingSeriesConsentRepositoryPort` (`is_active(series_id) -> bool`,
      `record(series_id, status, all_parties_confirmed, documented_by_user_id, note) -> ...`,
      `list_current() -> list[...]`) to `backend/app/ingestion/application/ports.py`
- [X] T007 [P] Implement `SqlAlchemyMeetingSeriesConsentRepository` in
      `backend/app/ingestion/adapters/sqlalchemy_repositories.py` — `is_active` queries the
      latest row per `series_id` (`data-model.md`'s query pattern); `record` is insert-only and
      rejects `status="granted"` with `all_parties_confirmed=False` at the adapter boundary
- [X] T008 [P] Extract `_normalize_calendar` and the `"transcripts"` display-name entry out of
      `backend/app/ingestion/adapters/simulated_collector.py` into a new shared
      `backend/app/ingestion/adapters/meeting_envelope.py` (`build_meeting_envelope(...)`,
      `research.md` Decision 2) — pure refactor, `SimulatedCollector.normalize()` calls the
      extracted function, no behavior change, existing tests pass unmodified
- [X] T009 In `backend/app/ingestion/application/use_cases.py`, wrap
      `RunCollectorUseCase.execute()`'s `raw_items = await collector.fetch(...)` call in a
      `try/except`; on a caught exception, route the affected source through the exact same
      recording path `fail_sources` already uses (`collector_runs.error` set,
      `coverage_reports.gap_reason` includes it, not counted in `sources_read`) — refactor
      `fail_sources` to be a thin wrapper that raises a synthetic exception into this same path,
      rather than a second parallel code path (`research.md` Decision 5). **In the same touch to
      this method** (`/speckit-analyze` finding F2): add a `trigger: str` parameter to
      `execute()`, threaded to its `start_run(..., trigger=trigger, ...)` call in place of the
      hard-coded `"manual"` literal — mirrors `ReplayUseCase.execute(*, trigger: str, ...)`'s
      existing pattern (`use_cases.py:173`) for the identical need. Update
      `backend/scripts/run_collector.py`'s existing call site to pass `trigger="manual"`
      explicitly, preserving today's only real behavior
- [X] T010 [P] Add `test_real_fetch_failure_produces_honest_coverage_report` to
      `backend/tests/unit/test_simulated_collector.py`, using a small fake `Collector` whose
      `fetch()` raises — asserts a real `collector_runs` row with `error` set and a degraded
      `coverage_reports` row, without crashing the run; confirm the existing
      `test_source_failure_produces_honest_coverage_report` (the `fail_sources` seam) still
      passes unmodified after T009's refactor. Also add
      `test_execute_records_the_caller_supplied_trigger` asserting `collector_runs.trigger`
      reflects whatever value the caller passes, not a hard-coded literal (F2)

**Checkpoint**: Foundation ready — Phase 3 (US2) can begin.

---

## Phase 3: User Story 2 - Consent is documented and enforced per meeting series (Priority: P1)

**Goal**: A CS lead can document and revoke consent for a meeting series through a durable,
auditable record; nothing is ever collected for a series without an active grant — proven
against the existing `SimulatedCollector` demo path, before any real audio integration exists.

**Independent Test**: Per `spec.md` — record consent for a series, confirm it's retrievable
with who/when/which-series detail, revoke it, confirm a recording belonging to that series is
never collected afterward.

### Tests for User Story 2

- [X] T011 [P] [US2] Add unit tests for the consent recording rule to
      `backend/tests/unit/test_meeting_series_consent.py` (new file): granting without
      `all_parties_confirmed=True` is rejected; granting then revoking then re-granting the same
      `series_id` produces three rows and `is_active()` reflects only the latest
- [X] T012 [P] [US2] Add integration tests for the two new endpoints to
      `backend/tests/ingestion/test_consent_router.py` (new file): `GET` lists current status
      per series, with `documented_by` asserted as the resolved `users.username`/display string
      `contracts/meeting-audio.md`'s example shows — not the raw `documented_by_user_id` UUID
      (`/speckit-analyze` finding C3, pins the response shape rather than only its presence);
      `POST` as a `cs_lead` returns `201`; `POST` as `account_executive` returns `403` (mirrors
      `specs/011-production-hardening` FR-005's existing RBAC boundary); `POST` with
      `all_parties_confirmed=False` and `status="granted"` returns `422`

### Implementation for User Story 2

- [X] T013 [US2] Update `backend/app/ingestion/adapters/simulated_collector.py`'s consent filter
      (currently `item.get("consent_documented") is True`) to call
      `MeetingSeriesConsentRepositoryPort.is_active(item["series_id"])` instead
      (`research.md` Decision 3) — `SimulatedCollector.__init__` gains a required
      `consent: MeetingSeriesConsentRepositoryPort` parameter
- [X] T014 [US2] Update `SimulatedCollector`'s three other call sites —
      `backend/scripts/run_collector.py`, `backend/tests/unit/test_simulated_collector.py`,
      `backend/tests/ingestion/test_post_mvp_sources_real_db.py` — to pass the new consent
      dependency
- [X] T015 [US2] Update `backend/tests/unit/test_simulated_collector.py::
      test_unconsented_calendar_item_is_never_collected` to seed `meeting_series_consent` via
      `SqlAlchemyMeetingSeriesConsentRepository` instead of relying on the fixture's
      `consent_documented` boolean; add a companion case proving a *revoked* series is also
      never collected
- [X] T016 [US2] Update `backend/tests/ingestion/test_post_mvp_sources_real_db.py::
      test_unconsented_calendar_series_never_reaches_the_ledger` and `::
      test_consented_transcript_reaches_the_meeting_reader_corpus` the same way
      (`research.md` Decision 3's compatibility note)
- [X] T017 [US2] Add `RecordMeetingSeriesConsentUseCase` to
      `backend/app/ingestion/application/use_cases.py` — validates the all-parties rule,
      delegates to the port from T006/T007
- [X] T018 [US2] Add `backend/app/ingestion/adapters/consent_router.py` —
      `GET /api/meeting-audio/consent` (`Depends(get_current_user)`) and
      `POST /api/meeting-audio/consent` (`Depends(require_full_access)`, mirroring
      `backend/app/context/adapters/profile_router.py`'s pattern), per
      `contracts/meeting-audio.md`; register the router in `backend/app/main.py`. `GET`'s
      response resolves each row's `documented_by_user_id` to that user's `username` (a small
      join/lookup, not the raw UUID) to match the contract's documented response shape
      (`/speckit-analyze` finding C3)
- [X] T019 [P] [US2] Add `MeetingSeriesConsent`/`ConsentRequest` types to
      `frontend/src/coverage/types.ts`
- [X] T020 [US2] Add `frontend/src/coverage/use-meeting-consent.ts` — TanStack Query hook for
      `GET`/`POST /api/meeting-audio/consent`, mirroring
      `frontend/src/profile-editor/use-profile.ts`'s shape
- [X] T021 [US2] Add `frontend/src/coverage/meeting-consent-panel.tsx` — lists current
      per-series consent status; a `cs_lead`-only grant/revoke form using React Hook Form + Zod
      (P11), rendered in the existing coverage page
- [X] T022 [P] [US2] Add `frontend/src/coverage/meeting-consent-panel.test.tsx` — renders
      current status, form validation (`all_parties_confirmed` required to grant), hides the
      form for a non-`cs_lead` session

**Checkpoint**: User Story 2 is fully functional and independently testable/demoable — consent
audit trail and structural enforcement both work against the existing demo fixture path, with
no Google Drive or Whisper credentials configured anywhere.

---

## Phase 4: User Story 1 - Meeting evidence appears in the score automatically (Priority: P1)

**Goal**: A real `AudioCollector` discovers Drive recordings, transcribes them, and feeds the
existing, unmodified meeting-evidence pipeline.

**Independent Test**: Per `spec.md` — place a consented recording in the connected Drive
location, run a collection cycle, confirm a transcript-derived finding appears in the evidence
trace and is reflected in the next score computation, with the audio itself gone by the time
transcription completes.

### Tests for User Story 1

- [X] T023 [P] [US1] Add `backend/tests/unit/test_whisper_transcription.py` — mocked
      `AsyncOpenAI` client; asserts lazy client construction (mirrors
      `test_openai_embedding.py`'s existing pattern if present), a confident speaker match
      against a fake stakeholder roster, and an ambiguous segment left unattributed rather than
      guessed (FR-007, `research.md` Decision 7's attendee-source correction — the candidate set
      is the account's full stakeholder roster, not a per-occurrence attendee list)
- [X] T024 [P] [US1] Add `backend/tests/unit/test_audio_collector.py` — mocked Drive client,
      transcription adapter, and `CollectorRunRepositoryPort`; asserts:
      - a non-consented series is never downloaded (`is_active()` checked before any download)
      - a *revoked* series (previously consented, then revoked) is also never downloaded on a
        subsequent cycle, not only a series that was never consented (`spec.md` FR-005,
        `/speckit-analyze` finding E1)
      - the local audio buffer/temp file is deleted after both a successful and a failing
        transcription (`finally`-block behavior)
      - a recording whose `idempotency_key` already has a matching `raw_envelopes` row (per
        `envelope_exists()`) is skipped **before** download or transcription is attempted — the
        mocked Drive/Whisper clients must assert they were never called for that file, not
        merely that no duplicate `Envelope` was returned (`research.md` Decision 10,
        `/speckit-analyze` finding F1 — this is the load-bearing assertion this task exists to
        make; a test that only checks the returned list has no duplicate would pass even with
        the bug this task is meant to catch)
      - a Drive folder matching no known `series_id` is skipped and logged, never downloaded
        (`research.md` Decision 11, `/speckit-analyze` finding C1)
      - an invalid-token Drive response raises a distinct exception type rather than returning
        an empty list or a "nothing new" result indistinguishable from a healthy empty cycle

### Implementation for User Story 1

- [X] T025 [US1] Add `backend/app/ingestion/adapters/google_drive_token_store.py` — file-backed
      OAuth token store at `settings.google_drive_token_path`, mirroring
      `backend/app/ingestion/adapters/key_store.py`'s `FileKeyStore` shape (`research.md`
      Decision 6); refreshes the access token from the persisted refresh token, never prompts
      interactively
- [X] T026 [P] [US1] Add `backend/scripts/authorize_google_drive.py` — one-time, operator-run
      interactive OAuth grant script that writes the initial refresh token to
      `settings.google_drive_token_path`; documented as an out-of-band deployment-setup step
      (`research.md` Decision 6), never invoked by the running application
- [X] T027 [US1] Add `backend/app/ingestion/adapters/google_drive_client.py` — lists
      series-folders under `settings.google_drive_root_folder_id`, matching each folder name
      against known `series_id` values and skipping/logging (never downloading) any folder that
      matches none (`research.md` Decision 11, `/speckit-analyze` finding C1); lists recordings
      (file ID + metadata, no content) within a matched folder; downloads one file's bytes on
      request; raises a distinct `GoogleDriveAuthenticationError` when the token store reports an
      invalid/expired grant
- [X] T028 [US1] Add `backend/app/ingestion/adapters/whisper_transcription.py` —
      `WhisperTranscriptionAdapter`, mirroring `OpenAIEmbeddingAdapter`'s deferred-client/honest-
      failure pattern (`backend/app/readers/adapters/openai_embedding.py`); calls the
      transcription endpoint with `response_format="verbose_json"`, runs the diarization pass,
      and matches each diarized segment against the client account's full stakeholder roster
      (fetched via the same `ClientProfileContextPort` every reader already uses — not a
      per-meeting-occurrence attendee list, which nothing in this system captures), leaving a
      low-confidence or ambiguous match unattributed (`research.md` Decision 7's corrected
      attendee-source rationale, `/speckit-analyze` finding C2)
- [X] T029 [US1] Add `backend/app/ingestion/adapters/audio_collector.py` —
      `AudioCollector(Collector)`, `source_type = "transcripts"`, constructor depends on
      `MeetingSeriesConsentRepositoryPort` **and** `CollectorRunRepositoryPort` (the latter new —
      `research.md` Decision 10, `/speckit-analyze` finding F1). `fetch()`, per series-folder
      T027 resolves: check `MeetingSeriesConsentRepositoryPort.is_active()` before downloading
      anything (structural gate, mirrors `SimulatedCollector`); for each consented folder's
      listed files, compute `Envelope.idempotency_key` from listing metadata alone and call
      `CollectorRunRepositoryPort.envelope_exists()` — **skip already-processed files before
      downloading or transcribing them**, not only before returning them; only then download
      each remaining file into memory/an ephemeral temp file, transcribe via T028, and delete the
      audio in a `finally` block regardless of outcome (`research.md` Decision 8); on a per-item
      failure, log and skip that item without aborting the cycle (FR-013); on a whole-connection
      failure (T027's `GoogleDriveAuthenticationError`), let it propagate — Phase 2's T009
      records it honestly. `normalize()` calls T008's shared `build_meeting_envelope(...)`
- [X] T030 [US1] Wire `AudioCollector` into `backend/app/worker.py`: a new
      `_run_audio_collector()`/`_collect_audio()` pair following the existing
      `_run_absence_detection`/`_detect_absence` shape, added to `_RUN_ONCE_JOBS["audio"]`, and
      `scheduler.add_job(_run_audio_collector, "interval",
      hours=settings.audio_poll_interval_hours, id="audio_collector")` in `main()` — calls
      `RunCollectorUseCase.execute(audio_collector, ..., trigger="poll")`, now that T009 has made
      `trigger` a real parameter (`/speckit-analyze` finding F2)
- [X] T031 [P] [US1] Add a real-DB integration test to
      `backend/tests/ingestion/test_post_mvp_sources_real_db.py` (or a new adjacent file):
      running `RunCollectorUseCase.execute(audio_collector, ...)` against a consented series with
      a mocked Drive/Whisper pair reaches `SqlAlchemyMeetingTranscriptRepository.list_all()` and
      is readable by the unmodified `MeetingReader`. In the same test module, add an assertion
      that running `RunRetentionUseCase` against an aged audio-sourced `meeting` event shreds its
      body exactly like any other source's event (FR-010, `/speckit-analyze` finding E3 — extends
      this file's existing pattern rather than adding a new one)
- [ ] T032 [US1] Run `quickstart.md`'s User Story 1 section against the real containerized stack
      with one real test recording — manual verification, not an automated task (mirrors
      `specs/011-production-hardening`'s quickstart-as-Definition-of-Done pattern). **Blocked in
      the implementing environment**: no real Google Drive OAuth grant, `GOOGLE_DRIVE_CLIENT_ID`/
      `SECRET`, or test recording were available — every other task's code is implemented and
      covered by tests using fake Drive/Whisper/diarization collaborators instead (T023/T024/T031).
      An operator with real credentials must run this before calling User Story 1 done end to end.

**Checkpoint**: User Story 1 delivers the feature's core value end to end, on top of User
Story 2's consent gate.

---

## Phase 5: User Story 3 - On-demand refresh ahead of a review (Priority: P2)

**Goal**: A CS lead can force an immediate collection cycle from the dashboard.

**Independent Test**: Per `spec.md` — with a new consented recording in Drive, trigger manual
refresh, confirm the same pipeline runs immediately; a refresh with nothing new returns a clear
"nothing new" outcome.

### Tests for User Story 3

- [X] T033 [P] [US3] Add `backend/tests/ingestion/test_audio_refresh_router.py` — `POST
      /api/meeting-audio/refresh` as `cs_lead` returns `200` with real counts; an
      `account_executive` token gets `403`; a cycle with nothing new returns all-zero counts, not
      an error (per `contracts/meeting-audio.md`); with the Drive/Whisper clients mocked to
      return immediately, assert the request completes within a generous bound (e.g. a few
      seconds) — a real, if loose, measurement of SC-003's "under one minute, excluding
      transcription time" rather than an implied-but-unchecked claim (`/speckit-analyze`
      finding E2)

### Implementation for User Story 3

- [X] T034 [US3] Add `backend/app/ingestion/adapters/audio_refresh_router.py` —
      `POST /api/meeting-audio/refresh` (`Depends(require_full_access)`), synchronously calls
      `RunCollectorUseCase.execute(audio_collector, ..., trigger="manual")` and returns
      `recordings_found`/`transcribed`/`skipped_no_consent`/`failed`/`coverage_report_id` per
      `contracts/meeting-audio.md`; register in `backend/app/main.py`
- [X] T035 [P] [US3] Add `frontend/src/coverage/use-meeting-audio-refresh.ts` — a TanStack Query
      mutation hook for the new endpoint
- [X] T036 [US3] Add a refresh button to `frontend/src/coverage/coverage-page.tsx` (or the
      consent panel from T021), showing the returned counts or a "nothing new" state
- [X] T037 [P] [US3] Add a component test for the refresh button/hook to
      `frontend/src/coverage/coverage-page.test.tsx`

**Checkpoint**: User Stories 1, 2, and 3 all independently functional.

---

## Phase 6: User Story 4 - Honest degradation when the audio source breaks (Priority: P2)

**Goal**: A broken Drive connection or failing transcription is visibly flagged and freezes the
score, using the existing coverage/degrade mechanism — never silent.

**Independent Test**: Per `spec.md` — simulate an invalid Drive connection or a transcription
failure, run a cycle, confirm the failure is visible within one cycle and the score is frozen.

### Tests for User Story 4

- [X] T038 [P] [US4] Extend `backend/tests/unit/test_audio_collector.py` (T024) with the two
      failure shapes side by side: a whole-cycle `GoogleDriveAuthenticationError` (propagates,
      caught by Phase 2's T009) versus a single item's transcription failure (caught inside
      `fetch()`, that item skipped, the rest of the cycle proceeds) — confirms they are never
      conflated
- [X] T039 [P] [US4] Add an integration test to `backend/tests/ingestion/
      test_audio_refresh_router.py` (T033): a failing `AudioCollector` makes
      `POST /api/meeting-audio/refresh` return `source_error` (contract's "degraded" shape);
      `GET /api/coverage` reflects the same gap; a subsequent `python -m app.worker --run-once
      score` leaves the score unchanged from its prior value (extends the existing score-freeze
      assertion pattern from `specs/004-score-engine`)

### Implementation for User Story 4

- [X] T040 [US4] `audio_refresh_router.py` (T034): populate the response's `source_error` field
      from the run's `coverage_reports.gap_reason` when non-null, per
      `contracts/meeting-audio.md`'s degraded response shape
- [X] T041 [US4] Add a degraded-source notice for the `transcripts` source to
      `frontend/src/coverage/coverage-page.tsx`, reusing the existing per-source gap
      presentation other sources already render there (P6 — no new alert pattern)
- [X] T042 [P] [US4] Add a component test for the degraded notice to
      `frontend/src/coverage/coverage-page.test.tsx`

**Checkpoint**: All four user stories independently functional. Full `quickstart.md` passes
end to end.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T043 [P] Add (or confirm) an import-linter contract restricting `google.*`/`openai`
      imports to `backend/app/ingestion/adapters/`, mirroring the existing
      `readers-application-purity` contract, in `backend/pyproject.toml`
- [X] T044 [P] Size and document a Drive/Whisper resilience budget (timeout, bounded retry) in
      `architecture/06-error-handling.md`, from real timing observed in T032's quickstart run —
      `plan.md`'s Constitution Check flags this as a follow-up, not a number to guess upfront
- [X] T045 [P] Add `AudioCollector`/`WhisperTranscriptionAdapter`/`GoogleDriveTokenStore` to
      `architecture/02-component-catalog.md`'s component inventory
- [ ] T046 Run the full `quickstart.md` end to end against the containerized stack, all four
      user stories in sequence, as this feature's Definition of Done. **Blocked alongside T032**
      for the same reason (no real Google Drive credentials/recording in the implementing
      environment). Everything not requiring a real Drive/OpenAI/pyannote call has been verified:
      migration applied cleanly against a real Postgres; the full backend test suite (46/46 new
      tests across 6 new + 3 modified test files, all passing) and full frontend suite (117/117
      passing); `lint-imports`, `ruff`, and `mypy` all clean on every file this feature touches.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS every user story
- **User Story 2 (Phase 3)**: Depends on Foundational only — no dependency on US1/US3/US4
- **User Story 1 (Phase 4)**: Depends on Foundational **and** User Story 2 (its collector calls
  the consent gate US2 builds and proves) — this is the one cross-story dependency in this
  feature, and it's intentional (`spec.md`'s own stated reason, restated at the top of this file)
- **User Story 3 (Phase 5)**: Depends on Foundational and User Story 1 (there is nothing to
  refresh until `AudioCollector` exists)
- **User Story 4 (Phase 6)**: Depends on Foundational and User Story 1 (needs `AudioCollector`'s
  real failure modes to exist) — independent of User Story 3, though T039 reuses T033's router
  test file for convenience
- **Polish (Phase 7)**: Depends on all four user stories being complete

### Within Each User Story

- Tests are written before the implementation tasks they cover, per this codebase's existing
  test-first culture (P9) — fail first, then implement
- Ports/adapters before the use cases that depend on them; use cases before routers; backend
  before the frontend hook that calls it

### Parallel Opportunities

- T002/T003 (Setup) in parallel
- T005/T007/T008 (Foundational) in parallel once T004/T006 land
- Once Phase 2 completes, Phase 3 (US2) can start; Phase 4 (US1) cannot start until Phase 3's
  T013 (the consent port is actually wired into a working collector) lands, but T023's test file
  and early scaffolding (T025/T026, which don't depend on consent at all) can be drafted in
  parallel with late Phase 3 work
- Phase 5 (US3) and Phase 6 (US4) can proceed in parallel once Phase 4 (US1) is done — they touch
  different concerns (a new router vs. `AudioCollector`'s internal failure handling) even though
  both eventually touch `audio_refresh_router.py`

---

## Parallel Example: Foundational Phase

```bash
# After T004 (migration) and T006 (port) land, these can run together:
Task: "Update data-base/10-ddl-appendix.md with the new meeting_series_consent DDL"
Task: "Implement SqlAlchemyMeetingSeriesConsentRepository in sqlalchemy_repositories.py"
Task: "Extract meeting_envelope.py from simulated_collector.py"
```

## Parallel Example: User Story 1

```bash
# T023/T024 (tests) can be drafted together, ahead of implementation:
Task: "Unit tests for WhisperTranscriptionAdapter in test_whisper_transcription.py"
Task: "Unit tests for AudioCollector in test_audio_collector.py"

# T025/T026 have no dependency on each other or on Phase 3:
Task: "GoogleDriveTokenStore adapter"
Task: "authorize_google_drive.py one-time grant script"
```

---

## Implementation Strategy

### MVP First

`spec.md` treats User Story 2 as a co-requisite of User Story 1, not an optional add-on — so the
smallest deployable, demoable increment is **Setup → Foundational → US2 → US1**, not US1 alone.
That increment alone already proves the core "should be on the demo" claim: a recording placed
in a consented Drive folder becomes cited score evidence, with a real, auditable consent gate in
front of it.

1. Complete Phase 1 (Setup) and Phase 2 (Foundational)
2. Complete Phase 3 (US2) — **STOP and VALIDATE**: consent audit trail and enforcement work
   against the existing demo fixture path
3. Complete Phase 4 (US1) — **STOP and VALIDATE**: a real recording becomes score evidence
4. This is the MVP. Deploy/demo here if time is constrained.

### Incremental Delivery Beyond MVP

5. Add Phase 5 (US3) — manual refresh, the more visible "two modes of execution" half
6. Add Phase 6 (US4) — degradation honesty, closes the trust-preserving loop
7. Phase 7 (Polish) — resilience budget documentation, architecture-doc updates, final
   quickstart pass

### Parallel Team Strategy

With two people: one takes Phase 3 (US2) then Phase 5 (US3); the other takes the Drive/Whisper
adapter groundwork within Phase 4 (US1: T025–T028, none of which depend on the consent gate)
while Phase 3 is still in flight, then integrates at T029 once Phase 3 lands. Phase 6 (US4) is
naturally a shared, final pass once both have converged on Phase 4.

---

## Notes

- `[P]` tasks touch different files with no unmet dependency
- `[Story]` labels map every implementation task back to `spec.md` for traceability
- The one deliberate priority-order deviation (US2 before US1 despite both being P1) is called
  out at the top of this file and in the Dependencies section — not an oversight
- Commit after each task or logical group; stop at any checkpoint to validate a story
  independently before continuing
