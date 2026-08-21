---

description: "Task list for Meeting Audio Ingestion — local storage migration"
---

# Tasks: Meeting Audio Ingestion (local storage migration)

**Input**: Design documents from `/specs/019-meeting-audio-ingestion/`

**Prerequisites**: plan.md, spec.md, research.md (Decision 12), contracts/meeting-audio.md, quickstart.md

**2026-08-20 revision — this file replaces the prior, fully-completed tasks.md.** The original
task list (all `[X]`, implementing the feature against Google Drive) is superseded, not
discarded: `git log` on this branch has that full implementation history. Everything it built
that does **not** depend on the storage source is already done and unaffected by this revision:

- The `meeting_series_consent` table, migration, port, and repository (US2, `research.md`
  Decision 3/4)
- The shared envelope builder (`meeting_envelope.py`, `research.md` Decision 2)
- `RunCollectorUseCase.execute()`'s `try/except` + caller-supplied `trigger` (`research.md`
  Decision 5)
- Scheduling (`worker.py`'s `APScheduler` job) and the manual-refresh endpoint's RBAC boundary
  (`research.md` Decision 9)
- Whisper transcription + pyannote.ai diarization (`whisper_transcription.py`,
  `pyannote_diarization.py`, `research.md` Decision 7) — operates on already-read audio bytes,
  indifferent to where they came from
- `GET`/`POST /api/meeting-audio/consent` (`contracts/meeting-audio.md`)

What actually changed in the plan (`research.md` Decision 12) is narrow: **where recordings come
from and how failures there are detected.** This file's tasks are exactly that delta — replacing
the Google Drive adapter with a local-storage one, and updating every test/config/doc that
referenced Drive specifically. No new feature capability is being built; every task below is a
migration of existing, working code and tests to the new source.

**Tests**: Included — this codebase's constitution (P9) requires near-100% unit coverage for
adapter code and real-DB integration tests at every adapter boundary; migrating existing tests
to the new fake follows that same standing requirement rather than opting out of it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependency)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are exact, relative to the repository root

## Path Conventions

Existing web app split: `backend/app/` (Python, Clean Architecture layers per module) and
`backend/tests/`. This migration touches only files already inside the existing
`backend/app/ingestion/` module and its tests — no new module, no frontend change (the consent
control and refresh button, `frontend/src/coverage/`, are storage-source-agnostic and untouched).

---

## Phase 1: Setup

**Purpose**: Remove the Google Drive dependency and secret surface; add the local storage
configuration; stage the demo fixture. Nothing downstream compiles cleanly until this lands.

- [X] T001 In `backend/pyproject.toml`: remove `google-api-python-client`,
      `google-auth`, and `google-auth-oauthlib` from `dependencies`; remove the four
      `[[tool.mypy.overrides]]` blocks for `googleapiclient.*`, `google.oauth2.*`,
      `google.auth.*`, and `google_auth_oauthlib.*` (lines 73–89, no longer needed — local
      storage uses only the standard library); run the project's lockfile update command
- [X] T002 In `backend/app/config.py`: remove `google_drive_token_path`,
      `google_drive_root_folder_id`, `google_drive_client_id`, `google_drive_client_secret`;
      add `meeting_audio_storage_path: str = "./demo/meeting-audio"` (CWD-relative, matching
      `client_profile_path`/`collector_fixture_path` in the same file, `research.md` Decision 12)
- [X] T003 [P] Create `demo/meeting-audio/wara-weekly-sync/` and copy the existing test fixture
      into it: `mkdir -p demo/meeting-audio/wara-weekly-sync && cp
      demo-wara/wara-weekly-sync-recovery.m4a demo/meeting-audio/wara-weekly-sync/` — lands
      inside the `./demo` directory both `api` and `worker` already mount read-only in
      `docker-compose.yml`, so no compose change is needed

**Checkpoint**: Google Drive dependency surface is gone; local storage configuration exists;
test audio is staged. No collector code compiles against the old adapter yet — that's Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Replace the Google Drive adapter with the local storage equivalent and repoint
every caller. Every user story's tests exercise `AudioCollector` through this new dependency, so
none of them can be migrated until this phase lands.

