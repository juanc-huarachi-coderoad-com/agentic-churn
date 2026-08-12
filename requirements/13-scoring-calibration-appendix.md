# 13 · Scoring calibration appendix (M6)

Companion to `06-scoring-engine.md`. That file specifies the *shape* of every formula in the scoring model (`points = base × influence × criticality × confidence × magnitude × recency × damping`, the diminishing-returns ranks, the saturating score curve). This file specifies the **numbers and edge-case rules** a real implementation needs that the shape alone doesn't pin down — the gap flagged in the pre-build consistency review as a "critical enabler": without these, two engineers could both correctly implement `06-scoring-engine.md` and produce two different scores for the same evidence.

Every value below is a **seed default** (`decisions/00-open-questions-resolved.md` Q4) — reasonable, defensible, and replaceable in the Post-MVP weight-elicitation workshop without any architecture change, only a `finding_type_config`/config edit and a full replay (REQ-M6-25).

## REQ-M6-CAL-01 — Open-and-overdue ageing

| ID | Requirement |
|---|---|
| REQ-M6-CAL-01a | `recency` for an `open_overdue` finding SHALL be computed as `min(1.0 + ageing_rate × overdue_ratio, ageing_cap)`, where `overdue_ratio = (elapsed_business_hours − threshold_business_hours) / threshold_business_hours`. |
| REQ-M6-CAL-01b | `ageing_rate` SHALL default to **0.08** and `ageing_cap` SHALL default to **2.0** (a finding's recency can never more than double from ageing alone, however overdue it gets). |

**Worked check** (matches `examples/01-end-to-end-walkthrough.md` §9.2 exactly): ticket #456, threshold 4h, elapsed 19h → `overdue_ratio = (19−4)/4 = 3.75` → `recency = min(1.0 + 0.08 × 3.75, 2.0) = min(1.30, 2.0) = 1.30`.

## REQ-M6-CAL-02 — Resolved-state fade

| ID | Requirement |
|---|---|
| REQ-M6-CAL-02 | `recency` for a `resolved` finding SHALL be computed as `0.5 ^ (days_since_resolved / half_life_days)`, where `half_life_days` comes from that finding type's row in `finding_type_config` (`data-base/05-schema-reasoning.md`). |

At `days_since_resolved = half_life_days`, recency is exactly 0.5 (half strength) — hence "half-life." A `broken_response_promise` (half-life 14 days) resolved 14 days ago contributes half its peak points; resolved 28 days ago, a quarter.

## REQ-M6-CAL-03 — Damping function (feedback memory → weight)

| ID | Requirement |
|---|---|
| REQ-M6-CAL-03a | `damping_weights.weight` SHALL be computed as `clamp(0.5 ^ false_alarm_count × 1.15 ^ correct_count, 0, 1.0)`, recomputed on every new verdict for that pattern. |
| REQ-M6-CAL-03b | `resolved` verdicts SHALL NOT affect `weight` — they describe the underlying issue being fixed, not the reader's accuracy, and are tracked in `resolved_count` for the disclosure text only. |

**Worked check** (matches `examples/01-end-to-end-walkthrough.md` §14 and `data-base/07-schema-feedback.md`): one `false_alarm` verdict → `weight = 0.5^1 × 1.15^0 = 0.500`. A second `false_alarm` on the same pattern → `0.5^2 = 0.250`. A subsequent `correct` verdict partially recovers trust: `0.5^2 × 1.15^1 = 0.2875` — the pattern is never fully "forgiven" back to 1.0 by a single correct call after two false alarms, which is the intended asymmetry (losing trust is faster than regaining it).

## REQ-M6-CAL-04 — Tone reader abstention threshold

| ID | Requirement |
|---|---|
| REQ-M6-CAL-04 | THE Tone reader SHALL require at least **5** prior messages from a stakeholder within a human-confirmed baseline window (`data-base/03-schema-ledger.md` `baseline_confirmations`) before producing any finding about that stakeholder; below that count it SHALL abstain (REQ-M5-04). |

Five is deliberately conservative for an MVP seed value — few enough that a moderately active stakeholder clears it within the first couple of weeks, high enough that a single unusually terse email doesn't get compared against a "baseline" of one prior sample.

## REQ-M6-CAL-05 — Identity resolution confidence threshold

| ID | Requirement |
|---|---|
| REQ-M6-CAL-05a | An exact match (`identity_map.resolved_by = exact_match`) SHALL always resolve — no threshold applies. |
| REQ-M6-CAL-05b | A fuzzy match SHALL be surfaced as a suggestion for human confirmation only at confidence ≥ **0.90**; below that, THE SYSTEM SHALL record `unresolved` and surface no suggestion at all (a low-confidence guess shown to a human is still a guess wearing a UI). |
| REQ-M6-CAL-05c | A fuzzy match SHALL NEVER auto-resolve regardless of confidence — only `exact_match` or `human_confirmed` are resolving states (REQ-M1-05). |

## REQ-M6-CAL-06 — Usage reader deviation threshold

| ID | Requirement |
|---|---|
| REQ-M6-CAL-06a | THE Usage reader SHALL flag a deviation only when **both** hold: the rolling z-score of the current window against the trailing 8-week baseline has `\|z\| ≥ 2.0`, **and** the absolute percentage change from the baseline mean is `≥ 10%`. |
| REQ-M6-CAL-06b | The `\|z\| ≥ 2.0` condition alone SHALL NOT be sufficient — it exists to prevent a reader from firing on a statistically "significant" but practically trivial change to a metric with very low natural variance. |

**Worked check:** `tracking_api` usage down 22% (`examples/01-end-to-end-walkthrough.md` §4) clears the 10% floor by more than 2×, and a 3-week sustained drop against an 8-week baseline comfortably clears `\|z\| ≥ 2.0` — both conditions hold, so the reader fires.

## REQ-M6-CAL-07 — Do heartbeat runs count toward the two-run stickiness rule?

| ID | Requirement |
|---|---|
| REQ-M6-CAL-07 | **Yes.** Every scoring run — regardless of `score_runs.trigger` (`new_event`, `burst_batch`, `urgent_fast_path`, `hourly_heartbeat`, `profile_edit_replay`, `weight_edit_replay`, `manual`) — SHALL count toward the two-consecutive-run requirement in REQ-M6-19. |

This was previously ambiguous. Resolving it any other way would mean a band change could get stuck waiting indefinitely for a *second new event* that might not arrive for days, even though the hourly heartbeat is already re-confirming the same score in the meantime (REQ-M6-24: "time itself changes the answer"). Counting every run keeps band stickiness meaningful without making it a de facto multi-day delay.

## REQ-M6-CAL-08 — Urgent-phrase fast path mechanics ("the double pass")

The urgent fast path (REQ-M6-23) has a chicken-and-egg problem: the full Intent reader is an LLM call that takes several seconds (`sequences/01-sequence-signal-to-score.md`: ~34s alongside Tone, running in the normal batched path) — it can't itself be the thing deciding, synchronously, whether to skip the batch window. The resolution is two distinct passes over the same new content:

| ID | Requirement |
|---|---|
| REQ-M6-CAL-08a | **Pass 1 — synchronous phrase router.** At ledger-append time, a cheap, deterministic keyword/phrase matcher (not an LLM call, not a reader, produces no finding) scans new message text against a short, versioned, human-maintained list of unambiguous urgency triggers (e.g. "cancel," "terminate contract," "legal," "competitor," "board"). A match sets `score_runs.trigger = urgent_fast_path` and skips the 30-second batch window (REQ-M6-22). |
| REQ-M6-CAL-08b | **Pass 2 — the real Intent reader.** The full LLM-based Intent reader (`requirements/05-interpreters-readers.md` REQ-M5-13) still runs exactly as it would on any other event, produces a normal structured finding, and goes through the validation gate like every other finding. Pass 1 never bypasses M5a — it only affects *when* the scoring engine recomputes, never *what* gets scored (REQ-M5-P4). |
| REQ-M6-CAL-08c | If Pass 1 fires but Pass 2's Intent reader subsequently abstains or produces a finding that fails validation, THE SYSTEM SHALL still have recomputed early — an early, unremarkable recompute is a lower-cost outcome than missing a genuine escalation, and the recompute itself carries no false information (scoring "nothing new" is a safe no-op). |

## Traceability

Companion to `requirements/06-scoring-engine.md` (REQ-M6-09, REQ-M6-11, REQ-M6-19, REQ-M6-22, REQ-M6-23), `requirements/04-feedback-memory.md` (REQ-M4-03), `requirements/05-interpreters-readers.md` (REQ-M5-04, REQ-M5-08, REQ-M1-05), `data-base/05-schema-reasoning.md` (`finding_type_config`), `data-base/07-schema-feedback.md` (`damping_weights`), `data-base/03-schema-ledger.md` (`baseline_confirmations`).
