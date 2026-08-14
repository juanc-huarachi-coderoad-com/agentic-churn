# Test strategy

How this system's own engineering acceptance criteria (spec §14.3, `requirements/11-non-functional-requirements.md` REQ-NFR-27…33) turn into an actual, runnable test suite. Every criterion below already existed as a requirement; this document is where each one gets a concrete test, a fixture, and a place in CI (`workflows/ci.yml`).

## The five kinds of test this system needs

| Kind | What it proves | Where it lives |
|---|---|---|
| Golden-replay | Dropping projections and replaying reproduces the dashboard exactly | `tests/golden_replay/` |
| Decimal reconciliation | Score contributions sum exactly to the total | `tests/scoring/test_reconciliation.py` |
| Monotonicity | Adding a negative finding never lowers the score | `tests/scoring/test_monotonicity.py` |
| Static no-LLM check | No model call exists anywhere in the scoring engine | `workflows/ci.yml` (AST-based, not a runtime test — see `decisions/02-repo-and-tooling.md`) |
| Reader eval harness | Reader quality, measured against the quarantine dataset it produces | `tests/eval/` |

## Golden-replay tests

The single most load-bearing test category — it's the mechanical proof behind REQ-NFR-09/28 and the spec's own Phase 4 checkpoint ("if the score cannot be explained and defended with hand-written findings, no amount of AI will fix it," spec §16 — Phase 4 is "Scoring engine with hand-written findings" in the v1.2 build order).

