---

description: "Task list for feature 029 — Real Zendesk Connector"
---

# Tasks: Real Zendesk Connector

**Input**: Design documents from `specs/029-real-zendesk-connector/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: Unit tests against a fake `ZendeskClient` (no real network) covering transition
classification, windowing, idempotency, per-item isolation, and whole-connection-failure
propagation. `tests/unit/test_simulated_collector.py` is the non-regression proof for FR-006 — it
needs zero changes and must keep passing exactly as-is.

**Organization**: Tasks are grouped by the three user stories in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Move `httpx` from `backend/pyproject.toml`'s `[dependency-groups] dev` list to its main
      `[project] dependencies` list (`research.md` Decision 5) — `uv sync` afterward.
- [x] T002 In `backend/app/config.py`, add `zendesk_subdomain: str = ""`, `zendesk_agent_email: str
      = ""`, `zendesk_api_token: str = ""` (same honest-empty-default discipline as
      `gmail_client_id`), and `zendesk_poll_interval_hours: int = 1`.

**Checkpoint**: `uv sync` succeeds with `httpx` available at runtime; new settings load without
error even when unset.

---

## Phase 2: Foundational (Blocking Prerequisites)

*None* — no schema change, no shared infrastructure beyond Phase 1's additions.

---

## Phase 3: User Story 1 - Real ticket activity becomes real signals (Priority: P1) 🎯 MVP

**Goal**: `ZendeskCollector` reads ticket creation/reopening/resolution from a connected account
and turns each into a correctly-typed ledger event, automatically.

**Independent Test**: Connect real credentials, create/reopen/resolve a ticket, confirm three
distinct, correctly-typed events with no manual script run (`quickstart.md` Story 1).

### Implementation for User Story 1

- [x] T003 [US1] New `backend/app/ingestion/adapters/zendesk_collector.py`: define `ZendeskClient`
      (a `Protocol` with `async def list_changed_tickets(self, after: datetime, before: datetime)
      -> list[dict[str, Any]]`, `async def get_ticket_audits(self, ticket_id: int) ->
      list[dict[str, Any]]`, `async def get_user_email(self, user_id: int) -> str | None`), and
      `_RealZendeskClient` implementing it via `httpx.AsyncClient` with Basic Auth
      (`f"{agent_email}/token"` / `api_token`, `research.md` Decision 5) against
      `https://{subdomain}.zendesk.com/api/v2/...` — `list_changed_tickets` wraps the Incremental
      Ticket Export cursor endpoint, `get_ticket_audits` wraps `GET /tickets/{id}/audits.json`,
      `get_user_email` wraps `GET /users/{id}.json`.
- [x] T004 [US1] Same file: a pure helper function `_classify_transitions(ticket: dict, audits:
      list[dict], window_start: datetime) -> list[dict]` — scans each audit's `events` for
      `type == "Change"` and `field_name == "status"`; a transition where `value` is `solved` or
      `closed` emits a `resolved` transition; a transition *from* `solved`/`closed` to an active
      status emits a `reopened` transition; if `ticket["created_at"]` falls within the window,
      additionally emits a `created` transition — each transition dict carries a stable, unique
      identifier derived from the audit's own `id` (or the ticket's `id` alone for `created`,
      which can only happen once per ticket) for idempotency (`research.md` Decision 3, FR-004/
      FR-012).
- [x] T005 [US1] Same file: `ZendeskCollector(Collector)` — `source_type = "zendesk"`,
      `mvp_sources_always_expected = False`. Constructor `(client: ZendeskClient, collector_runs:
      CollectorRunRepositoryPort, session: AsyncSession)`. `fetch()`: derive the window (same
      ledger-derived mechanism as `GmailCollector`, `research.md` Decision 6); call
      `list_changed_tickets`; for each ticket, fetch its audits, classify transitions (T004); for
      each transition, check `envelope_exists()` and skip if already processed; otherwise resolve
      the ticket's `requester_id` to an email via a per-`fetch()`-call cache around
      `get_user_email` (`research.md` Decision 4); wrap per-ticket work in a `try/except` that
      logs and continues on failure (FR-008) — a whole-connection failure from
      `list_changed_tickets` propagates unchanged (FR-007).
- [x] T006 [US1] Same file: `normalize(raw_item)` builds an `Envelope` matching
      `_normalize_zendesk`'s shape (`source_type="zendesk"`, `identity_status="unresolved"`,
      `resolved_stakeholder_id=None`, `redacted_fields=[]`, `payload_text=<ticket title>`,
      `structured_payload={"participant": <resolved email>, "ticket_number": <id>, "title":
      <subject>, "state": <created|reopened|resolved>}` — no `product_area` key, `spec.md`
      Assumptions) — FR-005, zero reader changes needed.
