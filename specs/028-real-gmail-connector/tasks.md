---

description: "Task list for feature 028 — Real Gmail Connector"
---

# Tasks: Real Gmail Connector

**Input**: Design documents from `specs/028-real-gmail-connector/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: Unit tests against a fake `GmailClient` (no real network) covering windowing,
idempotency-skip, per-item isolation, header/body parsing, and whole-connection-failure
propagation. `tests/unit/test_simulated_collector.py` is the non-regression proof for FR-005 — it
needs zero changes and must keep passing exactly as-is.

**Organization**: Tasks are grouped by the three user stories in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 `uv add google-api-python-client google-auth google-auth-httplib2
      google-auth-oauthlib` in `backend/`.
- [x] T002 In `backend/app/config.py`, add `gmail_client_id: str = ""`, `gmail_client_secret: str =
      ""`, `gmail_refresh_token: str = ""` (same honest-empty-default discipline as
      `openai_api_key`), and `gmail_poll_interval_hours: int = 1` (matching
      `audio_poll_interval_hours`'s configurable-cadence precedent).
- [x] T003 [P] New `backend/scripts/generate_gmail_token.py` — a one-time, interactive,
      operator-run script using `google_auth_oauthlib.flow.InstalledAppFlow.run_local_server()`
      with scope `https://www.googleapis.com/auth/gmail.readonly`, printing the resulting refresh
      token for the operator to add to `.env` as `GMAIL_REFRESH_TOKEN`. Not imported by any
      runtime `app/` code (`google-auth-oauthlib` is a one-time-script-only dependency,
      `research.md`'s Technical Context note).

**Checkpoint**: `uv run python scripts/generate_gmail_token.py` runs locally and, after a human
approves access in the browser, prints a usable refresh token.

---

## Phase 2: Foundational (Blocking Prerequisites)

*None* — no schema change, no shared infrastructure beyond Phase 1's dependency/config additions.

---

## Phase 3: User Story 1 - Real emails become real signals (Priority: P1) 🎯 MVP

**Goal**: `GmailCollector` reads new mail from a connected mailbox and turns it into ledger events,
automatically.

**Independent Test**: Connect real credentials, confirm a new email becomes a citable event with
no manual script run (`quickstart.md` Story 1).

### Implementation for User Story 1

- [x] T004 [US1] New `backend/app/ingestion/adapters/gmail_collector.py`: define `GmailClient`
      (a `Protocol` with `async def list_message_ids(self, after: datetime, before: datetime) ->
      list[str]` and `async def get_message(self, message_id: str) -> dict[str, Any]`), and
      `_RealGmailClient` implementing it — constructs `google.oauth2.credentials.Credentials`
      from `client_id`/`client_secret`/`refresh_token`, builds the Gmail v1 resource via
      `googleapiclient.discovery.build`, and runs both blocking calls through `asyncio.to_thread`
      (`research.md` Decision 5).
- [x] T005 [US1] Same file: `GmailCollector(Collector)` — `source_type = "gmail"`,
      `mvp_sources_always_expected = False`. Constructor `(client: GmailClient, collector_runs:
      CollectorRunRepositoryPort)`. `fetch(window_start, window_end)`: query the ledger for the
      latest `gmail`-sourced event's `occurred_at` (raw SQL against `events` joined to `sources`,
      matching this codebase's existing raw-SQL convention), subtract a 10-minute overlap buffer,
      or fall back to a 24-hour lookback if no prior `gmail` event exists (`research.md` Decision
      4/FR-010); call `self._client.list_message_ids(after, now())`; for each ID, check
      `self._collector_runs.envelope_exists(idempotency_key("gmail", message_id))` and skip if
      already processed (before the expensive per-message fetch, `AudioCollector`'s Decision 10
      precedent); otherwise `get_message(id)`, extract the `From` header (via
      `email.utils.parseaddr` to strip any display name) and body text (`research.md` Decision 6 —
      `text/plain` preferred, `text/html` stripped as fallback), wrapped in a per-item
      `try/except` that logs and continues on failure (FR-007) — a whole-connection failure from
      `list_message_ids`/an early `get_message` setup error is allowed to propagate
      unchanged (FR-006, mirrors `AudioCollector`'s `LocalStorageAccessError` propagation).
- [x] T006 [US1] Same file: `normalize(raw_item)` builds an `Envelope` matching
      `_normalize_gmail`'s exact shape (`source_type="gmail"`, `identity_status="unresolved"`,
      `resolved_stakeholder_id=None`, `redacted_fields=[]`, `payload_text=<body>`,
      `structured_payload={"participant": <from address>}`) — FR-004, zero reader changes needed.
- [x] T007 [US1] In `backend/app/worker.py`: add `_run_gmail_collector`/`_collect_gmail`
      (sync-wrapper + async body, matching `_run_audio_collector`/`_collect_audio`'s exact shape),
      constructing `_RealGmailClient` from `settings.gmail_client_id/_secret/_refresh_token` and
      `GmailCollector`, calling `RunCollectorUseCase.execute(collector, window_start=now,
      window_end=now, trigger="poll")` (the collector's own `fetch()` derives the real window
      internally per T005, matching how `AudioCollector` already ignores these two params too).
      Register `scheduler.add_job(_run_gmail_collector, "interval",
      hours=settings.gmail_poll_interval_hours, id="gmail_collector")`; add `"gmail":
      _run_gmail_collector` to `_RUN_ONCE_JOBS` (FR-009).

### Tests for User Story 1

- [x] T008 [P] [US1] New `backend/tests/unit/test_gmail_collector.py`: a fake `GmailClient`
      returning canned message IDs/bodies; assert `fetch()` returns correctly normalized items for
      new messages and skips ones already covered by `envelope_exists()`.
- [x] T009 [P] [US1] Same file: assert `normalize()`'s output shape matches
      `_normalize_gmail`'s field-for-field (same test fixture text, same resulting
      `structured_payload`).

**Checkpoint**: User Story 1 fully functional — real mail becomes real events.

---

## Phase 4: User Story 2 - Simulated sources keep working unchanged (Priority: P1)

**Goal**: Prove `SimulatedCollector` and its JSON fixture are untouched.

**Independent Test**: Run the simulated flow unchanged with the real connector also present
(`quickstart.md` Story 2).

### Tests for User Story 2

- [x] T010 [US2] Live-verify: run `tests/unit/test_simulated_collector.py` unchanged — confirm
      100% pass, zero modification to that file or to `simulated_collector.py` itself (`git diff`
      shows no changes to either).
- [x] T011 [US2] Live-verify: `scripts/run_collector.py --source simulated` produces the same
      `envelopes_emitted`/`duplicates_skipped` counts as before this feature (compare against
      feature 027's own verification run, which used the identical fixture).

**Checkpoint**: User Stories 1 and 2 both independently verified — the explicit, non-negotiable
constraint holds.

---

## Phase 5: User Story 3 - A Gmail connection problem is visible (Priority: P2)

**Goal**: A whole-connection failure is an honest coverage gap; a per-item failure never aborts
the run.

**Independent Test**: Invalid credentials produce a visible gap, not silence
(`quickstart.md` Story 3).

### Tests for User Story 3

- [x] T012 [US3] Same test file: a fake `GmailClient` whose `list_message_ids` raises — assert the
      exception propagates out of `fetch()` unchanged (FR-006), matching `AudioCollector`'s own
      propagation-not-swallowing test precedent.
- [x] T013 [US3] Same test file: a fake `GmailClient` whose `get_message` raises for one specific
      message ID among several — assert that message is skipped (logged) and every other message
      in the same `fetch()` call still succeeds (FR-007).
- [x] T014 [US3] Live-verify: run `--run-once gmail` with a deliberately invalid
      `GMAIL_REFRESH_TOKEN`, confirm `GET /api/coverage` shows `gmail` as not successfully read for
      that cycle — distinct from a healthy run with zero new mail.

**Checkpoint**: All three user stories independently functional and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 [P] Run `ruff`/`mypy`/`lint-imports --config ../.importlinter` clean across all changed
      files — confirm `ingestion-application-purity` still holds (no `googleapiclient`/`google`
      import outside `app.ingestion.adapters`).
- [x] T016 [P] Run `quickstart.md`'s full validation sequence end to end, using real credentials,
      as final sign-off.
- [x] T017 Confirm `specs/ROADMAP.md` is intentionally left unmodified, matching
      `specs/025`/`026`/`027`'s own precedent.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Empty.
- **User Story 1 (Phase 3)**: Depends on Phase 1. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on nothing this feature builds — it's a non-regression check,
  runnable any time after Phase 1, but placed after Phase 3 since that's when the real connector
  actually exists to prove non-interference against.
- **User Story 3 (Phase 5)**: Depends on Phase 3's `GmailCollector` existing.
- **Polish (Phase 6)**: Depends on Phases 3–5.

### Parallel Opportunities

- T008/T009 and T012/T013 (same new test file, independent test cases) can be drafted together.
- T015/T016 (independent checks) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) — including the one-time human token-generation step.
2. Phase 3 (User Story 1) — the real connector exists and works.
3. **STOP and VALIDATE** via `quickstart.md` Story 1.

### Incremental Delivery

1. Setup → Phase 3 (US1) → validate → real Gmail signals flow in.
2. Phase 4 (US2) → validate → the explicit non-negotiable constraint confirmed held.
3. Phase 5 (US3) → validate → failure visibility confirmed.
4. Phase 6 (Polish) → final sign-off.

## Notes

- No `[Story]` label on T001–T003 (Setup) or T015–T017 (Polish).
- User Story 2 has no implementation tasks by design — `SimulatedCollector` is untouched, so this
  phase is entirely a non-regression proof, not new behavior.

## Verification log (how each task was actually confirmed, not just assumed)

- **T001–T003**: Dependencies added (`google-api-python-client`, `google-auth`,
  `google-auth-httplib2`, `google-auth-oauthlib`); `GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET` added to
  `backend/.env` by the operator. `scripts/generate_gmail_token.py` written and reviewed (`ruff`/
  `mypy` clean) but **not yet run** — it requires a real, interactive Google login only the
  deployment's operator can perform. **`GMAIL_REFRESH_TOKEN` is not yet set** — this is the one
  remaining manual step before any *live* run against a real mailbox is possible.
- **T004–T009**: `GmailCollector`/`_RealGmailClient`/`GmailClient` implemented; `ruff`/`mypy`/
  `lint-imports --config ../.importlinter` all clean (4/4 contracts kept — `googleapiclient`/
  `google.oauth2` imports confirmed confined to `app.ingestion.adapters`). 8 new tests in
  `backend/tests/unit/test_gmail_collector.py`, all passing against a fake `GmailClient` (no real
  network) — covering normalization shape parity with `_normalize_gmail`, display-name stripping,
  idempotency-skip-before-fetch, and the window-derivation logic's exact arithmetic (proven via a
  real inserted ledger event, not an assumption about ambient database state).
