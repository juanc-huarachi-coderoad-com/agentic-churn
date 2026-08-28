# Feature Specification: Real Zendesk Connector

**Feature Branch**: `029-real-zendesk-connector`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "Replace SimulatedCollector's zendesk slice with a real ZendeskCollector implementing the Collector interface — same shape as GmailCollector/AudioCollector (real external I/O, per-item failure isolation, idempotency, its own scheduled interval). SimulatedCollector and its JSON fixture must keep working unchanged, same explicit constraint as the Gmail connector. Fifth feature in the 7-feature production-readiness roadmap; second of three real connectors (after Gmail, before the warehouse connector)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real ticket activity from a connected Zendesk account becomes real signals (Priority: P1)

Once a Zendesk account is connected (via API credentials configured for the deployment), tickets
being created, reopened, and resolved in that account are automatically read and turned into the
same kind of signal the system already produces from the simulated fixture — feeding the
Commitment and Recurrence readers with real support-ticket activity, not only fixture data.

**Why this priority**: Zendesk is named as Phase 1's primary real channel for the Commitment and
Recurrence readers (`decisions/01-mvp-scope-and-phasing.md`) — this is the entire point of the
feature. Every other story exists to make this one safe and honest, not to add capability on top
of it.

**Independent Test**: Connect a real Zendesk account with valid credentials, create/reopen/resolve
a ticket, and confirm — with no manual script run — that a corresponding event appears in the
ledger, distinguishing correctly between a new ticket, a reopened one, and a resolved one.

**Acceptance Scenarios**:

1. **Given** valid Zendesk credentials are configured, **When** a new ticket is created, **Then**
   it becomes a real "created" event in the ledger, citable by findings exactly like a
   simulated-source ticket would be.
2. **Given** an existing ticket is reopened after being resolved, **When** the connector runs,
   **Then** it becomes a real "reopened" event, distinct from the original "created" event for the
   same ticket.
3. **Given** an open ticket is resolved, **When** the connector runs, **Then** it becomes a real
   "resolved" event, correctly closing out the ticket's outstanding-commitment tracking exactly as
   a simulated-source resolution would.
4. **Given** the same ticket transition has already been collected once, **When** the connector
   runs again, **Then** it is not collected a second time.

---

### User Story 2 - The existing simulated/fixture-based sources keep working unchanged (Priority: P1)

Everything the system already does with `SimulatedCollector` and its JSON fixture — for Zendesk
*and* every other still-simulated source — keeps working exactly as it does today. Adding a real
Zendesk connector does not remove, disable, or alter the simulated path in any way.

**Why this priority**: The same explicit, non-negotiable constraint already established for the
Gmail connector, independent of Story 1's own priority — demos, existing tests, and any source
this roadmap hasn't reached yet all depend on the simulated path continuing to work unmodified.

**Independent Test**: Run the existing simulated-collector flow exactly as documented today, with
the real Zendesk connector also present, and confirm identical behavior to before this feature
existed — including its own `zendesk`-sourced fixture items.

**Acceptance Scenarios**:

1. **Given** the real Zendesk connector now exists in the system, **When** the simulated collector
   runs against its JSON fixture, **Then** it produces exactly the same events it did before this
   feature, including its own simulated Zendesk-sourced items.
2. **Given** a deployment has no Zendesk credentials configured at all, **When** the system runs,
   **Then** the simulated collector continues to work exactly as it always has.

---

### User Story 3 - A Zendesk connection problem is visible, never silent (Priority: P2)

If the Zendesk connection fails — bad credentials, revoked access, a network problem — that
failure shows up honestly as a coverage gap for the Zendesk source, never indistinguishable from
"nothing new happened."

**Why this priority**: The same honesty guarantee (P5) every other source already has; second
priority because it protects Story 1's failure path rather than adding new success-path
capability.

**Independent Test**: Configure invalid Zendesk credentials and run the connector; confirm the
resulting coverage report shows Zendesk as not successfully read, distinctly from a cycle where
nothing new happened.

**Acceptance Scenarios**:

1. **Given** Zendesk credentials are invalid or revoked, **When** the connector runs, **Then** the
   whole connection attempt fails visibly and is recorded as a coverage gap for the Zendesk
   source.
2. **Given** one individual ticket's activity fails to process for a reason specific to that
   ticket, **When** the connector runs, **Then** that one ticket is skipped and logged, and every
   other ticket in the same run is still collected.

