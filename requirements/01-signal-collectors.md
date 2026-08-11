# 01 · Signal collectors (M1)

Tier 1 · Ingestion — spec §7 (M1), §6.1, §13.2

> **Phasing note:** this module's requirements are source-agnostic by design — the same collector interface (REQ-M1-01) serves every source, Phase 1 or Phase 2. What differs by phase is *which* sources are actually connected: **Phase 1** ships Gmail, Zendesk, and warehouse telemetry; **Phase 2** adds Slack Connect, CSAT, and Calendar/transcripts. See `decisions/01-mvp-scope-and-phasing.md` for the full rationale, including why chat and meeting transcripts specifically wait for Phase 2.

## Purpose

Get material out of source systems and onto the event ledger, without interpreting it. One adapter per source, all implementing the same interface, plus a dedicated collector for the absence of expected contact.

## User stories

- As a **CS lead**, I want every ticket, email, chat message and usage change captured automatically, so that nothing depends on someone remembering to log it.
- As the **system**, I need identity resolution so that a message from `ana.reyes@meridian.com` is recognized as stakeholder `stk_ana`, not an anonymous sender.
- As a **CS lead**, I want to know what the system *could not* see, so that I never mistake silence-because-broken for silence-because-healthy (P5, P6).

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M1-01 | THE SYSTEM SHALL implement one adapter per connected source (tickets, email, chat, product usage, surveys, meetings, CRM/contracts), each conforming to a single common collector interface (`fetch`, `normalize`, `emit_envelope`). |
| REQ-M1-02 | WHEN a source supports webhooks, THE SYSTEM SHALL subscribe for near-real-time delivery, AND SHALL additionally run scheduled polling for correctness. |
| REQ-M1-03 | WHEN a collector runs (webhook or poll), THE SYSTEM SHALL fetch a deliberate overlap window with the previous run and de-duplicate using an idempotency key derived from the source's native record ID. |
| REQ-M1-04 | WHEN a raw signal is normalized, THE SYSTEM SHALL attempt to resolve each participant address/user ID to a stakeholder in the current client profile version. |
| REQ-M1-05 | IF a participant cannot be resolved to a known stakeholder, THEN THE SYSTEM SHALL emit the envelope with `identity_status = unresolved` rather than guessing a match. |
| REQ-M1-06 | THE SYSTEM SHALL run a scheduled **absence collector** that emits an `absence` event type when an expected contact (e.g. a promised weekly sync, an overdue response) does not occur within its defined window. |
| REQ-M1-07 | WHEN each collector run completes, THE SYSTEM SHALL produce a **coverage report** stating which sources were read, the time window covered, and the reason for any gap. |
| REQ-M1-08 | WHEN a source's credentials fail or the source is unreachable, THE SYSTEM SHALL mark that source `disconnected` in the coverage report and continue operating on the remaining sources (graceful degradation, never all-or-nothing). |
| REQ-M1-09 | THE SYSTEM SHALL redact sensitive data (per the client profile's `exclusions` list, e.g. `legal_threads`, `commercial_negotiation`) at the collector, before the envelope is persisted, and SHALL record that a redaction occurred. |
| REQ-M1-10 | THE SYSTEM SHALL wrap every raw signal in a standard **envelope** (source, native ID, occurred-at timestamp, resolved/unresolved participants, redaction flags, raw payload reference) before handing it to the event ledger (M2). |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M1-P1 | Collectors SHALL NOT assign severity, priority, or importance to any signal. |
| REQ-M1-P2 | Collectors SHALL NOT filter signals based on perceived importance — filtering by exclusion rules only. |
| REQ-M1-P3 | Collectors SHALL NOT interpret what a product area or stakeholder role means — that belongs to M3. |
| REQ-M1-P4 | Collectors SHALL NOT write to, or take any action in, a source system (read-only scopes only). |
| REQ-M1-P5 | The identity resolver SHALL NOT guess a stakeholder match below a defined confidence threshold — it must abstain and mark `unresolved`. |

## Inputs / Outputs

- **Input:** source-system APIs/webhooks (Zendesk, Jira, Intercom, Gmail, Microsoft 365, Slack Connect, Teams, product telemetry warehouse, CSAT/NPS tools, calendar/transcripts, Salesforce/contract store); current version of the client profile (M3) for identity resolution targets and `exclusions`.
- **Output:** envelopes appended to the event ledger (M2); one coverage report per run persisted for M8's coverage line.

## Non-functional constraints

- Read-only, narrowest available OAuth/API scopes per source, documented per source (spec §6.4).
- Message bodies encrypted at rest immediately on ingestion; keys scoped per deployment.
- Running any collector twice MUST produce no duplicate events (spec §14.3 engineering acceptance criterion).

## Acceptance criteria

- [ ] Re-running a collector over an overlapping window produces zero duplicate ledger entries.
- [ ] An unresolved sender never silently attaches to an existing stakeholder.
- [ ] A coverage report exists for every run, including runs where a source failed.
- [ ] Disconnecting one source does not stop collection from the others.
- [ ] Every excluded thread type is verifiably absent from stored envelopes.

## Traceability

Spec §7 M1, §6.1 (Sources), §6.3 (data deliberately not collected), §6.4 (privacy/security), §13.2 (honest limitations), §14.3 (no-duplicates criterion).
