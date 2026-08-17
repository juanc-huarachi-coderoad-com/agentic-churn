# Feature Specification: Production Hardening

**Feature Branch**: `011-production-hardening`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "011 production-hardening" — build-order Phase 11 (`base/Churn-Sentiment-Agent-Product-Specification.md` §16): "Automated retention/crypto-shredding job, role-based access control on top of authentication, observability, Post-MVP sources (Slack, CSAT, Calendar), weight-elicitation workshop, profile editor UI." Primary requirements: remaining items in `requirements/11-non-functional-requirements.md`; primary decisions: `decisions/01-mvp-scope-and-phasing.md`, `decisions/00-open-questions-resolved.md`.

## Clarifications

### Session 2026-08-16

- Q: How often should the automated retention/crypto-shredding job (User Story 1) run? → A: Daily — tightest compliance margin against the 90-day window, trivial cost at this deployment's 50k–200k events/year scale, and consistent with the existing hourly-heartbeat scheduled-job pattern from feature 004.
- Q: Who should be authorized to change a finding type's base scoring weight (User Story 4)? → A: `admin` role only — reuses the existing, currently-unused `admin` value in the `users.role` enum rather than opening this to every non-account-executive user; changing production scoring math going forward is a distinct, higher-stakes action than routine CS-lead work.
- Q: What should happen when a scheduled retention job run fails partway through? → A: Alert and auto-retry on the next scheduled run — no new alerting mechanism needed, and consistent with FR-003's idempotency guarantee that a re-run is always safe. **Revised 2026-08-16 (`/speckit-analyze` finding I1):** "alert" means the same structured logging every other scheduled job in this codebase already uses (`architecture/03-technology-stack.md`'s Phase 1 default), available the moment User Story 1 ships — not a dependency on User Story 3's tracing work. Once User Story 3 ships, the same failure additionally produces an operational trace, as a strict enhancement, not a prerequisite.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Message bodies expire automatically, on schedule (Priority: P1)

The system SHALL delete (crypto-shred) message-body content once it passes the client's agreed retention window, without a person having to remember to do it. Findings, scores, and evidence citations survive the deletion — only the underlying message text becomes permanently unreadable.

**Why this priority**: This closes the single Phase 1 limitation with real legal/compliance exposure (`decisions/00-open-questions-resolved.md` Q5: "retention is policy-enforced, not yet code-enforced"). Every day this stays manual is a day a client's data sits past its agreed retention window if a person forgets. It is the most urgent gap on the Phase 1 limitations list (`decisions/01-mvp-scope-and-phasing.md`).

**Independent Test**: Seed message-body events with `occurred_at` older than the retention window, run the scheduled job, and confirm the message bodies are unreadable while the originating events, findings, and scores remain intact and score history is unchanged.

**Acceptance Scenarios**:

1. **Given** a message-body event older than the retention window, **When** the scheduled retention job runs, **Then** the message body becomes permanently unreadable (its encryption key is destroyed) while the event's metadata (source, timestamp, participants) and every finding/score that cited it remain queryable exactly as before.
2. **Given** a message-body event younger than the retention window, **When** the scheduled retention job runs, **Then** the message body is left untouched.
3. **Given** the retention job has run, **When** a CS lead opens the evidence trace for a finding that cited a since-shredded message, **Then** the evidence still displays the finding's stored summary/citation metadata and clearly indicates the original message body is no longer available, rather than erroring or showing stale content.
4. **Given** the retention job runs a second time over a window it already processed, **When** it completes, **Then** no error occurs and no already-shredded content is affected (idempotent).

---

### User Story 2 - Account executives get a read-only view (Priority: P2)

The system SHALL let an authenticated account executive open the same dashboard, evidence trace, and coverage view a CS lead sees for their assigned client — with no ability to submit feedback verdicts, edit the client profile, request a draft, or ask the agent. Every other authenticated role continues to reach every endpoint exactly as it does today.