**⚠️ CRITICAL**: No user-story test migration can begin until this phase is complete.

- [X] T004 Create `backend/app/ingestion/adapters/local_storage_client.py`
      (`research.md` Decision 12): `LocalStorageAccessError` (replaces
      `GoogleDriveAuthenticationError`), `LocalRecording` (frozen dataclass:
      `file_id`, `name`, `modified_time`, `series_id`), and `LocalStorageClient(root_path: str)`
      with `list_recordings() -> list[LocalRecording]` (walks one level of subdirectories under
      `root_path`, each a `series_id`; skips non-audio extensions and hidden files; raises
      `LocalStorageAccessError` if `root_path` doesn't exist, isn't a directory, or isn't
      readable) and `read(file_id: str) -> bytes` (reads the file at `root_path / file_id`)
- [X] T005 [P] Delete `backend/app/ingestion/adapters/google_drive_client.py`
- [X] T006 [P] Delete `backend/app/ingestion/adapters/google_drive_token_store.py`
- [X] T007 [P] Delete `backend/scripts/authorize_google_drive.py` (the one-time OAuth-grant
      script — nothing left to authorize)
- [X] T008 Update `backend/app/ingestion/adapters/audio_collector.py` (depends on T004):
      constructor parameter `drive: GoogleDriveClient` → `storage: LocalStorageClient`;
      `self._drive.list_recordings()` → `self._storage.list_recordings()`,
      `self._drive.download(recording.file_id)` → `self._storage.read(recording.file_id)`;
      update the module docstring's Drive-specific references (lines 1–30) to describe local
      storage per `research.md` Decision 12
- [X] T009 Update `backend/app/ingestion/adapters/audio_refresh_router.py` (depends on T004,
      T008): `_build_audio_collector()` constructs
      `LocalStorageClient(settings.meeting_audio_storage_path)` instead of
      `GoogleDriveClient(token_store=GoogleDriveTokenStore(...), root_folder_id=...)`; remove
      the now-unused `google_drive_client`/`google_drive_token_store` imports
- [X] T010 Update `backend/app/worker.py` (depends on T004, T008): `_collect_audio()` constructs
      `LocalStorageClient(settings.meeting_audio_storage_path)` instead of
      `GoogleDriveClient(...)`; remove the now-unused `google_drive_client`/
      `google_drive_token_store` imports; update the module docstring's "an invalid/expired
      Drive token" reference (line 10) to describe a local-storage-access failure instead
- [X] T011 [P] Update `backend/app/ingestion/application/use_cases.py`'s Decision-5 comment
      (around line 324, "an invalid/expired Drive token, a network error") to describe a
      storage-agnostic failure example instead — the `try/except` behavior itself is unchanged

**Checkpoint**: `AudioCollector` and every caller now depend on `LocalStorageClient`. The
backend compiles; existing tests that import `google_drive_client`/`google_drive_token_store`
will fail to collect until their own phase below lands.

---

## Phase 3: User Story 1 - Meeting evidence appears in the score automatically (Priority: P1) 🎯 MVP

**Goal**: A recording placed in the local storage folder for a consented series becomes cited
score evidence, exactly as it did under Drive.

**Independent Test**: Per `quickstart.md` User Story 1 — place a consented recording under
`demo/meeting-audio/<series>/`, run the collector, confirm a `meeting_commitment` finding citing
the new event.

### Tests for User Story 1

- [X] T012 [US1] Rewrite `backend/tests/unit/test_audio_collector.py`: replace the `_FakeDrive`/
      `DriveRecording`/`GoogleDriveAuthenticationError` fakes with a `_FakeLocalStorage`/
      `LocalRecording`/`LocalStorageAccessError` equivalent (or a real `tmp_path`-backed
      `LocalStorageClient`, per `plan.md`'s revised Testing context — preferred, since there's no
      external API left to fake), preserving every existing scenario: no-consent skip,
      revoked-consent skip, unmapped-folder skip (C1), idempotency skip before read (F1),
      whole-cycle failure on inaccessible storage
- [X] T013 [US1] Rewrite `backend/tests/ingestion/test_audio_collector_real_db.py`: replace the
      fake Drive client (`DriveRecording`, `fake_drive` `AsyncMock`) with a `tmp_path` local
      storage fixture backing a real `LocalStorageClient`

