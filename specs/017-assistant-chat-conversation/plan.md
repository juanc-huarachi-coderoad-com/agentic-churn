# Implementation Plan: Assistant Chat Conversation

**Branch**: `017-assistant-chat-conversation` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-assistant-chat-conversation/spec.md`

## Summary

The Ask assistant (`AskBar`) currently answers exactly one question at a time: it discards the
previous exchange the moment a new one starts, leaves typed text stuck in the input after submit,
treats every conversational message ("hi") as an unrecognized question, and never uses earlier
turns to interpret a follow-up. This plan turns it into a real multi-turn chat: a persistent,
append-only transcript rendered in `AskBar` (frontend-only state, no new store — `research.md`
Decision 1), an input that clears on send, a small, fixed-string fast path for
greetings/thanks/capabilities questions that skips the classify LLM call entirely (Decision 4),
and a client-resent, server-validated 5-turn history that the `classify_intent` node uses to
resolve follow-up questions — without ever touching the fact-checked text-generation path
(Decision 3). No database migration and no new service are required (Decision 0/2's finding: this
is a single-account product, and memory is session-only by spec, so the client's own transcript is
the only copy of "history" that needs to exist).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript + React 18 (frontend) — unchanged, no new
language/runtime introduced.

**Primary Dependencies**: FastAPI, LangGraph (`langgraph`, `langchain_core`) for the Ask agent
graph (unchanged — this feature extends the existing graph, does not add a new orchestration
dependency); TanStack Query for the `/api/ask` mutation (unchanged); no new package required —
`research.md` explicitly rejects the one dependency that would have been new (a LangGraph
checkpointer backend).

**Storage**: PostgreSQL 16 (unchanged) — no schema change, no migration (`research.md`,
"Data-base impact: none"). Conversation history itself is never persisted to storage; it lives
only in `AskBar`'s in-memory component state for the duration of the session.

**Testing**: pytest (backend, `backend/tests/experience/test_ask_agent_graph.py` and
`test_ask_agent_latency.py`), Vitest + Testing Library (frontend, `frontend/src/ask/*.test.tsx`) —
both existing suites, extended, no new tooling.

**Target Platform**: unchanged — Docker Compose, one stack per client deployment (server-side);
modern evergreen browsers (client-side).

**Project Type**: Web application (existing `backend/` + `frontend/` split).

**Performance Goals**: Preserve the existing Ask agent resilience budgets exactly —
`component_only` 2.5s/no-retry, `text_only`/`hybrid` +15s hard-capped text generation
(`architecture/06-error-handling.md`, unchanged by this feature). The new small-talk fast path is
strictly faster than today's equivalent (skips the classify call entirely — `research.md`
Decision 4); adding history to the classify prompt only, capped at 5 compact entries, keeps that
call's added latency small and bounded.

**Constraints**: History accepted by the backend is independently capped at the 5 most recent
entries regardless of what the client sends (Zero Trust, constitution §5); conversation memory is
session-only — nothing added by this feature may cause data to survive a page reload or be shared
across browser sessions/devices (spec.md's resolved clarifications).

**Scale/Scope**: One conversation per active dashboard session (single-account product,
`research.md` Decision 0) — no multi-tenancy, no per-account keying to build.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Check | Result |
|---|---|---|
| P1 Evidence or It Does Not Exist | No new claim-producing surface; `sources`/citation behavior for answered/decline paths is unchanged | Pass |
| P2 The Model Interprets, Code Calculates | History→prompt serialization is plain code (`data-model.md`); small-talk replies are fixed strings, not model output; scoring untouched | Pass |
| P3 Each Component Refuses to Do the Next One's Job | `detect_smalltalk` only pattern-matches and returns a fixed string — no ranking/judging added; `classify_intent` still only classifies | Pass |
| P4 A Human Always Sends | Unchanged — no send capability touched | Pass |
| P5 Admit What We Cannot See | Unchanged — degraded-data fallbacks (`_no_data_fallback`, `_unknown_person_fallback`, source-not-connected) all untouched | Pass |
| P6 Silence Is a Success State | Unchanged — no new UI manufactures concern | Pass |
| P7 Context Over Sentiment | Not implicated — this feature doesn't touch the Tone reader or baseline comparisons | Pass |
| P8 Clean Architecture | `history` flows Adapter (`ask_router.py`) → Application (`AskAgentPort.answer()` signature) → Adapter (`LangGraphAskAgent`/graph state) — no ring imports outward; frontend keeps API calls in `ask/api.ts`, state in the component, per P11 | Pass |
| P9 Test-First Determinism | No scoring/ledger code touched — golden-replay, reconciliation, monotonicity, no-LLM-in-scoring checks are all out of this feature's blast radius | N/A (unaffected) |
| P10 Simplicity Over Speculative Generality | Explicitly the driver of `research.md` Decisions 0, 1, 2 — rejected per-account keying, a global store, and a checkpointer backend, each because the simpler option already meets spec.md's actual (bounded, session-only) requirement | Pass |
| P11 Frontend standards | Feature-orined (`frontend/src/ask/`, unchanged location); server state via TanStack Query, UI state via local component state (no Zustand needed — Decision 1); types stay strict; tests extend the existing hierarchy | Pass |
| AI safety Rule 1 (structured output / closed prose inventory) | Small-talk replies are fixed strings, **not** added to the prose-generation inventory (`research.md` Decision 4 explicitly chose this to avoid a constitution amendment) | Pass |
| AI safety Rule 2 (prompt injection defense) | History is framed as data, never instructions, in the classify prompt, matching the existing pattern for `question`/`component_props` | Pass |
| AI safety Rule 4 (fact-check) | `generate_text` prompt is explicitly untouched by history (`research.md` Decision 3) — the fact-check guarantee's input surface does not grow | Pass |
| Resilience budgets | Unaffected/improved — see Performance Goals above | Pass |

No violations. **Complexity Tracking is empty — nothing to justify.**

## Project Structure

### Documentation (this feature)

```text
specs/017-assistant-chat-conversation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── ask.md           # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── experience/
│   │   ├── adapters/
│   │   │   ├── ask_agent_graph.py      # + detect_smalltalk node, history-aware classify prompt
│   │   │   └── ask_router.py           # + `history` field on AskRequest, pass-through to agent.answer()
│   │   └── application/
│   │       └── ports.py                # + `history` key on AskAgentState, `answer()` param
└── tests/
    └── experience/
        ├── test_ask_agent_graph.py     # + small-talk cases, history-affects-classify-only cases
        └── test_ask_agent_latency.py   # confirm small-talk path stays well under budget

frontend/
├── src/
│   └── ask/
│       ├── ask-bar.tsx                 # transcript state (turns[]), send-gating, clears input on submit
│       ├── ask-bar.test.tsx            # + multi-turn, input-clears, send-gating, null-declined_reason cases
│       ├── api.ts                      # postAsk gains optional `history` param
│       ├── types.ts                    # + HistoryTurn type (request-side only; response types unchanged)
│       └── components/
│           ├── answer-renderer.tsx     # unchanged — already renders a `parts` list; now called per-turn
│           └── answer-renderer.test.tsx # + per-turn invocation coverage if needed
```

**Structure Decision**: Existing feature-oriented `backend/app/experience/` (Clean Architecture
rings: adapters → application → domain, P8) and `frontend/src/ask/` (feature folder, P11) layout
is reused as-is — this feature extends both, introduces no new top-level module, no new package,
and no new cross-feature dependency.
