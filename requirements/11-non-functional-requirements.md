# 11 · Non-functional requirements

Cross-cutting — spec §6.4, §9.4, §13, §14

## Performance

| ID | Requirement | Target |
|---|---|---|
| REQ-NFR-01 | Dashboard load | < 1s (pure database read) |
| REQ-NFR-02 | Event to updated score | < 60s (target ~40s) |
| REQ-NFR-03 | Ask agent response | < 3s |
| REQ-NFR-04 | Interpretation | Once per message per reader version, cached forever |
| REQ-NFR-05 | Scale | 50k–200k events/year per deployment — relational database, no message broker required |

## Availability

| ID | Requirement |
|---|---|
| REQ-NFR-06 | THE SYSTEM SHALL degrade gracefully on partial source failure — never all-or-nothing. |
| REQ-NFR-07 | THE SYSTEM SHALL freeze (not silently continue) the score when a required source is degraded, and display a visible staleness banner. |

## Determinism & replay

| ID | Requirement |
|---|---|
| REQ-NFR-08 | Same ledger + same code/prompt/weight versions SHALL always produce an identical score. |
| REQ-NFR-09 | Dropping all projections and replaying the ledger SHALL reproduce the current dashboard exactly. |

## Privacy & security (spec §6.4)

| Requirement | Approach | REQ ID |
|---|---|---|
| Sensitive data | Redacted at the collector, before storage; redactions recorded | REQ-NFR-10 |
| Encryption | Message bodies encrypted at rest; keys scoped per deployment | REQ-NFR-11 |
| Access | Read-only, narrowest available scopes, documented per source | REQ-NFR-12 |
| Deletion | Crypto-shredding — destroy keys, keep event skeleton so score history survives | REQ-NFR-13 |
| Retention | Message bodies expire on a schedule; findings and scores persist | REQ-NFR-14 |
| Isolation | One deployment, one client, one key set — no shared storage across deployments | REQ-NFR-15 |
| Audit | Append-only ledger with hash chaining for tamper evidence | REQ-NFR-16 |

## Data we deliberately do not collect (spec §6.3)

| ID | Requirement |
|---|---|
| REQ-NFR-17 | THE SYSTEM SHALL exclude threads listed in the client profile's `exclusions` (legal, HR, commercial negotiation). |
| REQ-NFR-18 | THE SYSTEM SHALL NEVER request write access to a source system. |
| REQ-NFR-19 | THE SYSTEM SHALL NEVER collect individual employee performance data. |
| REQ-NFR-20 | THE SYSTEM SHALL NEVER ingest meeting recordings without documented consent from all parties. |

## Hard product boundaries (spec §13.1)

| ID | Requirement |
|---|---|
| REQ-NFR-21 | One deployment SHALL serve exactly one client company. |
| REQ-NFR-22 | THE SYSTEM SHALL NEVER send anything to anyone (see `10-draft-composer.md` REQ-M10-P1). |
| REQ-NFR-23 | Human review SHALL be required for every recommendation and every message before any external use. |
| REQ-NFR-24 | The score SHALL always be presented as a risk estimate, never as a cancellation prediction. |
| REQ-NFR-25 | The client SHALL never be told or shown that they are being scored. |
| REQ-NFR-26 | The score SHALL NEVER be used as an input to individual employee performance management (written policy required, see spec §13.1). |

## Engineering acceptance criteria (spec §14.3) — global regression suite

| ID | Requirement |
|---|---|
| REQ-NFR-27 | Running any collector twice produces no duplicate events. |
| REQ-NFR-28 | Dropping all projections and replaying reproduces the current dashboard exactly. |
| REQ-NFR-29 | No finding reaches the score without validated evidence IDs. |
| REQ-NFR-30 | Score contributions reconcile to the total, to the decimal. |
| REQ-NFR-31 | Adding a negative finding never lowers the score. |
| REQ-NFR-32 | A score with a degraded source is visually distinguishable from a complete one. |
| REQ-NFR-33 | No model call exists anywhere in the scoring engine. |

## Success metrics (spec §14.1–14.2) — product-level, tracked post-launch

| Measure | Target |
|---|---|
| Lead time | Risk surfaced ≥ 2 weeks before the team would have escalated |
| Precision | ≥ 70% of At-risk alerts confirmed real by the team |
| Trust | ≥ 60% of alerts opened through to evidence |
| Quiet weeks are quiet | < 1 interruption per week when healthy |
| Action rate | ≥ 50% of proposed actions accepted or edited |
| Draft usefulness | ≥ 40% of drafts sent after light editing |

## Traceability

Spec §6.3–6.4, §9.4, §13, §14.1–14.3, §15 (risk table).
