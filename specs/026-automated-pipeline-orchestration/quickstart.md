# Quickstart: Automated Pipeline Orchestration

## Prerequisites

- A running, freshly provisioned stack (`docker compose up --build -d`, `alembic upgrade head`,
  `scripts/seed.py`) — same baseline every prior feature's quickstart uses.
- No new secrets — the new job reuses `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` exactly as the existing
  manual scripts already do (missing keys degrade the same way they do today: a per-reader
  failure, not a crash).

## Setup

1. In `backend/app/worker.py`, add a new job function (name TBD in `tasks.md`, e.g.
   `_run_pipeline_orchestration`) that:
   - Queries `SELECT MAX(created_at) FROM events`.
   - Compares against the module-level `_last_seen_event_at` variable; returns immediately (no
     reader/recompute/narrate call) if there's nothing new (`research.md` Decision 2).
   - Otherwise: runs `RunReadersUseCase.execute()`, then
     `RecomputeScoreUseCase.execute(trigger="new_event")`, then
     `NarrateScoreRunUseCase.execute(score_run.id)` — in that order (FR-003) — then updates
     `_last_seen_event_at` to the value captured *before* the pipeline ran.
2. Register it: `scheduler.add_job(_run_pipeline_orchestration, "interval", seconds=30,
   id="pipeline_orchestration")` — no `max_instances` override (Decision 6).
3. Add `"pipeline"` (or similar) to `_RUN_ONCE_JOBS` for `--run-once` parity with the existing four
   jobs (FR-007).

## Validation

**Story 1 (a new signal updates the dashboard automatically)**:
1. Start the full stack including `worker`.
2. Run `scripts/run_collector.py --source simulated` (or wait for a real/audio collector cycle).
3. Without running `scripts/run_readers.py` or `scripts/run_narrator.py` by hand, wait up to ~60s.
4. Confirm via `GET /api/dashboard` (or the UI) that findings/score/narration reflect the new
   signal, and via `worker` logs that the new job actually ran (not skipped).

**Story 2 (a quiet period costs nothing)**:
1. With no new signal ingested, observe two consecutive ticks of the new job in `worker` logs.
2. Confirm the second (and every subsequent) tick logs a skip — no reader invocation, no LLM call,
   no narration call — until a new signal is ingested again.

**Story 3 (manual trigger still works)**:
1. Run `python -m app.worker --run-once pipeline` (or whatever id T-tasks.md assigns).
2. Confirm it runs the full readers → recompute → narrate sequence immediately, regardless of the
   high-water-mark, mirroring `scripts/run_readers.py` + `scripts/compute_score.py` +
   `scripts/run_narrator.py`'s existing combined effect.
3. Separately, confirm `scripts/run_readers.py` and `scripts/run_narrator.py` still work exactly
   as before, unmodified (FR-008).

**Overlap (FR-006 / SC-004)**:
1. Temporarily lower the interval or inject an artificial delay to observe two ticks firing close
   together while a prior run is still in progress.
2. Confirm APScheduler's log shows the second trigger skipped (`max_instances` reached), never two
   concurrent runs.

**Failure isolation (FR-005, Acceptance Scenario 3)**:
1. Temporarily unset `ANTHROPIC_API_KEY` (or otherwise force one reader to fail).
2. Trigger a cycle with a new signal present.
3. Confirm the other readers still complete, their findings are still scored, and (if any findings
   resulted) narration still runs — matching `RunReadersUseCase`'s existing, already-tested
   per-reader isolation (FR-014a).

## Expected outcome

The dashboard reflects new signals within ~60s with zero manual script execution; a quiet account
produces zero additional reader/LLM/embedding cost between real signals; the existing manual
scripts remain fully functional as independent verification tools.
