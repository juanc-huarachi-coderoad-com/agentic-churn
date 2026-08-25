# Feature Specification: Real Gmail Connector

**Feature Branch**: `028-real-gmail-connector`

**Created**: 2026-08-24

**Status**: Draft

**Input**: User description: "Replace SimulatedCollector's gmail slice with a real GmailCollector implementing the Collector interface — following AudioCollector's shape exactly (real external I/O, per-item failure isolation, idempotency, its own scheduled interval in worker.py). User explicitly required: do not remove the existing JSON-fixture-based simulated functionality (SimulatedCollector, demo/fixtures/meridian-week.json) — it must keep working unchanged, for zendesk/warehouse/slack/csat/calendar and for demos/tests. Fourth feature in the 7-feature production-readiness roadmap. First of three real-connector features (Gmail, then Zendesk, then warehouse)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real emails from a connected Gmail account become real signals (Priority: P1)

Once a Gmail account is connected (via OAuth credentials configured for the deployment), new
emails in that mailbox are automatically read and turned into the same kind of signal the system
already produces from the simulated fixture — feeding the Tone and Intent readers with real
customer communication, not only fixture data.

**Why this priority**: This is the entire point of the feature — Gmail is named as Phase 1's
primary real channel for the Tone and Intent readers (`decisions/01-mvp-scope-and-phasing.md`).
Every other story in this feature exists to make this one safe and honest, not to add new
capability on top of it.

**Independent Test**: Connect a real Gmail account with valid credentials, send/receive a new
email, and confirm — with no manual script run — that a corresponding event appears in the ledger
and is available to the Tone/Intent readers exactly as a simulated-source email would be.

**Acceptance Scenarios**:

1. **Given** valid Gmail credentials are configured for this deployment, **When** a new email
   arrives in the connected mailbox, **Then** it becomes a real event in the ledger, citable by
   findings exactly like any other email-sourced event.
2. **Given** the same email has already been collected once, **When** the connector runs again,
   **Then** it is not collected a second time (no duplicate event).
3. **Given** an email the connector has never seen before, **When** it is collected, **Then** its
   sender and message text are captured in the same shape existing readers already expect from an
   email-sourced event — no reader needs to change to consume it.

---

### User Story 2 - The existing simulated/fixture-based sources keep working unchanged (Priority: P1)

Everything the system already does with `SimulatedCollector` and its JSON fixture — for Gmail
*and* for every other still-simulated source (Zendesk, warehouse, Slack, CSAT, calendar) — keeps
working exactly as it does today. Adding a real Gmail connector does not remove, disable, or alter
the simulated path in any way.

**Why this priority**: Explicitly required by the person requesting this feature, and independent
of Story 1's own priority — this is a hard constraint on *how* Story 1 is built, not a nice-to-have.
Demos, existing tests, and every source this roadmap hasn't reached yet (Zendesk, warehouse, and
everything still in Phase 2) depend on the simulated path continuing to work unmodified.

**Independent Test**: Run the existing simulated-collector flow (fixture-based) exactly as
documented today, with the real Gmail connector also present in the system, and confirm identical
behavior and output to before this feature existed — including its own `gmail`-sourced fixture
items.

**Acceptance Scenarios**:

1. **Given** the real Gmail connector now exists in the system, **When** the simulated collector
   is run against its JSON fixture, **Then** it still produces exactly the same events it did
   before this feature, including its own simulated Gmail-sourced items.
2. **Given** both the real Gmail connector and the simulated collector are present, **When**
   either runs, **Then** neither one's events, coverage reporting, or run history interferes with
   the other's.
3. **Given** a deployment has no Gmail credentials configured at all, **When** the system runs,
   **Then** the simulated collector continues to work exactly as it always has, unaffected by the
   real connector's absence of credentials.

---

### User Story 3 - A Gmail connection problem is visible, never silent (Priority: P2)

If the Gmail connection fails — bad credentials, revoked access, a network problem — that failure
shows up honestly as a coverage gap for the Gmail source, the same way any other source's
connection failure already does. It never looks identical to "nothing new happened."

**Why this priority**: This is the same non-negotiable honesty guarantee every other source in this
system already has (P5 — "admit what we cannot see"); it is second priority only because it
protects Story 1's failure path rather than adding new success-path capability.

**Independent Test**: Configure invalid Gmail credentials and run the connector; confirm the
resulting coverage report shows Gmail as not successfully read, distinctly from a cycle where
nothing new happened.