**Fixture:** `demo/fixtures/meridian-week.json` (the same fixture the demo's contingency path uses, `demo/03-environment-and-fixtures-checklist.md`) fed through `SimulatedCollector` into a fresh database.

**Procedure:**
1. Run the fixture through the full pipeline once; snapshot the resulting `score_runs`, `score_contributions`, `narrator_outputs`, and dashboard-facing read API response as `tests/fixtures/golden-dashboard.json`.
2. `TRUNCATE event_threads, response_pairs, rollups;` — the three projection tables, exactly as a real replay job would (`data-base/01-database-overview.md`).
3. Re-run the replay job against `events` + `client_profile_versions` + `baseline_confirmations` alone.
4. Assert the rebuilt state is **byte-identical** to the golden snapshot.

This test is the direct implementation of the two hardest-to-fake engineering acceptance criteria in the spec: "running any collector twice produces no duplicates" (covered by re-feeding the fixture through the collector layer twice and asserting zero new rows) and "dropping all projections and replaying reproduces the current dashboard exactly."

## Decimal reconciliation tests

For every `score_runs` row produced anywhere in the test suite: `SUM(score_contributions.points_contributed WHERE is_positive = false) = score_runs.total_negative_points` and the equivalent for positive contributions, asserted to the full `NUMERIC(10,3)` precision — not rounded, not approximated. Runs against both the worked example from `examples/01-end-to-end-walkthrough.md` §9 (a known-good hand-checkable case) and randomly generated finding sets (property-based testing via `hypothesis`) to catch reconciliation bugs the hand-worked example wouldn't happen to exercise.

## Monotonicity tests

Property-based: generate a random valid `score_runs` state, add one additional validated negative finding, recompute, and assert the new score is `>=` the old one, for a large number of random cases (`hypothesis`, several thousand examples per CI run). This directly tests REQ-M6-P4 and is exactly the kind of bug a single hand-picked example would likely miss — monotonicity has to hold for *every* input, not just the worked example's input.

## Static no-LLM check

Not a pytest test — an AST-walking CI step (full script in `decisions/02-repo-and-tooling.md`) that fails the build if `backend/app/scoring/` imports `anthropic`, `openai`, or `app.llm`, directly, transitively, or via a dynamic import it can detect. This is deliberately a static check rather than a runtime mock-and-assert test: a runtime test only proves the mock wasn't called *this run*; a static check proves the import isn't *reachable* at all, which is the actual guarantee REQ-M6-P1 makes.

## Reader eval harness

The `quarantine` table (`data-base/05-schema-reasoning.md`) is explicitly designed to become "the ongoing evaluation dataset for reader quality" (REQ-M5A-04) — this harness is what makes that real rather than aspirational:

1. On a schedule (or on-demand before a prompt/model change), pull all `quarantine` rows for a given reader type over a trailing window.
2. Group by `failed_check` (`schema_invalid`, `cited_event_missing`, `insufficient_evidence`, `confidence_below_floor`).
3. Report the rate per check, per reader, per reader version — a sustained rise in any one bucket after a prompt change is exactly the regression signal `architecture/06-error-handling.md`'s "sustained quarantine rate" alert is built to catch, but measured here at development time instead of production time.
4. For `confidence_below_floor` specifically, sample a handful of quarantined findings for human review each cycle — this is the human-in-the-loop check on whether the calibration values in `requirements/13-scoring-calibration-appendix.md` (confidence floors, evidence-count floors) are still set correctly, not just whether the reader is technically working.

This harness never "fixes" a quarantined finding (REQ-M5A-03 forbids that structurally) — it only ever informs a human decision to adjust `finding_type_config` or a prompt, which then goes through the normal versioned-prompt/full-replay path (`architecture/04-ai-safety-and-model-usage.md` Rule 5).

## Ask agent (LangGraph) tests

Same principle as everywhere else in this document — ports enable fakes, so branching logic gets tested without a real database or a real LLM call. `decisions/03-langgraph-for-ask-agent.md`'s compiled graph is invoked directly with a fixed `AskAgentState` and fake implementations of `EventRepositoryPort`/`FindingRepositoryPort`/`ScoreRunRepositoryPort` injected into `AskAgentToolkit`:

1. **Branch coverage** — one test per intent in `REQ-M9-02` (8 intents), plus the decline path (`REQ-M9-05`/`06`) and the fallback path (`REQ-M9-04`), asserting the graph reaches the expected terminal node and renders the expected component — no real tool execution, no real model call, since `LLMPort` and the toolkit are both fakes here.
2. **Read-only enforcement** — a test asserting `AskAgentToolkit.build_tools()` never returns a tool bound to a write method (`save`, `quarantine`, `append`) on any injected port — the mechanical check behind "the Ask agent's tools are read-only lookups only" (`.specify/memory/constitution.md`), run against the actual registered tool list, not just read by inspection.
3. **Latency budget** — an integration test (real `AnthropicLLMAdapter`, real Postgres, not fakes) asserting end-to-end response time stays under 3s (`REQ-M9-08`), run separately from the branch-coverage unit tests above since it needs the real network round trip the unit tests deliberately avoid.

## What's explicitly out of scope for automated testing

- **Draft quality** (is the generated message actually good) — inherently subjective; handled by the MVP success metric "≥ 40% of drafts sent after light editing" (spec §14.2), measured in production, not asserted in CI.
- **Narrator prose quality** — same reasoning; the *mechanical* fact-check (REQ-M7-06) is fully tested (every fact in output must exist in input), but "is this a good sentence" is not a CI assertion.

## CI integration

All of the above (except the reader eval harness, which runs on its own schedule, not per-commit) runs on every pull request via `workflows/ci.yml`. A golden-replay failure or a monotonicity counter-example blocks merge — these are the two categories the spec treats as non-negotiable (spec §16 Phase 4 checkpoint), so CI treats them the same way.

## Traceability

`base/Churn-Sentiment-Agent-Product-Specification.md` §14.3, `requirements/11-non-functional-requirements.md` REQ-NFR-27…33, `requirements/05-interpreters-readers.md` REQ-M5A-04, `requirements/06-scoring-engine.md` REQ-M6-P1…P4, `requirements/09-ask-agent.md` REQ-M9-02…08, `decisions/02-repo-and-tooling.md`, `decisions/03-langgraph-for-ask-agent.md`, `workflows/ci.yml`.
