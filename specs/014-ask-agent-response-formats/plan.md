# Implementation Plan: Ask Agent Flexible Response Formats

**Branch**: `design/apply-new-mockup` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-ask-agent-response-formats/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Give the Ask agent a third response shape (Markdown text) and a fourth (a component-and-text hybrid), alongside its two existing shapes (a structured component, or a decline/fallback). Concretely: `ClassifyOutput` gains a same-call, schema-constrained `response_mode` field (`component_only | text_only | hybrid`) alongside the existing `intent`; `resolve_and_render` keeps fetching data exactly as it does today (same 3 read-only tools, same intent→tool mapping, no new grounding mechanism); when `response_mode` calls for text, a **second** `LLMPort.generate_structured` call generates Markdown prose grounded in that same already-fetched data, which then passes through a mechanical fact-check reusing the Narrator's existing `fact_check()`/`VerifiedFactSet` pattern (`app.narrator.domain.services`) before being attached. The response becomes an ordered list of parts (`text` and/or `component`) instead of one flat shape; for `component_only` (the unchanged default), that list is exactly one component part carrying the identical data returned today. Decline/fallback responses are untouched. Two governance artifacts ship alongside the code: an amendment to the constitution's AI-safety Rule 1 (naming the Ask agent as a third prose-generating component, governed by the same Rule 4 discipline) and a new resilience-budget row for the added second LLM call (text/hybrid responses get their own, larger time budget; `component_only` keeps today's exact 2.5s/no-retry/3s-total budget, unchanged).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript ~6.0 / React 18.3 (frontend) — both touched, first feature since 011 to touch `backend/` (012/013 were frontend-only)

**Primary Dependencies**: Existing — LangGraph (Ask agent only, `decisions/03-langgraph-for-ask-agent.md`), the Anthropic SDK via the existing `LLMPort.generate_structured` (unchanged signature — a second call to the same method, not a new port method), FastAPI/Pydantic (`ask_router.py`'s response models), TanStack Query (frontend, unchanged). New — one small frontend Markdown-rendering dependency (research.md Decision 4; none exists today, confirmed by inspecting `frontend/package.json`)

**Storage**: PostgreSQL — one small, additive schema change: `ask_queries` gains a `response_mode` column (`component_only | text_only | hybrid`, matching the existing lightweight logging convention) so FR-013's "no format-specific gap in the log" is real, not just claimed. No other table changes; no new entities

**Testing**: pytest + `hypothesis` (backend, existing) — new property-based tests for the reused fact-check path (mirroring `backend/tests/` conventions already established for the Narrator's `fact_check()`); `vitest` + `@testing-library/react` (frontend, existing) for the new part-rendering logic

**Target Platform**: Existing web app (FastAPI + React SPA), unchanged

**Project Type**: Web application — `backend/app/experience/`, `backend/app/narrator/domain/` (import only, no changes), and `frontend/src/ask/` are the only directories touched

**Performance Goals**: `component_only` responses (the default whenever no additional explanation is warranted, FR-002) MUST keep today's exact budget — no regression. `text_only`/`hybrid` responses, which now make two LLM calls instead of one, get their own explicit, larger budget (research.md Decision 3) — the same pattern this codebase already uses for the Draft composer's distinct 10s×1 budget vs. readers' 8s×2 vs. today's Ask-agent-classify-only 2.5s×0

**Constraints**: Every constitution AI-safety rule applies, extended, not relaxed: structured output everywhere (both the `response_mode` decision and the generated Markdown are schema-constrained `LLMPort.generate_structured` calls, never a raw completion); the Ask agent's tool registry stays exactly the 3 existing read-only tools — no new tool, no new grounding mechanism, so a question with genuinely no fetchable data still declines exactly as it does today (FR-012); every claim in generated Markdown is mechanically fact-checked, reusing the Narrator's existing pattern, never inventing a new one; client message content appearing inside generated Markdown is exempted from paraphrase and never treated as an instruction (FR-007, same discipline as Rule 2 already requires elsewhere)

**Scale/Scope**: Backend — `ask_agent_graph.py` (extend `ClassifyOutput`, add one new node + fact-check step, change terminal-state assembly), `experience/application/ports.py` (`AskAgentState`/`AskAgentResult` gain a `parts`-shaped answered case), `ask_router.py` (new `AskAnsweredResponse` replacing `AskComponentResponse`'s shape; `AskFallbackResponse` untouched), one Alembic migration (`ask_queries.response_mode`). Frontend — `ask/types.ts` (new `ResponsePart` discriminated union), `ask/components/answer-renderer.tsx` (iterate parts; existing 8-component switch becomes one part-kind branch, unchanged internally), one new `ask/components/markdown-text.tsx`. Governance — one constitution amendment, one architecture-doc resilience-budget addition

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Applies how | Status |
|---|---|---|
| P1 Evidence or It Does Not Exist | Text parts cite the same `sources` the component path already cites (FR-006); nothing here weakens citation | Pass |
| P2 The Model Interprets, Code Calculates | The new text-generation call interprets already-computed data into prose; it never recomputes a score or any numeric value — `backend/app/scoring/` is untouched | Pass |
| P3 Each Component Refuses to Do the Next One's Job | `resolve_and_render`'s data-fetch logic is unchanged; the new text-generation step only writes prose about data another part of the graph already fetched deterministically — it doesn't fetch, judge, or rank anything itself | Pass |
| P4 A Human Always Sends | Unaffected — no send capability exists or is added anywhere in this feature | Pass |
| P8 Clean Architecture — Dependency Rule | Reusing `app.narrator.domain.services.fact_check`/`VerifiedFactSet` from `app.experience`'s new fact-check step is a **domain-to-domain import**, explicitly allowed by P8 ("Domain imports nothing from this codebase except other Domain code") — not a layering violation | Pass |
| P9 Test-First Determinism | N/A to `backend/app/ledger/`/`backend/app/scoring/` (untouched); the reused fact-check logic already has property-based test coverage in its home module, extended here for the new call site | Pass (N/A) |
| P10 Simplicity Over Speculative Generality | `response_mode` reuses the *existing* 8 intents and 3 tools — it does not add a new tool, a new grounding mechanism, or a new "answerable-question" detector; a question with no fetchable data still declines exactly as today (FR-012) | Pass |
| AI Safety Rule 1 "Structured output everywhere" | **Requires amendment** — today's rule text names only Narrator/Draft composer as prose-generating components; this feature is the first place the Ask agent itself generates free prose. See Complexity Tracking below — this is a planned, justified extension flagged in spec.md's own Assumptions, not an oversight | Amendment required (justified) |
| AI Safety Rule 2 "Prompt injection defense" | The Ask agent's tool registry stays the same closed, read-only 3-tool set (FR unchanged); client message text appearing in generated Markdown is exempt from paraphrase, quoted-only, never an instruction (FR-007) — extends the existing discipline, doesn't relax it | Pass |
| AI Safety Rule 3 "Confidence is first-class" | N/A — this feature doesn't introduce a confidence/magnitude field; abstention (decline/fallback) is unchanged | Pass (N/A) |
| AI Safety Rule 4 "No new facts, mechanically checked" | Directly implemented by reusing the Narrator's `fact_check()` — this is the rule this feature depends on most, not one it risks | Pass |
| AI Safety Rule 5 "Versioned prompts" | The new text-generation prompt gets its own version constant, following the same convention `narrator`'s `VERSION` already establishes | Pass |
| Resilience budgets (`architecture/06-error-handling.md`) | **Requires a new row** — `component_only` keeps the existing 2.5s/no-retry/3s-total budget unchanged; `text_only`/`hybrid` need their own, larger budget since they make two LLM calls. See Complexity Tracking | Amendment required (justified) |

No violation here is a design mistake — both flagged items were anticipated and explicitly called out in spec.md's own Assumptions during `/speckit-specify`, precisely so they'd be addressed deliberately in planning rather than discovered as a surprise later.

## Project Structure

### Documentation (this feature)

```text
specs/014-ask-agent-response-formats/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── ask.md            # Phase 1 output — supersedes specs/008-.../contracts/ask.md's
│                          #   response-shape section for the answered case; decline/
│                          #   fallback section is carried forward unchanged
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/app/
├── experience/
│   ├── adapters/
│   │   ├── ask_agent_graph.py       # MODIFIED — ClassifyOutput gains response_mode;
│   │   │                             #   ClassifyOutput's ResponseMode enum added; new
│   │   │                             #   generate_text node + fact-check step; terminal
│   │   │                             #   states assemble a `parts` list
│   │   ├── ask_router.py            # MODIFIED — AskAnsweredResponse (parts-based)
│   │   │                             #   replaces AskComponentResponse's shape;
│   │   │                             #   AskFallbackResponse UNCHANGED
│   │   └── sqlalchemy_repository.py # MODIFIED — SqlAlchemyAskQueryRepository.log()
│   │                                 #   gains response_mode param
│   ├── application/
│   │   └── ports.py                 # MODIFIED — AskAgentState/AskAgentResult gain a
│   │                                 #   parts-shaped answered case; AskQueryRepositoryPort.
│   │                                 #   log() gains response_mode
│   └── domain/                      # APPENDED to the existing file (already holds dashboard/evidence/
│       └── entities.py              #   same "domain ring appears once a module needs it"
│                                     #   draft-composer entities) — adds ResponsePart/
│                                     #   TextPart/ComponentPart alongside them
├── narrator/domain/
│   ├── services.py                  # UNCHANGED — fact_check() imported, not modified
│   └── entities.py                  # UNCHANGED — VerifiedFactSet/FactCheckResult imported
└── alembic/versions/
    └── xxxx_add_ask_queries_response_mode.py  # NEW migration

frontend/src/ask/
├── types.ts                          # MODIFIED — ResponsePart discriminated union;
│                                      #   AskComponentResponse -> AskAnsweredResponse
├── components/
│   ├── answer-renderer.tsx           # MODIFIED — iterates parts; existing 8-component
│   │                                  #   switch logic unchanged, now one part-kind branch
│   └── markdown-text.tsx             # NEW — renders a TextPart's markdown
└── ask-bar.tsx                       # MODIFIED — passes the parts-based answer through;
                                       #   no behavior change to idle/thinking/answered states

.specify/memory/constitution.md       # AMENDED — AI Safety Rule 1's component inventory
architecture/06-error-handling.md     # AMENDED — new resilience-budget row for text/hybrid
architecture/04-ai-safety-and-model-usage.md  # AMENDED — model-call inventory table
specs/008-narrator-and-ask-agent/contracts/ask.md  # UNCHANGED — this feature's own
                                       #   contracts/ask.md (above) is the current source of
                                       #   truth for the answered-response shape going forward
```

**Structure Decision**: Existing web-application split (`frontend/` + `backend/`), unchanged. Backend work is entirely inside `backend/app/experience/` (the Ask agent's home module) plus a read-only domain-to-domain import from `backend/app/narrator/domain/` — no new backend module, no new port type beyond extending two existing ones. Frontend work is entirely inside `frontend/src/ask/`. Three governance documents are amended alongside the code, not as an afterthought.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| AI Safety Rule 1's prose-generating-component inventory must add the Ask agent | The feature's own explicit purpose (spec.md FR-004, resolved via clarification) is genuine model-generated Markdown from the Ask agent — the constitution's rule text must name where this codebase generates free prose, and today's text doesn't, so leaving it unamended would make the shipped code silently non-compliant with its own governing document | Not extending the rule (keeping Ask agent text-generation "ungoverned") was rejected outright — that would mean shipping the one new prose-generation path in this codebase with *no* mechanical fact-check requirement stated anywhere, exactly the gap Rule 4 exists to close. Reusing Rule 4's existing mechanism (not inventing a parallel one) is what makes the amendment additive/consistent rather than a new category of risk |
| A new, larger resilience budget for `text_only`/`hybrid` Ask agent responses | Two sequential `LLMPort.generate_structured` calls (classify, then text generation) cannot fit inside the existing 2.5s/no-retry/3s-total budget sized for exactly one call | Keeping every Ask agent response inside the existing 2.5s/3s budget was rejected: it would force text/hybrid responses to either skip the fact-check (unacceptable per Rule 4) or silently violate REQ-M9-08's documented 3s guarantee. This codebase already has per-component-differentiated budgets (Draft composer's 10s×1 is the closest precedent for "a second, heavier LLM step") — adding one more differentiated row is consistent with that existing pattern, not a new kind of exception |
