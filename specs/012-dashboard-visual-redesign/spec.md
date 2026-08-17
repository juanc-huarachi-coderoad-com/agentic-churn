# Feature Specification: Main Dashboard Visual Redesign

**Feature Branch**: `012-dashboard-visual-redesign`

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Apply the new visual design for the main dashboard page based on the attached @base/mockup-mainPage.jpg The layout includes a left-aligned navigation sidebar, a central 'Signal Stream' vertical timeline, a Churn Risk Overview card with an area chart, and a 'The Action & Draft Hub' list. CRITICAL CONSTRAINT: The underlying business logic, state management, API calls, and data structures are fully functional and MUST NOT be modified. And the agent assistant should be a float component, like defined on the mockup. All the functionality is already implemented, please help me building this new visual requirement."

## Clarifications

### Session 2026-08-17

- Q: The mockup's header shows controls that don't exist in the current dashboard (a "Last 30 days" date-range dropdown, a "Live" status badge, a notification bell with a count) — should these become real functionality, or stay decorative given the no-new-state constraint? → A: Render as static/decorative elements matching the mockup visually — no new state or API calls.
- Q: The mockup's sidebar shows roughly five icons, but only three real destinations (Dashboard, Coverage, Profile) exist today — how should the sidebar handle the extra icons? → A: Sidebar shows exactly 3 icons, one per existing destination — no extras.
- Q: What is the floating assistant's initial open/collapsed state on page load? → A: Always starts collapsed (launcher only) on every page load, regardless of prior session.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the redesigned dashboard layout (Priority: P1)

A Customer Success manager opens the main dashboard and sees the new visual layout: a left-aligned navigation sidebar, a central "Signal Stream" vertical timeline of recent activity, and a right-hand column containing a "Churn Risk Overview" card (score, trend, and risk drivers) and an "Action & Draft Hub" list of prioritized actions — all populated with the same live account data the dashboard already shows today.

**Why this priority**: This is the foundational layout change every other part of the redesign sits inside. Without it, there is no "new dashboard" to evaluate — it is the minimum slice that makes the redesign visible and demonstrable.

**Independent Test**: Load the dashboard for an account with active findings and confirm the four regions (sidebar, Signal Stream, Churn Risk Overview, Action & Draft Hub) are all present, correctly positioned, and show the account's real score, findings, and actions — with no change to the underlying values compared to the current dashboard.

**Acceptance Scenarios**:

1. **Given** an account with active findings and a computed risk score, **When** the CS manager opens the dashboard, **Then** the sidebar, Signal Stream, Churn Risk Overview, and Action & Draft Hub are all visible in the layout positions shown in the approved reference design.
2. **Given** the redesigned dashboard is displayed, **When** the CS manager compares the score, finding details, and action list against the same account's current (pre-redesign) dashboard, **Then** every value matches exactly — only the visual presentation differs.
3. **Given** the sidebar is visible, **When** the CS manager selects a different existing destination (e.g. Coverage or Profile), **Then** they are taken to that existing page and the sidebar reflects which destination is now active.

---

### User Story 2 - Understand churn risk through the consolidated overview card (Priority: P2)

A Customer Success manager looks at the Churn Risk Overview card and sees the current risk score, its trend over the selected time window rendered as a continuous area chart, and the ranked list of factors driving that score — all in one place, without needing to piece it together from separate sections.

**Why this priority**: This is the dashboard's primary decision-support surface — it's how a CS manager judges "how worried should I be, and why," so it delivers the highest standalone analytical value after the base layout exists.

**Independent Test**: For an account with at least a few days of score history, open the dashboard and confirm the score, its band/label, a filled area chart of its trend, and the ranked risk-driver list are all visible together in the Churn Risk Overview card, with values identical to what the current score/trend/driver views already report.

**Acceptance Scenarios**:

