# Feature Specification: Input Connectors View

**Feature Branch**: `022-input-connectors-view`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Crear una pagina de input conectores o entrada de fuentes de de datos (source), actualmente son los siguientes . - live (1): transcripts → Meeting audio (local storage + OpenAI Whisper + pyannote.ai + Anthropic). - simulated (6): gmail, zendesk, warehouse, slack, csat, calendar. - planned (7, roadmap): jira, intercom, microsoft365, teams, nps, salesforce, contracts. Usa el mockup @base/mockupInputConectors.jpg, este mockup tiene que ser el resultado final busca los iconos en internet y descargalos para usarlos, Ya tenemos algunos conectores definidos en source completa con los que falta por favor, es mas una vista de los input connectors, esto no afecta a los otros procesos. Work all in english"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See every data source and its readiness at a glance (Priority: P1)

A user who wants to understand where the product's insights come from opens the Input Connectors page and immediately sees every known data source grouped by how ready it is: already live and feeding the system, simulated for demo/testing purposes, or planned for a future release.

**Why this priority**: This is the entire purpose of the page. Without this grouped, at-a-glance view, the feature delivers no value — everything else is refinement on top of this core listing.

**Independent Test**: Can be fully tested by opening the page and confirming three clearly labeled groups appear (Live, Simulated, Planned) each with an accurate count and the correct connectors listed underneath, matching the reference layout.

**Acceptance Scenarios**:

1. **Given** the user opens the Input Connectors page, **When** the page loads, **Then** a "Live" section appears showing 1 connector (Transcripts), a "Simulated" section showing 6 connectors (Gmail, Zendesk, Warehouse, Slack, CSAT, Calendar), and a "Planned" section showing 7 connectors (Jira, Intercom, Microsoft 365, Teams, NPS, Salesforce, Contracts).
2. **Given** the page has loaded, **When** the user looks at the section headers, **Then** each header displays a count that matches the number of connector entries listed beneath it.
3. **Given** the page has loaded, **When** the user looks at any single connector entry, **Then** they can see its name, a recognizable icon, a short description of what it provides, and a status badge (Live / Simulated / Planned) without needing to click anything.

---

### User Story 2 - Understand what a specific connector does (Priority: P2)

A user unfamiliar with a particular source (for example, "Warehouse" or "CSAT") reads its one-line description to understand what kind of data it contributes, without needing to ask an engineer.

**Why this priority**: The list itself (P1) already communicates existence and status; this story ensures each entry is self-explanatory, which is what makes the page useful to non-technical stakeholders rather than just a checklist.

**Independent Test**: Can be fully tested by reading the subtitle text under each connector entry and confirming it names the kind of data or integration involved (e.g., Transcripts shows "Meeting audio" plus its processing pipeline; Gmail/Zendesk/Warehouse/Slack/CSAT/Calendar and the planned connectors each show a short, plain-language description).

**Acceptance Scenarios**:

1. **Given** the Live section, **When** the user reads the Transcripts entry, **Then** it shows "Meeting audio" as its description and names the underlying pipeline (local storage, OpenAI Whisper, pyannote.ai, Anthropic).
2. **Given** any Simulated or Planned connector, **When** the user reads its entry, **Then** a short description or the connector's own recognizable branding communicates what the connector is for.

---

### User Story 3 - Discover how to add a new connector (Priority: P3)

A user who wants to expand the product's data sources looks for an entry point to add a new connector and finds one clearly presented on the page, understanding that it represents the path for future connectors rather than a fully self-serve integration today.

**Why this priority**: This affordance matters for completeness with the reference layout but does not block the core value of viewing existing connector status (P1/P2), so it is lower priority.

**Independent Test**: Can be fully tested by locating the "Add Connector" action on the page and confirming it is visibly present and clearly labeled.

**Acceptance Scenarios**:

1. **Given** the user is on the Input Connectors page, **When** they look at the top of the page, **Then** an "Add Connector" action is visible and clearly labeled.

---

### Edge Cases

