# Feature Specification: Dashboard Mockup V2 Refinement

**Feature Branch**: `016-dashboard-mockup-v2-refinement`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Improve the dashboard page conforming to the mockup @base/mockup-mainPage-v2.jpg. The dashboard is divided into three columns as shown in the mockup image. The first column has the company title, the AURA agent section with a gradient-colored circle showing the risk score (color changes based on risk score, using the gradient and style from the image), and the assistant chat component — already deployed and ready to converse, positioned below the AURA section as in the mockup. The second column is the Signal Stream, grouped in a column as in the mockup; each item shows time, signal type (Activity, Email, Chat, ...) with type-specific icons, severity instead of sentiment, and a connecting timeline line showing event history. The third column has the Churn Risk Overview (large color-coded score, trend chart with labeled Y-axis percentage and X-axis history sequence) and The Action & Draft Hub. Columns occupy the available screen height and scroll independently — no whole-page scroll. Every selectable item must have a hover/selectable affordance on its icon and a smooth interaction effect. Selecting an item opens its details in an elegant modal instead of a side panel."

## Clarifications

### Session 2026-08-18

- Q: The mockup's Signal Stream shows each entry labeled with a signal type (Activity, Email, Chat, etc.) and a matching icon, but today's data contract only carries severity — no type/channel field reaches the frontend, even though the database already stores a real event type that is never surfaced through the API. How should the signal type shown in the UI be sourced? → A: Extend the backend query/API contract to surface the database's existing event type, mapped to a human-readable label and icon — the displayed type always reflects the signal's real origin.
- Q: Each Signal Stream entry needs to convey both its signal type and its severity, but the mockup shows only one icon per entry. How should these two attributes be encoded on that single icon? → A: Icon shape is chosen by the entry's real signal type (e.g., envelope for a message, chart for usage, checkmark for a resolved ticket); icon color/ring is chosen by the entry's severity, reusing the existing severity color scheme.
- Q: The dashboard today also shows an AI-generated narrative headline, stakeholder cards, and a data-coverage/completeness indicator inside the Signal Stream column — none of which appear in the reference mockup. Where should they live in the new three-column layout? → A: Keep all three appended below the Signal Stream entries, in the second column, reachable by scrolling that column — nothing is removed or moved to a different column.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the three-column, full-height layout (Priority: P1)

A Customer Success manager opens the dashboard and sees three columns filling the available screen height: a left column with the company/agent branding, a middle column with the Signal Stream, and a right column with the Churn Risk Overview and Action & Draft Hub. Each column scrolls independently within its own space; the page itself never scrolls as a whole.

**Why this priority**: This is the structural foundation every other visual improvement in this feature sits inside — without the three-column, independently-scrolling shell, none of the other refinements can be evaluated in context.

**Independent Test**: Load the dashboard on a standard desktop viewport, confirm the three columns are visible side by side and each fills the vertical space up to the viewport edge, then add enough content to any one column to force scrolling and confirm only that column scrolls while the other columns and the overall page remain fixed.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** the CS manager views the page, **Then** three columns are visible side by side, each occupying the full height available within the viewport.
2. **Given** a column contains more content than fits its visible height, **When** the CS manager scrolls within that column, **Then** only that column's content moves; the other columns and the page frame stay in place.
3. **Given** the dashboard is loaded on a narrower viewport where three columns cannot reasonably fit side by side, **When** the CS manager views the page, **Then** the layout reflows consistent with how the rest of the application already handles reduced width, rather than clipping or hiding content.

---

### User Story 2 - Read churn risk at a glance from the enhanced overview (Priority: P2)

A Customer Success manager looks at the third column and immediately reads the account's churn risk score as a large, color-coded number matching the risk band's meaning, and can read the score trend chart's exact values because both axes are labeled — percentage on the Y axis, historical sequence on the X axis.

**Why this priority**: This is the dashboard's primary decision-support surface; making the score and its trend immediately legible (without hovering or guessing at scale) delivers the highest standalone value after the layout foundation exists.