---

### Edge Cases

- What happens the very first time the real connector ever runs against an account with years of
  ticket history? It must not attempt to ingest the account's entire history — only activity
  within a bounded, recent window, consistent with how this system already treats "new" for every
  other automated cycle.
- What happens when a ticket is reopened more than once? Each reopening is its own distinct event
  — the system already tracks a `reopen_count` concept in its existing fixture data, and a real
  ticket reopened twice must produce two distinct "reopened" events, not one.
- What happens to a ticket whose reporter cannot be resolved to a real email address (e.g. a
  ticket filed through an unusual channel)? The event is still collected with whatever identifying
  information is available; identity resolution downstream already handles an unresolvable
  participant honestly (`identity_status = unresolved`), this feature does not need to solve that
  itself.
- What happens if Zendesk access is granted with write scope by mistake? The connector must never
  require more than read access — this system has no send/write capability anywhere (P4), and a
  Zendesk connector is no exception.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST be able to read real ticket activity (creation, reopening,
  resolution) from a connected Zendesk account and turn each one into a ledger event, without any
  manual script execution.
- **FR-002**: A real Zendesk connector MUST request read-only access to the connected account —
  never a scope that would allow creating, modifying, or deleting tickets.
- **FR-003**: The system MUST NOT collect the same real ticket transition more than once, across
  any number of connector runs.
- **FR-004**: The system MUST correctly distinguish a ticket's creation, a reopening, and a
  resolution as three distinct kinds of events — never conflating them.
- **FR-005**: A real ticket event's captured shape MUST match what every existing reader that
  consumes Zendesk-sourced events already expects — no reader may need to change to consume real
  Zendesk data instead of simulated data.
- **FR-006**: The existing simulated/fixture-based collection path (all six of its currently
  simulated sources, including its own `zendesk`-labeled fixture items) MUST continue to function
  completely unchanged after this feature ships.
- **FR-007**: A whole-connection failure MUST be recorded as a visible, honest coverage gap for
  the Zendesk source, never indistinguishable from a quiet account with nothing new.
- **FR-008**: A failure specific to one individual ticket MUST be skipped and logged without
  aborting collection of the rest of that run's tickets.
- **FR-009**: The real connector MUST run on its own automatic, scheduled cadence, independent of
  and without modifying any other source's collection schedule.
- **FR-010**: An operator MUST be able to trigger one real Zendesk collection cycle on demand,
  independent of the automatic schedule.
- **FR-011**: The real connector's first-ever run against a given account MUST NOT attempt to
  ingest that account's entire ticket history — only a bounded recent window.
- **FR-012**: A ticket reopened multiple times MUST produce one distinct event per reopening, not
  a single collapsed event.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A ticket creation, reopening, or resolution in a connected Zendesk account becomes a
  citable ledger event without any person running a script, within this system's existing
  automated-collection cadence.
- **SC-002**: Running the same collection window twice never produces a duplicate event for the
  same ticket transition.
- **SC-003**: Every existing test and demo flow that exercises the simulated/fixture-based sources
  passes unchanged after this feature ships.
- **SC-004**: An invalid-credentials scenario is visibly distinguishable, in the system's own
  coverage reporting, from a healthy account with nothing new to report.
- **SC-005**: A ticket that is created, resolved, and reopened within one connector run produces
  three separate, correctly-typed events, not one merged event.

## Assumptions

- Per the approved production-readiness roadmap, this is the second of three real connectors built
  in sequence — this feature covers Zendesk only.
- API credentials (an account subdomain, an agent email, and an API token) are provisioned by
  whoever operates this deployment, outside this feature's own scope.
- "Bounded recent window" means ticket activity since the connector's own last successful run, or
  a small fixed lookback on the very first run — the exact mechanism is a technical decision for
  the implementation plan, matching the same approach already established for the Gmail connector.
- This feature does not attempt to map Zendesk-specific concepts (custom fields, tags) onto this
  product's "product area" concept — no standard mapping exists between the two, and guessing one
  would violate this system's own rule that collectors never interpret what a product area means
  (REQ-M1-P3). A ticket event without a resolved product area is handled exactly as any other
  optional, unresolved field already is.
- This feature does not change identity resolution, redaction, or any other step of the existing
  collection pipeline downstream of a normalized event.
