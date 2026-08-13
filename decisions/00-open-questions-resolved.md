# 00 · Open questions resolved

| | |
|---|---|
| **Document** | Decision record — resolves spec §17 "Open questions" |
| **Status** | Resolved for Phase 1 build start |
| **Date** | 2026-08-10 |
| **Source of truth** | `base/Churn-Sentiment-Agent-Product-Specification.md` §17 |

The product specification (§17) listed eight decisions that had to be made before build could start, each with an owner and a "needed by" phase. This document is where each one gets an actual answer. Where a decision splits work across time, it points at `decisions/01-mvp-scope-and-phasing.md`, which is the detailed map of what belongs in Phase 1 (the first working solution) versus Phase 2 (everything deferred).

**How to read the "Decision" column:** every answer names what happens in **Phase 1** first, then what's added in **Phase 2**. Nothing here removes a capability the spec describes — it only sequences when each piece gets built.

---

## Q1 — Which source systems for the first deployment?

| | |
|---|---|
| **Spec owner** | Product + client |
| **Needed by** | Phase 3 (spec v1.2 build order — was "Phase 1" under v1.0/v1.1's numbering) |
| **Decision** | **Phase 1:** Gmail (email), Zendesk (tickets), product-usage warehouse telemetry — three sources, read-only. **Phase 2:** Slack Connect (chat), CSAT survey, Calendar/meeting transcripts. |
| **Why these three first** | They cover the two things every account-health story in the spec's own examples (§2.1, §10) is actually built from: *what was promised and whether it was kept* (Zendesk → Commitment reader) and *what changed in behavior* (Gmail → Tone/Intent readers, warehouse → Usage reader). Three sources is also small enough that identity resolution, redaction, and coverage reporting can be proven correct before adding more surface area. |
| **What this defers** | The Absence and Relationship readers lose some of their signal in Phase 1 (no Slack channel to watch for silence or participant changes) — see `decisions/01-mvp-scope-and-phasing.md` for exactly what that means. The Meeting reader has nothing to read at all until Calendar/transcripts arrive in Phase 2. |
| **Traces to** | `requirements/01-signal-collectors.md`, `decisions/01-mvp-scope-and-phasing.md` |

## Q2 — Who authors and maintains the client profile?

| | |
|---|---|
| **Spec owner** | CS lead |
| **Needed by** | Phase 3 (spec v1.2 build order) |
| **Decision** | **Phase 1:** the CS lead edits the client profile directly as a YAML file (the exact format in spec §6.2), reviewed like any config change before being loaded. **Phase 2:** a profile editor UI (already in the screen inventory, spec §11.2) replaces direct file editing, with the same versioning rules underneath. |
| **Why** | The versioning and validation rules (`requirements/03-client-profile.md`) don't care whether the YAML came from a text editor or a form — building the UI is pure effort, not a blocker to getting a correct, working profile in front of the scoring engine. |
| **Traces to** | `requirements/03-client-profile.md`, `data-base/04-schema-context.md` |

## Q3 — Are meeting transcripts in scope, and is consent documented?

| | |
|---|---|
| **Spec owner** | Legal |
| **Needed by** | Phase 5 (spec v1.2 build order) |
| **Decision** | **No, not in Phase 1.** The Meeting reader and its transcript collector are deferred to **Phase 2**, and only turn on once documented, all-party consent exists for a given meeting series — this was already a hard rule in the spec (§6.3) and this decision doesn't loosen it. |
| **Why** | This is the one data source with a real legal precondition attached to it before a single byte can be collected (spec §6.3: "meeting recordings without documented consent from all parties" are explicitly excluded). Since Phase 1 already ships without it, there's no reason to rush the legal review — it can run in parallel with Phase 1 build, ready for Phase 2. |
| **Traces to** | `requirements/05-interpreters-readers.md` (Meeting reader), spec §6.3, §17 Q3 |

## Q4 — Base weights: who runs the elicitation workshop with CS leads?

| | |
|---|---|
| **Spec owner** | Product |
| **Needed by** | Phase 4 (spec v1.2 build order) |
| **Decision** | **Phase 1:** ship with seed default weights, pre-populated directly in the `finding_type_config` table (`data-base/05-schema-reasoning.md`) by the product team, using the values already worked through in this documentation set (e.g. broken response promise = 20 base points). **Phase 2:** Product runs a weight-elicitation workshop with real CS leads once there's a few weeks of real scored data to react to, and tunes the seed values based on it. |
| **Why** | Calibration workshops work far better against real, lived-with scores than against a blank spreadsheet — asking CS leads to weigh in before they've seen the system run even once would produce guesses, not calibration. The seed values are deliberately conservative and documented as such (`architecture/03-technology-stack.md`, `examples/01-end-to-end-walkthrough.md` §9). |
| **Traces to** | `requirements/06-scoring-engine.md`, `data-base/05-schema-reasoning.md` (`finding_type_config`) |

## Q5 — Retention period for message bodies?

| | |
|---|---|
| **Spec owner** | Legal + client |
| **Needed by** | Phase 3 (spec v1.2 build order) |
| **Decision** | **90 days**, proposed pending final legal sign-off with the client. **Phase 1:** message bodies are encrypted at rest as designed (`requirements/11-non-functional-requirements.md` REQ-NFR-11), but the *automatic* 90-day crypto-shredding job is **not** running yet — deletion is a manual, logged process. **Phase 2:** the scheduled shredding job (REQ-NFR-13) goes live, enforcing the 90-day window automatically. |
| **Why this is flagged, not hidden** | This is a genuine Phase 1 limitation, not a footnote — it means the "admit what we cannot see" principle (spec P5) applies to the system's own data handling, not just to coverage gaps. Anyone reviewing Phase 1 for a real deployment needs to know retention is policy-enforced, not yet code-enforced. This gets a visible line in `decisions/01-mvp-scope-and-phasing.md`'s "known Phase 1 limitations" table. |
| **Traces to** | `requirements/11-non-functional-requirements.md` REQ-NFR-13/14, spec §6.4 |

## Q6 — Where do notifications land — email, Slack, or in-app?

| | |
|---|---|
| **Spec owner** | CS lead |
| **Needed by** | Phase 6 (spec v1.2 build order) |
| **Decision** | **Phase 1:** in-app only — a band change or daily digest shows up on the dashboard the next time the CS lead opens it; nothing is pushed to them. **Phase 2:** email and/or Slack push notifications, per the CS lead's preference, using the `notifications.channel` column that already supports all three (`data-base/08-schema-experience.md`). |
| **Why** | In-app is the only channel that requires zero new integration and zero new "is this actually the client, not us, receiving something" risk review — the fastest path to a working demo. The schema was already designed to support the other two channels without a migration. |
| **Traces to** | `data-base/08-schema-experience.md` (`notifications`), spec §15 (over-notification risk) |

## Q7 — Who signs off the playbook of standard actions?

| | |
|---|---|
| **Spec owner** | CS lead |
| **Needed by** | Phase 8 (spec v1.2 build order) |
| **Decision** | **Marta (CS lead)** signs off the playbook — the same Marta referenced in the spec's own walkthrough example (§10, "Marta called Ana"). **Phase 1** ships with a deliberately small playbook: **3–5 standard actions** (e.g. escalate a broken commitment, call a disengaging sponsor before a known date, schedule a check-in after a milestone). **Phase 2** grows the library as real cases surface actions the initial 3–5 didn't anticipate. |
| **Why start small** | The narrator (`requirements/07-narrator.md`) is only allowed to personalize actions that already exist in the playbook — it can never invent one. A tiny, well-understood playbook is easier to keep to that rule honestly than a large one assembled speculatively before any real case has tested it. |
| **Traces to** | `requirements/07-narrator.md` REQ-M7-04, `data-base/08-schema-experience.md` (`playbook_actions`) |

## Q8 — Do we display the score to the account executive, or only to CS?

| | |
|---|---|
| **Spec owner** | Product |
| **Needed by** | Phase 6 (spec v1.2 build order) |
| **Decision** | **Phase 1:** CS lead only. **Phase 2:** the account executive gets a **read-only** view of the same dashboard — same evidence trace, same "no send" boundary, no separate scoring or interpretation for their view. |
| **Why** | The AE persona is explicitly in scope (spec §3.1: "what do I need to know before the renewal call?"), but giving them access before the score has proven itself with the CS team risks the exact trust problem the spec warns about (§15, "false alarms erode trust") spreading to a second audience before it's earned with the first. |
| **Traces to** | `requirements/00-overview-and-glossary.md` (personas table), spec §3.1, §15 |

---

## Summary table

| # | Question | Phase 1 decision | Phase 2 addition | Owner |
|---|---|---|---|---|
| 1 | Source systems | Gmail, Zendesk, Warehouse | Slack, CSAT, Calendar | Product + client |
| 2 | Profile authoring | CS lead, YAML file | Profile editor UI | CS lead |
| 3 | Meeting transcripts | Out of scope | In scope, consent-gated | Legal |
| 4 | Base weights | Seed defaults | Elicitation workshop | Product |
| 5 | Retention | 90 days, manual deletion | Automated shredding job | Legal + client |
| 6 | Notification channel | In-app only | Email / Slack | CS lead |
| 7 | Playbook sign-off | Marta (CS lead), 3–5 actions | Expanded library | CS lead |
| 8 | AE visibility | Not visible | Read-only view | Product |

See `decisions/01-mvp-scope-and-phasing.md` for how these eight decisions add up to the full Phase 1 / Phase 2 boundary across every module.