**Independent Test**: Open the dashboard for an account with score history and confirm the score renders at prominent size in the color matching its current risk band, and that the trend chart shows labeled percentage values on the Y axis and labeled sequence points on the X axis without requiring a hover interaction.

**Acceptance Scenarios**:

1. **Given** an account with a computed risk score, **When** the CS manager views the Churn Risk Overview card, **Then** the score is displayed at large, prominent size in a color that matches the account's current risk band.
2. **Given** an account with score history, **When** the CS manager views the trend chart, **Then** the Y axis shows percentage labels and the X axis shows labels for the historical sequence, both visible without hovering.
3. **Given** an account has fewer than two historical score points, **When** the CS manager views the chart, **Then** it degrades gracefully (e.g., a single labeled point or a clear "not enough history yet" presentation) instead of rendering a misleading or broken chart.

---

### User Story 3 - Scan the Signal Stream by real signal type and severity (Priority: P3)

A Customer Success manager scans the Signal Stream and, for each entry, sees how long ago it occurred, what kind of signal it is (e.g., activity, email/message, ticket, usage) shown with a type-specific icon reflecting its real origin, and its severity — connected by a visible timeline line showing the sequence of events.

**Why this priority**: This lets a CS manager triage signals by origin and severity without opening each one, which is a meaningful scanning improvement, but it depends on the column layout from User Story 1 and is secondary to the risk overview's decision-support value.

**Independent Test**: Open the dashboard for an account with a mix of event types and severities in its Signal Stream and confirm each entry shows elapsed time, a type label with a matching icon that reflects the entry's real underlying event type, and a severity indicator — with a connecting line linking entries in chronological order.

**Acceptance Scenarios**:

1. **Given** a Signal Stream entry backed by a specific underlying event type, **When** the CS manager views it, **Then** the displayed type label and icon shape reflect that entry's real underlying type, not a generic or fabricated category.
2. **Given** multiple Signal Stream entries with different severities, **When** the CS manager views the column, **Then** each entry's icon color/ring reflects its severity (not a sentiment label), its shape reflects its type, and a connecting timeline line links the entries in chronological order.
3. **Given** an event type without a defined mapping to a human-readable label/icon, **When** the CS manager views that entry, **Then** the entry still renders using a sensible fallback label/icon rather than breaking the stream.

---

### User Story 4 - Converse with AURA from an always-ready docked panel (Priority: P4)

A Customer Success manager opens the dashboard and finds the AURA Assistant already expanded and ready to converse in the first column, directly below the AURA risk indicator — not a floating button they must first open.

**Why this priority**: This changes how the assistant is reached but the dashboard's core information is fully usable without it; it depends on the column layout existing first and is lower priority than the risk overview and signal stream content.

**Independent Test**: Load the dashboard and confirm the AURA Assistant panel is visible and interactive (not collapsed) directly below the AURA risk indicator without any additional click, and that sending a message and scrolling elsewhere on the page does not close or reset it.

**Acceptance Scenarios**:

1. **Given** the CS manager loads the dashboard, **When** the page finishes loading, **Then** the AURA Assistant panel is already expanded and ready to accept a message, positioned below the AURA risk indicator in the first column.
2. **Given** an existing assistant conversation, **When** the CS manager scrolls or interacts elsewhere on the dashboard, **Then** the assistant panel and its conversation history remain visible and unchanged.
3. **Given** the assistant panel is docked in column one, **When** the CS manager views columns two and three, **Then** neither is obscured or resized by the assistant panel.

---

### User Story 5 - Open item details in an elegant modal with clear selectable affordance (Priority: P5)

A Customer Success manager hovers over a Signal Stream entry or an Action & Draft Hub item and sees a smooth visual cue (on the icon and the item) indicating it can be selected. Selecting it opens its full details in a centered modal overlay, instead of a panel sliding in from the side of the screen.

**Why this priority**: This is a polish/interaction-quality improvement on top of the content already delivered by the earlier stories; the dashboard is functionally complete without it, but it makes selection intent and detail viewing feel more deliberate and less disruptive to the surrounding layout.