### Validation for User Story 1

- [X] T014 [US1] Run `quickstart.md`'s User Story 1 steps end-to-end against the migrated code:
      `mkdir -p demo/meeting-audio/wara-weekly-sync && cp
      demo-wara/wara-weekly-sync-recovery.m4a demo/meeting-audio/wara-weekly-sync/`, grant
      consent, `python -m app.worker --run-once audio`, confirm a new `events` row and (if the
      recording contains a verbal commitment) a `meeting_commitment` finding; re-run and confirm
      no duplicate row (FR-011)

**Checkpoint**: User Story 1 works end-to-end against local storage, independently testable.

---

## Phase 4: User Story 2 - Consent is documented and enforced per meeting series (Priority: P1)

**Goal**: Confirm the consent gate — entirely unaffected by this revision — still holds after
`AudioCollector`'s dependency swap.

**Independent Test**: Per `quickstart.md` User Story 2 — no code changes are expected here; this
phase is a regression check, not new implementation.

- [X] T015 [US2] Run `backend/tests/unit/test_audio_collector.py`'s consent-gate assertions
      (migrated in T012) and confirm FR-003/FR-004/FR-005 behavior is byte-for-byte unchanged —
      consent enforcement (`MeetingSeriesConsentRepositoryPort.is_active()`) never depended on
      `GoogleDriveClient` vs. `LocalStorageClient`, so this is verification, not new code

**Checkpoint**: Consent gate confirmed intact post-migration.

---

## Phase 5: User Story 3 - On-demand refresh ahead of a review (Priority: P2)

**Goal**: The manual-refresh endpoint works against local storage, including its "degraded"
response shape reflecting a local-storage-access failure instead of a Drive-auth failure.

**Independent Test**: Per `quickstart.md` User Story 3 — add a second recording, call
`POST /api/meeting-audio/refresh`, confirm it's picked up immediately.

### Tests for User Story 3

- [X] T016 [US3] Rewrite `backend/tests/ingestion/test_audio_refresh_router.py`: replace the
      `_FakeDrive`/`DriveRecording`/`GoogleDriveAuthenticationError` fixtures with local-storage
      equivalents (mirroring T012); update
      `test_a_failing_drive_connection_returns_the_degraded_shape`'s expected `source_error`
      text to match `contracts/meeting-audio.md`'s revised message ("Meeting audio storage
      location is not accessible…") and rename the test to describe a storage-access failure
      rather than a Drive connection failure

### Validation for User Story 3

- [X] T017 [US3] Run `quickstart.md`'s User Story 3 steps: add a second recording under
      `demo/meeting-audio/wara-weekly-sync/`, `POST /api/meeting-audio/refresh` as a `cs_lead`
      user, confirm `transcribed: 1` within the request itself (SC-003); call again with nothing
      new and confirm all-zero counts, no error

**Checkpoint**: On-demand refresh works against local storage, independently testable.

---

## Phase 6: User Story 4 - Honest degradation when the audio source breaks (Priority: P2)

**Goal**: An inaccessible local storage location degrades honestly through the existing
coverage/score-freeze mechanism, the same contract the Drive-auth failure used to satisfy.

**Independent Test**: Per `quickstart.md` User Story 4 — make the storage folder inaccessible,
confirm a visible coverage gap and a frozen score, restore it, confirm recovery with no
re-authentication step (there is none to perform).

### Tests for User Story 4

- [X] T018 [US4] Update `backend/tests/unit/test_simulated_collector.py`'s Decision-5
      failure-shape test (around lines 283–345): the stand-in failure message
      `"Google Drive authorization is no longer valid"` → a storage-agnostic message consistent
      with `LocalStorageAccessError` (e.g. `"Meeting audio storage location is not
      accessible"`), including the assertion at line 345; this test simulates a generic
      whole-source failure and was never Drive-specific in its actual mechanism, only in its
      example wording

### Validation for User Story 4

