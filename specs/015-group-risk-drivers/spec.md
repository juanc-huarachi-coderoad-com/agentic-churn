# Feature Specification: Group Repeated Risk Drivers

**Feature Branch**: `015-group-risk-drivers`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Group duplicate-label rows in the Churn Risk Overview's 'Top Risk Drivers' list. Today the list renders one row per underlying signal 1:1, which is correct and intentional per the dashboard evidence-trace contract (every row must trace to a real underlying record so it can open its own evidence). But when multiple signals share the same label (e.g. two separate 'escalation language' signals, or five 'commitment met' signals), the list visually shows the same label repeated many times with different point deltas, which reads as a bug to users even though it isn't one. The fix: group same-label signals into a single row showing the net summed points and a count badge (e.g. '×3'), expandable to reveal each original signal as its own sub-row, each still individually clickable to open its own evidence — so the underlying evidence-trace contract is completely unchanged; only the presentation of that list is grouped. This also makes the list sorted by absolute net points descending, which was always the intended sort for 'Top Risk Drivers' but was never actually enforced. Out of scope: the underlying data contract, the evidence panel itself, the dashboard's separate 'click the score' shortcut, and the Action & Draft Hub (a separate card with its own ranking). This spec is being written retroactively to document a change already implemented, per this repository's spec-first convention."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A repeated driver label reads as one clear signal, not visual noise (Priority: P1)

A Customer Success manager opens a client's Churn Risk Overview and looks at "Top Risk Drivers" to understand what's pushing the score up or down. When several separate signals of the same kind occurred (e.g. three separate contractual-reference mentions), the manager sees one row for that driver type showing its combined impact, instead of the same label repeated several times in a row with no visual grouping.

**Why this priority**: This is the core complaint — the list currently looks broken/duplicated even though every row is legitimate, which erodes trust in the dashboard and makes the top drivers harder to scan at a glance. Fixing the read is the entire point of this feature.

**Independent Test**: Load a client whose latest score run includes multiple signals sharing the same driver label with different point values; confirm the "Top Risk Drivers" list shows exactly one row per distinct label, with a combined point value and a count indicator when more than one signal contributed.

**Acceptance Scenarios**:

1. **Given** a client's latest score run has three signals labeled "contractual reference" contributing different point values, **When** the manager opens Churn Risk Overview, **Then** "Top Risk Drivers" shows a single "contractual reference" row with the net combined point value and a "×3" indicator.
2. **Given** a client's latest score run has exactly one signal for a given label, **When** the manager opens Churn Risk Overview, **Then** that label's row shows no count indicator and looks exactly as it did before this change.
3. **Given** the grouped list is displayed, **When** the manager compares row order, **Then** rows are ordered by the magnitude of their combined impact, highest first.

---

### User Story 2 - Every individual signal remains traceable to its own evidence (Priority: P1)

A Customer Success manager wants to verify why a driver has the score it does. Even after same-label signals are grouped into one row, the manager can still see and open each individual underlying signal that contributed to that row, and each one opens the correct, specific evidence for that signal — never a different signal's evidence, and never a generic/blended view.

**Why this priority**: Losing the ability to trace a driver back to its specific real evidence would break the dashboard's core trust guarantee (every number shown must be explainable by a real record) — this is equally critical to User Story 1, not a secondary nice-to-have.

**Independent Test**: Open a grouped driver row with multiple contributing signals, expand it, and confirm each sub-row opens its own distinct evidence when selected.

**Acceptance Scenarios**:

1. **Given** a grouped driver row representing three signals, **When** the manager expands the row, **Then** three individual sub-rows appear, each showing that specific signal's own point value.
2. **Given** the row is expanded, **When** the manager selects one specific sub-row, **Then** the evidence shown is for that exact signal, distinguishable from the other two.
3. **Given** a driver row with only one contributing signal, **When** the manager selects it, **Then** its evidence opens directly, with no extra expand step required (unchanged from today's behavior).

---

### Edge Cases

- What happens when a grouped label's contributing signals don't all push the score in the same direction (some increase risk, some reduce it)? The combined value shown is the net effect, and the row's visual treatment (e.g. color) follows that net direction.
- What happens when there are no risk drivers at all for a client (a healthy account with nothing contributing to the score)? The section remains empty exactly as it does today — grouping introduces no new "no data" state.
- What happens when a driver label has a very large number of contributing signals (e.g. 10+)? All of them remain visible in the expanded view; no artificial cap is introduced by this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The "Top Risk Drivers" list MUST show at most one row per distinct driver label for a given client's latest score.
- **FR-002**: When more than one signal shares a driver label, the list MUST display a visible indicator of how many signals contributed to that row (e.g. a count).
- **FR-003**: A grouped row's displayed point value MUST equal the net combined effect of all its contributing signals, using the same point convention (sign/direction) already used for a single signal today.
- **FR-004**: A driver label with only one contributing signal MUST look and behave exactly as a single risk-driver row does today — no count indicator, no extra step to reach its evidence.
- **FR-005**: Users MUST be able to reveal every individual signal that contributed to a grouped row.
- **FR-006**: Every individual signal, whether shown directly (single-signal row) or after revealing a grouped row, MUST remain independently selectable to open that exact signal's own evidence — never another signal's evidence, and never a blended/summary evidence view.
- **FR-007**: The "Top Risk Drivers" list MUST be ordered by the magnitude of each row's combined point value, highest impact first.
- **FR-008**: This feature MUST NOT change how many signals are recorded, how their points are calculated, or the underlying 1:1 relationship between a signal and its evidence record — only how same-label signals are presented together in this one list.
- **FR-009**: This feature MUST NOT change the "click the score" shortcut, the Action & Draft Hub's own ranked list, or any other surface that independently consumes the same underlying signals.

### Key Entities *(include if feature involves data)*

- **Risk Driver Row (grouped)**: A presentation-only grouping of one or more underlying signals that share the same driver label within a client's latest score. Attributes: label, combined point value, contributing signal count, the ordered list of contributing signals. Not persisted — recomputed each time the list is displayed.
- **Underlying Signal**: An existing, already-persisted individual finding that contributes points to a client's score (unchanged by this feature) — the thing a grouped row's count refers to and each expanded sub-row represents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any client whose latest score has repeated driver labels, the "Top Risk Drivers" list shows zero duplicate label rows at the top level.
- **SC-002**: A manager can identify, for any grouped driver row, exactly how many signals contributed to it, without leaving the dashboard.
- **SC-003**: 100% of individual signals remain reachable to their own specific evidence — grouping never reduces the set of signals a manager can trace back to a real record.
- **SC-004**: The order of rows in "Top Risk Drivers" always matches descending combined impact magnitude.

## Assumptions

- This is a presentation-layer change only: the underlying data supplied to the dashboard already contains one entry per signal, and that shape is not modified by this feature.
- "Net combined effect" for a grouped row is a simple sum of the individual signals' point values (using the existing single-signal sign convention); no new weighting or decay logic is introduced.
- No cap is placed on how many rows the grouped list can show or how many signals a single group can expand to — existing list length is already bounded by how many signals exist for the client's latest score.
- The Action & Draft Hub and any other dashboard surface that separately renders the same underlying signals are out of scope; only the "Top Risk Drivers" list within Churn Risk Overview is affected.
