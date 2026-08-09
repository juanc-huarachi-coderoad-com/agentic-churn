# 05 · Interpreters / readers (M5) & Validation gate (M5a)

Tier 3 · Reasoning — spec §7 (M5, M5a), §12.4, §12.5

## Purpose

M5 turns raw ledger material into structured **findings**. Each reader answers exactly one question and cites the events it used. M5a rejects anything unproven before it can reach the score — the mechanical enforcement of product principle P1.

## User stories

- As a **CS lead**, I want to know that Ana's tone changed *relative to how Ana normally writes*, not against some generic sentiment scale, so that the signal reflects this specific relationship (P7).
- As an **engineer**, I want every finding to cite real event IDs, so that a hallucinated claim is structurally impossible to score.
- As a **CS lead**, I want a reader to say "no history, no opinion" rather than fabricate a baseline, so that I can trust a "still learning" state over a false confidence.

## The eight readers

| Reader | Type | Question it answers |
|---|---|---|
| Commitment | Deterministic code | Did a response exceed what we promised, in business hours? |
| Usage | Statistics | Has activity deviated beyond normal variance? |
| Recurrence | Embeddings + clustering | Is this the same problem returning? |
| Absence | Statistics | Is expected contact missing? |
| Relationship | Graph diff | Has the cast of people changed? |
| **Tone** | **LLM** | Is this person writing differently *than they normally do*? |
| **Intent** | **LLM** | Are there escalation, competitive or contractual phrases? |
| **Meeting** | **LLM** | What did we verbally promise, and by when? |

## Functional requirements — readers (M5)

| ID | Requirement |
|---|---|
| REQ-M5-01 | THE SYSTEM SHALL implement each reader as an independent function/service that consumes ledger events + client profile context and emits zero or more `finding` records. |
| REQ-M5-02 | Every finding SHALL carry: `type`, `magnitude` (0–1, size of the change), `confidence` (0–1, certainty of the reader), `cited_event_ids[]`, `reader_version`. |
| REQ-M5-03 | THE SYSTEM SHALL keep `magnitude` and `confidence` as two separate fields — a small, certain change and a large, uncertain guess must never collapse into one number. |
| REQ-M5-04 | WHEN a reader lacks sufficient history to establish a baseline (e.g. a new stakeholder with no prior tone samples), THE SYSTEM SHALL abstain — emit no finding — rather than produce a low-confidence guess. |
| REQ-M5-05 | Every finding SHALL cite the specific event IDs it was derived from; a finding with zero cited events SHALL be structurally unrepresentable (schema-enforced non-empty array). |
| REQ-M5-06 | THE Tone reader SHALL compute deviation relative to a **baseline frozen at a human-confirmed healthy period** for that specific stakeholder — never against an absolute/generic sentiment scale. |
| REQ-M5-07 | THE Commitment reader SHALL compute elapsed business hours (via M2 response pairs) against the profile's `commitments[].threshold_business_hours`, using deterministic arithmetic only — no model call. |
| REQ-M5-08 | THE Usage reader SHALL flag a deviation only when it exceeds a statistically defined variance threshold from that metric's own historical distribution (not a fixed percentage). |
| REQ-M5-09 | THE Recurrence reader SHALL use embedding similarity plus clustering to group tickets/messages describing the same underlying issue, and SHALL NOT use a generative LLM call to make the clustering decision. |
| REQ-M5-10 | THE Absence reader SHALL flag missing expected contact only against a defined expectation (a commitment, a recurring meeting, a typical response rhythm) — never against an arbitrary silence duration. |
| REQ-M5-11 | THE Relationship reader SHALL diff the set of active participants over a rolling window against the profile's stakeholder list and flag additions/disappearances. |
| REQ-M5-12 | THE Tone, Intent, and Meeting readers SHALL call an LLM with a **closed, structured output schema** (enumerated categories / bounded numeric fields) — free-form prose output is not a valid reader output. |
| REQ-M5-13 | THE Intent reader SHALL classify against a closed enumeration (e.g. `escalation`, `competitive_mention`, `contractual_reference`, `none`) with confidence, never open text categories. |
| REQ-M5-14 | THE Meeting reader SHALL extract verbal commitments (what was promised, by whom, by when) only from transcripts with documented consent, and SHALL cite the transcript segment. |
| REQ-M5-15 | THE SYSTEM SHALL cache interpretation results per message — a given event is interpreted by a given reader version at most once, then cached forever. |

## Functional requirements — validation gate (M5a)

| ID | Requirement |
|---|---|
| REQ-M5A-01 | THE SYSTEM SHALL run four checks on every finding before it may reach the scoring engine: (1) schema valid, (2) cited events exist within the supplied evidence window, (3) sufficient evidence quantity for that finding type, (4) confidence at or above the type's floor. |
| REQ-M5A-02 | IF any check fails, THEN THE SYSTEM SHALL quarantine the finding — store it, tag it with the failure reason, and exclude it from scoring. |
| REQ-M5A-03 | THE SYSTEM SHALL NEVER attempt to repair or auto-correct a quarantined finding. |
| REQ-M5A-04 | Quarantined findings SHALL be retained and exposed (System health screen) as the ongoing evaluation dataset for reader quality. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M5-P1 | No reader SHALL rank or compare findings against each other — ranking belongs to M6/M7. |
| REQ-M5-P2 | No reader SHALL have tool access or side effects — interpreters read data and return structured output only (prompt-injection containment, spec §12.5). |
| REQ-M5-P3 | A finding SHALL NEVER be treated as an instruction, regardless of its content — client text is data, never control flow. |
| REQ-M5-P4 | THE SYSTEM SHALL NOT allow a reader's output to bypass the validation gate under any trigger (including "urgent" fast-path scoring, REQ-M6-09). |

## Inputs / Outputs

- **Input:** event ledger projections + client profile context (norms, calendar, multipliers' *definitions*, not the multipliers themselves).
- **Output:** `findings` (validated) → M6; `quarantine` (rejected) → System health screen only, never scored.

## Non-functional constraints

- Only affected windows are re-read on new events (spec §10 walkthrough — not a full re-read of history per event).
- Interpretation latency: reader output ready within the ~40s end-to-end score-update budget (see `11-non-functional-requirements.md`).
- All LLM calls use versioned, structured-output prompts (see `architecture/04-ai-safety-and-model-usage.md`).

## Acceptance criteria

- [ ] No finding reaches the scoring engine without passing all four validation checks (spec §14.3).
- [ ] A finding citing a non-existent event ID is quarantined, never scored (demonstrated in the spec §10 walkthrough).
- [ ] Re-interpreting the same event with the same reader version returns the cached result, not a new model call.
- [ ] Tone reader on a stakeholder with < N historical samples abstains (emits nothing) rather than emitting a low-confidence finding.

## Traceability

Spec §7 M5/M5a, §8.1 (confidence/magnitude as scoring inputs), §10 (walkthrough example of quarantine), §12.4–12.5 (AI usage, model safety), §15 (prompt injection risk).
