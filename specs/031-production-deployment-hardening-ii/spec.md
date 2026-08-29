# Feature Specification: Production Deployment Hardening II

**Feature Branch**: `031-production-deployment-hardening-ii`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "Closes the remaining piece of the 7-feature production-readiness roadmap: a scheduled backup job for the database, a provider-agnostic alerting mechanism built on the existing observability pipeline, and a one-service-at-a-time redeploy procedure that keeps the running deployment available throughout. Cloud-vendor-specific KMS and Infrastructure-as-Code are explicitly deferred — no cloud provider has been chosen yet for this client, and building against a specific one now would be speculative, unverifiable work."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator trusts that data loss from a crashed database is recoverable (Priority: P1)

An operator responsible for a client's deployment needs confidence that if the database is lost or corrupted, the client's data can be restored to a recent point, without depending on anyone remembering to run a manual command.

**Why this priority**: Data loss is the most severe, least reversible failure this system can suffer — a client's entire ledger of collected events, findings, and scores. Every other hardening measure in this roadmap protects against smaller risks than this one.

**Independent Test**: Let the scheduled backup job run for a full cycle against a real database, confirm a usable dump file exists afterward, and confirm restoring it into a fresh database reproduces the original data.

**Acceptance Scenarios**:

1. **Given** a running deployment with real data in its database, **When** the backup job's scheduled interval elapses, **Then** a new backup file appears at the configured destination and a durable record of that successful run is created.
2. **Given** a backup file produced by a prior run, **When** an operator restores it into a fresh, empty database, **Then** the restored database's data matches the original at the time of the backup.
3. **Given** backup files older than the configured retention window, **When** the backup job runs again, **Then** those old files are deleted and only files within the window remain.
4. **Given** the backup job fails partway through (e.g., the destination is unwritable), **When** the failure occurs, **Then** the failure is recorded durably and visibly — the operator can find out without checking logs by hand.

---

### User Story 2 - Operator learns about a real problem without watching logs constantly (Priority: P1)

An operator does not have time to tail logs or dashboards all day. When something genuinely wrong happens — a source stops reporting reliably, a scheduled safety job fails — they need to be notified through a channel they already check (e.g., a team chat tool), without this system depending on a specific cloud vendor's alerting product.

**Why this priority**: Silent failure is the failure mode this whole roadmap has been closing, one automated job at a time (specs/025-030). A hardening feature that adds more automated jobs but no way to be told when one of them fails would make this worse, not better.

**Independent Test**: Deliberately produce one of the real conditions this system already detects (e.g., a degraded score run, a failed backup run), confirm exactly one notification is sent to a configured destination with a clear description of what happened, and confirm no notification is sent when nothing is wrong.

**Acceptance Scenarios**:

1. **Given** a scheduled safety job (backup, retention) fails, **When** the next alert check runs, **Then** a notification describing which job failed and when is sent to the configured destination.
2. **Given** a score run completes with data quality degraded (a source stopped reporting), **When** the next alert check runs, **Then** a notification describing the degradation is sent.
3. **Given** everything is operating normally, **When** the alert check runs, **Then** no notification is sent.
4. **Given** no alert destination has been configured for this deployment, **When** a real condition worth alerting on occurs, **Then** the condition is still recorded/logged, but nothing fails or crashes because there is nowhere to send it.
5. **Given** a condition was already alerted on and has not changed, **When** the alert check runs again, **Then** the operator is not repeatedly re-notified about the same still-ongoing condition.

---

### User Story 3 - Operator ships a code fix without taking the client's deployment offline (Priority: P2)

An operator needs to deploy a bug fix or update to one part of the running system (e.g., a backend fix) without disrupting the parts that don't need to change, and without a window where the client-facing service is completely down.

**Why this priority**: Lower priority than data-loss protection and alerting because, today, deployments are already a manual `docker compose` operation an operator controls directly — this improves the safety of an existing manual process rather than closing a silent-failure gap. Still real: a careless redeploy today can take the whole stack down at once.

**Independent Test**: With a real deployment running, redeploy one updated service while continuously checking that the other services remain reachable and responsive throughout the entire operation.

**Acceptance Scenarios**:

1. **Given** a running deployment, **When** an operator redeploys one service with an updated version, **Then** that service is confirmed healthy before the redeploy is considered complete, and the other services were never unreachable during the operation.
2. **Given** a redeployed service fails its own health check after the update, **When** the redeploy procedure detects this, **Then** it reports the failure clearly rather than silently leaving the deployment in a broken state.

