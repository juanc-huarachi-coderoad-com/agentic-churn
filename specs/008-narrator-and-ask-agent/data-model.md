# Phase 1 Data Model: Narrator and Ask Agent

No new tables. `narrator_outputs`, `playbook_actions`, and `ask_queries`
(`data-base/08-schema-experience.md`) all already exist since feature 001's
`0001_initial_schema.py`. This feature is the first real *writer* of
`narrator_outputs` and `ask_queries`, and the first real *reader* of
`playbook_actions` (already seeded, `data-base/11-seed-data.sql`). One real
schema change is needed — a Postgres `ENUM` value addition
(`research.md` Decision 6).

## Migration: `declined_reason` gains a fifth value

```sql
ALTER TYPE declined_reason ADD VALUE 'insufficient_history';
```

New Alembic revision, following the migration chain after `0001_initial_schema.py`
(`decisions/02-repo-and-tooling.md`'s "every schema change afterward is a new
Alembic revision" rule). `data-base/10-ddl-appendix.md`'s `CREATE TYPE
declined_reason` line and `data-base/08-schema-experience.md`'s
`ask_queries.declined_reason` description both get updated to list all five
values, keeping the DDL appendix, the prose schema doc, and the running
schema from drifting apart (`AGENTS.md`'s schema discipline rule).

## `narrator_outputs` (existing table, first real writer)

No column changes. `data-base/08-schema-experience.md`'s existing shape is
exactly what this feature writes:

| Field | Set by |
|---|---|
| `score_run_id` | The score run being narrated — `UNIQUE`, exactly one row per run |
| `headline` | Either the fact-checked LLM headline, or the deterministic fallback template (`research.md` correction 1) when every candidate fails the fact-check |
| `reasons` | `[{text, points, evidence_event_ids}]` — only fact-check-passing entries |
| `actions` | `[{text, owner, due_date, playbook_id}]` — only entries with both `owner` and `due_date` (REQ-M7-05) |
| `fact_check_passed` | `false` when the fallback headline path fired, `true` otherwise |
| `prompt_version` | The versioned prompt template's version string (REQ-M7-08) |

## `ask_queries` (existing table, first real writer)

No column changes beyond the enum migration above.

| Field | Set by |
|---|---|
| `question_text` | The submitted question, verbatim |
| `matched_intent` | One of REQ-M9-02's 8 closed-enum intent names, or `NULL` on no match |
| `rendered_component` | One of `AskComponentResponse.component`'s 8 values (7 render + `draft_handoff`), or `NULL` on decline/fallback |
| `declined_reason` | One of the now-5 `declined_reason` enum values, or `NULL` when a component was rendered |
| `response_time_ms` | Wall-clock time for the whole graph run |
| `asked_by_user_id` | From the bearer token, never the request body (`architecture/07-api-spec.md`) |

## New domain value objects — `app.narrator.domain.entities` (this module's first real content)

Pure, no I/O — `app.narrator.domain.services`'s fact-check function consumes/
produces these.

| Type | Fields | Description |
|---|---|---|
| `RankedContribution` | `finding_id, finding_type, points, is_positive, cited_event_ids` | One `score_contributions` row for the run being narrated, in the scoring engine's own order — the Narrator never re-sorts this list (REQ-M7-01, REQ-M7-P2) |
| `VerifiedFactSet` | `numbers: frozenset[str], names: frozenset[str]` | Every number and name that legitimately exists in this run's structured input (points, stakeholder names, ticket numbers, dates) — built once per run, before any generation call |
| `FactCheckResult` | `passed: bool, extracted_numbers: frozenset[str], extracted_names: frozenset[str]` | One candidate sentence's check outcome against a `VerifiedFactSet` |
| `NarratedReason` | `text, points, evidence_event_ids` | One fact-check-passed reason, ready to persist |
| `NarratedAction` | `text, owner, due_date, playbook_id` | One personalized, fact-check-passed action; never constructed if either `owner` or `due_date` is missing (REQ-M7-05) |
| `NarratorOutput` | `headline, reasons: list[NarratedReason], actions: list[NarratedAction], fact_check_passed: bool, prompt_version: str` | The use case's final result, mapped 1:1 onto `narrator_outputs`' columns |

## New ports — `app.narrator.application.ports`

Narrator-owned, same convention `experience`/`readers` already established —
no cross-module adapter import. `LLMPort` itself is the one deliberate
exception (`research.md` Decision 1): imported from `app.readers.application.
ports`, not redefined here.

| Port | Method(s) | Used by |
|---|---|---|
| `ScoreContextPort` | `get_ranked_contributions(score_run_id) -> list[RankedContribution]`; `get_top_issue(score_run_id) -> IssueSummary` (label, points — for the deterministic fallback template) | The narrator use case |
| `ClientContextPort` | `resolve_names(cited_event_ids) -> dict[UUID, str]` — event ID → the stakeholder/ticket name or number actually present in that event, the concrete material `VerifiedFactSet` is built from | The narrator use case, building `VerifiedFactSet` |
| `PlaybookPort` | `list_active(finding_type: str) -> list[PlaybookTemplate]` | The narrator use case, personalizing actions |
| `NarratorOutputRepositoryPort` | `persist(output: NarratorOutput, score_run_id: UUID) -> None` | The narrator use case's one and only write |

## New adapters — `app.narrator.adapters`

| Adapter | Implements | Note |
|---|---|---|
| (none new) | `LLMPort` | Reuses `app.readers.adapters.AnthropicLLMAdapter`, constructed with `settings.generation_model_id` instead of `settings.reader_model_id` (`research.md` Decision 1) — no new adapter class |
| `SqlAlchemyScoreContextRepository` | `ScoreContextPort` | Reads `score_contributions` ordered by the scoring engine's own rank (`points_contributed`, most impactful first — the same order `contribution_bars` already renders in) joined to `issues` for the fallback template's `top_issue` |
| `SqlAlchemyClientContextRepository` | `ClientContextPort` | Resolves cited events → stakeholder names / ticket numbers, reusing the same decrypted-event read path feature 003/007 already established |
| `SqlAlchemyPlaybookRepository` | `PlaybookPort` | Reads `playbook_actions WHERE is_active AND applies_to_finding_type = :finding_type` |
| `SqlAlchemyNarratorOutputRepository` | `NarratorOutputRepositoryPort` | One `INSERT` into `narrator_outputs`, `UNIQUE(score_run_id)` already enforces "exactly one row per run" at the DB level |

## `NarrateScoreRunUseCase` — `app.narrator.application.use_cases` (new)

```
run = self._score_context.get_ranked_contributions(score_run_id)
facts = self._client_context.build_verified_facts(run)   # names, numbers
candidates = self._llm.generate_structured(prompt, NarrationSchema)  # {headline, reasons[], actions[]}
reasons = [r for r in candidates.reasons if fact_check(r.text, facts).passed]
actions = [
    a for a in personalize(candidates.actions, self._playbook.list_active(...))
    if a.owner and a.due_date
]
headline = candidates.headline if fact_check(candidates.headline, facts).passed \
    else deterministic_fallback_headline(top_issue)   # research.md correction 1
output = NarratorOutput(headline, reasons, actions, fact_check_passed=..., prompt_version=...)
self._repo.persist(output, score_run_id)
```

Mirrors `RecomputeScoreUseCase`'s existing shape (Application orchestrates
ports; the pure fact-check function is Domain, zero I/O). No exception
handling beyond the 10s/1-retry budget already specified in
`architecture/06-error-handling.md` — total generation failure routes into the
same fallback-headline path as a total fact-check failure, per that document's
"same deterministic fallback applies to a total narrator failure" note.

## New ports — `app.experience.application.ports` (extended, not replaced)

Reuses `FindingReadPort` and `ScoreReadPort` (already exist, feature 006) for
5 of the Ask agent's 7 lookup intents. One genuinely new port:

| Port | Method(s) | Used by |
|---|---|---|
| `LedgerQueryPort` (new) | `baseline_vs_current(stakeholder_id: UUID) -> tuple[ConfirmedBaselineWindow, list[MessageEventInfo]] \| None` — reuses `app.readers.domain`'s existing value objects (feature 007) as its return shape, `None` when the stakeholder has fewer than 5 confirmed-baseline messages | The "is this normal for X?" intent — the one lookup feature 006 never needed |
| `AskQueryRepositoryPort` (new) | `log(question_text, matched_intent, rendered_component, declined_reason, response_time_ms, asked_by_user_id) -> None` | Every graph run, exactly once, regardless of which terminal node fired (REQ-M9's logging requirement, FR-023) |
| `NarratorReadPort` (new) | `get_for_score_run(score_run_id: UUID) -> NarratorSummary \| None` — `NarratorSummary` mirrors `narrator_outputs`' `headline`/`reasons`/`actions` columns, `None` when no row exists yet | Populates `DashboardResponse.narrator` (`contracts/dashboard.md`) — found missing from this table during `/speckit-analyze` (I3); the underlying read is trivial (one `SELECT` by `score_run_id`) but the port itself was never named until then |

**`FindingReadPort.get_finding`/`resolve_events` gain a `status = 'validated'`
filter** (found during `/speckit-analyze`, C1): as built by feature 006,
neither method filtered on `findings.status`, which would have let
`QueryFindingsTool` surface a quarantined finding through `/api/ask` —
violating FR-024 the same way an unfiltered query would violate P1's
"structurally impossible, not just discouraged by convention" bar elsewhere
in this codebase. `ScoreReadPort`-backed lookups need no equivalent change:
`score_contributions` only ever contains validated findings' contributions,
since `RecomputeScoreUseCase` reads `FindingRepositoryPort.list_validated()`
— safe by construction, not by an added filter.

`FindingReadPort.get_finding`/`resolve_events` back "what's the top risk,"
"what did we promise them" (via `get_commitment_comparison`), and "show me
everything about X" (via `resolve_events`). `ScoreReadPort.latest_run`/
`list_contributions` back "why did the score go up." `StakeholderReadPort`
(existing) backs "who's gone quiet."

## `AskAgentState` — `app.experience.application` (new, TypedDict)

Exactly `architecture/08-class-diagrams.md` diagram 4's shape — `question`,
`intent`, `tool_results`, `component`, `component_props`, `fallback_text`,
`declined_reason`. Not persisted; lives only for the duration of one graph
run.

## `AskAgentPort` / `LangGraphAskAgent` — `app.experience.application` / `app.experience.adapters.ask_agent_graph` (new)

```
class AskAgentPort(ABC):
    async def answer(self, question: str, user: User) -> AskAgentResult: ...
```

`LangGraphAskAgent` implements it: `classify_intent` (via `LLMPort`, closed
enum from REQ-M9-02) → branch → `decline` (prediction/colleague-judgment, no
tool call) | `fallback` (no match) | `handoff` (write-to-X, no tool call,
`component = "draft_handoff"`) | tool-calling loop over `AskAgentToolkit`'s 3
tools → `render_component`. Every terminal node calls `AskQueryRepositoryPort.
log(...)` exactly once before returning (`research.md` Decision 4).

## New adapters — `app.experience.adapters` (extended)

| Adapter | Implements | Note |
|---|---|---|
| (reused) | `LLMPort` (via `classify_intent`) | `AnthropicLLMAdapter` from `app.readers.adapters`, `settings.generation_model_id` — same reuse as the Narrator |
| `LangGraphAskAgent` | `AskAgentPort` | Holds the compiled `StateGraph`; no checkpointer configured (`decisions/03-langgraph-for-ask-agent.md` — off in the MVP) |
| `AskAgentToolkit`, `QueryLedgerTool`, `QueryFindingsTool`, `QueryScoreRunsTool` | — | Thin wrappers: `QueryLedgerTool` → `LedgerQueryPort`, `QueryFindingsTool` → `FindingReadPort`, `QueryScoreRunsTool` → `ScoreReadPort`. Each wraps exactly one `get_*`/`query_*`-style method — no write method is ever reachable to register (`.specify/memory/constitution.md`'s AI safety rule 2) |
| `SqlAlchemyLedgerQueryRepository` | `LedgerQueryPort` | Reuses feature 007's `ConfirmedBaselineRepositoryPort` read shape (baseline window + sample texts), read-only |
| `SqlAlchemyAskQueryRepository` | `AskQueryRepositoryPort` | One `INSERT` into `ask_queries` per graph run |
| `ask_router.py` | — | New FastAPI route, `POST /api/ask`, following `dashboard_router.py`/`coverage_router.py`'s existing pattern in the same package |

## API contract changes — `architecture/07-api-spec.md`

- `DashboardResponse` gains one new field: `narrator: NarratorSummary | null`
  — `{headline: str, reasons: [{text, points, evidence_event_ids}],
  actions: [{text, owner, due_date}]}`, `null` when no `narrator_outputs` row
  exists yet for the latest `score_runs.id` (the same "absent, not empty"
  discipline every other optional dashboard field already follows). No new
  field is needed for the Ask bar's `Idle`/`Thinking`/`Answered` states —
  those are pure frontend request-lifecycle state around calling
  `POST /api/ask`, not server-returned data (`contracts/ask.md`).
- `AskComponentResponse.component` gains an 8th enum value, `draft_handoff`
  (`research.md` Decision 5); `component_props` for that value is
  `{issue_id: uuid, stakeholder_id: uuid}`.
- `AskFallbackResponse.declined_reason` enum gains `insufficient_history`
  (`research.md` Decision 6), matching the DB migration above.
- `CoverageResponse` (feature 006) gains `ask_intent_coverage:
  {total_questions: int, fallback_count: int, fallback_rate: float} | null`
  — `null` when no `ask_queries` rows exist yet, computed from
  `matched_intent IS NULL` over all logged questions. Added during
  `/speckit-analyze` (E1): SC-007 promises the fallback rate is "visible and
  measurable at any time, without querying the database directly," but
  nothing else in this feature builds a non-DB-query surface for it — this
  is that surface, reusing the System health screen's existing route
  (feature 006) rather than adding a new one.

## State transitions

`narrator_outputs`: none — write-once per `score_run_id`, `UNIQUE` constraint
already enforces this, no update path exists (matches `draft_messages`'
append-only discipline elsewhere in this schema).

`ask_queries`: none — write-once per question, an immutable log entry, never
updated or deleted.