- [x] T007 [US1] In `backend/app/worker.py`: add `_run_zendesk_collector`/`_collect_zendesk`
      (sync-wrapper + async body, matching `_run_gmail_collector`/`_collect_gmail`'s exact shape),
      constructing `_RealZendeskClient` from the new settings and `ZendeskCollector`, calling
      `RunCollectorUseCase.execute(collector, window_start=now, window_end=now, trigger="poll")`.
      Register `scheduler.add_job(_run_zendesk_collector, "interval",
      hours=settings.zendesk_poll_interval_hours, id="zendesk_collector")`; add `"zendesk":
      _run_zendesk_collector` to `_RUN_ONCE_JOBS` (FR-010).

### Tests for User Story 1

- [x] T008 [P] [US1] New `backend/tests/unit/test_zendesk_collector.py`: a fake `ZendeskClient`;
      assert a ticket whose `created_at` is in-window produces a `created` transition; assert a
      status-change audit event to `solved` produces a `resolved` transition; assert a
      status-change audit event *from* `solved` back to `open` produces a `reopened` transition.
- [x] T009 [P] [US1] Same file: a ticket resolved then reopened twice within one window (two
      separate status-change audit events, `solved`→back, `solved`→back again) produces **two**
      distinct `reopened` transitions with different stable identifiers, not one collapsed event
      (FR-012/SC-005).
- [x] T010 [P] [US1] Same file: assert `normalize()`'s output shape matches `_normalize_zendesk`'s
      field-for-field.

**Checkpoint**: User Story 1 fully functional — real ticket activity becomes real, correctly-typed
events.

---

## Phase 4: User Story 2 - Simulated sources keep working unchanged (Priority: P1)

**Goal**: Prove `SimulatedCollector` and its JSON fixture are untouched.

### Tests for User Story 2

- [x] T011 [US2] Live-verify: run `tests/unit/test_simulated_collector.py` unchanged — confirm
      100% pass, zero modification to that file or to `simulated_collector.py` (`git diff` shows
      no changes to either).
- [x] T012 [US2] Live-verify: `scripts/run_collector.py --source simulated` produces the same
      `envelopes_emitted`/`duplicates_skipped` counts as before this feature.

**Checkpoint**: User Stories 1 and 2 both independently verified.

---

## Phase 5: User Story 3 - A Zendesk connection problem is visible (Priority: P2)

**Goal**: A whole-connection failure is an honest coverage gap; a per-item failure never aborts
the run.

### Tests for User Story 3

- [x] T013 [US3] Same test file: a fake `ZendeskClient` whose `list_changed_tickets` raises —
      assert the exception propagates out of `fetch()` unchanged (FR-007).
- [x] T014 [US3] Same test file: a fake `ZendeskClient` whose `get_ticket_audits` raises for one
      specific ticket among several — assert that ticket's transitions are skipped (logged) and
      every other ticket's transitions in the same `fetch()` call still succeed (FR-008).
- [ ] T015 [US3] Live-verify (only if real credentials are available in this environment): run
      `--run-once zendesk` with a deliberately invalid `ZENDESK_API_TOKEN`, confirm `GET
      /api/coverage` shows `zendesk` as not successfully read for that cycle.

**Checkpoint**: All three user stories independently functional and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T016 [P] Run `ruff`/`mypy`/`lint-imports --config ../.importlinter` clean across all changed
      files.
- [x] T017 [P] Run `quickstart.md`'s full validation sequence end to end (with real credentials, if
      available) as final sign-off.
- [x] T018 Confirm `specs/ROADMAP.md` and `README.md` are intentionally left unmodified, matching
      `specs/025`–`028`'s own precedent.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Empty.
- **User Story 1 (Phase 3)**: Depends on Phase 1. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on nothing this feature builds — a non-regression check,
  placed after Phase 3 since that's when the real connector exists to prove non-interference
  against.
- **User Story 3 (Phase 5)**: Depends on Phase 3's `ZendeskCollector` existing.
- **Polish (Phase 6)**: Depends on Phases 3–5.

### Parallel Opportunities

- T008/T009/T010 and T013/T014 (same new test file, independent test cases) can be drafted
  together.
