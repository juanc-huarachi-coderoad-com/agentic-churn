# 07 · Narrator (M7)

Tier 3 · Reasoning — spec §7 (M7), §12.1

## Purpose

Turn calculated facts into sentences a human wants to read. Receives findings already ranked — it never decides what matters.

## User stories

- As a **CS lead**, I want "Ana stopped greeting us — and she signs the renewal," not "negative sentiment detected," so that I understand *why* it matters here.
- As a **CS lead**, I want every proposed action to have an owner and a date, so that it's actionable rather than a wish.

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M7-01 | THE SYSTEM SHALL receive findings/issues pre-ranked by the scoring engine and SHALL NOT alter their order. |
| REQ-M7-02 | THE SYSTEM SHALL produce, per scoring run: one headline, a list of reasons (each with its point contribution and evidence link), and a prioritized action list. |
| REQ-M7-03 | Each generated reason SHALL follow the pattern: **a person, a number, and why it matters here** (e.g. "We took 19 hours to reply. We promised 4."), not generic sentiment language. |
| REQ-M7-04 | Proposed actions SHALL be drawn from a human-authored **playbook** of standard actions, personalized by the model with real names, ticket numbers, and dates — never invented from scratch. |
| REQ-M7-05 | Every action in the output SHALL include an **owner** and a **when** — an action without both SHALL NOT be displayed. |
| REQ-M7-06 | THE SYSTEM SHALL mechanically check that every number and name in the narrator's output already exists in its structured input (findings/issues/profile) before display. |
| REQ-M7-07 | IF the mechanical fact-check (REQ-M7-06) fails for any sentence, THEN THE SYSTEM SHALL discard that sentence rather than display an unverifiable claim. |
| REQ-M7-08 | THE SYSTEM SHALL use a versioned, structured-output prompt for narration; changing the prompt SHALL be a tracked, replayable event. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M7-P1 | The narrator SHALL NEVER introduce a fact, number, or name absent from its structured input. |
| REQ-M7-P2 | The narrator SHALL NEVER re-rank or re-weight findings — ranking is M6's output, consumed as-is. |
| REQ-M7-P3 | The narrator SHALL NEVER invent an action outside the human-authored playbook. |

## Inputs / Outputs

- **Input:** ranked findings/issues + point contributions (M6), client profile (names, roles), playbook (human-authored action templates).
- **Output:** `narrator_outputs` (headline, reasons[], actions[]) consumed by M8 (dashboard) and M9 (ask-agent fallback answers).

## Non-functional constraints

- Structured output only; prose generated once, at the end, from validated structured content (spec §12.5).
- Narration must complete within the ~40s end-to-end score-update budget.

## Acceptance criteria

- [ ] Every number/name in a narrator sentence traces to an input field (automated check passes on 100% of generated outputs before display).
- [ ] Every displayed action has both an owner and a date.
- [ ] Swapping the finding ranking order (test harness) changes the narrator's emphasis without the narrator re-deriving its own ranking.

## Traceability

Spec §7 M7, §12.1 (narrator patterns), §12.5 (model safety / structured output / versioned prompts), §17 Q7 (playbook sign-off owner — open question).
