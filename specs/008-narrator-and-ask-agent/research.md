# Phase 0 Research: Narrator and Ask Agent

No `[NEEDS CLARIFICATION]` markers remain in `spec.md` — both open questions
found during `/speckit-clarify` are already resolved there. This document
covers technical decisions the spec deliberately left to planning, surfaced by
reading the actual current state of the codebase (not just the docs) before
writing `tasks.md`, plus two corrections to `spec.md` itself made during this
phase when research turned up documented behavior that contradicted an
assumption written during `/speckit-specify`.

## Corrections made to `spec.md` during this phase

Both corrections are already applied to `spec.md`; recorded here for the
record, the same transparency `specs/007-model-findings/spec.md`'s own
Edge Cases correction used.

1. **Narrator's total fact-check failure.** The original Edge Cases entry said
   "no narration is produced at all" when the headline fails its fact-check.
   `architecture/06-error-handling.md` ("What if the fact-check discards every
   sentence?") already specifies a deterministic, non-LLM fallback headline —
   `"{score} — {band}. Top issue: {issue.label} ({issue.points} pts). See
   evidence trace for detail."` — clearly marked as auto-generated. Corrected.
2. **Narrator's trigger mechanism.** The original Assumptions said the
   Narrator runs "chained into the recompute pipeline." Reading
   `backend/scripts/compute_score.py`, `run_readers.py`, `run_collector.py`,
   and `confirm_baseline.py` shows every pipeline stage built so far is a
   separate, manually-invoked script — there is no live, event-driven trigger
   path anywhere yet (`specs/007-model-findings/plan.md`'s own Technical
   Context already recorded this exact caveat for Tone/Intent's timing
   budget: "the live-trigger path this budget protects doesn't exist as a
   caller yet"). Corrected to match: Narrator gets its own
   `scripts/run_narrator.py`, run after `compute_score.py`, not automatic
   chaining.

## Decision 1 — Where `LLMPort` lives for the Narrator and the Ask agent's `classify_intent` step

**Decision**: Both import `LLMPort` from `app.readers.application.ports` — the
existing interface, unchanged. Neither module defines its own copy.

**Rationale**: `specs/007-model-findings/research.md` Decision 1 already
settled this, explicitly naming this feature: *"Future features that need an
LLM call (Narrator/M7, Draft composer/M10) import `LLMPort` from
`app.readers.application`."* `decisions/02-repo-and-tooling.md`'s
module→package mapping ratifies the same placement. `AnthropicLLMAdapter`
(`app.readers.adapters.anthropic_llm`) already takes `model_id` as a
constructor argument — no new adapter class is needed, just a second instance
constructed with `settings.generation_model_id` (`claude-sonnet-5`,
`decisions/02-repo-and-tooling.md`'s Claude model ID pinning table) instead of
`settings.reader_model_id`. Each call site (the Narrator's use case, the Ask
agent's `classify_intent` node) receives its own `AnthropicLLMAdapter`
instance via constructor injection — no shared singleton, mirroring how
`scripts/run_readers.py` already constructs its own instance rather than
importing one from elsewhere.

**Alternatives considered**: A new top-level `app.llm` shared-kernel module —
rejected for the same reason 007 rejected it: it contradicts the
already-ratified package map. Giving Narrator its own duplicate `LLMPort`
interface — rejected as needless duplication of a one-method interface with
no module-specific shape to justify a copy (unlike `experience/application/
ports.py`'s deliberately-owned read records, which *do* differ in shape from
`readers`'/`scoring`'s equivalents).

## Decision 2 — Module layout: `app.narrator` gets its first real content

**Decision**: `app.narrator.domain` (new — this module's first real content;
today it's empty scaffold folders) holds pure value objects and the
mechanical fact-check function. `app.narrator.application` holds the use case
and the module's own ports. `app.narrator.adapters` holds the SQLAlchemy
adapters and the versioned prompt template.

**Rationale**: `.importlinter`'s `global-dependency-rule` contract already
lists `app.narrator` in its `containers`, with `domain` wrapped as optional
— foundation work (feature 001) anticipated this module gaining a domain ring
later, exactly like `app.readers.domain` stayed empty through feature 005 and
gained its first real content in feature 007 ("this module's first real
domain logic," `specs/007-model-findings/plan.md`). The fact-check itself —
extracting every number/name token from a candidate sentence and confirming
each exists verbatim in the structured input — is a pure function of
`(sentence: str, verified_facts: FactSet) -> bool`, zero I/O, exactly the kind
of logic `architecture/09-clean-architecture-and-patterns.md`'s "domain ring
appears once a module has genuine pure logic to isolate" pattern describes.

**Alternatives considered**: Putting the fact-check inside `application` as a
private method on the use case — rejected because it's pure, deterministic,
and independently unit-testable without a database or an LLM, the same
justification `ValidationGate`'s four checks already used to earn their own
`readers/domain/services.py` home in feature 007.

## Decision 3 — Ask agent module layout: inside `experience`, not a new module

**Decision**: `LangGraphAskAgent` and `AskAgentToolkit` live in
`app.experience.adapters.ask_agent_graph`. `AskAgentPort` and the graph's
state schema (`AskAgentState`) live in `app.experience.application`. The three
tool wrappers (`QueryLedgerTool`, `QueryFindingsTool`, `QueryScoreRunsTool`)
live alongside `LangGraphAskAgent` in the same adapter file.

**Rationale**: Not a new decision — `decisions/02-repo-and-tooling.md`'s
module→package mapping already places M9 at exactly this path ("M9 Ask agent
| `backend/app/experience/adapters/ask_agent_graph.py`"), and
`architecture/08-class-diagrams.md` diagram 4 and
`decisions/03-langgraph-for-ask-agent.md` both describe `AskAgentPort` as
living in `experience/application/`. `langgraph` becomes a dependency of
exactly one file; `.importlinter`'s existing `global-dependency-rule` layers
contract already keeps every other module's `application`/`domain` package
from reaching it, with no config change needed (`decisions/02`'s own closing
note on this).

**Alternatives considered**: A new top-level `app.ask` module — rejected;
would contradict the already-ratified mapping and fragment M8/M9/M10, which
`decisions/02` deliberately groups under one `experience` package as "M8, M9,
M10 — dashboard read API, ask agent, draft composer."

## Decision 4 — The Ask agent's three read-only tools reuse `experience`'s own ports where they already fit, and add one new one

**Decision**: `QueryFindingsTool` and `QueryScoreRunsTool` wrap methods
already on `experience/application/ports.py`'s existing `FindingReadPort` and
`ScoreReadPort` (built in feature 006 for the dashboard/evidence-trace read
path) — no new port for either. `QueryLedgerTool` needs a new
`LedgerQueryPort` (`query(stakeholder_id, since) -> list[MessageEventInfo]`)
— feature 006 never needed raw ledger event lookup by stakeholder/window, so
no existing `experience`-owned port covers it.

**Rationale**: `experience/application/ports.py`'s own module docstring
already establishes the convention this feature follows: "Reader-owned, no
cross-module adapter import... mirrors feature 004/005's own established
convention." `FindingReadPort.get_finding`/`resolve_events` and
`ScoreReadPort.latest_run`/`list_contributions`/`get_contribution` already
return exactly the shapes the "why did the score go up," "what's the top
risk," "what did we promise them," and "show me everything about X" intents
need (`requirements/09-ask-agent.md` REQ-M9-02). `sequences/
02-sequence-ask-agent.md`'s own diagram shows the "is this normal for Ana"
branch reading raw ledger baseline-vs-current samples — the one genuinely new
read shape this feature needs, reusing `app.readers.domain`'s existing
`MessageEventInfo`/`ConfirmedBaselineWindow` value objects (feature 007) as
its return type rather than inventing new ones, since it's the identical data
the Tone reader already reads for the identical purpose.

**Alternatives considered**: Wrapping `app.ingestion.application.
EventRepositoryPort`/`app.scoring.application.FindingRepositoryPort`/
`ScoreRunRepositoryPort` directly, per `architecture/08-class-diagrams.md`
diagram 4's port names — rejected as a literal reading of a diagram that
predates this feature's own module-ownership convention (established by
feature 006, after diagram 4 was drawn); importing another module's
*application*-layer port directly (not just its adapter) would be the same
kind of cross-module reach `experience`'s own ports file was written
specifically to avoid for its read-side records. The three tools still answer
to the exact same *data* diagram 4 names — ledger, findings, score runs — just
through `experience`'s already-established, module-owned read ports instead
of importing three other modules' ports wholesale.

**Correction found during `/speckit-analyze`**: `FindingReadPort`'s existing
`get_finding`/`resolve_events` methods (built by feature 006, before the
validation gate existed) have no `status = 'validated'` filter — confirmed
by reading `backend/app/experience/adapters/sqlalchemy_repository.py`
directly. Reusing them unmodified for `QueryFindingsTool` would have let a
quarantined finding reach an Ask agent answer, violating FR-024.
`data-model.md` now documents the required filter; `tasks.md` T024/T028 fold
the fix and its test into this feature's own implementation rather than
carrying it forward as a known gap the way earlier features sometimes did.

## Decision 5 — The "write to X about this" handoff response shape

**Decision**: `AskComponentResponse.component` gains an 8th enum value,
`draft_handoff`, alongside the existing 7. `component_props` for that value
carries `{issue_id, stakeholder_id}` — the minimum context feature 009's
draft composer will need to pick up.

**Rationale**: `spec.md`'s Clarifications already settled *that* a distinct
handoff response is needed; this decides its concrete shape. Reusing the
existing `AskComponentResponse`/`component_props: object` schema (rather than
inventing a third `oneOf` response variant in `architecture/07-api-spec.md`)
is the smaller change — `component_props` is already typed as a generic
object, so no schema restructuring is needed, only one new enum value and one
new dispatch case in `render_component`.

**Alternatives considered**: A third top-level response schema
(`AskHandoffResponse`) — rejected as unnecessary duplication of a shape
`AskComponentResponse` already accommodates; the frontend still needs the same
"is this a handoff, not a real component" discriminant either way, and
`component: "draft_handoff"` provides it identically to a wrapper type would.

## Decision 6 — `insufficient_history`: a real Postgres enum change, not just a documentation update

**Decision**: `ask_queries.declined_reason` is a Postgres `ENUM` type
(`CREATE TYPE declined_reason AS ENUM (...)`, `backend/migrations/versions/
0001_initial_schema.py`), not a `CHECK` constraint or free text. Adding
`insufficient_history` requires a real Alembic migration —
`ALTER TYPE declined_reason ADD VALUE 'insufficient_history'` — not just an
`architecture/07-api-spec.md` documentation edit.

**Rationale**: Read the actual DDL rather than trusting
`data-base/08-schema-experience.md`'s prose description, which lists the
enum's four current values without flagging the type's exact SQL shape. This
is exactly the kind of drift `AGENTS.md`'s "Schema changes go through
`data-base/10-ddl-appendix.md` first" discipline exists to prevent — this
feature's migration must update both the running schema *and*
`data-base/10-ddl-appendix.md`'s DDL appendix and
`data-base/08-schema-experience.md`'s prose, not just the code.

**Alternatives considered**: Reusing `source_not_connected` for the
insufficient-history case, avoiding a migration entirely — this was Option B
in the `/speckit-clarify` session and was explicitly rejected there as
inaccurate (`spec.md` Clarifications).

## Decision 7 — Golden-replay: this feature is where the placeholder test goes live

**Decision**: `tests/golden_replay/test_placeholder.py`'s `@pytest.mark.skip`
is removed in this feature. The real test follows `tests/strategy.md`'s
already-documented procedure exactly: snapshot `score_runs`/
`score_contributions`/`narrator_outputs`/the dashboard read response after one
fixture run, truncate the three projection tables, replay, assert
byte-identical reconstruction.

**Rationale**: `specs/007-model-findings/plan.md`'s Complexity Tracking table
already named this feature as the one that closes this exact gap: *"That
test's own documented procedure requires the full ledger → readers → score →
Narrator chain; Narrator (M7, feature 008) still doesn't exist... Expected to
go green naturally once feature 008 lands."* This is not a new obligation this
plan invents — it is a debt three prior features (004, 005, 007) explicitly
deferred to this one, by name, in their own Complexity Tracking tables. The
snapshot's own procedure (`tests/strategy.md` §Golden-replay tests) already
includes `narrator_outputs` in what gets snapshotted, confirming the test was
always designed to wait for this feature specifically, not for the Ask agent
(which produces no persisted-and-replayed-from state — `ask_queries` is a log,
not a projection).

**Alternatives considered**: Deferring golden-replay again with a fourth
Complexity Tracking entry — rejected; every precondition the prior three
entries named (readers real, gate real, scoring real, and now narration real)
is satisfied once this feature ships, so deferring again would have no
remaining technical justification, only inertia.

## Decision 8 — Ask agent test strategy: already fully specified, not re-decided here

**Decision**: Follow `tests/strategy.md`'s existing "Ask agent (LangGraph)
tests" section verbatim: the compiled graph invoked directly with a fixed
`AskAgentState` and fake ports (branch coverage, one test per intent plus
decline/fallback/handoff); a read-only-enforcement test asserting
`AskAgentToolkit.build_tools()` never returns a tool bound to a write method;
one real-network, real-Postgres latency test for the 3s budget, run
separately from the fake-backed branch-coverage suite.

**Rationale**: This section of `tests/strategy.md` already names this
feature's exact test shape — nothing to design here, only to build. Matches
`specs/007-model-findings/plan.md`'s own precedent of citing an
already-authoritative test document rather than re-deriving a test strategy
mid-feature.

## Decision 9 — Frontend: extend, don't rebuild

**Decision**: `frontend/src/dashboard/dashboard-page.tsx` gains a new
`narrator-panel.tsx` component (headline/reasons/actions) rendered from
`DashboardResponse`'s new fields. `frontend/src/ask/` (currently an empty
scaffold folder, `.gitkeep` only) gets its first real content: an `ask-bar.tsx`
component (Idle/Thinking/Answered) plus one renderer per closed-set component
type, following the same TanStack Query + typed-response pattern
`frontend/src/dashboard/types.ts` already establishes.

**Rationale**: `frontend/src/ask/` already exists as a named, empty directory
— confirms `decisions/02-repo-and-tooling.md`'s frontend layout
(`frontend/src/{dashboard,ask,draft-composer,profile-editor}/`) anticipated
this feature, the same way `backend/app/narrator/` did on the backend side.
No new top-level frontend directory is needed.
