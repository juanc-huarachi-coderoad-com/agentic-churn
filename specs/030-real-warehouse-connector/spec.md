# Feature Specification: Real Warehouse Connector

**Feature Branch**: `030-real-warehouse-connector`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "Replace SimulatedCollector's warehouse slice with a real WarehouseCollector implementing the Collector interface — same shape as GmailCollector/ZendeskCollector. Genuinely open architectural question resolved by reading the actual code: ComputeRollupsUseCase (the projection UsageReader actually reads from) is never called anywhere in production code today — a real, pre-existing gap dating back to feature 007's own ROADMAP log entry, not something this feature invents. Closing it is required for this feature to deliver any real value at all: without it, real warehouse events would be collected but never reach the Usage reader. User confirmed (clarifying question): the connector must be a generic SQL-based connector (a read-only connection string + a client-authored SQL query file), not a specific warehouse vendor SDK — the architecture's own docs never name a specific vendor for 'warehouse read connector', treating it as inherently client-specific, matching the existing precedent of CLIENT_PROFILE_PATH being a directly human-edited, per-deployment file. SimulatedCollector must keep working unchanged, same explicit constraint as the Gmail/Zendesk connectors. Sixth feature in the 7-feature production-readiness roadmap; last of three real connectors."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real product-usage data from a connected warehouse becomes real signals, and actually reaches the Usage reader (Priority: P1)

Once a client's read-only warehouse connection and usage query are configured, product-usage
readings are automatically read and turned into the same kind of signal the system already
produces from the simulated fixture — and, unlike today, those readings actually become available
to the Usage reader, closing a real gap that predates this feature (the projection the Usage
reader reads from is never populated in production today, regardless of source).

**Why this priority**: Warehouse telemetry is named as Phase 1's primary channel for the Usage
reader. Collecting real usage data that never reaches the reader that's supposed to interpret it
would deliver zero real value — this story explicitly includes making the existing,
already-built-but-never-wired-in projection step run for real, not just adding a new data source
on top of a broken pipe.

**Independent Test**: Configure a real read-only warehouse connection and a query returning at
least one usage reading, run a collection cycle with no manual script, and confirm the reading
becomes both a ledger event and an actual finding-eligible input the Usage reader can see.

**Acceptance Scenarios**:

1. **Given** a valid warehouse connection and query are configured, **When** the connector runs,
   **Then** each row the query returns becomes a real event in the ledger, citable exactly like a
   simulated-source usage reading would be.
2. **Given** real warehouse events have just been collected, **When** the automated pipeline's
   readers next run, **Then** the Usage reader can actually see and interpret that data — not
   silently see nothing, which is what happens for *every* source today, including the simulated
   one, until this feature closes that gap.
3. **Given** the same usage reading has already been collected once, **When** the connector runs
   again and the underlying query still returns that same row, **Then** it is not collected a
   second time.

---

### User Story 2 - The existing simulated/fixture-based sources keep working unchanged (Priority: P1)

Everything the system already does with `SimulatedCollector` and its JSON fixture — for warehouse
*and* every other still-simulated source — keeps working exactly as it does today. Adding a real
warehouse connector does not remove, disable, or alter the simulated path in any way.

**Why this priority**: The same explicit, non-negotiable constraint already established for the
Gmail and Zendesk connectors.

**Independent Test**: Run the existing simulated-collector flow exactly as documented today, with
the real warehouse connector also present, and confirm identical behavior — including its own
`warehouse`-sourced fixture items.

**Acceptance Scenarios**:

1. **Given** the real warehouse connector now exists in the system, **When** the simulated
   collector runs against its JSON fixture, **Then** it produces exactly the same events it did
   before this feature, including its own simulated warehouse-sourced items.
2. **Given** a deployment has no warehouse connection configured at all, **When** the system runs,
   **Then** the simulated collector continues to work exactly as it always has.

---

### User Story 3 - A warehouse connection problem is visible, never silent (Priority: P2)

If the warehouse connection fails — bad credentials, unreachable database, a malformed query —
that failure shows up honestly as a coverage gap for the warehouse source, never indistinguishable
from "nothing new happened."

**Why this priority**: The same honesty guarantee (P5) every other source already has.

**Independent Test**: Configure an invalid warehouse connection and run the connector; confirm the
resulting coverage report shows warehouse as not successfully read.

