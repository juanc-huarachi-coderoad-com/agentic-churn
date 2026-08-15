# Spec-Kit Roadmap

Tracks progress across this repository's spec-kit features. Updated as each feature moves
through `/speckit-specify` → `/speckit-implement`.

## Why one feature per build-order phase

`requirements/` and `architecture/` already contain more detail (EARS-syntax `REQ-IDs`,
an explicit traceability matrix, ratified architecture decisions) than a typical
greenfield `spec.md` would. Re-deriving that content per module through spec-kit would
duplicate and likely drift from what's already authoritative. Instead:

- **`requirements/*.md` stays the single source of truth** for *what* each module must do
  — spec-kit doesn't re-author it.
- **`spec.md`/`plan.md`/`tasks.md` are a thin, per-build-phase translation layer**:
  `spec.md` turns a slice of already-decided requirements into prioritized,
  independently-testable user stories; `plan.md`'s Technical Context is filled by *citing*
  `architecture/*.md` instead of re-researching it; `tasks.md` is the one genuinely new
  artifact — concrete file-level build tasks.
- Every acceptance criterion cites a `REQ-ID` rather than restates its content.

The product spec's own build order (`base/Churn-Sentiment-Agent-Product-
Specification.md` §16) already segments the system into eleven phases, each of which
"leaves a working system" — exactly spec-kit's definition of an independently
testable/demoable feature slice. That's the feature boundary used below, not one
spec-kit feature per module (M1–M10), which would fragment single working slices.

## Status

| # | Feature | Build-order phase | Status | Primary requirements | Primary architecture |
|---|---|---|---|---|---|
| 001 | [`project-foundation`](001-project-foundation/) | 1 · Foundation | ✅ **Complete** — all 33 tasks implemented and verified against real Docker/Postgres | `requirements/11-non-functional-requirements.md` (CI/determinism criteria) | `architecture/03-technology-stack.md`, `architecture/09-clean-architecture-and-patterns.md`, all of `data-base/` |
| 002 | [`dashboard-shell`](002-dashboard-shell/) | 2 · Vertical slice (login + dashboard) | ✅ **Complete** — all 29 tasks implemented and verified end to end, including a real browser against the containerized production build | `requirements/14-authentication.md`, `requirements/08-health-dashboard.md` (shell only) | `architecture/07-api-spec.md`, `data-base/12-users-and-auth.md` |
| 003 | [`ingestion-and-context`](003-ingestion-and-context/) | 3 · Ledger + profile | ✅ **Complete** — all 44 tasks implemented and verified against real Docker/Postgres, including a genuine RunCollectorUseCase bug (see Log) | `requirements/01-signal-collectors.md`, `02-event-ledger.md`, `03-client-profile.md` | `architecture/01`, `02-component-catalog.md`; `data-base/02,03,04` |
| 004 | [`score-engine`](004-score-engine/) | 4 · Scoring engine (checkpoint phase) | ✅ **Complete** — all 29 tasks implemented and verified against real Docker/Postgres, including three genuine bugs found and fixed (see Log) | `requirements/06-scoring-engine.md`, `13-scoring-calibration-appendix.md` | `data-base/06-schema-scoring.md`; `sequences/06` |
| 005 | [`deterministic-findings`](005-deterministic-findings/) | 5 · Findings (no AI) | ✅ **Complete** — all 37 tasks implemented and verified against real Docker/Postgres, including one genuine defensive-coding gap found during verification, not blocking (see Log) | `requirements/05-interpreters-readers.md` (Commitment/Usage/Recurrence/Absence/Relationship — REQ-M5-11's Relationship reader isn't assigned to any phase in `base/...md` §16's table despite being deterministic and paired with Absence throughout; grouped here with its fellow non-LLM readers rather than left dangling or bundled with the LLM readers in feature 007) | `data-base/05-schema-reasoning.md` |
| 006 | [`dashboard-evidence-trace`](006-dashboard-evidence-trace/) | 6 · Full dashboard | ✅ **Complete** — all 52 tasks implemented and verified against real Docker/Postgres, including two `/speckit-analyze` remediations applied before implementation and one genuine Docker build gap found during verification, not blocking (see Log) | `requirements/08-health-dashboard.md` (full) | `architecture/07-api-spec.md`, `data-base/08` |
| 007 | `model-findings` | 7 · Tone/Intent + validation gate | ⬜ Not started — **next up** | `requirements/05-interpreters-readers.md` (Tone/Intent/M5a) | `architecture/04-ai-safety-and-model-usage.md`, `05-agent-catalog.md` |
| 008 | `narrator-and-ask-agent` | 8 · Explanation layer | ⬜ Not started | `requirements/07-narrator.md`, `09-ask-agent.md` | `sequences/02`, `decisions/03-langgraph-for-ask-agent.md` (Ask agent orchestration — decided ahead of this feature so `/speckit-plan` cites it rather than re-deciding it) |
| 009 | `draft-composer` | 9 · The closer | ⬜ Not started | `requirements/10-draft-composer.md` | `sequences/04` |
| 010 | `feedback-memory` | 10 · Learning loop | ⬜ Not started | `requirements/04-feedback-memory.md` | `data-base/07`; `sequences/03` |
| 011 | `production-hardening` | 11 · Hardening | ⬜ Not started | remaining NFRs, `decisions/01-mvp-scope-and-phasing.md` | — |

`requirements/12-traceability-matrix.md` maps REQ-ID → spec section → module →
acceptance test — every `spec.md` and `tasks.md` produced below links into that matrix
rather than reproducing it.

## Per-feature loop

Repeat for each row above, in order:

1. **`/speckit-specify`** — description explicitly cites the REQ-IDs and architecture docs
   in scope; user stories are derived from them, not restated.
2. **`/speckit-clarify`** — expect few findings per feature; most ambiguity is already
   resolved in `decisions/00-open-questions-resolved.md`.
3. **`/speckit-plan`** — Technical Context is filled by citing `architecture/*.md` and the
   relevant `data-base/*.md`; the Constitution Check gate validates against
   `.specify/memory/constitution.md`.
4. **`/speckit-tasks`** — the one net-new artifact: concrete, file-level tasks grouped by
   user story.
5. **`/speckit-analyze`** — cross-checks `spec.md`/`plan.md`/`tasks.md` against each other
   and against `requirements/`/`architecture/` for drift.
6. **`/speckit-implement`** — executes `tasks.md`, verified against real tooling wherever
   possible (not just written and assumed correct).

## Log

- **2026-08-13** — `.specify/memory/constitution.md` ratified at v1.0.0, then amended to
  v1.1.0 (added P11, frontend engineering standards).
- **2026-08-13** — Feature 001 (`project-foundation`) specified, planned, tasked,
  analyzed, and implemented. All 33 tasks complete; stack verified end to end against
  real Docker containers and Postgres 16 (migration round-trip, seed script, CI gates —
  both positive and negative import-linter cases — health checks, restart persistence,
  volume-wipe reprovisioning, and full-stack startup timing against SC-001).
- **2026-08-13** — Feature 002 (`dashboard-shell`) specified, planned, tasked, analyzed,
  and implemented. All 29 tasks complete. Two design adaptations surfaced and documented
  during implementation (both in `specs/002-dashboard-shell/research.md`): the login
  rate limiter is keyed by source IP rather than username (`slowapi`'s key function is
  synchronous, can't safely read the async request body) and counts only failed
  attempts, not every call. Verified against the real, fully containerized stack: the
  full auth lifecycle via `curl` (login, generic failure messages, rate limiting,
  logout/revocation), 10 backend pytest cases and 3 frontend Vitest cases, 4 Playwright
  end-to-end specs, and a real Chrome browser driven against the nginx-served
  production build — screenshotted login → "Meridian Logistics" / "Still learning — 0
  of 6 signal types available." Login-to-dashboard round trip: 0.61s (SC-001 threshold
  5s).
- **2026-08-14** — LangGraph adopted, scoped to the Ask agent (M9) only —
  `decisions/03-langgraph-for-ask-agent.md`. The other five LLM touchpoints (Tone,
  Intent, Meeting readers; Narrator; Draft composer) keep the plain `LLMPort` design
  unchanged. `.specify/memory/constitution.md` amended to v1.2.0 (Technology and Data
  Standards + an AI-safety clarification). Decided ahead of feature 008 so its future
  `/speckit-plan` has an authoritative decision to cite.
- **2026-08-14** — Feature 003 (`ingestion-and-context`) specified, planned, tasked,
  analyzed (7 remediations applied — a CRITICAL finding that `ReplayUseCase` was
  referenced but never actually built as a task, plus fixture/coverage gaps), and
  implemented. All 44 tasks complete. Verified against the real, fully containerized
  stack: `scripts/run_collector.py` against the Meridian fixture (6 events, 0 broken
  hash-chain links, ticket #398 = 2.0h resolved / #456 = open_overdue matching the
  worked example, `legal_threads` redaction, identity resolution), the full profile
  lifecycle via `curl` (version 3→4, `is_current` flip, 422 rejection of a corrupted
  profile with no new version created, replay history), a real encryption-key-missing
  startup failure and recovery, and 35 backend pytest cases (up from 10 after feature
  002) across three consecutive runs against the same accumulating database. One real
  bug found and fixed during verification, not by inspection: `RunCollectorUseCase`
  originally grouped envelopes by source and processed each group to completion,
  silently breaking the hash chain's required global occurred_at-ordered append
  sequence whenever two sources' items interleaved chronologically (e.g. a day-4 Gmail
  message appended before a day-1 Zendesk ticket) — caught by running the full
  ledger's `verify_hash_chain()` for real, three times in a row, not by a single
  green test run. `specs/003-ingestion-and-context/research.md` documents the fix and
  the underlying "insertion order must match occurred_at order" invariant it protects.
- **2026-08-14** — Feature 004 (`score-engine`) specified, planned, tasked, analyzed (6
  remediations applied — a CRITICAL finding that `examples/01-end-to-end-walkthrough.md`
  §9.2's published Issue A rank order contradicts its own stated ranking rule), and
  implemented. All 29 tasks complete. Verified against the real, fully containerized
  stack via `scripts/seed_score_fixture.py` + `scripts/compute_score.py`, all three real
  recomputation triggers exercised live (`manual`, a forced `hourly_heartbeat` via the
  worker, `profile_edit_replay` via a real `/api/profile/reload` call), and the
  source-degraded freeze path against a real `coverage_reports` row — plus 71 backend
  pytest cases (up from 44 after feature 003, including `test_worked_example.py`'s
  full-precision reproduction of the worked example and two previously-skipped
  property-based placeholders, `test_reconciliation.py`/`test_monotonicity.py`, now
  real). Four genuine bugs found and fixed during verification, not by inspection: (1)
  the same `:param::type` SQLAlchemy bind-tokenizer corruption bug from feature 003,
  recurring in `resolve_lifecycle`'s `ANY(:cited_ids::uuid[])` clause; (2)
  `points_to_score` returning exactly `100.0` for extreme inputs when
  `e^(-total_points/33)` underflows to `0.0` in float64, violating REQ-M6-16 and
  `score_runs.score`'s DB `CHECK`; (3) `seed_score_fixture.py`'s synthetic CSAT event
  insert wasn't idempotent (unlike its sibling MVP-event resolver), and separately its
  `FIXTURE_PATH` constant walked up one directory too many, working by accident on a
  host checkout but breaking inside the container's mount layout; (4) a Clean
  Architecture violation (`app.scoring.domain.services` importing from
  `app.scoring.application.ports`), caught by `lint-imports`, fixed by relocating
  `FindingLifecycle` to `domain/entities.py`. Also caught, as a side effect of writing
  a real integration test: `tests/unit/test_simulated_collector.py` reused
  `ticket_number = 456` across test runs without uniquifying it (only `source_
  native_id` was suffixed), corrupting the shared, ticket-number-keyed
  `response_pairs` projection for any other ticket-456-dependent test — fixed by
  offsetting `ticket_number` too. `data-model.md`'s worked-example table pre-rounds
  `rank_within_issue_factor` to 2 decimals before multiplying for display, which
  doesn't match a full-precision implementation's output (`score = 85.63`, not the
  originally-published `85.64`) — corrected in `data-model.md` and `quickstart.md`.
- **2026-08-15** — Feature 005 (`deterministic-findings`) verified complete. All 37
  tasks implemented: five readers (Commitment, Usage, Recurrence, Absence,
  Relationship), `RunReadersUseCase` with per-reader failure isolation (FR-014a), and
  the long-deferred `rollups` computation (REQ-M2-06, unpopulated since feature 001).
  Independently verified against the real, already-running containerized stack, not
  just read: `lint-imports --config ../.importlinter` passes clean (3/3 contracts
  kept — confirms T035's no-AI-SDK-in-domain claim mechanically, not by inspection);
  28/28 pure-domain reader unit tests pass (Commitment, Usage, Absence, Relationship,
  Recurrence, purity check); 102/104 of the full backend suite
  (`golden_replay`/`readers`/`scoring`/`unit`, 104 tests total) pass against the live
  database. One genuine finding during verification, not blocking:
  `SqlAlchemyCandidateCorpusRepository.list_candidates()`
  (`backend/app/readers/adapters/sqlalchemy_repository.py`) assumes every
  `ticket_state_change` `created`/`reopened` event's `structured_payload` has a
  `title` key and raises `KeyError` if not — exercisable right now by two stray
  malformed rows already present in the shared dev database (`ticket_number` 518959
  and 500488, not part of the Meridian fixture, pre-existing this verification pass —
  consistent with leftover synthetic data from earlier property-based test runs
  against the same shared database, not a defect this feature introduced).
  `RunReadersUseCase`'s per-reader isolation (FR-014a) already contains the failure to
  Recurrence alone, exactly as designed, but the two failing rows are proof the
  assumption itself has no defensive fallback. Worth a `.get("title", ...)` hardening
  pass before feature 007 builds on top of this repository — not yet documented in
  `specs/005-deterministic-findings/research.md`, flagged here rather than silently
  patched, matching this roadmap's own standard for genuine findings (features
  003/004, above).
- **2026-08-15** — Feature 006 (`dashboard-evidence-trace`) specified, planned,
  tasked, analyzed (2 remediations applied before implementation — CV1: the
  evidence dispatch table had no fallback for `finding_type`s outside feature 005's
  five readers, a real crash risk against this deployment's own seeded demo data
  [`escalation_language`/`tone_deterioration`/`csat_deviation`]; CV2:
  `ClientHeader.days_to_renewal` had no documented data source), and implemented.
  All 52 tasks complete: `GET /api/dashboard` now returns the full
  `DashboardResponse` (score block, contribution bars, pulse timeline, stakeholder
  cards, coverage line, all seven `state` values with `base/...md` §11.5's exact
  copy) in place of feature 002's permanent shell; `GET /api/evidence/{id}` (this
  feature's namesake) reproduces `data-model.md`'s worked example exactly,
  including the generic fallback; `GET /api/coverage` backs a new system health
  screen. Verified against the real, freshly reset and fully re-ingested/scored
  Meridian database (fixture collection, all five feature 005 readers,
  `seed_score_fixture.py`'s nine-finding worked example, `compute_score.py`) via
  direct `curl` calls reproducing every contract example verbatim, 20 pure
  domain-service tests (state precedence, evidence dispatch, arithmetic
  formatting), 14 real-DB route tests, 15 frontend Vitest tests, and the full
  backend suite (134/137 passing, 2 expected skips). One test-ordering artifact,
  not a regression: `tests/readers/test_run_readers_use_case.py`'s "every finding
  is `pending_validation`" assertion fails once `seed_score_fixture.py` (feature
  004's demo script, which inserts `validated` rows directly) has also run against
  the same database — the two scripts were never designed to coexist in one
  ledger, and this verification pass is the first to run both in sequence. Two
  additional genuine findings, neither blocking: (1) `PulseEvent` and
  `StakeholderCard` both needed an additive field beyond
  `architecture/07-api-spec.md`'s originally-drafted schemas
  (`score_contribution_id`, and a nullable `stakeholder_id` for an unresolved-
  identity card) to actually satisfy FR-007/spec.md's own acceptance scenarios —
  documented inline in `ports.py`, not yet reflected back into the architecture
  doc itself; (2) `docker compose build api` fails (`hdbscan` needs a C compiler
  the builder stage's image lacks `gcc` for) — pre-existing since feature 005
  added `hdbscan`, not caused by this feature, but it blocked a full containerized
  Playwright E2E run this pass, so verification relied on a local uvicorn process
  against the real database instead. Worth a Dockerfile fix (add `gcc`/`build-
  essential` to the builder stage) before any feature next needs a containerized
  E2E run.