1. **Given** an account with score history across the selected time window, **When** the CS manager views the Churn Risk Overview card, **Then** the trend is rendered as a continuous filled area chart (not isolated points) and matches the account's actual historical scores.
2. **Given** a risk driver breakdown exists for the account, **When** the CS manager views the card, **Then** the drivers are listed ranked by contribution, with the same signs and magnitudes the dashboard already computes.
3. **Given** an account has fewer than two historical score points, **When** the CS manager views the card, **Then** the chart degrades gracefully (e.g. a single point or a clear "not enough history yet" presentation) instead of rendering a misleading or broken chart.

---

### User Story 3 - Reach the AI assistant through a floating component (Priority: P3)

A Customer Success manager wants to ask the AI assistant a question at any point while reading the Signal Stream or Action & Draft Hub. Instead of a fixed bar permanently occupying screen space, the assistant is available as a floating component they can open on demand and collapse when done, without losing their place on the page or their conversation history.

**Why this priority**: This is a real usability improvement (reclaiming screen space for the Signal Stream and Action & Draft Hub) but the dashboard is fully usable without it if the assistant were simply restyled in place — it depends on the layout from User Story 1 existing first.

**Independent Test**: From anywhere on the dashboard, open the floating assistant, confirm prior conversation history is still present, ask a question, collapse it, and confirm the underlying page content is unobstructed and unchanged.

**Acceptance Scenarios**:

1. **Given** the CS manager has scrolled down within the Signal Stream, **When** they open the floating assistant, **Then** it becomes visible and usable without requiring a page navigation or losing their scroll position.
2. **Given** an existing assistant conversation, **When** the CS manager collapses and reopens the floating assistant, **Then** the full prior conversation is still present, unchanged.
3. **Given** the floating assistant is collapsed, **When** the CS manager views the Signal Stream and Action & Draft Hub, **Then** neither is obscured or resized by the collapsed assistant component.

---

### Edge Cases

- What happens when an account is healthy and has nothing actionable to show? The redesigned layout MUST still collapse to the existing near-empty "all clear" presentation rather than forcing sidebar/timeline/chart/hub chrome to display empty or fabricated content.
- What happens when the floating assistant is open at the same time as the evidence detail view or the draft composer overlay? Both must remain usable without one silently closing or visually breaking the other.
- What happens when the Signal Stream has zero recent entries versus far more entries than fit on screen?
- What happens when the Action & Draft Hub has more prioritized actions than fit in the visible list — is there a way to reach the rest?
- What happens on a narrower browser window/viewport — do the sidebar, Signal Stream, and right-hand column reflow sensibly, or is a minimum width assumed, consistent with how the rest of the application already handles this?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST present a left-aligned, persistent navigation sidebar giving access to exactly the application's existing destinations (Dashboard, Coverage, Profile) — one icon per real destination, without introducing new pages, placeholder/disabled icons, or changing what any destination does.
- **FR-002**: The sidebar MUST visually indicate which destination is currently active.
- **FR-003**: The dashboard MUST present the existing activity/finding feed as a vertical "Signal Stream" timeline, showing for each entry how long ago it occurred, its type or severity, a short evidence-backed description, and sentiment where applicable — sourced from the same underlying finding data and evidence links the dashboard already exposes today.
- **FR-004**: The dashboard MUST present the current churn score, its trend over the selected time window, and the ranked risk-driver breakdown together in a single "Churn Risk Overview" card, with the trend rendered as a continuous filled area chart rather than the current sparkline.
- **FR-005**: The Churn Risk Overview card MUST display the score's risk band/label exactly as currently computed, with no change to how the band is determined.
- **FR-006**: The dashboard MUST present the existing prioritized actions and any associated drafted outreach as an "Action & Draft Hub" list, showing each action's priority/urgency and a preview of its drafted message where one exists, with a way to reach the full list of actions.
- **FR-007**: The AI assistant MUST be presented as a floating component, reachable from anywhere on the dashboard, that the CS manager can open and collapse on demand without it permanently occupying primary content space. It MUST start collapsed (launcher only) on every page load, regardless of any prior session's open/collapsed state.
- **FR-008**: Opening or collapsing the floating assistant MUST NOT alter, discard, or reset the assistant's existing conversation state, history, or any in-flight request.
- **FR-009**: Every existing dashboard interaction — viewing evidence for a finding, opening the draft composer for an action, asking the assistant a question, viewing coverage/degraded-data indicators — MUST remain available after the redesign and MUST produce results identical to today's, since only presentation is changing.
- **FR-010**: The redesigned dashboard MUST preserve the existing "healthy account" near-empty state: when there is nothing actionable to show, the new layout MUST NOT manufacture chart activity, signal entries, or action items that do not reflect real underlying data.
- **FR-011**: The redesign MUST NOT modify, replace, or bypass any existing state management, API call, or data structure that feeds the dashboard; every visually redesigned element MUST continue to be populated from the same underlying data source it uses today.
- **FR-012**: The redesign MUST preserve existing accessibility behavior (keyboard reachability, screen-reader labeling) for every interactive element being restyled, at least at parity with today's implementation.
- **FR-013**: Header elements shown in the reference design that have no existing backing functionality today (e.g. a date-range selector, a live-status indicator, a notification bell/count) MUST be rendered as static, decorative visual elements only — they MUST NOT introduce new state, new API calls, or any new interactive behavior.

