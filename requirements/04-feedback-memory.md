# 04 · Feedback memory (M4)

Tier 2 · Context — spec §7 (M4)

## Purpose

Remember what the team said the system got wrong. No retraining, no fine-tuning — learning the user can read.

## User stories

- As a **CS lead**, I want to mark a finding as a false alarm, so that the system stops raising that same pattern repeatedly.
- As a **CS lead**, I want to see *why* a card's weight was reduced, so that the system's "learning" is never a silent black box.

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M4-01 | THE SYSTEM SHALL allow any finding-bearing card to be marked with a verdict: `correct`, `false_alarm`, or `resolved`. |
| REQ-M4-02 | WHEN a verdict is recorded, THE SYSTEM SHALL match it against the finding's type and originating pattern (reader type + event signature class) to compute a damping weight for future occurrences of that pattern, using the exact formula in `requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-03a/b. |
| REQ-M4-03 | THE SYSTEM SHALL apply damping as one multiplicative term (`0 ≤ damping ≤ 1.0`) in the scoring formula (see `06-scoring-engine.md`, REQ-M6-01). |
| REQ-M4-04 | WHEN a damped finding is displayed, THE SYSTEM SHALL show the damping reason in plain language (e.g. "weight reduced — your team dismissed this pattern twice"). |
| REQ-M4-05 | THE SYSTEM SHALL NEVER retrain or fine-tune any model as a result of feedback — damping is a stored numeric weight, not a model update. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M4-P1 | Feedback memory SHALL NOT silently delete or hide a dismissed finding type — it must remain visible, just damped and labeled. |
| REQ-M4-P2 | Feedback memory SHALL NOT be usable to damp an entire reader type globally in one action — damping applies to matched patterns, not blanket suppression. |

## Inputs / Outputs

- **Input:** verdict clicks from dashboard cards, evidence trace panel, ask-agent answers (M8/M9).
- **Output:** `feedback_verdicts`, `damping_weights` tables consumed by M6 on every scoring run.

## Non-functional constraints

- Feedback controls: one click, no modal, no confirmation toast (spec §11.6).
- Damping weight changes must be visible/auditable — never applied invisibly.

## Acceptance criteria

- [ ] Marking a card `false_alarm` **once** measurably reduces the `damping` term for the next matching finding (e.g. to 0.500); a **second** `false_alarm` on the same pattern reduces it further (e.g. to 0.250) — per the exact formula in `requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-03a (`weight = clamp(0.5 ^ false_alarm_count × 1.15 ^ correct_count, 0, 1.0)`).
- [ ] The damping reason string is always present and accurate whenever `damping < 1.0` on a displayed card.
- [ ] No model weights or prompts change as a side effect of feedback.

## Traceability

Spec §7 M4, §8.1 (damping term in the formula), §11.4 (feedback controls on evidence panel), §15 (Goodhart's law risk mitigation). Exact damping formula and worked values: `requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-03.
