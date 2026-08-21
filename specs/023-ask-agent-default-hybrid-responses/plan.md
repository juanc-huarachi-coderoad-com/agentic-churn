# Implementation Plan: Ask Agent Default Hybrid Responses

**Branch**: `023-ask-agent-default-hybrid-responses` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-ask-agent-default-hybrid-responses/spec.md`

## Summary

Every Ask Agent answer that renders a generative-ui component must now also carry a
short (≤3 sentence), executive-toned text explanation of what the component shows, in
the same reply — not occasionally, by default. The mechanism for this already shipped
in `specs/014-ask-agent-response-formats` (a `hybrid` response mode: ordered
`TextPart`/`ComponentPart` list, grounded + fact-checked text generation, 15s hard
timeout, graceful degradation to component-alone on failure). The gap being closed is
that `014`'s classify step is explicitly biased *away* from hybrid (`component_only`
is "the default whenever you're unsure — prefer it"), so hybrid rarely fires, and its
text prompt is framed as "answer the question" rather than "explain the visual."

The approach: collapse `ResponseMode` from three values (`component_only | text_only |
hybrid`) to two (`text_only | hybrid`), making hybrid the only outcome whenever a
structured intent resolves to a component; reframe the text-generation prompt around
explaining the visual in ≤3 sentences; leave `write_to_stakeholder` (draft-only)
untouched since it never reaches this code path. This is a targeted change to one
backend adapter file and its tests — no new port, no migration, no frontend change,
no new API contract shape.

## Technical Context

**Language/Version**: Python 3.12 (backend only — no frontend change)

**Primary Dependencies**: FastAPI, LangGraph (Ask-agent orchestration, per
`decisions/03-langgraph-for-ask-agent.md`), Anthropic Claude (Sonnet-class, via the
existing `LLMPort`/`AnthropicLLMAdapter`) — all already in use, no new dependency

**Storage**: PostgreSQL — `ask_queries.response_mode` is an existing free-text nullable
column (migration `0005_ask_queries_response_mode.py`); no schema change, historical
`"component_only"` rows remain valid as history

**Testing**: pytest (`backend/tests/experience/test_ask_agent_graph.py`,
`test_ask_agent_latency.py`)

**Target Platform**: Linux server (Docker Compose), unchanged

**Project Type**: Web application (backend + frontend) — this feature touches
**backend only**

**Performance Goals**: No new latency ceiling. The already-shipped, already-accepted
15s-capped text-generation budget (typical ~7-8s per spec 014's live testing) simply
applies to virtually every structured-intent answer now, instead of only the subset
the classifier previously routed to `hybrid`/`text_only`. The former `component_only`
2.5s fast path is retired as a distinct outcome.

**Constraints**: Reuse the existing `LLMPort.generate_structured` signature (no port
change); reuse the existing per-sentence `fact_check`/`VerifiedFactSet`/UUID-stripping
machinery unchanged; `write_to_stakeholder` must keep returning draft-only, unchanged;
decline/fallback behavior unchanged; every response still logged with no gap.

**Scale/Scope**: One backend adapter file
(`backend/app/experience/adapters/ask_agent_graph.py`) plus its two existing test
files. No new module, no new class of component, no new frontend code.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.4.0:

| Principle / Rule | Assessment |
|---|---|
| P1 Evidence or It Does Not Exist | **Pass** — accompanying text is grounded in and fact-checked against the same fetched `component_props` as the visual; mechanism unchanged. |
| P2 Model Interprets, Code Calculates | **Pass** — no scoring code touched. |
| P3 Component boundaries | **Pass** — no cross-module responsibility shift. |
| P4 A Human Always Sends | **Pass** — no send capability added. |
| P5 Admit What We Cannot See | **Pass** — unaffected. |
| P6 Silence Is a Success State | **Pass** — the text prompt only states facts present in the data (existing, unchanged instruction); a calm account still produces a calm blurb, not manufactured concern. |
| P7 Context Over Sentiment | **Pass** — unaffected (Tone reader untouched). |
| P8 Clean Architecture | **Pass** — all changes stay inside the existing Adapters-ring file; no new inward/outward dependency introduced. |
| P9 Test-First Determinism | **Pass** — no ledger/scoring change; existing Ask-agent tests updated for the new default, not weakened. |
| P10 YAGNI | **Pass, and reinforced** — this change *removes* a mode (`component_only`) rather than adding one; `route_after_resolve_and_render`'s branch gets simpler, not more branched. |
| P11 Frontend | **Pass** — no frontend change; `AnswerRenderer`/`ResponsePart` already render an ordered `parts` list generically. |
| AI Safety Rule 1 (structured output; response-format decision schema-constrained) | **Pass in substance** — `response_mode` remains a schema-constrained enum field on the same classify call, just with 2 values instead of 3. **Constitution text itself needs a follow-up amendment** (see below) — it currently names the decision as `component_only` vs `text_only` vs `hybrid`. |
| AI Safety Rule 4 (fact-check) | **Pass** — reuses `fact_check()` unchanged. |
| Resilience budgets paragraph | **Constitution text needs a follow-up amendment** — it currently gives `component_only` its own separate 2.5s/no-retry budget as a distinct, common case. Once `component_only` is retired, that row no longer describes a reachable outcome for the 8 structured intents; the `text_only`/`hybrid` 15s-capped budget becomes the only one for that path (this is not a *new* budget — it is the existing, already-shipped-and-accepted `014` budget applying to virtually all responses instead of a subset). |

**Result**: No Core Principle (P1-P11) is violated or redefined — this passes the gate.
Two places in the constitution's **Development Workflow & Quality Gates** section
(not a Core Principle) contain verbatim, now-stale language naming `component_only`
as a live, distinct mode with its own budget. Per this project's own established
precedent (the `1.3.0 → 1.4.0` amendment was made *for* `spec 014` introducing
`hybrid` in the first place — see the constitution's Sync Impact Report), a MINOR
constitution amendment updating Rule 1's inventory sentence and the resilience-budgets
paragraph is planned as part of this feature's implementation tasks, not treated as a
silent drift. This is flagged here (Assumptions) rather than discovered as a surprise
later, matching that same precedent's own stated discipline.

## Project Structure

### Documentation (this feature)

```text
specs/023-ask-agent-default-hybrid-responses/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── ask.md            # Phase 1 output — supersedes 014's timing/mode-inventory notes only
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── experience/
│       └── adapters/
│           └── ask_agent_graph.py   # ResponseMode enum, ClassifyOutput default,
│                                    # _classify_prompt, _text_generation_prompt,
│                                    # route_after_resolve_and_render, answer()
│                                    # parts assembly, log_result default — all edited
└── tests/
    └── experience/
        ├── test_ask_agent_graph.py     # updated: fakes/assertions for 2-way enum
        └── test_ask_agent_latency.py   # updated: branches on the new default

.specify/memory/constitution.md         # MINOR amendment: Rule 1 inventory sentence +
                                         # resilience-budgets paragraph (see research.md)
```

No `frontend/` changes. No new migration. No new module or port.

**Structure Decision**: This is a surgical change within the existing web-application
structure's backend — one adapter file in the `experience` module's Adapters ring,
its two test files, and a documentation-only constitution amendment. No new
directories, no Option-2 scaffolding changes needed.

## Complexity Tracking

*No entries — no Core Principle is violated. The one required follow-up (constitution
text amendment for Rule 1 / resilience budgets) is a documentation update to match
already-approved product behavior, matching this project's own established precedent
from the `014` amendment; it is not a violation requiring justification.*