### Key Entities

- **Signal Stream entry**: A single timestamped item already produced by the dashboard's activity/finding feed — its type, severity, short description, and sentiment where applicable. No new data; only its presentation changes.
- **Churn Risk Overview**: The consolidated view of the account's current risk score, its historical trend, its risk band, and the ranked list of contributing risk drivers. All values already exist today; this feature co-locates and re-charts them.
- **Action & Draft Hub item**: A prioritized recommended action, optionally paired with a preview of an already-drafted outreach message. No new data; only its presentation changes.
- **Assistant conversation**: The ongoing exchange between the CS manager and the existing AI assistant, now reached through a floating entry point instead of a fixed, always-visible bar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time viewer can identify all four primary dashboard regions (navigation, Signal Stream, Churn Risk Overview, Action & Draft Hub) within 5 seconds of the page loading, matching the approved reference design's layout.
- **SC-002**: 100% of pre-existing dashboard interactions (evidence view, draft composer, assistant chat, coverage/degraded-data indicators) continue to work after the redesign, returning values identical to before the redesign.
- **SC-003**: The AI assistant can be opened from any scrolled position on the dashboard in a single action, without a page navigation and without losing the manager's current scroll position.
- **SC-004**: For any account with at least two historical score points, the churn risk trend is presented as a continuous area, not a disconnected sequence of points.
- **SC-005**: A side-by-side comparison against the approved reference design shows the four primary regions in their specified positions (sidebar left, Signal Stream center, Churn Risk Overview and Action & Draft Hub right) with zero discrepancies between displayed values and the account's actual underlying data.

## Assumptions

- This feature is presentation-layer only: markup, component structure, and styling may change, but existing state management, API calls, data structures, and business logic must not be touched. Any place where achieving the new visual design would require changing what data is fetched or how it is computed is out of scope and must be flagged rather than silently done.
- "Signal Stream," "Churn Risk Overview," and "Action & Draft Hub" are new visual framings of data the dashboard already surfaces today (activity/finding feed, score + trend + risk drivers, prioritized actions + drafts, respectively) — this feature restyles and rearranges them, it does not introduce new data.
- The floating assistant is a visual and interaction restyle of the existing always-present assistant into a collapsible floating widget (open/collapse on demand), preserving all existing conversational functionality and history. This follows the user's explicit instruction for a floating component, taking precedence where the reference mockup's illustrative placement differs.
- Sidebar destinations map to the application's existing pages (Dashboard, Coverage, Profile); no new pages or routes are introduced by this feature.
- Desktop/laptop viewport is the primary target, consistent with the rest of the application; narrower-viewport behavior follows the same conventions the application already uses elsewhere, unless a discrepancy is found during implementation.
- Specific chart-rendering and iconography technology choices are a planning-phase decision, governed by the project's existing technology standards; this specification describes the required visual outcome, not the implementation.