- What happens when a connector has no well-known public brand icon (e.g., Warehouse, CSAT, Contracts)? A clear, generic icon representing the concept is used instead of leaving the entry blank.
- What happens if the counts in a section header and the number of entries listed under it ever disagree? The count must always be derived from the same list that is rendered, so they cannot drift apart.
- How does the page communicate connector state to users who cannot distinguish status by color alone? Each status is also conveyed through its text label (Live / Simulated / Planned), not color alone.
- What happens when the user selects a connector entry? Nothing further is required: every connector entry is a static display of its full information (name, icon, description, status) with no additional detail behind it, so entries are not interactive in this iteration (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated "Input Connectors" page reachable from the application's primary navigation.
- **FR-002**: The page MUST organize connectors into exactly three status groups — Live, Simulated, and Planned — each displaying a heading and a count of the connectors it contains.
- **FR-003**: The Live group MUST contain exactly one entry: Transcripts, described as "Meeting audio" with its underlying pipeline named (local storage, OpenAI Whisper, pyannote.ai, Anthropic).
- **FR-004**: The Simulated group MUST contain exactly six entries: Gmail, Zendesk, Warehouse, Slack, CSAT, and Calendar.
- **FR-005**: The Planned group MUST contain exactly seven entries, labeled as roadmap items: Jira, Intercom, Microsoft 365, Teams, NPS, Salesforce, and Contracts.
- **FR-006**: Each connector entry MUST display a name, a recognizable icon, a short descriptive subtitle, and a status badge matching its group.
- **FR-007**: The page MUST present an "Add Connector" action as a visible entry point for adding future connectors.
- **FR-008**: Connector status MUST be conveyed through both a visual indicator and a text label, so status is never communicated by color alone.
- **FR-009**: The page MUST be read-only with respect to the underlying data ingestion, scoring, and other product pipelines — viewing or interacting with this page MUST NOT alter data collection, processing, or any other existing system behavior.
- **FR-010**: The page's visual layout, grouping, counts, and connector set MUST match the approved reference mockup as the definitive target for this feature.

### Key Entities

- **Connector**: A representation of one data source the product can draw insights from. Attributes: name, status group (Live / Simulated / Planned), icon, short description, and — for the Live group — the names of the underlying services involved in producing its data.
- **Status Group**: A named category (Live, Simulated, or Planned) used to bucket connectors, carrying a label and a count of its member connectors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can identify how many data sources are Live, Simulated, and Planned from a single, unscrolled view of the page — no scrolling or clicking required to see all three group counts.
- **SC-002**: All 14 known connectors (1 Live + 6 Simulated + 7 Planned) are visible on the page, correctly grouped, with no missing or miscategorized entries.
- **SC-003**: A user unfamiliar with the system can state, for any connector shown, which status group it belongs to and what kind of data it provides, using only the information on the page.
- **SC-004**: Existing product functionality (dashboard, scoring, ingestion, and other pipelines) shows zero behavioral change after this page is added, confirmed by existing tests continuing to pass unmodified.

## Assumptions

- This feature is a static, informational catalog view of the product's data sources; it does not implement any new backend integration, connector installation flow, or data pipeline change.
- The three status groups mirror the product's actual current state: connectors already wired to real external services are "Live," connectors backed by demo/synthetic data are "Simulated," and connectors not yet built are "Planned" (roadmap).
- Recognizable third-party brand icons are used where an official mark exists (e.g., Gmail, Slack, Zendesk, Microsoft 365, Teams, Salesforce, Jira, Intercom); a clear generic icon is used for connectors without an official public brand mark (e.g., Warehouse, CSAT, Calendar, NPS, Contracts).
- The "Add Connector" action is a visible entry point consistent with the reference mockup; it does not need to launch a fully built connector-onboarding workflow as part of this feature.
- The page is available to any authenticated user of the application, consistent with the other existing primary navigation destinations (no new permission tier is introduced).
- The new navigation entry is added alongside the application's existing primary destinations, following the same single-source-of-truth pattern already used for navigation.
- Connector entries are static and non-interactive in this iteration: clicking or tapping one has no effect beyond what is already visible (name, icon, description, status). No detail page, expand/collapse, or modal is part of this feature's scope.