**Why this priority**: This is the first functional use of the `role` column that has existed, unenforced, since authentication shipped (`requirements/14-authentication.md` REQ-AUTH-P3, `data-base/12-users-and-auth.md`). It's deferred behind the retention job because it's a trust-scope expansion (`decisions/00-open-questions-resolved.md` Q8: giving a second audience access before the score has proven itself with the first risks the exact trust problem the product spec warns about) — appropriate now that ten feature phases of real, evidence-backed scoring exist to show them.

**Independent Test**: Log in as a user with `role = account_executive`, confirm the dashboard, evidence trace, and coverage screens render normally, and confirm every write-capable endpoint (feedback verdict, profile edit, draft request, ask agent) returns an authorization error rather than executing.

**Acceptance Scenarios**:

1. **Given** an authenticated user with `role = account_executive`, **When** they open the dashboard, **Then** they see the same score, evidence trace, and coverage information a CS lead sees for that client, with the same "no send" boundary and no separate scoring or interpretation for their view.
2. **Given** an authenticated account executive, **When** they attempt to submit a feedback verdict, edit the client profile, request a draft, or ask the agent, **Then** the system rejects the request with a clear authorization error and takes no action.
3. **Given** an authenticated user with `role = cs_lead` (or any role other than `account_executive`), **When** they use any existing endpoint, **Then** behavior is unchanged from before this feature — full access, exactly as today.

---

### User Story 3 - Operators can see what the running system is doing (Priority: P3)

The system SHALL emit structured traces and metrics for its key operational paths (collector runs, score recomputation, reader execution, Ask agent responses) so that an operator monitoring more than one deployment can compare health and diagnose a problem without reading raw logs line by line.

**Why this priority**: Structured logging alone (the Phase 1 choice, `architecture/03-technology-stack.md`) was explicitly sufficient for a single deployment; it stops being sufficient once there's more than one deployment to compare, or once a performance regression against `REQ-NFR-01…03`'s targets needs to be diagnosed after the fact rather than reproduced live.

**Independent Test**: Trigger a collector run, a score recomputation, and an Ask agent query against a running deployment, and confirm each produces a trace showing its duration and outcome (success/failure/degraded), queryable without reading raw application logs.

**Acceptance Scenarios**:

1. **Given** a collector run, a score recomputation, a reader execution, or an Ask agent query, **When** it completes, **Then** a trace exists recording its start time, duration, outcome, and (on failure) the failure reason.
2. **Given** an operator wants to know whether the current deployment is meeting `REQ-NFR-01…03`'s performance targets, **When** they inspect the collected metrics, **Then** they can see recent dashboard-load, event-to-score, and Ask-agent-response latencies without reproducing the scenario live.
3. **Given** a source's collector or an LLM-backed reader begins failing, **When** it happens, **Then** the failure is visible in the collected metrics within one collection interval, consistent with the existing coverage-report/reader-health signals already shown on the dashboard (`architecture/06-error-handling.md`).

---

### User Story 4 - Base weights can be recalibrated without a code deploy (Priority: P4)

Once Product has run the weight-elicitation workshop with real CS leads against real scored data (`decisions/00-open-questions-resolved.md` Q4), the system SHALL let a user with the `admin` role update a finding type's base point weight, with the change taking effect on the next score computation and a durable record of who changed which value, when, and from what.

**Why this priority**: The seed weights were always meant to be a starting point, not the final calibration (`decisions/01-mvp-scope-and-phasing.md`: "seed [weights] are deliberately conservative"). This is lower priority than retention/RBAC/observability because it depends on an external, real-world process (the workshop itself) that only becomes possible once a deployment has "a few weeks of real scored data to react to" — it cannot be exercised meaningfully on day one of this feature.

**Independent Test**: Update a finding type's base weight through the system, trigger a score recomputation, and confirm the new weight is reflected in the resulting score contribution while a prior, already-computed score run is unaffected.

**Acceptance Scenarios**:

1. **Given** a user with the `admin` role changes a finding type's base weight, **When** the next score recomputation runs, **Then** it uses the new weight, and the change is attributed to who made it, when, and what the previous value was.
2. **Given** a weight was changed after a score run already completed, **When** that earlier score run is viewed again, **Then** its stored value and contributions are unchanged (byte-identical to before the weight change, consistent with `REQ-NFR-08`'s determinism guarantee for the version of weights it actually ran against).
3. **Given** a user whose role is not `admin` (including a `cs_lead`) attempts to change a base weight, **When** they try, **Then** the system rejects the request.

---

### User Story 5 - CS lead edits the client profile without touching YAML (Priority: P5)

The system SHALL provide a profile editor screen that lets the CS lead view and edit the client profile (stakeholders, exclusions, renewal date, contract value band, communication norms) using the same versioning and validation rules the YAML-file workflow already enforces, with no new way to bypass those rules.

**Why this priority**: This replaces a workflow that already works (`decisions/00-open-questions-resolved.md` Q2: "building the UI is pure effort, not a blocker to getting a correct, working profile in front of the scoring engine"). It's a usability improvement, not a capability gap — appropriately last among the same-tier UI/process items.

**Independent Test**: Edit a client profile field through the editor screen and confirm a new profile version is created, validated exactly as a YAML upload would be, and immediately reflected in subsequent reader/scoring runs.

**Acceptance Scenarios**:

1. **Given** a CS lead opens the profile editor, **When** they view it, **Then** they see the current profile version's stakeholders, exclusions, renewal date, contract value band, and communication norms.
2. **Given** a CS lead submits a valid edit through the editor, **When** it's submitted, **Then** a new profile version is created and attributed to them, exactly as `requirements/03-client-profile.md`'s existing versioning rules already require for a YAML-sourced edit.
3. **Given** a CS lead submits an edit that would fail the existing profile validation rules (e.g. a malformed date, a reference to a nonexistent stakeholder), **When** they submit it, **Then** the editor rejects it with a clear, field-level error and creates no new version — exactly as an invalid YAML upload is rejected today.

---

### User Story 6 - The system reads from the Post-MVP sources (Priority: P6)

The system SHALL connect Slack Connect (chat), the CSAT/NPS survey tool, and Calendar/meeting transcripts (consent-gated, per source-series) using the same collector interface every Phase 1 source already implements, and SHALL restore the Absence and Relationship readers to full strength and activate the Meeting reader once their respective sources are connected.

**Why this priority**: Lowest priority by explicit product decision, not oversight — Phase 1 deliberately proved the hardest, most important thing (a defensible, evidence-backed number) on the smallest source set that could produce it (`decisions/01-mvp-scope-and-phasing.md`, "the one-sentence rule"). Every other user story in this feature hardens what already exists; this one adds breadth, which the same document says explicitly waits until the core is trusted.

**Independent Test**: Connect one new source (e.g. Slack Connect) in isolation, run its collector, and confirm new envelopes reach the event ledger, are visible in the coverage report, and feed the readers designed to consume them — without needing the other two Post-MVP sources connected.

**Acceptance Scenarios**:

1. **Given** Slack Connect is connected for a client, **When** its collector runs, **Then** chat messages reach the event ledger as envelopes (redacted/identity-resolved exactly as every other source already is), the coverage report reflects the new source, and the Absence and Relationship readers begin using chat-silence and channel-participant signals in addition to their existing email/ticket signals.
2. **Given** the CSAT/NPS survey tool is connected, **When** its collector runs, **Then** numeric CSAT scores feed the Usage reader as a second tracked metric and written survey comments feed the Tone reader, alongside their existing signals.
3. **Given** documented, all-party consent exists for a specific meeting series and Calendar/transcripts is connected for it, **When** a transcript from that series is collected, **Then** the Meeting reader activates and produces findings from it; **When** no consent is documented for a series, **Then** THE SYSTEM SHALL NEVER collect a transcript for that series.
4. **Given** none of the three Post-MVP sources is connected for a given client, **When** the dashboard is viewed, **Then** behavior is unchanged from Phase 1 — the Absence/Relationship readers stay in their documented "reduced" state and the Meeting reader stays inactive, exactly as `decisions/01-mvp-scope-and-phasing.md` already specifies.

---

### Edge Cases

- What happens when the retention job runs while a score recomputation is reading a message body in the same daily bucket the job is about to shred? (The job only ever targets a bucket whose entire day has already fully elapsed relative to the retention window at job start — never the current or most recent bucket a read could plausibly still be touching — so an in-flight read is never racing a shred of the same bucket. This is a scheduling-margin guarantee, not a transactional lock: it is not mechanically tested, only true by construction of which buckets the job selects. **Revised 2026-08-16 (`/speckit-analyze` finding U1):** narrowed from an unverified "never shredded mid-read" claim to the actual, weaker guarantee this design provides.)
- What happens when the retention job fails partway through a run? (FR-004a: logged via standard structured logging — independent of User Story 3 — and auto-retried on the next scheduled run; no manual step unless the failure recurs.)
- What happens when an account executive's `is_active` status is revoked mid-session? (Consistent with the existing token-revocation behavior in `requirements/14-authentication.md` — their next request with that token is rejected, not honored against a stale session. There is no separate per-client "assignment" to track: `REQ-NFR-21` already guarantees one deployment serves exactly one client, so every active account-executive user in a deployment sees that same one client.)
- What happens when an operator's trace/metrics backend is itself unreachable? (Collection, scoring, and every existing user-facing path must continue operating exactly as if observability were never added — degrade the diagnostic signal, never the product.)
- What happens when a weight change is submitted for a finding type that has no historical findings yet? (Accepted and recorded; it simply has no effect until a matching finding is scored.)
- What happens when a profile editor submission and a concurrent YAML-file edit target the same profile at once? (The existing profile versioning rules already define which one wins — this feature must not introduce a second, conflicting resolution path.)
- What happens when consent for a meeting series is later revoked after transcripts were already collected? (Already-collected transcripts and any findings derived from them are subject to the same retention/crypto-shredding path as any other message body — this feature does not add a second deletion mechanism.)
- What happens when a Post-MVP source's credentials fail after being connected? (Identical to any Phase 1 source failure — REQ-M1-08's graceful degradation applies without exception.)