**Acceptance Scenarios**:

1. **Given** the warehouse connection is invalid, unreachable, or the configured query is
   malformed, **When** the connector runs, **Then** the whole connection attempt fails visibly and
   is recorded as a coverage gap for the warehouse source.

---

### Edge Cases

- What happens if the client-authored query returns the same underlying reading with a different
  value on a later run (e.g. a corrected figure)? Out of scope for this feature — a reading is
  identified by its content at the time it's read; a genuinely corrected value from the source
  system is a data-quality concern for the client's own warehouse, not something this connector
  resolves.
- What happens if the configured query returns rows in an unexpected shape (missing an expected
  field)? That reading is skipped and logged, exactly like any other per-item failure — one
  malformed row never aborts the rest of the cycle.
- What happens the very first time the connector runs? Unlike Gmail/Zendesk, there is no
  system-derived "bounded recent window" — the client's own query is responsible for scoping
  itself to relevant/recent data (documented guidance, not a rule this connector enforces, since it
  has no visibility into the target warehouse's own schema).
- What happens if warehouse write access is granted by mistake? The connector must never require
  more than read access — this system has no send/write capability anywhere (P4).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST be able to read product-usage readings from a connected, real
  warehouse (via a read-only connection and a client-authored query) and turn each one into a
  ledger event, without any manual script execution.
- **FR-002**: The system MUST use only read-only access to the connected warehouse — never a
  connection or query capable of writing to it.
- **FR-003**: The system MUST NOT collect the same real usage reading more than once, across any
  number of connector runs.
- **FR-004**: A real usage reading's captured shape MUST match what the Usage reader already
  expects — no reader may need to change to consume real warehouse data instead of simulated data.
- **FR-005**: The existing simulated/fixture-based collection path MUST continue to function
  completely unchanged after this feature ships.
- **FR-006**: The system MUST turn collected `usage_measurement` events (from any source, not only
  the new real warehouse connector) into the projection the Usage reader actually reads from, as
  part of the regular automated pipeline — this projection step exists today but is never invoked
  in production, a pre-existing gap this feature closes because its own value depends on it.
- **FR-007**: A whole-connection failure MUST be recorded as a visible, honest coverage gap for
  the warehouse source.
- **FR-008**: A failure specific to one individual reading MUST be skipped and logged without
  aborting collection of the rest of that run's readings.
- **FR-009**: The real connector MUST run on its own automatic, scheduled cadence.
- **FR-010**: An operator MUST be able to trigger one real warehouse collection cycle on demand.
- **FR-011**: The connector MUST support any warehouse reachable via a standard read-only database
  connection, not a single named vendor — matching how this system's own architecture documents
  "warehouse read connector" generically.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A usage reading returned by the configured warehouse query becomes a citable ledger
  event without any person running a script.
- **SC-002**: Running the same collection cycle twice never produces a duplicate event for the
  same underlying reading.
- **SC-003**: After a real warehouse collection cycle and the next automated readers cycle, the
  Usage reader has actually processed the newly-collected data — not silently seen nothing, for
  the first time in this system's history for any source.
- **SC-004**: Every existing test and demo flow that exercises the simulated/fixture-based sources
  passes unchanged after this feature ships.
- **SC-005**: An invalid-connection scenario is visibly distinguishable, in the system's own
  coverage reporting, from a healthy warehouse with nothing new to report.

## Assumptions

- Per the approved production-readiness roadmap, this is the third and last of three real
  connectors built in sequence — this feature covers the warehouse channel only.
- A read-only connection string and a client-authored SQL query file are provisioned by whoever
  operates this deployment, matching the existing `CLIENT_PROFILE_PATH` precedent (a
  human-edited, per-deployment file) rather than a vendor-specific integration UI.
- The client-authored query is responsible for scoping itself to relevant, recent data and for
  computing each reading's already-interpreted percentage change — this connector reads
  already-computed values, it does not calculate deltas itself (REQ-M1-P1/P2).
- This feature does not change identity resolution, redaction, or any other step of the existing
  collection pipeline downstream of a normalized event.
- Closing the pre-existing "rollup projection never runs" gap (FR-006) is scoped narrowly to
  wiring the existing, already-built `ComputeRollupsUseCase` into the automated pipeline — it does
  not redesign that use case's own logic.
