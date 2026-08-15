# Implementation Plan: Score Engine

**Branch**: `004-score-engine` *(no dedicated branch — no `before_specify` git hook is configured; this work continues on the current branch, same as features 001–003)* | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-score-engine/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build M6 (scoring engine) for real: five domain services (`ScoringCalculator`,
`BandClassifier`, `DampingCalculator`, `AgeingCalculator`, `IssueGrouper` —
`architecture/09-clean-architecture-and-patterns.md`'s already-named pattern catalog for
this exact module) compute a finding's weighted contribution, rank it within its issue,
age it by state, cap positive signals, convert points to a saturating 0–100 score, and
classify a hysteresis-protected band — all deterministic, zero LLM calls anywhere in the
path. Proven against a hand-authored fixture reproducing `examples/01-end-to-end-
walkthrough.md` §9's 9-finding worked example, corrected for a rank-order
inconsistency found in that document during `/speckit-analyze` (`research.md`; score
85.64, band `at_risk`), since no reader module (feature 005) or validation gate
(feature 007) exists yet to produce findings automatically. Technical approach: build
into `backend/app/scoring/{domain,
application,adapters}/`, already scaffolded empty by feature 001, following
`architecture/09`'s exact file layout for this module rather than inventing a new one.

## Technical Context

**Language/Version**: Python 3.12 (backend) — unchanged from features 001–003

