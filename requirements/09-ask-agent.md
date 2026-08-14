# 09 · Ask agent (M9)

Tier 4 · Experience — spec §7 (M9), §12.2

## Purpose

The question box. Answers by building UI components, not paragraphs. Looks facts up; never recalculates the score.

## User stories

- As a **CS lead**, I want to ask "why did the score go up?" and get a delta breakdown with traces, not a paragraph, so I can act immediately.
- As a **support lead**, I want the agent to say "I'm not sure what you mean" rather than guess, so I don't act on a misread question.

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M9-01 | THE SYSTEM SHALL classify each incoming question into a closed set of intents, each mapped to a specific UI component to render. |
| REQ-M9-02 | THE SYSTEM SHALL support at minimum the following intent → component mappings: "why did the score go up?" → delta breakdown with per-cause points and traces; "is this normal for X?" → baseline-vs-current comparison; "who's gone quiet?" → stakeholder cards with last-seen; "what's the top risk?" → ranked issue list; "what should we do?" → action checklist with owners/dates; "what did we promise them?" → commitments and status; "show me everything about X" → filtered timeline; "write to X about this" → hands off to the draft composer (M10). |
| REQ-M9-03 | THE SYSTEM SHALL answer every question by looking up already-computed data (ledger, findings, score_runs, narrator_outputs) — it SHALL NEVER trigger a new score computation. |
| REQ-M9-04 | IF a question does not match a known intent, THEN THE SYSTEM SHALL fall back to a plain-text answer, clearly marked as such, with sources attached — never a fabricated component. |
| REQ-M9-05 | THE SYSTEM SHALL decline prediction questions ("will they cancel?") with an explicit statement that it describes today's evidence and does not forecast. |
| REQ-M9-06 | THE SYSTEM SHALL decline requests for judgments about colleagues or character assessments of client stakeholders, with an explicit refusal message. |
| REQ-M9-07 | WHEN a requested data source is not connected, THE SYSTEM SHALL respond "that source isn't connected" rather than silently omit the answer. |
| REQ-M9-08 | THE SYSTEM SHALL respond within 3 seconds for intent-matched questions (spec §9.4 target). |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M9-P1 | The ask agent SHALL NEVER recalculate or override the stored score. |
| REQ-M9-P2 | The ask agent SHALL NEVER build a case against an individual employee (Goodhart's-law guardrail, spec §15). |
| REQ-M9-P3 | The ask agent SHALL NEVER answer with an uncited claim — every rendered component and fallback text must carry evidence links. |

## Inputs / Outputs

- **Input:** user question (natural language), ledger/findings/score data for lookup.
- **Output:** `ask_queries` (question, matched intent, rendered component reference) logged for evaluation; rendered UI component or marked fallback text.

## Non-functional constraints

- < 3 seconds response time for intent-matched questions (spec §9.4; matches REQ-M9-08 exactly — this line previously read "≥ 3 seconds max," which said the opposite of the requirement).
- The small, fixed intent menu should resolve ~90% of real questions per spec §12.2 — measured, not assumed; tracked via `ask_queries.intent = 'fallback'` rate.

## Acceptance criteria

- [ ] Every listed intent in REQ-M9-02 renders its specified component type in a scripted test set.
- [ ] Asking a prediction question always returns the decline message, never a probability.
- [ ] Asking about an individual employee's performance always returns the decline message.
- [ ] The fallback rate (unmatched intents) is measured and visible in `ask_queries` for product tuning.

## Traceability

Spec §7 M9, §12.2 (question→component table, decline list), §9.3 (the "ask loop"), §9.4 (latency target). **Implementation:** `decisions/03-langgraph-for-ask-agent.md` — LangGraph fulfills every REQ-M9-ID above; none are renumbered or changed by that choice, it's an implementation decision, not a new requirement.
