# Implementation Plan: Narrator and Ask Agent

**Branch**: `008-narrator-and-ask-agent` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/008-narrator-and-ask-agent/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Fill in `backend/app/narrator/`'s empty scaffold with real code — a
`NarrateScoreRunUseCase` that reads a score run's already-ranked
`score_contributions`, generates a headline/reasons/actions via `LLMPort`
(reused from `app.readers.application`, `research.md` Decision 1), mechanically
fact-checks every sentence, and persists exactly one `narrator_outputs` row —
and give `app.narrator.domain` its first real content (the pure fact-check
function). Build the Ask agent for the first time: `LangGraphAskAgent` +
`AskAgentToolkit` in `app.experience.adapters.ask_agent_graph.py`
(`decisions/02-repo-and-tooling.md`'s already-ratified location), a compiled
`StateGraph` classifying each question into one of REQ-M9-02's 8 intents and
either rendering a component, declining, falling back, or handing off to the
not-yet-built draft composer — wiring `POST /api/ask` for the first time since
`architecture/07-api-spec.md` documented it. Close both dashboard gaps feature
006 explicitly deferred: `DashboardResponse` gains a `narrator` field, and the
frontend's already-scaffolded, empty `frontend/src/ask/` directory gets its
first real content (the Ask bar). Two small, real schema/contract additions
surfaced during `/speckit-clarify`: `declined_reason` gains a fifth Postgres
enum value (`insufficient_history`, a genuine Alembic migration, not just a
doc update — `research.md` Decision 6), and `AskComponentResponse.component`
gains an 8th value (`draft_handoff`, `research.md` Decision 5). This is also
the feature that finally turns `tests/golden_replay/test_placeholder.py`
real — three prior features' Complexity Tracking tables (004, 005, 007)
explicitly named this feature as the one that closes that gap, because the
golden-replay snapshot has always included `narrator_outputs`
(`research.md` Decision 7).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript + React 18 (frontend)
— unchanged from features 001–007; this is the first feature since 006 to
touch both sides of the stack in one pass.

**Primary Dependencies (new in this feature)**: `langgraph` +
`langchain-anthropic` (or equivalent LangChain Anthropic integration),
confined to exactly one file — `app.experience.adapters.ask_agent_graph`
(`decisions/02-repo-and-tooling.md`'s already-ratified location,
`decisions/03-langgraph-for-ask-agent.md`). No new dependency for the
Narrator — it reuses `anthropic` (already adopted since feature 007) via the
existing `AnthropicLLMAdapter`, constructed with a new model ID
(`research.md` Decision 1). `.importlinter`'s existing `global-dependency-
rule` layers contract already keeps `langgraph` out of every module's
`application`/`domain` package, including `experience`'s own, with no config
change needed.

**Storage**: PostgreSQL 16 — no new tables (`narrator_outputs`,
`playbook_actions`, `ask_queries` all exist since feature 001's migration,
`data-model.md`). One real schema change: `ALTER TYPE declined_reason ADD
VALUE 'insufficient_history'` (`research.md` Decision 6 — a genuine Alembic
migration, found by reading the actual DDL rather than trusting the prose
schema doc, which doesn't flag the column's exact SQL type). This feature is
the first real writer of `narrator_outputs` and `ask_queries`, and the first
real reader of `playbook_actions` (already seeded).

**Testing**: pytest + `hypothesis` (backend), Vitest (frontend). Narrator: the
fact-check function is pure and unit-tested directly against known-good/
known-bad `(sentence, VerifiedFactSet)` pairs, no DB, no LLM; `LLMPort` faked
in the use-case test, matching every prior feature's fake-in-tests precedent.
Ask agent: `tests/strategy.md`'s already-documented "Ask agent (LangGraph)
tests" section (`research.md` Decision 8) — branch-coverage tests invoke the
compiled graph directly with fake ports (one per REQ-M9-02 intent plus
decline/fallback/handoff), a read-only-enforcement test asserting
`AskAgentToolkit.build_tools()` never registers a write method, and one
separate real-network/real-Postgres latency test for the 3s budget. This
feature also removes `tests/golden_replay/test_placeholder.py`'s
`@pytest.mark.skip` and implements the real snapshot/truncate/replay/assert
test (`research.md` Decision 7) — the first time this suite has ever run for
real.

**Target Platform**: Same Docker Compose stack as features 001–007 — no new
service, no `docker-compose.yml` change. One new `Settings` field
(`generation_model_id`) and one new env var
(`GENERATION_MODEL_ID=claude-sonnet-5`, `decisions/02-repo-and-tooling.md`'s
Claude model ID pinning table) added to `backend/app/config.py` and
`.env.example`, mirroring `reader_model_id`'s existing pattern exactly.

**Project Type**: Web application — backend (Python/FastAPI) and frontend
(React/TypeScript) both change. Backend: new `app.narrator.{domain,
application,adapters}` content, extended `app.experience.{application,
adapters}`, one new route (`POST /api/ask`), one migration. Frontend: a new
`narrator-panel.tsx` on the existing dashboard page, and `frontend/src/ask/`
(currently an empty scaffold, `.gitkeep` only) gets its first real components
(`research.md` Decision 9).

**Performance Goals**: Ask agent — 3 seconds for intent-matched questions
(REQ-M9-08), 2.5s-per-attempt/no-retry on the classify step
(`architecture/06-error-handling.md`, already specified, not re-decided here,
now actually measured for the first time by this feature's own latency test).
Narrator — 10s/1-retry budget, same document; not directly measured against
the ~40s end-to-end target since the Narrator stays a manually-triggered
script in this feature (`research.md` correction 2) — the live-triggered path
that budget describes doesn't have a caller yet, the same status feature 007
already recorded for Tone/Intent's own timing budget.

**Constraints**: REQ-M7-P1/P2/P3 — the Narrator never introduces an
unverified fact, never re-ranks, never invents an action outside the
playbook; all three are structural: `RankedContribution`'s order is read
once and never re-sorted, `fact_check()` is the only gate between a candidate
sentence and persistence, and `PlaybookPort.list_active()` is the only source
`NarratedAction` instances are ever constructed from. REQ-M9-P1/P2/P3 — the
Ask agent never recalculates the score (`AskAgentToolkit` wraps only
`get_*`/`query_*` methods, no `FindingRepositoryPort.save`/`quarantine`-style
method is ever reachable to register as a tool — `tests/strategy.md`'s
read-only-enforcement test makes this a mechanical guarantee, not a
convention), never builds a case against a colleague, never answers without
a source. `declined_reason`'s DB-level `ENUM` type constrains
`insufficient_history` to a real migration, not a soft convention.

**Scale/Scope**: Fixture-driven, same as every prior feature — the real,
already-ingested/read/scored/validated Meridian ledger. Ana (has a confirmed
baseline since feature 007) exercises the Narrator's real headline and the
Ask agent's "is this normal for X?" happy path; Diego (no confirmed baseline)
exercises the new `insufficient_history` decline path honestly, without a
synthetic fixture.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Yes — every Narrator reason cites real `evidence_event_ids` (unchanged, sourced from the `Finding`s it narrates); the mechanical fact-check (REQ-M7-06/07) is this principle's second, independent enforcement layer for *prose*, the same role the validation gate's `cited_event_missing` check already plays for *findings* (feature 007). Every Ask agent answer carries evidence links/sources (REQ-M9-P3) | **Pass** — FR-006, FR-007, FR-021 |
| **P2 The Model Interprets, Code Calculates** | Yes — the Narrator's `LLMPort` call never produces a number; every point value in a `NarratedReason` is read verbatim from `score_contributions`, already computed by M6. The Ask agent never recalculates the score (REQ-M9-P1) — its tools are read-only lookups, its `classify_intent` step is a closed-enum classification, not arithmetic | **Pass** — FR-013, FR-019; `.importlinter`'s `scoring-domain-purity` contract is untouched (this feature adds no code to `app.scoring`) |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — the Narrator never re-ranks (REQ-M7-P2, findings arrive pre-ranked and stay that way); the Ask agent never rescores and never composes a draft itself, only hands off (FR-012a) | **Pass** — FR-001, FR-010, FR-012a |
| **P4 A Human Always Sends** | No send capability touched — the draft-handoff response carries context for feature 009 to pick up later; nothing in this feature sends anything anywhere | N/A |
| **P5 Admit What We Cannot See** | Yes — `narrator: null` when no `narrator_outputs` row exists yet, never an empty object masquerading as "narrated, nothing to say" (REQ-M8-P2's existing discipline, extended to this new field); `insufficient_history` makes a real data gap (no confirmed baseline) visibly distinct from a disconnected source, rather than collapsing both into one generic "can't answer" message | **Pass** — `data-model.md`'s `narrator: null` rule; Clarifications' `insufficient_history` addition |
| **P6 Silence Is a Success State** | Yes — a healthy score run with nothing to narrate produces no `narrator_outputs` row at all (Edge Cases); the Ask agent declines instead of guessing on every one of its three "I don't know / I won't" paths | **Pass** — Edge Cases, User Story 3 |
| **P7 Context Over Sentiment** | Yes — the "is this normal for X?" intent reuses the Tone reader's own per-stakeholder baseline (feature 007) rather than a generic sentiment comparison, including that reader's own honest abstention threshold (now `insufficient_history`) | **Pass** — `research.md` Decision 4, Clarifications |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — `app.narrator` gains its first real `domain/` ring (pure fact-check function, no I/O) exactly where `.importlinter`'s `global-dependency-rule` already anticipated it (`containers` already lists `app.narrator` with `domain` as optional); `LangGraphAskAgent`/`AskAgentToolkit` sit exactly where `decisions/02`/`03` already assign them — no new architectural choice, only building what was already decided | **Pass** — `research.md` Decisions 1–4; no `.importlinter` config change needed |
| **P9 Test-First Determinism** | Yes, more fully than any prior feature — this is the feature that turns golden-replay from a documented placeholder into a real, passing test (`research.md` Decision 7), closing the exception three prior Complexity Tracking tables recorded. The Ask agent's own non-determinism (LLM calls) stays isolated behind `LLMPort`/fake ports in every test except the one dedicated real-network latency test, matching `tests/strategy.md`'s design | **Pass — no Complexity Tracking exception carried forward** |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | Yes — `AskComponentResponse` gains one enum value rather than a new response-type hierarchy for the handoff (`research.md` Decision 5); the Ask agent's toolkit stays at exactly 3 tools, no speculative 4th; no checkpointer is wired in (`decisions/03`'s "off in the MVP" stays off — this feature doesn't turn it on) | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | Yes — `narrator-panel.tsx` and `frontend/src/ask/`'s new components follow the existing `dashboard/` package's typed, TanStack-Query pattern (`types.ts` gains `narrator`/Ask-response types); no ad hoc fetches, no untyped props | **Pass** |
| Full-Stack §4 Testing Strategy | Yes — Narrator and Ask agent each need dedicated unit coverage plus the golden-replay integration test now going live | **Pass** — see Testing above |
| Full-Stack §5 Security & Quality Gates | Yes — no new external credential (reuses `ANTHROPIC_API_KEY`); `asked_by_user_id` sourced from the bearer token, never the request body, matching every existing "who did this" column's discipline | **Pass** |

**No violations requiring justification.** This feature closes the one
Complexity Tracking exception every prior feature carried forward
(golden-replay), rather than adding a new one.

## Project Structure

### Documentation (this feature)

```text
specs/008-narrator-and-ask-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — new ports/value objects, migration, contract deltas
├── contracts/
│   ├── dashboard.md      # Phase 1 output — the one new DashboardResponse field
│   └── ask.md            # Phase 1 output — POST /api/ask, first real implementation
└── quickstart.md         # Phase 1 output — narrate a run, ask 4 real questions, verify golden-replay
```

### Source Code (repository root)

Fills in `backend/app/narrator/`, already scaffolded (empty) since feature
001, and extends `backend/app/experience/`, already substantial since feature
006 — following `decisions/02-repo-and-tooling.md`'s module→package mapping
and `architecture/08-class-diagrams.md` diagram 4's named class catalog:

```text
backend/
├── app/
│   ├── narrator/
│   │   ├── domain/
│   │   │   ├── entities.py            # NEW — this module's first real
│   │   │   │                           #   content: RankedContribution,
│   │   │   │                           #   VerifiedFactSet, FactCheckResult,
│   │   │   │                           #   NarratedReason, NarratedAction,
│   │   │   │                           #   NarratorOutput
│   │   │   └── services.py            # NEW: fact_check(sentence, facts) —
│   │   │                               #   pure, no I/O
│   │   ├── application/
│   │   │   ├── ports.py               # NEW: ScoreContextPort,
│   │   │   │                           #   ClientContextPort, PlaybookPort,
│   │   │   │                           #   NarratorOutputRepositoryPort
│   │   │   │                           #   (LLMPort imported from
│   │   │   │                           #   app.readers.application, not
│   │   │   │                           #   redefined — research.md Decision 1)
│   │   │   ├── use_cases.py           # NEW: NarrateScoreRunUseCase
│   │   │   └── prompts/
│   │   │       └── narration_v1.py    # NEW: versioned structured-output
│   │   │                               #   prompt template (REQ-M7-08) —
│   │   │                               #   lives in application/, not
│   │   │                               #   adapters/ (matches IntentReader's
│   │   │                               #   own prompt/schema placement,
│   │   │                               #   feature 007); a real
│   │   │                               #   `import-linter` violation was
│   │   │                               #   found and fixed here during
│   │   │                               #   T040 — application must never
│   │   │                               #   import its own adapters package
│   │   └── adapters/
│   │       └── sqlalchemy_repository.py  # NEW: SqlAlchemyScoreContext
│   │                                       #   Repository, SqlAlchemyClient
│   │                                       #   ContextRepository, SqlAlchemy
│   │                                       #   PlaybookRepository, SqlAlchemy
│   │                                       #   NarratorOutputRepository
│   ├── experience/
│   │   ├── application/
│   │   │   └── ports.py               # extended: LedgerQueryPort,
│   │   │                               #   AskQueryRepositoryPort,
│   │   │                               #   NarratorReadPort; AskAgentPort,
│   │   │                               #   AskAgentState
│   │   │                               #   (no separate use-case class —
│   │   │                               #   ask_router.py calls AskAgentPort
│   │   │                               #   directly, the same thin
│   │   │                               #   orchestration pattern
│   │   │                               #   decisions/02-repo-and-
│   │   │                               #   tooling.md already describes
│   │   │                               #   for M8/M10's routers)
│   │   └── adapters/
│   │       ├── ask_agent_graph.py     # NEW — the only file importing
│   │       │                           #   langgraph: LangGraphAskAgent,
│   │       │                           #   AskAgentToolkit, QueryLedgerTool,
│   │       │                           #   QueryFindingsTool (validated-only
│   │       │                           #   filtered — /speckit-analyze C1),
│   │       │                           #   QueryScoreRunsTool
│   │       ├── ask_router.py          # NEW: POST /api/ask
│   │       ├── coverage_router.py     # extended: ask_intent_coverage field
│   │       │                           #   (/speckit-analyze E1)
│   │       └── sqlalchemy_repository.py  # extended: SqlAlchemyLedgerQuery
│   │                                       #   Repository, SqlAlchemyAsk
│   │                                       #   QueryRepository,
│   │                                       #   SqlAlchemyNarratorRead
│   │                                       #   Repository
│   └── config.py                      # extended: generation_model_id
├── scripts/
│   └── run_narrator.py                # NEW: manual NarrateScoreRunUseCase
│                                        #   trigger, mirrors compute_score.py/
│                                        #   run_readers.py's existing pattern
├── migrations/
│   └── versions/
│       └── 0002_ask_insufficient_history.py  # NEW: ALTER TYPE (id
│                                               #   shortened to fit
│                                               #   alembic_version's
│                                               #   VARCHAR(32))
└── tests/
    ├── narrator/
    │   ├── test_fact_check.py         # pure, no DB, no LLM — known-good/
    │   │                               #   known-bad sentence/fact-set pairs
    │   ├── test_narrate_score_run_use_case.py  # LLMPort faked
    │   └── test_run_narrator_real_db.py  # real-DB integration
    ├── experience/
    │   ├── test_ask_agent_graph.py    # branch coverage — one test per
    │   │                               #   REQ-M9-02 intent + decline +
    │   │                               #   fallback + handoff, fake ports,
    │   │                               #   no live model call
    │   ├── test_ask_agent_toolkit.py  # read-only-enforcement — asserts no
    │   │                               #   write method is ever registered
    │   └── test_ask_agent_latency.py  # real network, real Postgres — 3s
    │                                    #   budget (REQ-M9-08)
    └── golden_replay/
        └── test_placeholder.py        # RENAMED/replaced with the real
                                         #   snapshot/truncate/replay/assert
                                         #   test (research.md Decision 7)

frontend/
└── src/
    ├── dashboard/
    │   ├── narrator-panel.tsx         # NEW: headline/reasons/actions
    │   ├── narrator-panel.test.tsx    # NEW
    │   ├── dashboard-page.tsx         # extended: renders NarratorPanel +
    │   │                               #   AskBar
    │   └── types.ts                   # extended: NarratorSummary field on
    │                                    #   DashboardResponse
    └── ask/                            # currently .gitkeep only
        ├── ask-bar.tsx                # NEW: Idle/Thinking/Answered
        ├── ask-bar.test.tsx           # NEW
        ├── components/                # NEW: one renderer per closed-set
        │   │                           #   component type (delta-breakdown,
        │   │                           #   baseline-comparison, etc.)
        │   └── ...
        ├── api.ts                     # NEW: POST /api/ask client, typed
        └── types.ts                   # NEW: AskComponentResponse,
                                         #   AskFallbackResponse

.env.example                            # extended: GENERATION_MODEL_ID
architecture/07-api-spec.md             # extended: DashboardResponse.narrator,
                                          #   AskComponentResponse.component's
                                          #   8th value, AskFallbackResponse.
                                          #   declined_reason's 5th value
data-base/10-ddl-appendix.md            # extended: declined_reason's 5th
                                          #   enum value
data-base/08-schema-experience.md       # extended: same
```

**Structure Decision**: Same monorepo, filling in `narrator/` — empty since
feature 001 — with real code for the first time, and extending `experience/`
— substantial since feature 006 — with the Ask agent, per
`decisions/02-repo-and-tooling.md`'s already-ratified module→package mapping.
No new top-level backend directory, no new Docker service — one new outbound
dependency (`langgraph`, confined to one adapter file) alongside the
`anthropic`/`openai` dependencies features 005/007 already introduced. On the
frontend, `frontend/src/ask/` — an empty scaffold directory since before this
feature — gets its first real content; no new top-level frontend directory.

## Complexity Tracking

> No violations requiring justification — see Constitution Check above. This
> feature closes the one exception carried forward by every prior feature's
> own Complexity Tracking table (golden-replay's `@pytest.mark.skip`,
> `research.md` Decision 7) rather than adding a new one.