- **T010/T011**: `git diff` confirms zero changes to `simulated_collector.py` or
  `test_simulated_collector.py`; both the test file (8/8 passing, unchanged) and a live
  `scripts/run_collector.py --source simulated` run were exercised with `GmailCollector` also
  present in the codebase — `envelopes_emitted=18`, matching feature 027's own prior run of the
  identical fixture exactly. FR-005/User Story 2 holds.
- **T012/T013**: Whole-connection-failure propagation and per-item-failure isolation both covered
  by dedicated fake-`GmailClient` tests, passing.
- **T014**: The *logic* (connection failure propagates, is never silently swallowed) is proven by
  T012's unit test. The live half (invalid-token run) remains unverified — see the outstanding-gap
  note below, now narrowed to this one scenario only.
- **T015**: `ruff check .`, `uv run mypy app`, `lint-imports --config ../.importlinter` all clean.
- **T016**: The full backend suite was run against a **freshly created** `pgvector/pgvector:pg16`
  container, twice, with the exact same result both times: **192 passed, 1 skipped**, with exactly
  one failure — `tests/unit/test_hash_chain.py::test_appended_sequence_has_no_broken_links` —
  reproduced only in the full-suite run, passing cleanly (2/2) when run alone against the same
  fresh container. Confirmed **pre-existing and unrelated to this feature**: this exact test is
  named in `specs/ROADMAP.md`'s feature-011 log entry as one of five known full-suite test-ordering
  flakes, already "git-stash-verified against unmodified code" there. Also confirmed it does not
  reproduce on real GitHub Actions CI (this feature's own PR: `lint`/`type-check`/`test` all green).
- **T017**: `specs/ROADMAP.md` intentionally left unmodified, matching prior features' precedent.

**Post-merge live verification (2026-08-25), run by the operator with real credentials**: after
`GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET`/`GMAIL_REFRESH_TOKEN` were configured (the last one via a
real, interactive run of `scripts/generate_gmail_token.py` — genuinely could not be automated, per
`research.md`'s own reasoning), `--run-once gmail` was run twice against a freshly migrated,
freshly seeded `pgvector/pgvector:pg16` container, with **real** Gmail API calls:

- **Run 1 (cold)**: `envelopes_emitted=17 duplicates_skipped=0` — 17 real emails from the
  connected mailbox became real ledger events. `sources` row: `status='connected'`,
  `display_name='Meridian — Email'` (the same row `SimulatedCollector`'s fixture items already
  used, exactly as `research.md` Decision 2 predicted). Directly queried: 17/17 events have a
  correctly-parsed, valid-email-shaped `structured_payload->>'participant'` (confirming
  `email.utils.parseaddr` correctly stripped display names from real Gmail `From` headers, not
  just fixture-shaped test headers) and 17/17 real message bodies extracted successfully (zero
  dropped for "no readable body," `spec.md` Edge Cases) — real proof `_extract_body_text`'s MIME
  walking works against real Gmail payloads, not only the synthetic shapes in
  `test_gmail_collector.py`. All 17 show `identity_status='unresolved'` — correct and expected:
  the connected mailbox's real senders (e.g. LinkedIn notifications) don't match any stakeholder in
  the demo/Meridian client profile, which is fixture data unrelated to this real inbox; REQ-M1-05's
  "abstain, never guess" held for every one of them.
- **Run 2 (warm, immediately after)**: `envelopes_emitted=0 duplicates_skipped=0` — confirms
  SC-002 for real. The `duplicates_skipped=0` (not `>0`) is the *correct* signature of this
  collector's specific idempotency design (`envelope_exists()` checked before the expensive
  per-message fetch, `AudioCollector`'s Decision 10 precedent) — every already-seen message was
  filtered out before ever reaching `RunCollectorUseCase`'s own dedup layer, so nothing was left
  for that layer to count as a duplicate.

This closes the "implemented and unit-tested but not yet live-verified" gap this section
originally flagged for Story 1 and Story 2 (FR-001–FR-005, FR-009, FR-010, SC-001–SC-003) against
a real Gmail account, not just fakes. **T014's live half (an invalid-token run) remains the one
still-open item** — a smaller, lower-risk scenario than what's now confirmed, deferred rather than
blocking, since it exercises the same already-unit-tested propagation path (T012) against a real
but deliberately-broken credential.

Separately, found and fixed post-merge: `.env.example` had no `GMAIL_*` entries at all (unlike
`PYANNOTEAI_API_KEY`'s own precedent for a prior real-connector feature) — a real gap, now closed.
`README.md` was deliberately left unmodified — it already stops covering any feature past 011
(confirmed: zero mentions of `specs/019-meeting-audio-ingestion` either), so omitting Gmail from it
matches this repository's own established convention rather than being an oversight.