## Requirements *(mandatory)*

### Functional Requirements

**Retention & crypto-shredding (User Story 1)**

- **FR-001**: THE SYSTEM SHALL run a scheduled job, at least once every 24 hours, that identifies every message body older than the client's configured retention window (default 90 days per `decisions/00-open-questions-resolved.md` Q5) and destroys its encryption key, rendering it permanently unrecoverable, while leaving the originating event's metadata, findings, and score history intact.
- **FR-002**: THE SYSTEM SHALL log every retention job run (start time, records evaluated, records shredded, any errors) to a durable, queryable record, independent of application logs.
- **FR-003**: THE SYSTEM SHALL be idempotent when the retention job is re-run over a window it has already processed — no error, and no effect on already-shredded content.
- **FR-004**: WHEN evidence for a finding cites a message body that has since been shredded, THE SYSTEM SHALL display the finding's stored citation metadata and clearly indicate the original content is no longer available, rather than erroring or fabricating content.
- **FR-004a**: WHEN a scheduled retention job run fails partway through, THE SYSTEM SHALL log the failure (structured, queryable independently of User Story 3's tracing — this requirement is fully satisfiable by User Story 1 alone) and SHALL automatically retry on the next scheduled run, with no manual step required unless the failure recurs. Once User Story 3 ships, the same failure additionally produces an operational trace, as an enhancement layered on top of this logging, not a replacement for it.

**Role-based access control (User Story 2)**

- **FR-005**: THE SYSTEM SHALL enforce that a user with `role = account_executive` can only reach read endpoints for the dashboard, evidence trace, and coverage view.
- **FR-006**: THE SYSTEM SHALL reject, with a clear authorization error, any attempt by an `account_executive`-role user to submit a feedback verdict, edit the client profile, request a draft, or query the Ask agent.
- **FR-007**: THE SYSTEM SHALL leave existing behavior unchanged for every role other than `account_executive` — no new restriction is introduced for `cs_lead` or any other existing role by this feature.
- **FR-008**: THE SYSTEM SHALL record which role a request was authorized under, alongside the existing per-action `*_user_id` attribution, wherever an access decision was enforced. Since `users.role` is mutable, this record must reflect the role **at the time of the decision**, not a value looked up later — satisfied by a structured log line emitted at each role-gated authorization point (`require_full_access`, `require_admin`), not a new database column on every action table (`/speckit-analyze` finding G1).

**Observability (User Story 3)**

- **FR-009**: THE SYSTEM SHALL emit a trace for each collector run, score recomputation, reader execution, and Ask agent query, recording start time, duration, and outcome (success, failure, or degraded).
- **FR-010**: THE SYSTEM SHALL emit metrics sufficient to report recent dashboard-load, event-to-score, and Ask-agent-response latencies against `REQ-NFR-01…03`'s targets without reproducing the scenario live.
- **FR-011**: THE SYSTEM SHALL surface a source or reader failure in collected metrics within one collection interval of it occurring.
- **FR-012**: THE SYSTEM SHALL continue all existing collection, scoring, and user-facing functionality unaffected if the observability backend itself is unreachable.

**Weight recalibration (User Story 4)**

- **FR-013**: THE SYSTEM SHALL let a user with `role = admin` update a finding type's base point weight, taking effect starting with the next score computation.
- **FR-014**: THE SYSTEM SHALL record, for every weight change, who changed it, when, the previous value, and the new value.
- **FR-015**: THE SYSTEM SHALL leave every already-completed score run's stored score and contributions unchanged when a base weight is later modified (consistent with `REQ-NFR-08`).
- **FR-016**: THE SYSTEM SHALL reject a weight change from any user whose `role` is not `admin`, including a `cs_lead`.

**Profile editor UI (User Story 5)**

- **FR-017**: THE SYSTEM SHALL provide a screen where a CS lead can view the current client profile version's stakeholders, exclusions, renewal date, contract value band, and communication norms.
- **FR-018**: THE SYSTEM SHALL apply the same validation rules to a profile editor submission that already apply to a YAML-file profile update, rejecting an invalid submission with a field-level error and creating no new version.
- **FR-019**: THE SYSTEM SHALL create a new, attributed client profile version on a valid editor submission, using the same versioning behavior already defined for YAML-sourced updates.

**Post-MVP sources (User Story 6)**

- **FR-020**: THE SYSTEM SHALL implement one normalization path each for Slack Connect, the CSAT/NPS survey tool, and Calendar/meeting transcripts, each conforming to the existing common collector interface (REQ-M1-01) and its existing non-functional constraints (read-only, narrowest scopes, redaction, encryption, coverage reporting, graceful degradation) without exception. **Revised 2026-08-16 (`/speckit-analyze` finding U2):** "normalization path," not "a collector each" — matching this codebase's existing precedent of Gmail/Zendesk/warehouse already sharing one `Collector` implementation rather than one class per source; the interface-conformance and non-functional guarantees apply per source regardless of class boundaries.
- **FR-021**: THE SYSTEM SHALL restore the Absence and Relationship readers to full strength (chat-silence detection and the Slack channel's participant graph, respectively) once Slack Connect is connected, without requiring any other Post-MVP source.
- **FR-022**: THE SYSTEM SHALL feed CSAT numeric scores to the Usage reader and CSAT written comments to the Tone reader once the CSAT/NPS source is connected, without requiring any other Post-MVP source.
- **FR-023**: THE SYSTEM SHALL activate the Meeting reader for a specific meeting series only once both the Calendar/transcript source is connected for that series AND documented, all-party consent exists for it; THE SYSTEM SHALL NEVER collect a transcript for a series lacking that consent.
- **FR-024**: THE SYSTEM SHALL leave dashboard behavior identical to the pre-Phase-11 (feature 010) state for any client where none of the three Post-MVP sources is connected.

### Key Entities

- **Retention job run**: One execution of the scheduled crypto-shredding job — when it ran, how many message bodies it evaluated and shredded, and any errors. Distinct from the message-body encryption keys themselves (which already exist per `requirements/11-non-functional-requirements.md` REQ-NFR-11).
- **Role permission**: The mapping from a `users.role` value to the set of endpoints/actions it may perform — the first real consumer of the `role` column that has existed, unenforced, since `data-base/12-users-and-auth.md`.
- **Operational trace/metric**: A record of one operational unit of work (a collector run, a score recomputation, a reader execution, an Ask agent query) — its duration and outcome, kept separate from the business data it describes.
- **Weight change record**: One edit to a finding type's base point weight — who made it, when, the previous and new value. Distinct from the `finding_type_config` value itself, which it modifies.
- **Post-MVP source connection**: Per-client connection state for Slack Connect, CSAT/NPS, and Calendar/transcripts — whether connected, and (for Calendar/transcripts) which meeting series have documented consent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero message bodies older than the configured retention window (default 90 days) plus 24 hours remain readable at any point, verified by a daily automated job run with no manual intervention.
- **SC-002**: An account executive can open a client's dashboard and evidence trace within the same load-time target as a CS lead (`REQ-NFR-01`, under 1s), while 100% of write-capable actions attempted under that role are refused.
- **SC-003**: An operator can determine, for any of the last 30 days, whether each deployment met its dashboard-load, event-to-score, and Ask-agent-response latency targets without reproducing the scenario live.
- **SC-004**: A base weight change made through the system is reflected in the very next score computation for every affected client, with 100% of changes carrying a complete who/when/previous-value/new-value record.
- **SC-005**: A CS lead can complete a client profile edit through the editor screen in under the time a YAML edit + review currently takes, with the same validation guarantees (zero invalid profiles reach a new version through either path).
- **SC-006**: Connecting any one Post-MVP source in isolation produces new findings-eligible events within one collection cycle, with zero disruption to the dashboard for clients that haven't connected it.

## Assumptions

- Retention window defaults to 90 days per `decisions/00-open-questions-resolved.md` Q5, configurable per deployment rather than hardcoded, since the decision itself is described as "pending final legal sign-off with the client" and different deployments may finalize different windows.
- Cloud KMS-based key management (`architecture/03-technology-stack.md`'s Phase 2 note) is a candidate implementation detail for FR-001, not a separate requirement — the retention SLA (message bodies unrecoverable past the window) is what this spec requires, not a specific key-management technology.
- The `support_lead` and `engineering_manager` values already present in the `users.role` enum (`data-base/12-users-and-auth.md`) are out of scope for functional restriction in this feature — they retain full access, matching FR-007. `account_executive` gets the reduced, read-only permission set per `decisions/00-open-questions-resolved.md` Q8 (User Story 2), and `admin` is the sole role authorized to change base scoring weights (User Story 4, resolved in Clarifications above) — the first two functional uses of a `users.role` value beyond "informational."
- Post-MVP source connectors (User Story 6) reuse the existing collector interface and its non-functional constraints (REQ-M1-01…10) as-is; this feature does not redesign that interface, only adds three more implementations of it plus the reader-side wiring `decisions/01-mvp-scope-and-phasing.md` already specifies.
- Notification-channel expansion (email/Slack push, `decisions/00-open-questions-resolved.md` Q6) and playbook library expansion (Q7) are explicitly out of scope for this feature — the base product spec's Phase 11 deliverable list (§16) does not name them, unlike the six items above.