---

### Edge Cases

- What happens when the backup destination fills up mid-write? The job must fail loudly (User Story 1, Scenario 4) rather than leave a silently truncated, unusable dump file.
- What happens when the alert destination itself is unreachable (e.g., the webhook URL is misconfigured or the receiving service is down)? The alert check must log this and continue — a broken notification channel must never crash a scheduled job or block anything else.
- What happens if an operator tries to redeploy the database service through the same one-at-a-time procedure? Out of scope for this feature — see Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST periodically create a complete backup of the database on a configurable schedule, without requiring a person to run a command manually.
- **FR-002**: System MUST write each backup to a configurable destination location.
- **FR-003**: System MUST delete backup files older than a configurable retention window as part of the same scheduled job.
- **FR-004**: System MUST durably record the outcome (success or failure, and when) of every backup run, so an operator can review backup history without reading raw logs.
- **FR-005**: A documented procedure MUST exist for restoring a backup file into a working database.
- **FR-006**: System MUST periodically evaluate a fixed set of real, already-detectable conditions (a degraded score run; a failed scheduled safety job) and send a notification when one is found.
- **FR-007**: System MUST send notifications to a destination configured per deployment, without requiring code changes to point at a different destination.
- **FR-008**: System MUST NOT send any notification when no monitored condition is currently true (constitution P6, "Silence Is a Success State").
- **FR-009**: System MUST NOT fail, crash, or block other scheduled work when the notification destination is unset or unreachable — it degrades to logging only.
- **FR-010**: System MUST avoid sending a repeat notification for a condition that was already alerted on and has not changed since.
- **FR-011**: A documented, executable procedure MUST exist for redeploying one non-database service at a time such that the other services remain available throughout.
- **FR-012**: The redeploy procedure MUST confirm the redeployed service is healthy before considering the redeploy complete, and MUST report clearly if it is not.
- **FR-013**: System MUST NOT extend this feature's redeploy procedure to the database service (see Assumptions).
- **FR-014**: This feature MUST NOT introduce a cloud-vendor-specific key management or infrastructure-provisioning implementation (see Assumptions).

### Key Entities

- **Backup run record**: One entry per attempted backup — when it ran, whether it succeeded, where the file went (if it did), and why it failed (if it didn't).
- **Alert condition**: A named, checkable condition this system already has enough information to evaluate (e.g., "a score run degraded", "the backup job failed") and whether it is currently true.
- **Notification**: One outbound message describing a currently-true alert condition, sent to a configured destination.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A database backup exists that is no older than the configured backup interval, at all times after the first scheduled run completes.
- **SC-002**: A backup taken by this system can be restored into a working database that reproduces the original data, verified at least once as part of this feature's own validation.
- **SC-003**: An operator is notified of a genuine problem (a failed safety job, a degraded score run) without needing to read logs, within one alert-check cycle of the problem occurring.
- **SC-004**: Zero notifications are sent during a full validation cycle in which nothing is actually wrong.
- **SC-005**: A single-service redeploy completes with zero failed requests to the other, unchanged services observed throughout the operation.

## Assumptions

- No concrete cloud provider (AWS, GCP, or otherwise) has been selected for this client as of this feature. Building a cloud-vendor-specific KMS adapter, cloud object-storage adapter, or cloud-specific Infrastructure-as-Code module now would be speculative and unverifiable — deferred until a provider is actually chosen. The existing key-storage abstraction (from specs/011-production-hardening) already anticipates this and needs no interface change later.
- The backup destination for this feature is a configurable local/mounted filesystem location, consistent with this project's existing "one Docker Compose stack per client" deployment model — not a cloud object store. A cloud-storage-backed destination is a natural later addition behind the same abstraction, once a provider is chosen.
- The notification mechanism is a plain webhook POST to a configured URL (e.g., a Slack incoming webhook, or any service accepting a JSON payload) — genuinely provider-agnostic, not built against one vendor's alerting API.
- Redeploying the stateful database service is explicitly out of scope for this feature's one-at-a-time redeploy procedure — a database redeploy has a fundamentally different risk profile (in-flight transactions, replication, data migration ordering) than the stateless api/worker/web services, and deserves its own dedicated treatment rather than being folded into this one.
- This feature continues to operate within the existing "one Docker Compose stack per client" deployment model (constitution P10) — it does not introduce multi-tenant or Kubernetes-style orchestration.