- [X] T019 [US4] Run `quickstart.md`'s User Story 4 steps: `mv demo/meeting-audio
      demo/meeting-audio.bak`, `POST /api/meeting-audio/refresh`, confirm `200` with
      `source_error` present; `GET /api/coverage` shows a real gap; `python -m app.worker
      --run-once score` confirms the score is frozen at its prior value; restore the directory
      and confirm normal behavior resumes immediately, with no reconnection step (FR-001)

**Checkpoint**: Degradation honesty confirmed against local storage, independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Bring the remaining Drive-era documentation in line with the shipped local-storage
design, and run a full verification pass.

- [X] T020 [P] Rewrite `demo-wara/AUDIO-INGESTION-TESTING.md`'s "Step 0 — One-time Google Drive
      setup" section: remove the Cloud Console/OAuth-client/interactive-grant walkthrough and
      the `GOOGLE_DRIVE_*` env var table row; replace with the two-command local storage setup
      from `quickstart.md` Prerequisites (`mkdir -p demo/meeting-audio/wara-weekly-sync && cp
      demo-wara/wara-weekly-sync-recovery.m4a demo/meeting-audio/wara-weekly-sync/`); update the
      "Current state in this environment" prerequisites table to drop the two Drive rows
- [X] T021 Run the full verification pass: `cd backend && uv run pytest && uv run ruff check .
      && uv run mypy app` — confirm zero references to `google_drive`/`GoogleDrive` remain
      outside `git log` (`grep -rli drive backend/app backend/tests` should return nothing)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T002's config field) — BLOCKS every user story
  phase below, since all of them exercise `AudioCollector` through the swapped dependency
- **User Stories (Phase 3–6)**: All depend on Foundational (Phase 2) completion
  - US1 and US2 can proceed in either order once Phase 2 lands (US2 is verification-only here,
    unlike the original build where it was a real prerequisite for US1)
  - US3 and US4 each depend only on Phase 2, not on US1/US2's test migrations, so all four
    story phases are parallelizable across people once Phase 2 is done
- **Polish (Phase 7)**: T020 can run any time after Phase 1 (it's documentation-only); T021
  depends on every prior phase being complete (it's the final gate)

### Within Each User Story

- Test migration before validation (can't validate against tests that still reference the
  deleted Drive fakes)
- Story complete before moving to the next priority, if working sequentially

### Parallel Opportunities

- T005, T006, T007 (deletions) can run in parallel with each other and with T003 (fixture
  staging) — none share a file
- T011 (a comment-only change in `use_cases.py`) can run in parallel with T005–T007
- Once Phase 2 completes, Phases 3, 4, 5, 6 (US1–US4) can be worked in parallel by different
  people — none of their test files overlap
- T020 (docs) can run in parallel with any code phase

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After T004 (LocalStorageClient exists), these three can run together:
Task: "Delete backend/app/ingestion/adapters/google_drive_client.py"
Task: "Delete backend/app/ingestion/adapters/google_drive_token_store.py"
Task: "Delete backend/scripts/authorize_google_drive.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational) — the actual migration work
2. Complete Phase 3 (US1) — **STOP and VALIDATE**: a recording in local storage becomes score
   evidence
3. This alone re-proves the feature's core claim against the new source. Deploy/demo here if
   time is constrained.

### Incremental Delivery Beyond MVP

4. Add Phase 4 (US2) — cheap: verification only, no new code
5. Add Phase 5 (US3) — manual refresh against local storage
6. Add Phase 6 (US4) — degradation honesty against local storage
7. Phase 7 (Polish) — demo documentation, final full-suite pass

### Parallel Team Strategy

With two people: one takes Phase 1 + Phase 2 (the migration itself, sequential by nature); the
other stages T003 and drafts T020 in parallel. Once Phase 2 lands, split Phases 3–6 across
however many people are available — they don't depend on each other.

---

## Notes

- `[P]` tasks touch different files with no unmet dependency
- `[Story]` labels map every task back to `spec.md` for traceability
- This is a migration task list, not a greenfield one — most of the feature (consent gate,
  scheduling, transcription, contracts) is already built and explicitly out of scope for these
  tasks; only the storage-source swap and everything that named Google Drive by name is in scope
- Commit after each task or logical group; stop at any checkpoint to validate a story
independently