**Primary Dependencies (new in this feature)**: None beyond what's already installed —
`hypothesis` (property-based testing for reconciliation/monotonicity) has been a dev
dependency since feature 001; no production dependency is new, matching REQ-M6-P1's "no
model call anywhere" — this is the one module with the *shortest* dependency list, on
principle (P2, `.importlinter`'s `scoring-domain-purity` contract).

**Storage**: PostgreSQL 16 — no schema change; `findings`, `finding_type_config`,
`issues`, `finding_issue_map`, `quarantine` (`data-base/05-schema-reasoning.md`),
`score_runs`, `score_contributions`, `band_history` (`data-base/06-schema-scoring.md`)
all already exist from feature 001's migration. This feature is the first to write the
latter three for real, and the first to read `findings`/`issues`/`finding_issue_map` —
via a hand-authored fixture, not reader output.

**Testing**: pytest + `hypothesis` — the worked-example reproduction (exact per-finding
and per-run decimal values, `spec.md` User Story 1), property-based reconciliation
(`tests/scoring/test_reconciliation.py`, thousands of generated `score_runs` states,
REQ-NFR-30) and monotonicity (`tests/scoring/test_monotonicity.py`, thousands of
generated cases plus one additional negative finding, REQ-NFR-31) tests — both already
scaffolded as skipped placeholders since feature 001, filled in for real by this
feature — plus unit tests per domain service (recency by state, hysteresis/stickiness,
damping, rank-within-issue, stakes).

**Target Platform**: Same Docker Compose stack as features 001–003; no new service, no
new container — scoring runs inside the existing `api`/`worker` processes

**Project Type**: Backend-only for this feature — no frontend work (this feature adds
no new API route, `research.md`'s Decision below)

**Performance Goals**: Not directly measured in this feature — REQ-M6-21's "~40s
end-to-end" latency target applies specifically to the `new_event` trigger, which is
explicitly out of scope here (no live reader pipeline exists yet to generate that
trigger); this feature's own recompute (`manual`/`hourly_heartbeat`/
`profile_edit_replay`) has no comparable real-time budget to hit

**Constraints**: `REQ-M6-P1` — never a model call anywhere in the scoring path, the one
constraint this whole module exists to prove, enforced by the already-existing
`.importlinter` `scoring-domain-purity` contract (feature 001) with no change needed;
`REQ-M6-P2` — the previous score is never read as an input to the new one;
`REQ-M6-P3`/`REQ-M6-P4` — the 25% positive cap and monotonicity are structural
properties of the arithmetic, not runtime checks bolted on after

**Scale/Scope**: Fixture-driven for this feature (9 hand-authored findings across 2
issues + 1 standalone, matching `examples/01` §9 exactly) — REQ-NFR's ~50k–200k
events/year scale target is a ledger-layer (feature 003) concern; this feature's own
scale is bounded by finding count per account, which stays small (tens, not thousands)
even at full production maturity, so no batching/pagination concern exists here

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| P1 Evidence or It Does Not Exist | Indirectly — `findings.cited_event_ids`'s non-empty `CHECK` is what makes this real (feature 001's DDL); this feature reads that constraint's guarantee, doesn't enforce it itself | N/A this phase (already enforced upstream) |
| **P2 The Model Interprets, Code Calculates** | Yes — this is the module P2 was written about | **Pass** — zero LLM imports anywhere in `backend/app/scoring/`; `.importlinter`'s existing `scoring-domain-purity` contract already covers it, no change needed |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — the scoring engine computes, never judges beyond arithmetic; it does not decide what counts as a finding (that's M5/M5a) | **Pass** — FR-001..016 are all deterministic arithmetic/persistence, nothing interpretive |
| P4 A Human Always Sends | No send capability anywhere in this feature | N/A |
| **P5 Admit What We Cannot See** | Yes — a degraded source must freeze the score visibly, never compute silently on an incomplete picture | **Pass** — FR-011, `is_frozen`/`source_degraded` columns already exist (feature 001's DDL), this feature is the first to set them |
| **P6 Silence Is a Success State** | Yes — a healthy account's score should rest at a low, unremarkable value, not manufacture concern | **Pass** — Edge Cases: zero findings → score 0, `band = healthy`, the formula's natural resting state, not a special-cased branch |
| P7 Context Over Sentiment | No sentiment/tone computation in this feature (that's the Tone reader, M5) | N/A |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — `scoring/{domain,application,adapters}` follows the exact three-ring shape and file layout `architecture/09` already names for this module | **Pass** — `.importlinter`'s `global-dependency-rule` contract already lists `app.scoring`; no config change needed, only the code to fill it |
| **P9 Test-First Determinism** | Yes — this feature fills in the two property-based tests (reconciliation, monotonicity) `tests/strategy.md` names as this module's own acceptance gates, already scaffolded skipped since feature 001 | **Pass, with a noted exception** — see Testing above; the full cross-module golden-replay test stays skipped (needs readers + narrator, features 005/008 — see `research.md`), which is in tension with Governance's literal "a passing golden-replay run before merge" clause for any PR touching `backend/app/scoring/` — see Complexity Tracking below for the justification, rather than silently asserting Pass against that specific clause |
| P10 Simplicity Over Speculative Generality (YAGNI) | Yes — no plugin system for scoring formulas (fixed by spec), no generic "rule engine," `stakes` gets one small function, not a new named service, since it's one multiplication | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | N/A — no frontend surface in this feature | N/A |
| Full-Stack §4 Testing Strategy | Yes — first feature with real domain-service unit tests at this density (5 named services) | **Pass** — each of `ScoringCalculator`/`BandClassifier`/`DampingCalculator`/`AgeingCalculator`/`IssueGrouper` gets a dedicated test file; see `tasks.md` |
| Full-Stack §5 Security & Quality Gates | N/A — no user input, no external call, no new attack surface in this feature | N/A |

**One noted exception, justified below** (found during `/speckit-analyze`) — see
Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-score-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — entity/relationship notes beyond the schema docs
└── quickstart.md         # Phase 1 output — fixture load + score computation validation guide
```

No `contracts/` directory — this feature adds no new API route or external interface
(`spec.md`'s own scope boundary: `GET /api/dashboard`, feature 006, is the first and
only consumer-facing surface for score data). Matches the plan template's own guidance
to skip contracts for a purely internal component.

### Source Code (repository root)

Builds into `backend/app/scoring/`, scaffolded empty by feature 001 — following
`architecture/09-clean-architecture-and-patterns.md`'s exact, already-named file layout
for this module (not a new structure invented by this feature):

```text
backend/
├── app/
│   ├── scoring/
│   │   ├── domain/
│   │   │   ├── entities.py           # Finding, Issue, ScoreRun, ScoreContribution —
│   │   │   │                          #   defined once, here, per architecture/09
│   │   │   │                          #   ("scoring.domain owns Finding's lifecycle,
│   │   │   │                          #   since ScoringEngine is what changes its state")
│   │   │   └── services.py           # ScoringCalculator, BandClassifier,
│   │   │                              #   DampingCalculator, AgeingCalculator,
│   │   │                              #   IssueGrouper (architecture/09's named
│   │   │                              #   pattern catalog) + compute_stakes() (FR-012,
│   │   │                              #   one function, not a 6th named class — P10)
│   │   ├── application/
│   │   │   ├── ports.py              # FindingRepositoryPort, ScoreRunRepositoryPort
│   │   │   │                          #   (architecture/09), ClientProfileMultipliersPort,
│   │   │   │                          #   DampingRepositoryPort, CoverageCheckPort —
│   │   │   │                          #   new, scoring-scoped ports reading the same
│   │   │   │                          #   underlying tables feature 003's ports read,
│   │   │   │                          #   for a different query shape (multipliers vs.
│   │   │   │                          #   calendar/exclusions) — no cross-module
│   │   │   │                          #   adapter import either way (constitution P8)
│   │   │   └── use_cases.py          # RecomputeScoreUseCase (architecture/09)
│   │   └── adapters/
│   │       └── sqlalchemy_repository.py  # SqlAlchemyFindingRepository,
│   │                                       #   SqlAlchemyScoreRunRepository
│   │                                       #   (architecture/09), plus the three
│   │                                       #   smaller port implementations above
│   └── worker.py                     # updated: hourly heartbeat also triggers
│                                      #   RecomputeScoreUseCase (extends feature 003's
│                                      #   absence-collector job registration)
├── app/context/application/use_cases.py  # updated: SubmitProfileUseCase triggers
│                                           #   RecomputeScoreUseCase after replay
│                                           #   completes (REQ-M6-25) — same file
│                                           #   feature 003 already owns
├── scripts/
│   ├── seed_score_fixture.py         # Applies the hand-authored findings/issues
│   │                                   #   fixture (research.md's Decision) — separate
│   │                                   #   from scripts/seed.py's real-deployment seed
│   └── compute_score.py              # Manual RecomputeScoreUseCase trigger, mirroring
│                                       #   scripts/run_collector.py's pattern
└── tests/
    ├── scoring/
    │   ├── test_reconciliation.py    # filled in for real (was a skipped placeholder)
    │   ├── test_monotonicity.py      # filled in for real (was a skipped placeholder)
    │   ├── test_scoring_calculator.py
    │   ├── test_band_classifier.py
    │   ├── test_ageing_calculator.py
    │   ├── test_damping_calculator.py
    │   ├── test_issue_grouper.py
    │   └── test_worked_example.py    # User Story 1 — exact reproduction of
    │                                   #   examples/01 §9's published numbers
    └── unit/
        └── test_recompute_score_use_case.py

demo/
└── fixtures/
    └── score-engine-findings.json    # New — the hand-authored findings/issues fixture
                                        #   (research.md's Decision), JSON + a Python
                                        #   script (not static SQL — cited_event_ids
                                        #   need runtime resolution against real ledger
                                        #   rows), mirroring demo/fixtures/meridian-
                                        #   week.json + SimulatedCollector's pattern
                                        #   from feature 003; separate from
                                        #   data-base/11-seed-data.sql's real-deployment
                                        #   seed data
```

**Structure Decision**: Same monorepo, extending `scoring/` — the module folder
`decisions/02-repo-and-tooling.md`'s map and `architecture/09`'s updated package layout
both assign M6 to — with real code for the first time. No new top-level directories, no
new Docker service.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| `tests/golden_replay/test_placeholder.py` stays `@pytest.mark.skip` for this feature, in tension with the constitution's Governance clause requiring "a passing golden-replay run before merge" for any PR touching `backend/app/scoring/` | That test's own documented procedure (`tests/strategy.md` §Golden-replay tests) requires feeding the ledger fixture through real readers to produce findings automatically, then through the Narrator for `narrator_outputs` — neither exists until features 005/008. No code in this feature (or any feature before 005/008) can make that specific test pass for real | Building throwaway reader/narrator stubs just to flip this test green would be speculative generality (P10) and would itself need to be un-built later, for a test whose real purpose (proving the *actual* pipeline replays byte-identically) a stub can't honestly demonstrate. This feature substitutes its own real, scoped determinism guarantee instead — `test_worked_example.py` asserts `RecomputeScoreUseCase` run twice against identical input produces byte-identical `score_contributions` (`spec.md` SC-006) — which is the same property the golden-replay test asserts, just bounded to this module's own inputs rather than the full ledger→reader→score→narrator chain. The full cross-module test is expected to go green naturally once feature 008 (Narrator) lands, with no further justification needed at that point |