**Independent Test**: Hover over a Signal Stream entry and an Action & Draft Hub item and confirm each shows a smooth selectable affordance; select each and confirm details open in a centered modal (not a side panel) with all information and actions the current detail view provides, and confirm the modal closes without residual layout shift.

**Acceptance Scenarios**:

1. **Given** a selectable Signal Stream entry or Action & Draft Hub item, **When** the CS manager hovers over it, **Then** the item and its icon show a smooth visual affordance indicating it is selectable.
2. **Given** the CS manager selects an item, **When** its details open, **Then** they appear in a centered modal overlay containing the same information and actions available in today's detail view.
3. **Given** a detail modal is open, **When** the CS manager selects a different item, **Then** at most one detail modal is visible at a time.
4. **Given** a detail modal is open, **When** the CS manager dismisses it (e.g., via backdrop or close control), **Then** the underlying columns return to their prior scroll position and layout, unchanged.

---

### Edge Cases

- What happens when a Signal Stream entry's underlying event type has no defined label/icon mapping (e.g., a new type added later)? The entry MUST still render with a sensible fallback rather than breaking the stream.
- What happens when the account is healthy and has nothing actionable to show? The layout MUST still collapse to the existing near-empty "all clear" presentation rather than forcing column chrome to display empty or fabricated content.
- What happens when the AURA Assistant's conversation grows long within the docked panel? The panel's own content MUST scroll (or the column MUST scroll) without disrupting the columns beside it.
- What happens when the Signal Stream or Action & Draft Hub has far more entries than fit in the visible column height? The column MUST remain independently scrollable to reach the rest.
- What happens when a CS manager selects a new item while a detail modal is already open? The system MUST show at most one modal at a time rather than stacking modals.
- What happens on a narrower browser window where three fixed-width columns cannot fit? The layout MUST reflow consistent with the rest of the application's existing responsive handling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST present three columns — branding/assistant, Signal Stream, and Churn Risk Overview with Action & Draft Hub — matching the structure of the approved reference design.
- **FR-002**: Each column MUST occupy the height available within the viewport and scroll independently when its content exceeds that height; the overall page MUST NOT scroll as a whole.
- **FR-003**: The first column MUST show the company/product title, the "AURA" agent label, and a gradient-colored circular risk indicator whose color reflects the account's current risk band, using the existing risk band color scheme.
- **FR-004**: The first column MUST present the AURA Assistant as a persistently docked, already-expanded panel directly below the risk indicator — not a floating or collapsed launcher — ready to send and receive messages as soon as the dashboard loads, while preserving existing conversation behavior and history.
- **FR-005**: The second column (Signal Stream) MUST show, for each entry: elapsed time since occurrence, a signal-type label with a matching icon reflecting the entry's real underlying event type, its severity, and its evidence-quoted text.
- **FR-005a**: Each Signal Stream entry's icon MUST encode both attributes at once — its shape/glyph chosen by the entry's real signal type, and its color/ring chosen by the entry's severity, reusing the existing severity color scheme — rather than one icon representing only one of the two attributes.
- **FR-006**: The system MUST surface the event type already stored for each signal (previously not exposed through the API) through the backend query and API contract, mapped to a human-readable label and icon, without fabricating a category unrelated to the signal's real origin.
- **FR-007**: The second column MUST render a connecting vertical timeline line linking consecutive Signal Stream entries in chronological order, consistent with the reference design.
- **FR-008**: The Signal Stream MUST display each entry's severity; it MUST NOT display a sentiment-based label in its place.
- **FR-009**: The third column MUST display the current churn risk score as a large, prominently sized number colored according to its current risk band.
- **FR-010**: The third column's score trend chart MUST label the Y axis with percentage values and the X axis with the historical sequence/day index, visible without requiring a hover interaction.
- **FR-011**: The third column MUST continue to present the ranked risk-driver list and the Action & Draft Hub beneath the Churn Risk Overview card, sourced from the same underlying data used today.
- **FR-012**: Every selectable item (Signal Stream entries and Action & Draft Hub items) MUST provide a smooth visual affordance on its icon and body indicating it can be selected (e.g., on hover/focus).
- **FR-013**: Selecting a Signal Stream entry or an Action & Draft Hub item MUST open its details in a centered modal overlay rather than a side-docked panel, preserving all information and actions currently available in the existing detail view.
- **FR-014**: At most one detail modal MUST be visible at a time; selecting a different item while a modal is open MUST NOT stack a second modal.
- **FR-015**: The redesign MUST NOT alter the underlying score computation, risk-band classification, risk-driver ranking, action prioritization, or draft content — only presentation, and, per FR-006, the exposure of the already-stored event type.
- **FR-016**: The redesign MUST preserve existing accessibility behavior (keyboard reachability, screen-reader labeling, focus management) for every restyled interactive element, and MUST extend that behavior to the new modal pattern.
- **FR-017**: The layout MUST preserve the existing "healthy account" near-empty state, without manufacturing signal entries, chart activity, or action items that do not reflect real data.
- **FR-018**: On viewports too narrow to show three columns side by side, the layout MUST reflow consistent with the application's existing responsive handling rather than clipping or hiding column content.
- **FR-019**: The second column MUST continue to present the existing narrative headline, stakeholder information, and data-coverage/completeness indicator beneath the Signal Stream entries, reachable by scrolling that column — none of these MUST be removed or relocated to a different column by this redesign.

