# Implementation Plan: Automated Pipeline Orchestration

**Branch**: `main` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/026-automated-pipeline-orchestration/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a fifth APScheduler job to `backend/app/worker.py` — alongside the four already there
(absence detection, score recompute, retention, audio collector) — that closes the one real gap
left in this pipeline's automation: `RunReadersUseCase` and `NarrateScoreRunUseCase` are wired in
for the first time, on a 30-second poll (`research.md` Decision 3) gated by an in-memory
high-water-mark on `events.created_at` (Decision 2) so a quiet account costs nothing (P6, FR-004).
No message broker, no `LISTEN`/`NOTIFY` (Decision 1) — same primitive the existing jobs already
use. Score recompute inside this new cycle uses the schema's own already-defined-but-unused
`new_event` trigger value (Decision 4); narration's existing "nothing to narrate" behavior already
satisfies FR-009 with zero new logic (Decision 5); overlap prevention (FR-006) is APScheduler's
own default behavior, verified against this project's installed version (Decision 6). The existing
manual scripts (`scripts/run_readers.py`, `scripts/run_narrator.py`) are untouched — they remain
real, independent verification tools, not replaced.

## Technical Context

**Language/Version**: Python 3.12 — unchanged; this feature only adds one function and one
`scheduler.add_job()` call to an existing file.

**Primary Dependencies**: None new. Reuses `apscheduler` (already a dependency, already imported
in `worker.py`), and the already-existing `RunReadersUseCase`/`NarrateScoreRunUseCase`/
`RecomputeScoreUseCase` application classes and their existing `SqlAlchemy*Repository` adapters —
the exact same set `backend/scripts/run_readers.py`/`run_narrator.py`/`compute_score.py` already
construct, assembled inside `worker.py` instead of a standalone script.

**Storage**: PostgreSQL 16 — no schema change. `research.md` Decision 4 reuses an already-defined,
currently-unused `score_trigger` enum value (`new_event`); Decision 2's high-water-mark is
in-process memory, not a new column/table.

**Testing**: pytest, matching the existing suite's real-DB integration style (e.g.
`tests/unit/test_simulated_collector.py`'s "assert against the real, running Postgres" discipline)
for the new orchestration function, plus the existing golden-replay/reconciliation/monotonicity
suite unchanged (P9) — this feature adds a new caller of already-tested use cases, it does not
change any of their internals, so no new property-based tests are needed beyond confirming the
new job's own skip/run/order logic.

**Target Platform**: Same Docker Compose `worker` service (`docker-compose.yml`) already running
`python -m app.worker` — no new service, no new port, no new container.

**Project Type**: Web application backend (Python/FastAPI) — this feature touches only
`backend/app/worker.py` and its own test coverage; no frontend change.

**Performance Goals**: `requirements/11-non-functional-requirements.md` REQ-NFR-02 — event to
updated score within ~40s typical, 60s cap. The 30-second poll interval (Decision 3) leaves
headroom under that cap for the pipeline's own execution time.

**Constraints**: Must preserve `RunReadersUseCase`'s existing per-reader failure isolation (FR-005)
and the existing golden-replay/reconciliation/monotonicity guarantees (P9) exactly as they behave
today — this feature is purely a new *caller* of existing, unmodified use cases.

**Scale/Scope**: One new function (`_run_pipeline_orchestration` or similar) plus one new
`scheduler.add_job(...)` call and one new `--run-once` entry in `backend/app/worker.py`. No other
file changes except this feature's own test file and `specs/ROADMAP.md`/`CLAUDE.md` pointers.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| P1 Evidence or It Does Not Exist | No | No change to how findings cite evidence — this feature only changes *when* the existing readers run, not what they produce. |
| P2 The Model Interprets, Code Calculates | No | Scoring arithmetic (`RecomputeScoreUseCase`) is called unchanged; this feature adds no code to `backend/app/scoring/`. |
| P3 Each Component Refuses to Do the Next One's Job | Yes | The new job is a pure orchestrator (call readers, then recompute, then narrate, in order) — it contains no reader logic, no scoring logic, no narration logic of its own, exactly mirroring `_run_score_recompute`'s existing shape (a thin composition-root function, not a reimplementation). |
| P4 A Human Always Sends | No | No send capability touched — narration output still only ever reaches the dashboard, never sent anywhere. |
| P5 Admit What We Cannot See | No | No change to coverage/degraded-state reporting. |
| **P6 Silence Is a Success State** | **Yes — this is the feature's second-highest-priority requirement (User Story 2).** | The high-water-mark skip (Decision 2) ensures a quiet, healthy account triggers zero reader re-runs, zero re-embedding, and zero narration calls between real signals — matching this principle directly, not just avoiding a UI regression. |
| P7 Context Over Sentiment | No | No change to the Tone reader's baseline-comparison logic. |
| P8 Clean Architecture — the Dependency Rule Is Law | Yes | `worker.py` is already an application-composition-root (it imports adapters and application use cases across `ingestion`/`readers`/`scoring`/`narrator`/`observability` to wire dependencies, exactly as `main.py` does for the API) — the new function follows this exact existing pattern, importing nothing new that any Domain ring doesn't already permit. No import-linter contract needs to change. |
| **P9 Test-First Determinism** | **Yes.** | This feature must not weaken golden-replay/reconciliation/monotonicity — it doesn't touch `backend/app/ledger/`, `backend/app/scoring/domain/`, or `backend/app/scoring/application/` at all; it only adds a new caller of `RecomputeScoreUseCase.execute(trigger="new_event")`, an already-tested, already-deterministic entry point (three of its four trigger values are already exercised by real tests per `tests/scoring/test_recompute_score_use_case.py`). |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | **Yes — the organizing constraint for every decision in `research.md`.** | No broker (Decision 1), no new schema for the high-water-mark (Decision 2), no new enum value (Decision 4), no new "skip if empty" logic that already exists (Decision 5), no manual locking that APScheduler already provides (Decision 6). Every alternative considered and rejected in `research.md` was rejected specifically for adding abstraction/infrastructure this feature's actual requirement does not need. |
| P11 Frontend | No | No frontend change. |

**Result**: PASS. No violation requires justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/026-automated-pipeline-orchestration/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `data-model.md` — no schema change (`research.md` Decisions 2 and 4 both explicitly avoid one).
No `contracts/` — this feature adds no new API endpoint or external interface; its only "contract"
is the ordering/skip behavior of one new scheduled job, fully specified in `quickstart.md`.

### Source Code (repository root)

```text
backend/
├── app/
│   └── worker.py                          # MODIFIED — new job function + scheduler.add_job() + --run-once entry
└── tests/
    └── unit/
        └── test_worker_pipeline_orchestration.py   # NEW — real-DB test of the new job's skip/run/order logic
specs/026-automated-pipeline-orchestration/           # NEW — this feature's spec-kit artifacts
```

**Structure Decision**: Single-file backend change plus its own test file — `worker.py` is already
the established home for every scheduled job in this system (`architecture/03-technology-stack.md`:
"Background/scheduled processing — APScheduler... inside the `worker` container"); this feature
extends that existing file rather than introducing a new module or package for what is, in shape,
identical to the four jobs already there.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
