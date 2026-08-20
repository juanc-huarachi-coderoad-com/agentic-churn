# Feature Specification: Aura Orb Heartbeat Redesign

**Feature Branch**: `020-aura-orb-heartbeat`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Build the next improve: Tengo este componente frontend/src/dashboard/aura-risk-orb.tsx y quiero mejorarlo. Quiero que se vea como base/aura.png. Quiero que tenga una animacion como de latido suave y elegante, como si el agente estuviera vivo, y quitar el socre. Claro solo el color de este circulo va relacionado con el score. Por favor que sea profesional y elegante."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Polished, glowing risk indicator (Priority: P1)

As a dashboard user reviewing a customer's churn risk, I see a refined, glossy, glowing orb — matching the elegant reference look — instead of a flat gradient circle, so the risk indicator feels premium and professional at a glance.

**Why this priority**: This is the core visual upgrade the request is about; without it, nothing else in this feature has value.

**Independent Test**: Can be fully tested by viewing the orb in each risk band and confirming it renders as a soft, luminous sphere with a highlight and outer glow consistent with the reference image, independent of the animation or label changes.

**Acceptance Scenarios**:

1. **Given** a customer record with any risk band, **When** the dashboard renders the risk orb, **Then** the orb displays as a glossy sphere with a soft highlight and a gentle outer glow, colored according to the customer's risk band.
2. **Given** the three existing risk bands (healthy, watch, at_risk), **When** each is rendered, **Then** the glossy/glow visual treatment is consistent across all three, differing only in color.

---

### User Story 2 - Living, breathing pulse (Priority: P2)

As a dashboard user, I see the orb gently pulse in a slow, elegant rhythm, so the interface feels alive and actively monitoring, rather than a static graphic.

**Why this priority**: The animation is the signature "alive" feeling the request calls for, but it builds on top of the visual redesign in User Story 1.

**Independent Test**: Can be fully tested by observing the orb over several seconds and confirming a continuous, smooth, subtle pulsing motion (not abrupt or mechanical) occurs without any user interaction.

**Acceptance Scenarios**:

1. **Given** the orb is visible on screen, **When** no user interaction occurs, **Then** the orb continuously animates a slow, soft pulse (e.g., gentle scale and/or glow breathing) on a loop.
2. **Given** a user has enabled a reduced-motion accessibility preference, **When** the orb is displayed, **Then** the pulse animation is paused or significantly minimized so it does not trigger motion sensitivity.

---

### User Story 3 - Score removed from the orb face (Priority: P3)

As a dashboard user, I no longer see the raw numeric score printed on the orb itself, so the visual reads as a clean, elegant indicator rather than a data readout; the score continues to influence only the orb's color.

**Why this priority**: This is a decluttering change that depends on the redesigned visual (P1) already being in place to look intentional rather than like a missing element.

**Independent Test**: Can be fully tested by rendering the orb for any score/band combination and confirming no numeric text appears anywhere on or over the orb.

**Acceptance Scenarios**:

1. **Given** a customer record with a specific numeric score, **When** the risk orb renders, **Then** no digits or numeric score text are displayed on the orb.
2. **Given** two customers with different scores but the same risk band, **When** their orbs render, **Then** the orbs are visually identical except for the animation phase (color is band-driven, not score-driven).

---

### Edge Cases

- What happens when a customer's risk band changes (e.g., after a re-score)? The orb's color should update to the new band's color without a jarring flash; the pulse animation continues uninterrupted.
- How does the orb behave when the user's system/browser is set to prefer reduced motion? The pulse must be paused or minimized rather than forced to play.
- How does the orb look at very small or very large rendered sizes (e.g., a compact list row vs. a large dashboard tile)? The glow and pulse must scale with the orb and must not be clipped by, or overflow into, surrounding layout elements.
- What happens when multiple orbs are visible on the same screen at once (e.g., a list of customers)? Each orb's pulse animates independently; the score value remains accessible elsewhere in the UI (e.g., the surrounding score card) for users who need the exact number.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The risk orb MUST render as a glossy, luminous sphere with a soft highlight and a gentle outer glow, visually consistent with the provided reference image, rather than a flat gradient disc.
- **FR-002**: The orb's fill color MUST continue to be determined solely by the customer's risk band, using the existing band-to-color mapping, with no other visual element tied to the raw score.
- **FR-003**: The orb MUST NOT display the numeric score, or any other digits, as text on or over its surface.
- **FR-004**: The orb MUST continuously animate a slow, smooth, subtle pulsing ("heartbeat"/breathing) motion for as long as it is visible on screen, requiring no user interaction to start or sustain it.
- **FR-005**: The pulse animation MUST read as gentle and elegant — small in amplitude and slow in tempo — rather than bouncy, abrupt, or attention-grabbing.
- **FR-006**: The pulse animation MUST respect the user's reduced-motion accessibility preference, pausing or substantially minimizing motion when that preference is active.
- **FR-007**: The glossy/glow visual treatment and the pulse animation MUST render consistently across all existing risk bands (healthy, watch, at_risk), differing only in color.
- **FR-008**: The orb MUST remain fully responsive, preserving its circular shape, highlight, and glow proportionally when its container is resized, without clipping into or overflowing surrounding layout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify a customer's risk band from the orb's color alone, with no numeric score visible on the orb, in 100% of rendered instances.
- **SC-002**: The orb animates a continuous, visible pulse in every risk band state, verified by observing each band for at least one full pulse cycle.
- **SC-003**: In stakeholder design review, the redesigned orb is confirmed to match the intended reference look (glossy, glowing, professional/elegant) and is approved without requesting further visual rework.
- **SC-004**: Users with a reduced-motion accessibility preference enabled report no jarring or distracting motion when viewing the dashboard.
- **SC-005**: The orb renders correctly (no clipped glow, no layout overflow) across the range of sizes it is currently used at in the dashboard.

## Assumptions

- The exact numeric score remains available to users elsewhere in the dashboard (e.g., the surrounding score card/detail view), so removing it from the orb face does not reduce the information available overall — it only removes the duplicate readout on the orb itself.
- The existing three-band color palette (healthy/watch/at_risk) is reused as-is; this feature does not introduce a new continuous score-to-color gradient.
- "Heartbeat" refers to a slow, smooth, soft pulse (subtle breathing-like scale and/or glow variation), not a literal two-beat cardiac rhythm.
- The provided reference image sets the target aesthetic direction (glossy sphere, soft highlight, gentle outer glow) rather than an exact pixel-level specification to match precisely.
- The component continues to be used in its existing placements within the dashboard; this feature does not change where or how the orb is positioned on the page.
- When multiple orbs render on the same screen, their pulse animations are independent and do not need to be synchronized with one another.