**Acceptance Scenarios**:

1. **Given** Gmail credentials are invalid or revoked, **When** the connector runs, **Then** the
   whole connection attempt fails visibly and is recorded as a coverage gap for the Gmail source —
   it does not silently produce zero events indistinguishable from a healthy, quiet mailbox.
2. **Given** one individual email fails to process for a reason specific to that email (e.g. an
   unusual format), **When** the connector runs, **Then** that one email is skipped and logged, and
   every other email in the same run is still collected — one bad message never aborts the whole
   cycle.

---

### Edge Cases

- What happens the very first time the real connector ever runs against a mailbox with years of
  history? It must not attempt to ingest the account's entire history — only mail within a bounded,
  recent window, consistent with how this system already treats "new" for every other automated
  cycle.
- What happens if the same message is somehow visible to both the real Gmail connector and the
  simulated fixture (e.g. a coincidentally identical fixture entry)? They are tracked as
  completely separate sources with separate identifiers — no cross-source deduplication is implied
  or attempted by this feature.
- What happens to an email with no plain-text body (HTML-only, or an attachment-only message)? The
  connector extracts the best available human-readable text it can; a message with no readable text
  at all is skipped like any other per-item failure, not force-fit into an empty finding.
- What happens if Gmail access is granted read-only, as intended? The connector must never require
  more than read access — this system has no send capability anywhere (P4), and a Gmail connector
  is no exception.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST be able to read new email from a real, connected Gmail account and
  turn each one into a ledger event, without any manual script execution.
- **FR-002**: A real Gmail connector MUST request read-only access to the connected mailbox —
  never a scope that would allow sending, modifying, or deleting mail.
- **FR-003**: The system MUST NOT collect the same real email more than once, across any number of
  connector runs.
- **FR-004**: A real email's captured sender and message text MUST be in the same shape every
  existing reader that consumes email-sourced events already expects — no reader may need to
  change to consume real Gmail data instead of simulated data.
- **FR-005**: The existing simulated/fixture-based collection path (all six of its currently
  simulated sources, including its own `gmail`-labeled fixture items) MUST continue to function
  completely unchanged after this feature ships — this feature is strictly additive.
- **FR-006**: A whole-connection failure (invalid credentials, unreachable service) MUST be
  recorded as a visible, honest coverage gap for the Gmail source, never indistinguishable from a
  quiet mailbox with nothing new.
- **FR-007**: A failure specific to one individual email MUST be skipped and logged without
  aborting collection of the rest of that run's emails.
- **FR-008**: The real connector MUST run on its own automatic, scheduled cadence, independent of
  and without modifying any other source's collection schedule.
- **FR-009**: An operator MUST be able to trigger one real Gmail collection cycle on demand,
  independent of the automatic schedule, for verification and troubleshooting.
- **FR-010**: The real connector's first-ever run against a given mailbox MUST NOT attempt to
  ingest that mailbox's entire history — only a bounded recent window.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new email in a connected Gmail account becomes a citable ledger event without any
  person running a script, within this system's existing automated-collection cadence.
- **SC-002**: Running the same collection window twice never produces a duplicate event for the
  same email.
- **SC-003**: Every existing test and demo flow that exercises the simulated/fixture-based sources
  passes unchanged after this feature ships — zero behavior difference attributable to this
  feature's own changes.
- **SC-004**: An invalid-credentials scenario is visibly distinguishable, in the system's own
  coverage reporting, from a healthy mailbox with nothing new to report.

## Assumptions

- Per the approved production-readiness roadmap, Gmail is the first of three real connectors built
  in sequence (Gmail, then Zendesk, then a warehouse read connector) — this feature covers Gmail
  only.
- OAuth credentials (a client ID/secret and an authorized account's refresh token) are provisioned
  by whoever operates this deployment, outside this feature's own scope — this feature consumes
  those credentials once they exist, it does not build a credential-management UI.
- "Bounded recent window" (Edge Cases, FR-010) means new mail since the connector's own last
  successful run, or a small fixed lookback on the very first run — the exact mechanism is a
  technical decision for the implementation plan, not specified here.
- This feature does not change identity resolution, redaction, or any other step of the existing
  collection pipeline downstream of a normalized event — a real Gmail-sourced event flows through
  exactly the same `RunCollectorUseCase` orchestration every other source already uses.
