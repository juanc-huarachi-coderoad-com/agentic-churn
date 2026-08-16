# Phase 0 Research: Model Findings

No `[NEEDS CLARIFICATION]` markers remain in `spec.md` — the one open question
found during `/speckit-clarify` (finding_type_config seeding) is already
resolved there. This document covers technical decisions the spec deliberately
left to planning, surfaced by reading the actual current state of the codebase
(not just the docs) before writing `tasks.md`.

## Decision 1 — Where `LLMPort` and `AnthropicLLMAdapter` live

**Decision**: `LLMPort` (the abstract interface) is defined in
`app.readers.application.ports`, alongside the existing `EmbeddingPort`/
`FindingRepositoryPort`. `AnthropicLLMAdapter` (the only class in the codebase
that imports the `anthropic` SDK) lives in `app.readers.adapters`.

**Rationale**: Not a new decision — `decisions/02-repo-and-tooling.md`'s
module→package mapping already ratifies this exact placement ("`readers/
application/` … LLMPort, EmbeddingPort", "`readers/adapters/` … 
AnthropicLLMAdapter, OpenAIEmbeddingAdapter"), predating this feature. Future
features that need an LLM call (Narrator/M7, Draft composer/M10) import
`LLMPort` from `app.readers.application` — a cross-module import, but the
already-decided one, not something this feature invents. `.importlinter`'s
`readers-application-purity` contract already forbids `anthropic`/`openai`
inside `app.readers.application`, so `LLMPort` itself (a pure interface, no
SDK import) is contract-compliant; only `AnthropicLLMAdapter` in
`app.readers.adapters` may import `anthropic`, mirroring
`OpenAIEmbeddingAdapter`'s existing precedent exactly.

**Alternatives considered**: A new top-level `app.llm` shared-kernel module —
rejected because it contradicts the already-ratified, checked-in package map;
introducing it now would mean re-litigating a Phase 1 foundation decision
mid-feature, not making a new one.

## Decision 2 — What the Tone reader's baseline input actually is

**Decision**: The Tone reader's LLM call receives the new message's text plus
the **raw text of prior messages from the stakeholder's confirmed baseline
window** (resolved via a new `ConfirmedBaselineRepositoryPort` that joins
`baseline_confirmations` → matching `events` for that `stakeholder_id`/
`metric` window) — not a single pre-computed scalar like
`rollups.avg_words_per_message`.

**Rationale**: REQ-M5-06/architecture's Tone agent card both frame this as a
*linguistic* judgment ("is this person writing differently than they normally
do"), which needs real text samples to compare against, not a word-count
average — a word-count comparison alone wouldn't need an LLM call at all.
`data-base/03-schema-ledger.md`'s `avg_words_per_message` row is illustrative
narrative for the general `rollups`/`is_baseline` design (which the Usage
reader, feature 005, actually instantiated for its own numeric metric), not a
literal input contract for Tone. Feature 005's `ComputeRollupsUseCase`
(`backend/app/ingestion/application/use_cases.py`) is scoped narrowly to
`usage_measurement` events at `product_area` granularity — extending it with a
`stakeholder`-scoped word-count metric to satisfy an input the reader doesn't
actually need would be exactly the premature generality P10/YAGNI warns
against.

**Alternatives considered**: Extending `ComputeRollupsUseCase` with a
stakeholder-scoped `avg_words_per_message` rollup, matching `data-base/03`'s
literal example row — rejected: solves a problem the LLM-based reader doesn't
have (it doesn't need a hand-engineered numeric feature; it needs the text
itself), and would grow the already-scoped `ingestion` module for a consumer
that doesn't need it.

## Decision 3 — How a baseline gets confirmed at all in Phase 1

**Decision**: A new manual script, `scripts/confirm_baseline.py`, writes a row
directly to `baseline_confirmations` for a given `stakeholder_id`/`metric`/
window — mirroring `scripts/run_readers.py`/`scripts/compute_score.py`'s
already-established "manual trigger script, no live UI" pattern. The read
side (`ConfirmedBaselineRepositoryPort.get_confirmed_window`, `data-model.md`)
deliberately doesn't filter by `metric` — see `data-model.md`'s note on that
column for the one-window-per-stakeholder assumption this implies.

**Rationale**: `baseline_confirmations` exists in the schema since feature
001's migration but has zero application code reading or writing it today —
no repository, no port, no endpoint. `requirements`/`decisions/01-mvp-scope-
and-phasing.md`'s Phase 2 diagram lists "Profile editor UI" as Post-MVP, so
there is no live human-clicking-a-button flow to build this feature's data
into in Phase 1 — confirmed independently by
`demo/03-environment-and-fixtures-checklist.md` item 3, which frames baseline
confirmation as pre-demo *seeding*, not a runtime feature ("A human … confirms
the healthy window via `baseline_confirmations` before demo day"). Building a
script, not an endpoint, matches feature 005's own precedent for
`RunReadersUseCase` triggering and avoids inventing a UI this feature's spec
never asked for.

**Alternatives considered**: An authenticated `POST /api/baseline/confirm`
route — rejected as scope creep beyond this feature's spec (no user story asks
for a human-facing confirmation flow) and premature ahead of the Post-MVP
Profile editor UI that would be its natural home.

## Decision 4 — Structured output via the Messages API's native `output_format`, not a tool-use trick

**Decision**: `AnthropicLLMAdapter.generate_structured(prompt, schema)` calls
`client.messages.parse(model=..., messages=[...], output_format=schema)` —
the Anthropic Python SDK's native structured-output mechanism, which returns a
`ParsedMessage` whose `.parsed_output` is already an instance of `schema`.
`schema` is a plain Python `dataclass` (verified compatible with the SDK's
internal `pydantic.TypeAdapter`-based JSON-schema generation, matching this
codebase's existing "plain dataclasses, no Pydantic in the domain" style — the
`anthropic` package's own transitive `pydantic` dependency stays confined to
`app.readers.adapters.anthropic_llm`, the one file already carrying the SDK
import).

**Rationale**: An earlier draft of this decision (before checking current SDK
documentation) proposed a forced-single-tool-call pattern as the structured-
output mechanism, reasoning that a "tool" whose only purpose is JSON-schema
shaping — never actually invoked as an action — wouldn't violate REQ-M5-P2 ("no
reader SHALL have tool access"). That reasoning turned out to be unnecessary:
the current SDK has a dedicated `output_format`/`messages.parse()` API that
achieves the same result without `tools`/`tool_choice` ever being passed at
all. This is a strictly *stronger* structural guarantee than the tool-based
approach would have been — there is no tool-shaped object anywhere in the
adapter's request, so the "the tool is never invoked" argument doesn't even
need to be made. `LLMPort.generate_structured(prompt, schema)`
(`architecture/09-clean-architecture-and-patterns.md`'s already-named
interface) still takes no `tools` parameter and returns a plain object either
way — the interface itself makes tool-granting structurally impossible from
the reader's side, which is the property REQ-M5-P2 actually requires.

**Alternatives considered**: A forced single-tool-call pattern (this
decision's own original proposal) — superseded once `messages.parse()`'s
existence was confirmed; strictly more moving parts for the same result, and
invites exactly the "but doesn't this grant a tool?" question this simpler
mechanism avoids needing to answer at all. Prompt-only "reply with JSON only"
instruction, manually parsed — rejected as less reliable (no schema
enforcement at the API level, higher parse-failure rate feeding straight into
M5a's `schema_invalid` quarantine bucket for no good reason).

## Decision 5 — The validation gate is wired synchronously inside `RunReadersUseCase`

**Decision**: `RunReadersUseCase.execute()` is extended so that, immediately
after each reader's `interpret()` returns its findings, every finding is
passed to `ValidationGate.evaluate()` before persistence — replacing the
current unconditional `status=pending_validation` persist with either a
`validated` or `quarantined` write (plus a `quarantine` row on failure) —
instead of a separate, later batch job over already-persisted findings.

**Rationale**: Matches `architecture/08-class-diagrams.md`'s already-drawn
wiring exactly (`RunReadersUseCase --> ValidationGate: every output passes
through`) and `architecture/09`'s Chain-of-Responsibility framing of the
gate's four checks. It also directly resolves this feature's own User Story
3/FR-008: gating happens at emission time, for every reader (not just Tone/
Intent), with no separate re-scan step to build or keep in sync.

**Alternatives considered**: A separate `ValidateQueuedFindingsUseCase` run as
a distinct batch step after `RunReadersUseCase` — rejected as an unnecessary
extra moving part for no benefit; nothing in the spec needs findings to be
briefly visible in an unvalidated state between the two steps, and the
simpler synchronous wiring is what the architecture diagram already shows.

## Decision 6 — What each of M5a's four checks actually evaluates

**Decision**:

1. **Schema valid** — re-validates the constructed `Finding`'s own field
   invariants in Python (`magnitude`/`confidence` within `[0, 1]`, non-empty
   `cited_event_ids`, `finding_type` present in `finding_type_config`) before
   attempting persistence, converting what would otherwise surface as an
   unhandled DB `CHECK`/FK violation into a clean `quarantine` row. The
   `finding_type` sub-check is implemented via `FindingTypeConfigPort.
   get_thresholds()` returning `None` for an unconfigured type rather than
   raising (`data-model.md`'s port table) — a `None` result *is* a
   `schema_invalid` failure, not a separate code path, so this sub-check is
   concretely reachable rather than only asserted in prose (gap found and
   closed during `/speckit-analyze`).
2. **Cited events exist as real rows in the ledger** — every ID in
   `cited_event_ids` must resolve to a real row in `events`. Readers self-
   fetch their own input via injected ports (`Reader.interpret()` takes no
   parameters, per `backend/app/readers/application/reader.py`'s existing
   docstring), so there is no separately-tracked "supplied window" object to
   compare against beyond the ledger itself — a cited ID that doesn't exist
   can only be a hallucinated or stale reference, exactly what this check
   exists to catch. (`spec.md`'s edge case originally described a narrower,
   per-run "window" version of this check that nothing in this feature's
   design actually tracks; reconciled to this simpler, buildable version
   during `/speckit-analyze` rather than left contradicting the plan.)
3. **Sufficient evidence quantity** — `len(cited_event_ids) >=
   finding_type_config[finding_type].min_evidence_count`.
4. **Confidence at or above the floor** — `confidence >=
   finding_type_config[finding_type].confidence_floor` (inclusive, per
   `spec.md`'s Edge Cases).

**Rationale**: Grounded directly in `data-base/05-schema-reasoning.md`'s
`quarantine.failed_check` enum (`schema_invalid`, `cited_event_missing`,
`insufficient_evidence`, `confidence_below_floor`) and its worked example
(`fnd-10` failing `confidence_below_floor` at `0.55 < 0.65`). Each check is
independent and order-agnostic (Chain of Responsibility, `architecture/09`),
so a finding failing more than one check produces one `quarantine_reasons` row
per failed check (FR per spec's User Story 3, acceptance scenario 3).

## Decision 7 — `finding_type_config` seeding for the two new Intent categories

**Decision**: Add two `INSERT` rows to `data-base/11-seed-data.sql` (not a new
Alembic migration — `finding_type_config` already exists as a table since
feature 001's `0001_initial_schema.py`), matching `spec.md`'s Clarifications
resolution exactly: `competitive_mention` and `contractual_reference`, each
mirroring `escalation_language`'s existing row (`base_points=14.00`,
`confidence_floor=0.60`, `min_evidence_count=1`, `half_life_days=14`,
`version='v1'`).

**Rationale**: Data seeding in this repo is a SQL-seed concern, not a schema-
migration concern (`data-base/11-seed-data.sql` already seeds
`escalation_language` and the other seven finding types the same way) — no
new column, table, or constraint is needed, only new rows.

## Deliberately not re-litigated (already settled, cited not re-decided)

- **Model tier/IDs**: `claude-haiku-4-5-20251001` for Tone/Intent, via
  `READER_MODEL_ID` (`decisions/02-repo-and-tooling.md`).
- **Timeout/retry budget**: 8s × 2 retries, 1s/2s backoff, abstain (not
  quarantine) on exhaustion (`architecture/06-error-handling.md`).
- **Sustained-quarantine ops alert**: 50% rolling-24h threshold, already
  specified (`architecture/06-error-handling.md`) — this feature's gate just
  needs to write real `quarantine` rows for that existing alerting logic (out
  of this feature's scope, not yet built anywhere) to eventually read.
- **Golden-replay test status**: `tests/golden_replay/test_placeholder.py`
  stays `@pytest.mark.skip` — same justification feature 004/005 already
  recorded (needs the full ledger→readers→score→Narrator chain; Narrator is
  feature 008). This feature does not change that status; see plan.md's
  Complexity Tracking.