### Key Entities

- **Signal Stream entry**: A timestamped item from the account's activity/finding feed, now additionally carrying a real signal type/channel (sourced from the underlying event type) alongside its existing elapsed time, severity, and evidence-quoted text. Its icon shape is determined by type and its icon color/ring by severity, so both attributes remain visible at a glance.
- **Churn Risk Overview**: The account's current risk score, risk band, historical trend, and ranked risk-driver list, now presented with a prominently sized, band-colored score and an explicitly axis-labeled trend chart.
- **AURA Assistant conversation**: The ongoing exchange between the CS manager and the assistant, now reached through an always-expanded, docked panel in the first column instead of a floating launcher.
- **Detail Modal**: The centered overlay presentation used to show full details for a selected Signal Stream entry or Action & Draft Hub item, replacing the previous side-docked panel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A CS manager can identify a Signal Stream entry's elapsed time, signal type, and severity within a single glance, without opening its detail view.
- **SC-002**: A CS manager can determine the account's risk standing (score value and band) from the Churn Risk Overview card without any additional interaction (hover, click, or scroll).
- **SC-003**: A CS manager can read the trend chart's percentage value and historical position for any labeled axis point directly, without hovering.
- **SC-004**: No dashboard column requires the overall page to scroll to reach its content; scrolling is always contained within the individual column, on supported desktop viewport widths.
- **SC-005**: Selecting any Signal Stream entry or Action & Draft Hub item opens its details in a centered modal in a single interaction, with no more than one modal ever visible at a time.
- **SC-006**: 100% of Signal Stream entries display a signal type that reflects their real underlying origin — no entry shows a placeholder or fabricated type when a real type exists.
- **SC-007**: The AURA Assistant is usable (able to send a message) immediately on dashboard load, with zero additional clicks needed to reach an expanded conversation state.

## Assumptions

- The existing risk band colors (healthy, watch, at_risk) are reused for the gradient risk indicator and the large score display; no new color thresholds are introduced.
- "Elegant modal" means a centered, dismissible overlay (backdrop click and an explicit close control) that preserves all content and actions from today's side-docked detail panels; only the presentation position and framing change.
- This feature targets the primary desktop/wide-viewport experience, consistent with the dashboard's existing responsive precedent; a narrower-viewport-specific redesign beyond existing reflow behavior is out of scope.
- The AURA Assistant becomes a permanently docked, expanded panel in the first column for the main dashboard; the previously floating, collapse-by-default launcher behavior is superseded by this feature on this page.
- Mapping the database's stored event types to the mockup's example categories (Activity, Email, Chat, etc.) uses reasonable human-readable labels and icons chosen during implementation; this specification does not fix the exact wording or icon per type.
- This feature applies to the main dashboard page only; other pages (Coverage, Profile) are out of scope.