- T016/T017 (independent checks) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup).
2. Phase 3 (User Story 1) — the real connector exists and correctly classifies transitions.
3. **STOP and VALIDATE** via `quickstart.md` Story 1 (with real credentials if available).

### Incremental Delivery

1. Setup → Phase 3 (US1) → validate → real Zendesk signals flow in, correctly typed.
2. Phase 4 (US2) → validate → the explicit non-negotiable constraint confirmed held.
3. Phase 5 (US3) → validate → failure visibility confirmed.
4. Phase 6 (Polish) → final sign-off.

## Notes

- No `[Story]` label on T001–T002 (Setup) or T016–T018 (Polish).
- User Story 2 has no implementation tasks by design — `SimulatedCollector` is untouched.
- T004's transition-classification logic is the one genuinely new piece of domain logic this
  feature adds beyond `GmailCollector`'s own template — it gets more test coverage (T008/T009)
  than any single piece of `GmailCollector`'s own logic did, proportionate to its real complexity.

## Verification log (how each task was actually confirmed, not just assumed)

- **T001/T002**: `httpx` moved to main dependencies (`uv sync` succeeds); new Zendesk settings
  added with the established honest-empty-default discipline.
- **T003–T007**: `ZendeskCollector`/`_RealZendeskClient`/`ZendeskClient` implemented and wired into
  `worker.py`; `ruff`/`mypy`/`lint-imports --config ../.importlinter` all clean on first pass (4/4
  contracts kept).
- **T008–T010**: New `backend/tests/unit/test_zendesk_collector.py` (7 tests), all passing.
- **Genuine bug found and fixed during this feature's own test-writing, not by inspection**: the
  first version of these tests anchored fixture timestamps to a fixed `_NOW = datetime.now(UTC)`
  module constant, exactly the mistake `specs/028-real-gmail-connector`'s own test file had already
  learned to avoid (documented there in a comment) — reintroduced here anyway, then caught for real:
  running the tests alone passed, but running the full suite failed all 7 with `0 == 1`/`0 == 2`.
  Root cause, confirmed by direct query: this shared, cumulative test database already had
  `zendesk`-sourced events dated in **2041** (the same class of cross-test synthetic-data pollution
  already documented for `source_type='gmail'`, now confirmed to affect `zendesk` too), pushing
  `ZendeskCollector._derive_window()`'s ledger-derived `after` bound far past any fixture timestamp
  anchored to real "now." Fixed the same way feature 028 fixed it: a `_zendesk_anchor()` helper
  inserts one real, controlled `zendesk`-sourced event at `ledger_floor()+1s` (guaranteed to become
  the new max) and every test computes its fixture timestamps relative to *that* anchor, not real
  wall-clock time. Confirmed fixed: full suite run twice (once against the already-polluted shared
  container, once against a freshly created one) — **199 passed / 200 passed** respectively, both
  times with zero `test_zendesk_collector.py` failures.
- **T011/T012**: `git diff` confirms zero changes to `simulated_collector.py` or
  `test_simulated_collector.py`; `envelopes_emitted=18` on a live `--source simulated` run, matching
  every prior real-connector feature's own baseline exactly. FR-006/User Story 2 holds.
- **T013/T014**: Whole-connection-failure propagation and per-ticket-failure isolation both covered
  by dedicated fake-`ZendeskClient` tests, passing.
- **T015**: Not completed — no real Zendesk account/credentials were available in this session (the
  user explicitly chose to build against fakes first, unlike the Gmail connector where real
  credentials became available). The *logic* is proven by T013's unit test. Genuinely open, not
  assumed complete, exactly matching how feature 028's own T014 was flagged before its later live
  verification.
- **T016**: `ruff check .`, `uv run mypy app`, `lint-imports --config ../.importlinter` all clean.
- **T017**: Full backend suite run against two separate containers (one shared/polluted, one
  freshly created): **199 passed, 1 skipped** / **200 passed, 0 skipped-relevant-failures**
  respectively. The pre-existing, already-documented `test_hash_chain.py` full-suite-only flake
  (named in `specs/ROADMAP.md`'s feature-011 log entry) appeared once, out of two runs — consistent
  with its already-established intermittent, unrelated nature, not a new regression.
- **T018**: `specs/ROADMAP.md` and `README.md` intentionally left unmodified, matching
  `specs/025`–`028`'s own precedent.

**Outstanding**: live verification against a real Zendesk account (T015, `quickstart.md`'s live
scenarios) requires real credentials, which were not available in this session — flagged honestly
here, the same as feature 028's Gmail connector was before its own later live verification.
