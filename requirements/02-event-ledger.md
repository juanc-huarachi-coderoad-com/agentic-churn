# 02 · Event ledger (M2)

Tier 1 · Ingestion — spec §7 (M2)

## Purpose

One append-only timeline that is the single source of truth. Nothing is updated or deleted; corrections are new events that supersede old ones. This is the foundation the entire system replays from.

## User stories

- As an **engineer**, I want to drop all derived projections and replay the ledger, so that I can reproduce the current dashboard exactly and trust the system's math.
- As a **CS lead**, I want response times measured in business hours against the client's real calendar, so that a promise made at 5pm Friday isn't judged as broken by Saturday morning.
- As an **auditor**, I want every event tamper-evident, so that the score's evidence trail can be trusted.

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M2-01 | THE SYSTEM SHALL append every envelope from M1 as an immutable event; THE SYSTEM SHALL NEVER update or delete an existing event row. |
| REQ-M2-02 | THE SYSTEM SHALL record two timestamps on every event: `occurred_at` (when it happened in the source system) and `recorded_at` (when the ledger learned of it). |
| REQ-M2-03 | WHEN a correction to a prior event arrives (e.g. an edited message, a reclassified ticket), THE SYSTEM SHALL append a new event that references and supersedes the prior one, never mutate the prior row. |
| REQ-M2-04 | THE SYSTEM SHALL attempt thread stitching across channels (email → ticket → chat) using participant, subject/reference, and timing heuristics, and SHALL record a confidence score for each stitched link. |
| REQ-M2-05 | THE SYSTEM SHALL compute **response pairs** (a client message and the first qualifying reply) measured in business hours according to the client profile's working calendar and timezone. |
| REQ-M2-06 | THE SYSTEM SHALL maintain derived projections (timeline view, per-person rollups, response-pair table) as materialized views that are fully rebuildable by replaying the event log from empty. |
| REQ-M2-07 | WHEN a replay is triggered (profile edit, weight change, or manual request), THE SYSTEM SHALL rebuild all projections deterministically from the immutable event log and produce an identical result to the equivalent live-computed state. |
| REQ-M2-08 | THE SYSTEM SHALL hash-chain events (each event's hash includes the previous event's hash) to make the ledger tamper-evident. |
| REQ-M2-09 | THE SYSTEM SHALL allow querying the ledger "as of" any past `recorded_at` value, enabling honest replay of what was known on a given historical date. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M2-P1 | The ledger SHALL NOT store any judgment, score, or severity label — only observed facts (e.g. "19 business hours elapsed" is storable; "the promise was broken" is not — that belongs to M5). |
| REQ-M2-P2 | THE SYSTEM SHALL NEVER perform a destructive UPDATE or DELETE against the `events` table outside of crypto-shredding key destruction (see `11-non-functional-requirements.md`). |
| REQ-M2-P3 | Projections SHALL NOT be treated as a source of truth — they must always be reproducible from the event log alone. |

## Inputs / Outputs

- **Input:** envelopes from M1 collectors.
- **Output:** immutable `events` table; projections (`event_threads`, `response_pairs`, `rollups`) consumed by M5 interpreters and M8/M9 for evidence lookups.

## Non-functional constraints

- Determinism: same ledger + same code/prompt/weight versions → identical score, always (spec §9.4).
- Scale target: ~50k–200k events/year per deployment — a relational database is sufficient; no message broker required.
- Dashboard reads must be pure database reads (< 1s), so projections must be pre-materialized, not computed on request.

## Acceptance criteria

- [ ] Dropping all projection tables and replaying the event log reproduces the current dashboard exactly (spec §14.3).
- [ ] No `UPDATE`/`DELETE` statement exists in application code against the `events` table (verified by code review / DB grants).
- [ ] Response-pair business-hour calculations match the client profile's working calendar in all test cases, including across a timezone and a weekend boundary.
- [ ] The hash chain validates end-to-end on demand.

## Traceability

Spec §7 M2, §6.4 (audit: append-only, hash chaining), §9.4 (determinism, scale), §14.3 (replay criterion).
