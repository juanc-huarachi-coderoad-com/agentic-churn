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
| 007 | [`model-findings`](007-model-findings/) | 7 · Tone/Intent + validation gate | ✅ **Complete** — all 30 tasks implemented and verified against real Docker/Postgres, including four genuine bugs found and fixed (see Log) | `requirements/05-interpreters-readers.md` (Tone/Intent/M5a) | `architecture/04-ai-safety-and-model-usage.md`, `05-agent-catalog.md` |
| 008 | [`narrator-and-ask-agent`](008-narrator-and-ask-agent/) | 8 · Explanation layer | ✅ **Complete** — all 43 tasks implemented and verified against real Docker/Postgres, including a real layer-boundary violation and a golden-replay test-design bug, both found and fixed (see Log) | `requirements/07-narrator.md`, `09-ask-agent.md` | `sequences/02`, `decisions/03-langgraph-for-ask-agent.md` (Ask agent orchestration — decided ahead of this feature so `/speckit-plan` cites it rather than re-deciding it) |
| 009 | [`draft-composer`](009-draft-composer/) | 9 · The closer | ✅ **Complete** — all 36 tasks implemented and verified against real Docker/Postgres, including a `/speckit-analyze` remediation before implementation (5→3→5 checks, see Log) and one genuine regression found and fixed during implementation (see Log) | `requirements/10-draft-composer.md` | `sequences/04` |
| 010 | [`feedback-memory`](010-feedback-memory/) | 10 · Learning loop | ✅ **Complete** — all 31 tasks implemented and verified against a freshly rebuilt real Docker/Postgres stack, including a real duplicate-formula discovery and a `pattern_signature` doc/code mismatch found and fixed (see Log) | `requirements/04-feedback-memory.md` | `data-base/07`; `sequences/03` |
| 011 | [`production-hardening`](011-production-hardening/) | 11 · Hardening | ✅ **Complete** — all 68 tasks implemented and verified against a freshly rebuilt real Docker/Postgres stack, including a genuine crypto-shredding grant bug, two absence/relationship readers confirmed to need zero code changes, and a legacy-encryption regression in an unrelated pre-existing test found and fixed (see Log) | `requirements/11-non-functional-requirements.md`, `decisions/01-mvp-scope-and-phasing.md` | `data-base/10-ddl-appendix.md`, `architecture/04-ai-safety-and-model-usage.md` |

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
- **2026-08-15** — Feature 007 (`model-findings`) specified, clarified (1
  question — `findings.finding_type`'s hard FK into `finding_type_config` had
  no seeded row for two of Intent's three categories; resolved by seeding
  dedicated rows per category, not collapsing them onto `escalation_language`),
  planned, analyzed (7 findings — 1 HIGH: `spec.md`'s "supplied evidence
  window" edge case described a narrower check than anything in the design
  could actually implement, reconciled to a real-ledger-existence check; 6
  MEDIUM/LOW covering under-documented ports and a P5 constitution
  mis-classification, all fixed before implementation), and implemented. All
  30 tasks complete: `ToneReader` (baseline-relative deviation, abstains
  honestly below REQ-M6-CAL-04's 5-sample floor), `IntentReader` (closed-enum
  escalation/competitive/contractual classification), and the M5a
  `ValidationGate` — now wired into `RunReadersUseCase` for all eight readers,
  not just these two, closing the gap feature 005 deliberately left open
  (findings promoted past `pending_validation` for the first time).
  `AnthropicLLMAdapter` uses the Messages API's native `output_format`
  structured-output mechanism — no `tools` parameter ever passed, a stronger
  guarantee than the forced-tool-call design first proposed in `research.md`
  before checking current SDK docs. Verified against the real, freshly reset
  and re-provisioned Meridian database: the full nine-finding worked example
  (`examples/01-end-to-end-walkthrough.md`) reproduces end to end for the
  first time including both new LLM findings, all real and `validated`; every
  step of `quickstart.md` walked live via `curl` against the running
  containers (`GET /api/coverage`'s `quarantine` field real for the first
  time, a validated finding visible to `scripts/compute_score.py`); the full
  backend suite (155/157, 2 expected skips, up from 137 after feature 006)
  and `lint-imports --config ../.importlinter` (3/3 contracts kept) both pass
  clean. Four genuine bugs found and fixed during verification, not by
  inspection: (1) `SqlAlchemyCoverageReader.list_quarantine()`
  (`backend/app/experience/adapters/sqlalchemy_repository.py`) was still
  hardcoded to `return []` even with the gate wired in — `tasks.md` had
  wrongly assumed feature 006 needed no route-level change, when the route's
  contract was right but this one query was still a placeholder; (2)
  `RunReadersUseCase`'s gate-evaluate-then-persist step was unguarded by its
  own `try`/`except` (only each reader's `interpret()` call was) — an
  unexpected exception there would have silently skipped every reader still
  queued after the failing one; (3) a missing `ANTHROPIC_API_KEY` was
  initially caught and silently treated as per-message abstention inside
  `ToneReader`/`IntentReader`, unlike `RecurrenceReader`'s identical missing-
  `OPENAI_API_KEY` case, which reports a clear reader-level failure — fixed
  so a systemic misconfiguration can never look identical to a genuinely
  healthy, nothing-to-report run; (4) `SqlAlchemyCandidateCorpusRepository.
  list_candidates()`'s `KeyError` on a `title`-less malformed row — exactly
  the gap feature 005's own roadmap entry above flagged as "worth a
  `.get('title', ...)` hardening pass before feature 007 builds on top of
  this repository" — fixed now rather than deferred again. Also fixed, as a
  direct consequence of (2)/(4) surfacing through it: feature 004's
  `test_worked_example.py` reset routine did `DELETE FROM findings` without
  first clearing `quarantine`/`validation_failures`, an FK dependency that
  never actually fired against a real row until this feature became the
  first to populate either table. One pre-existing, non-blocking gap flagged,
  not fixed (out of this feature's scope): `ComputeRollupsUseCase` (feature
  005, REQ-M2-06) has no caller anywhere in the actual pipeline — only its
  own dedicated unit test invokes it — so `usage_deviation` will not appear
  from a real `scripts/run_readers.py` run against a freshly provisioned
  database until that use case is wired into the collector/readers flow
  itself.
- **2026-08-16** — Feature 008 (`narrator-and-ask-agent`) specified, clarified
  (2 questions — the "write to X about this" intent had no representable
  response shape in `AskComponentResponse`'s enum for a draft composer that
  doesn't exist until feature 009, resolved to a distinct `draft_handoff`
  response now carrying issue/stakeholder context; the "is this normal for
  X?" intent's insufficient-baseline-history failure mode was indistinguishable
  from `source_not_connected`, resolved to a new `insufficient_history`
  `declined_reason`), planned, analyzed (5 findings — 1 HIGH: `QueryFindingsTool`
  could have surfaced a quarantined finding through the Ask agent with no
  validated-only filter, closed before implementation; 4 MEDIUM/LOW covering
  a missing port in `data-model.md`, a stale `plan.md` artifact, an
  unbuilt SC-007 promise, and an under-tested REQ-M9-P3 assertion, all fixed),
  and implemented. All 43 tasks complete: the Narrator (`app.narrator`'s
  first real content — a mechanical fact-check discarding any unverifiable
  headline/reason/action, a deterministic non-LLM fallback headline when
  every candidate fails it) and the Ask agent (`LangGraphAskAgent`, the
  first and only compiled `StateGraph` in this codebase — classify → branch
  → {decline, fallback, handoff, resolve_and_render} → log → END, all 8
  REQ-M9-02 intents plus 5 `declined_reason` values live). Closes both
  dashboard gaps feature 006 explicitly deferred: `DashboardResponse.narrator`
  and the always-present Ask bar are both real for the first time. This is
  also the feature three prior Complexity Tracking tables (004, 005, 007)
  named as the one that would finally turn `tests/golden_replay/` from a
  skipped placeholder into a real, passing test — done, verified stable
  across 3 consecutive runs. Verified against the real, freshly built, fully
  containerized stack (`docker compose up --build -d`, not just the host
  venv): `GET /api/dashboard`'s new `narrator` field, `GET /api/coverage`'s
  new `ask_intent_coverage` field, and `POST /api/ask`'s first real
  implementation (failing honestly inside the container without a live
  `ANTHROPIC_API_KEY`, the same as on the host) all confirmed live; full
  backend suite (201 tests total, up from 157 after feature 007) and
  `lint-imports --config ../.importlinter` (3/3 contracts kept) both pass in
  isolation; frontend `lint`/`typecheck`/`test` (19/19)/`build` all clean.
  Six genuine bugs found and fixed during implementation, not by inspection:
  (1) the fact-check's proper-noun extraction treated every sentence's own
  leading word as a claimed name if capitalized, so any action beginning
  with an imperative verb ("Escalate the ticket...") was discarded every
  time — found by running the use case against real playbook/contribution
  data, not a synthetic test case; fixed by excluding the sentence's leading
  word from name-candidates, a documented trade-off (a genuine name that
  opens a sentence is now also exempted); (2) `ask_queries.matched_intent`
  was being set to `"prediction"`/`"colleague_judgment"` on decline paths,
  contradicting `data-base/08-schema-experience.md`'s own worked example
  (`matched_intent = NULL` for "Will Meridian actually cancel?") — found
  while writing the branch-coverage tests, fixed with a shared
  `_matched_intent_value()` helper; (3) `narration_v1.py` (the prompt
  template + `NarrationModelOutput` schema) was originally placed in
  `app.narrator.adapters.prompts`, and `app.narrator.application.use_cases`
  imported it directly — a real `import-linter` violation
  (`application is not allowed to import adapters`) only caught by actually
  running `lint-imports`, not by writing the code; fixed by moving it to
  `app.narrator.application.prompts`, matching `IntentReader`'s own
  precedent from feature 007; (4) the golden-replay test's first draft
  compared a fresh post-replay rebuild against *ambient* pre-existing
  `event_threads`/`response_pairs`/`rollups` counts and failed spuriously (7
  vs 22 threads) — this suite runs against a shared, cumulative dev database
  many other test files also append real events to; fixed by establishing a
  fresh baseline via one rebuild first, then comparing a second rebuild
  against that, not against ambient state; (5) `docker compose build api`
  alone does not rebuild the separately-tagged `migrate` image sharing the
  same Dockerfile, so a fresh migration silently ran against a stale image
  with no migration file — found by actually running `docker compose up`
  end to end, not assumed from a single service's build; (6) the originally
  planned `alembic` revision id (`0002_declined_reason_insufficient_history`)
  didn't fit `alembic_version.version_num`'s `VARCHAR(32)` column, caught
  only by actually running the migration against a real database — shortened
  to `0002_ask_insufficient_history`. One pre-existing, non-blocking gap
  flagged, not fixed (entirely outside this feature's scope): 6
  `tests/scoring/test_recompute_score_use_case.py` cases fail only when the
  full suite runs together, never in isolation — a `score_runs.score` value
  rounds to exactly `100.00` at column precision for that test file's own
  large synthetic point totals, violating `CHECK (score < 100)`; entirely
  within `backend/app/scoring/` (feature 004's module), which this feature
  never touches.
- **2026-08-16** — Feature 009 (`draft-composer`) specified, clarified (3
  questions — no in-app editing, since `data-model.md`'s `draft_messages`
  has no edited-text column and REQ-M10-08 names exactly two actions; "any
  issue with cited evidence" is draftable, not only the top-ranked one,
  since `DraftRequest.issue_id` is a generic contract parameter; a
  pre-display-check failure shows the exact same generic message a
  generation timeout already defines, never one naming which check failed),
  planned, analyzed (9 findings — 3 HIGH: SC-003's discount/blame guarantee
  and REQ-M10-P3's "invented causes" half both had zero mechanical
  verification, and SC-004's "code-level review" had no task; 6 MEDIUM/LOW
  covering a missing stakeholder-existence check, an unenforced "exactly
  one ask" claim, an overclaiming tone-variant success criterion, an
  undocumented exception type, and FR-017's task-invisible rationale — all
  fixed before implementation, growing the pre-display check pipeline from
  three functions to five: `verify_no_invented_cause` and
  `verify_no_concession` joined `verify_facts`/`verify_dates`/
  `verify_no_leak`), and implemented. All 36 tasks complete: `GenerateDraftUseCase`
  (`backend/app/experience/application/use_cases.py`, alongside
  `GetDashboardUseCase`) reads a requested issue's own aggregated evidence
  (a new `IssueReadPort`), the client profile's `communication_norms` (one
  additive field on the already-existing `ClientProfileRecord`), real
  thread history (feature 008's `LedgerQueryPort`, reused unchanged), and
  the latest run's already-narrated actions filtered to the issue's own
  finding types (`research.md` Decision 4) — generates via the same
  `LLMPort`/`GENERATION_MODEL_ID` the Narrator and Ask agent already use,
  and persists only once all five checks pass. Zero migrations —
  `draft_messages` and the `tone_variant` enum have existed, unpopulated,
  since feature 001. Verified against the real, freshly built, fully
  containerized stack (`docker compose up --build -d`): `POST /api/drafts`
  fails honestly with the same `ANTHROPIC_API_KEY` error inside the
  container as narrator/ask-agent already do (proving the wiring, not just
  the business logic); `.../copy`, `.../log-as-sent`, and a live `/send`
  probe all return exactly the documented status codes; 13/13 real-DB
  integration tests pass against the real "Issue A"/Ana Reyes fixture,
  including a scripted red-team case per check; the full backend suite
  (241 tests total, up from 201 after feature 008) and `lint-imports
  --config ../.importlinter` (3/3 contracts kept, confirming the new
  `experience.domain`→`narrator.domain` cross-module import doesn't violate
  the layer boundary) both pass; frontend `lint`/`typecheck`/`test`
  (23/23, up from 19)/`build` all clean. One genuine regression found and
  fixed during implementation, not by inspection: adding
  `StakeholderReadPort.get()` (closing `/speckit-analyze` finding U3) broke
  an existing feature-008 test fake
  (`tests/experience/test_ask_agent_toolkit.py`'s `_FakeStakeholders`,
  which had no implementation for the new abstract method) — caught by
  running the full suite, not just this feature's own tests, and fixed by
  extending the fake rather than weakening the port. One genuine test-
  fixture bug found while writing this feature's own tests, not a code
  bug: a fake draft text using a mid-sentence capitalized common word
  ("Ana — Engineering is on it today.") reproduced the exact same
  leading-word-exclusion limitation feature 008 already documented for the
  Narrator's `fact_check` — `verify_facts` correctly failed it, and the
  fixture was reworded rather than the check weakened. Two pre-existing,
  non-blocking gaps confirmed unrelated to this feature during full-suite
  verification, not fixed (out of scope): the same 6
  `tests/scoring/test_recompute_score_use_case.py` score-rounding failures
  this roadmap already flagged for feature 008, plus one newly-observed
  `tests/readers/test_run_readers_use_case.py` failure (a `recurring_issue`
  finding citing only 1 event instead of the expected 2+) that reproduces
  only when run after `tests/scoring/test_worked_example.py` has already
  mutated the same shared, cumulative dev database in this session — both
  entirely within `backend/app/scoring/`/`backend/app/readers/` (features
  004/005/007's modules), which this feature never touches.
- **2026-08-16** — Feature 010 (`feedback-memory`) specified, clarified (2
  questions — `pattern_signature`'s composition, later corrected during
  `/speckit-plan` once the already-shipped scoring engine's real code was
  read (see below); an issue-scoped verdict never needs to fan out across
  several readers' patterns, since `false_alarm`/`correct` always require
  a specific `finding_id` and issue-scoped verdicts are effectively always
  `resolved`, which REQ-M6-CAL-03b already guarantees never touches
  weight), planned, analyzed (4 findings — 2 HIGH: `plan.md`'s Project
  Structure tree still showed a nonexistent `tests/context/` directory
  after `tasks.md` had already corrected it to the real `tests/unit/`
  convention, and the static no-LLM-import scan (T029) was scoped only to
  `app/context/` despite this feature also touching `app/experience/`/
  `app/scoring/`; 2 MEDIUM: a confusing double-priority phase header, and
  FR-004/FR-009 having no task or "intentionally absent" note unlike
  REQ-M4-P1/P2 — all fixed before implementation), and implemented. All 31
  tasks complete: `RecordFeedbackVerdictUseCase` lands inside `app.context`
  (M4's designated home per `decisions/02-repo-and-tooling.md`, alongside
  M3) with its own pure `damping_calculator.py`
  (`pattern_signature`/`compute_weight`/`build_disclosure_text`,
  REQ-M6-CAL-03a/b); `POST /api/feedback` is real for the first time;
  `GET /api/evidence/{id}` gains a live `disclosure_text` field; and
  `EvidencePanel` (`frontend/src/evidence/evidence-panel.tsx`) gets its
  first real verdict controls, closing the exact slot feature 006's own
  comment reserved for this feature ("no feedback controls here — feature
  010's job"). The Ask agent's `delta_breakdown`/`ranked_issues` answers
  now click through to that same panel via a field (`score_contribution_id`)
  their backend response already sent but the frontend never read — zero
  new backend surface needed for that wiring. Verified against a
  completely fresh, rebuilt stack (`docker compose down -v` +
  `up --build -d`, then `scripts/seed.py` → `run_collector.py` →
  `seed_score_fixture.py` → `compute_score.py`, the same bootstrap
  sequence feature 004's quickstart documents): every step of
  `quickstart.md` walked live via `curl` against the real running `api`
  container — `weight` moving `1.000 → 0.500 → 0.250 → 0.2875` exactly on
  REQ-M6-CAL-03a's worked values (stored as `0.287` at
  `damping_weights.weight`'s own `NUMERIC(4,3)` precision), the matching
  `disclosure_text` wording, a pre-existing `score_run` staying
  byte-identical after a fresh recompute while that same fresh run's
  `score_contributions.damping` read the new weight live and the
  dashboard score moved `91.82 → 71.60` as a direct, observed
  consequence, and REQ-M4-P2/FR-005a's `422` rejection of an
  issue-only `false_alarm`; 148 backend tests + a dedicated 8-test
  real-DB feedback suite + 25 frontend tests all pass, and
  `lint-imports --config ../.importlinter` keeps all 3 contracts clean
  with the two new cross-module `domain`→`domain` imports this feature
  adds (`app.scoring.application`→`app.context.domain` for
  `pattern_signature`, `app.experience`→`app.context.domain` for the
  same). Two genuine findings, not by inspection: (1) `data-base/
  07-schema-feedback.md` documented `pattern_signature` as
  `reader_type+finding_type+event_signature_class` (three components) —
  found false during `/speckit-plan`, before any code was written, by
  reading feature 004's actual shipped `RecomputeScoreUseCase` source
  rather than trusting the prose doc: it constructs and reads the key as
  literally `f"{reader_type}+{finding_type}"`, two components, with no
  event-type join at all. Building a three-component writer against a
  two-component reader would have made every `damping_weights` lookup
  miss silently, so this feature follows the shipped format instead —
  `spec.md`'s Clarifications entry and `data-base/07-schema-feedback.md`'s
  own prose were both corrected in place. (2)
  `app.scoring.domain.services.DampingCalculator` already existed —
  feature 004 built and unit-tested the identical REQ-M6-CAL-03a formula
  ahead of time, but nothing in production ever called it. Found via a
  pytest test-basename collision (`tests/scoring/test_damping_
  calculator.py` vs. this feature's own new test file of the same name),
  not by inspection; this feature's `compute_weight()` now delegates to
  that pre-existing class instead of reimplementing the arithmetic a
  second time, removing a real duplication before it could silently
  drift — the same "one canonical implementation" reasoning already
  applied to `pattern_signature` itself. One pre-existing, non-blocking
  gap reconfirmed unrelated to this feature during full-suite
  verification: the same `tests/readers/test_run_readers_use_case.py`
  `recurring_issue`-citing-only-1-event failure this roadmap already
  documented for feature 009, reproducing again for the identical reason
  (the shared, cumulative dev database's `tests/scoring/` suite mutating
  state before `tests/readers/` runs in the same session) — not touched by
  this feature's own module boundaries.
- **2026-08-17** — Feature 011 (`production-hardening`) specified, clarified
  (3 questions: daily retention cadence, admin-only weight authorization,
  alert + auto-retry on retention failure), planned, tasked (71 tasks
  across 6 user stories), analyzed (9 findings, all suggested and applied
  before implementation — FR wording corrections, a clarified FR-008
  audit mechanism, a softened Edge Cases claim), and implemented. All 71
  tasks complete (Polish's T068 folded into this entry).

  **User Story 1 (retention/crypto-shredding)**: daily key-rotation
  buckets (`FileKeyStore`) + a real `RunRetentionUseCase`/
  `retention_job_runs` audit trail. Two genuine bugs found only by running
  the job against a real Postgres, not by inspection: an earlier draft
  granted `shredder_role` `UPDATE`/`SELECT` on `raw_envelopes` for a
  mistaken reason (the DDL's own note already says destroying the key
  alone suffices there — no row ever needs touching); and Postgres
  rejected the shredder's own `UPDATE ... WHERE data_key_ref = ... AND
  body_encrypted IS NOT NULL` with `InsufficientPrivilegeError` until a
  `SELECT (data_key_ref, body_encrypted)` grant was added — Postgres
  requires read access to every column a `WHERE` clause references, not
  only the column being written.

  **User Story 2 (RBAC) / User Story 4 (weight recalibration)**:
  `require_full_access`/`require_admin` FastAPI dependencies gate
  `account_executive` (read-only) and `admin` (weight edits) respectively,
  each emitting a structured `access_decision` log line (FR-008) rather
  than a new schema column, since `users.role` is mutable and the record
  needs the role *as it was at the moment of the decision*.

  **User Story 3 (observability)**: `app.observability` (adapters-only,
  no domain/application rings — there is no business rule here) wraps the
  collector run and each reader's execution in OTel spans via an async
  `BatchSpanProcessor`, verified to never block the caller when the
  configured OTLP endpoint is unreachable (FR-012).

  **User Story 5 (profile editor)**: `POST /api/profile` accepts
  `ClientProfileInput` directly — the exact same Pydantic model
  `load_profile_yaml` already builds, so a JSON submission gets
  byte-identical validation with no separate request model to keep in
  sync. `frontend/src/profile-editor/` (React Hook Form + Zod, a
  `.gitkeep` placeholder scaffolded all the way back in feature 001)
  built out for the first time.

  **User Story 6 (Post-MVP sources)**: three normalize functions
  (`_normalize_slack`/`_normalize_csat`/`_normalize_calendar`) extend
  `SimulatedCollector`; a new `MeetingReader` activates for consented
  transcripts. Three real, plan-vs-actual corrections found by reading the
  shipped code rather than trusting the docs: (1) the fixture is a single
  **flat array** with a per-item `source_type` discriminator, not the
  nested per-source arrays `data-model.md`/`research.md` both assumed —
  new items follow the real shape; the original content is preserved
  verbatim as `meridian-week-phase1-only.json` for the FR-024 regression
  check. (2) `absence_reader.py`/`relationship_reader.py` need **zero**
  code changes — both already query the source-agnostic `events` table
  with no `source_type` filter, so a Slack-sourced event counts as
  "contact"/"activity" automatically; `usage_reader.py`'s orchestration
  and `SqlAlchemyMessageEventRepository`'s SQL, by contrast, genuinely
  needed extending (CSAT scores as a `stakeholder`-scoped rollup routing
  to a `csat_deviation` finding_type — a seeded config row that had sat
  unused since Phase 1 — and CSAT written comments joining Tone/Intent's
  shared corpus). (3) `"calendar"` as a `source_type` value was already
  claimed by `DetectAbsenceUseCase`'s internal absence-monitor events
  (feature 005) — the new Calendar/transcripts source uses the DDL's
  separate `"transcripts"` enum value instead, avoiding a silent
  `sources`-row collision. FR-023's consent gate ("SHALL NEVER collect a
  transcript" — stronger than "the reader abstains on it") is enforced
  once, at `SimulatedCollector.fetch()`, confirmed live against the real
  database across 11 accumulated collector runs: zero `raw_envelopes` rows
  ever exist for the non-consented series, while the consented one
  persists every time.

  **Verified against a freshly rebuilt real Docker/Postgres stack**
  (`docker compose down -v` → `up -d` → `alembic upgrade head` →
  `scripts/seed.py`, repeated several times to separate real regressions
  from noise): `GET /api/coverage` live via `curl` showing `slack`/
  `csat`/`transcripts` as connected sources after a real
  `run_collector.py` run (19 envelopes); `GET /api/dashboard`
  200-for-`account_executive` / `POST /api/feedback` 403-for-the-same;
  `PATCH /api/admin/finding-types/...` 403-for-`cs_lead` /
  200-for-`admin`; `GET /api/profile` reflecting the real seeded Meridian
  profile; `scripts/run_readers.py` showing `MeetingReader` correctly
  registered and failing honestly (no `ANTHROPIC_API_KEY` configured in
  this environment) in isolation from the other seven readers, exactly
  matching Tone/Intent's own established precedent (FR-014a). 324 backend
  tests pass (25 skipped — no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`
  configured), including 11 new/extended tests for User Story 6 across
  `test_simulated_collector.py`, `test_meeting_reader.py`,
  `test_usage_reader.py`, and a new `test_post_mvp_sources_real_db.py`.
  `lint-imports` keeps all 3 contracts clean; `mypy` reports the same 6
  pre-existing, unrelated errors it did before this feature (zero new).

  **One genuine bug found and fixed, unrelated to this feature's own new
  code but surfaced by its clean-slate verification**:
  `tests/narrator/test_run_narrator_real_db.py` still constructed the
  legacy single-key `FernetEncryption` directly instead of
  `BucketedFernetEncryption` — every event body has been bucket-encrypted
  since this feature's own User Story 1, so on a truly fresh database
  (no leftover pre-bucketing rows the shared dev DB had quietly been
  carrying) all 3 of that file's tests failed with `EncryptionKeyError`.
  Fixed to match every other test/script in the codebase.

  **Pre-existing, out-of-scope fragility reconfirmed, not touched by this
  feature**: a full from-scratch suite run still shows 5 failures —
  `test_hash_chain.py`, `test_run_readers_use_case.py`'s first test,
  `test_worked_example.py`, `test_absence_collector.py`, and a
  business-hours-rounding boundary flake in `test_replay.py` — the same
  family of full-suite test-ordering/non-floor-anchored-fixture issues
  already investigated and documented at this feature's own User Story 1
  checkpoint (git-stash-verified against unmodified code). None touch any
  Post-MVP file; confirmed by running `tests/ingestion tests/unit
  tests/readers` together from a fresh reset, where only
  `test_hash_chain.py` and the one `test_run_readers_use_case.py` test
  remain and every Post-MVP-specific test passes cleanly. Also surfaced
  along the way (left as-is, cross-feature, not this feature's to fix):
  the shared dev database's current `client_profile_versions` row
  (submitted by earlier User Story 5 testing) carries no `recurring_sync`
  commitment, silently starving `DetectAbsenceUseCase`'s own test — a
  User Story 5 test-isolation gap, not a User Story 6 one.
