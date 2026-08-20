# Feature Specification: Chat Component Sender Identification Redesign

**Feature Branch**: `021-chat-component-redesign`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Mejorar el componente del chat, adicionar los componentes especificamente para identificar que actor a escrito la siguiente parte como un chat normal. Solo modificar esta parte (el componente de chat), basate en este archivo base/chatComponent.jpg. Identificar al humano, mostrar la hora, mostrar el icono como esta en la imagen, de la misma manera para AURA assistant, mostrar la hora y al lado la hora, alinear las horas a los extremos de cada participante, que sea uniforme. El componente chat deberia verse elegante y profesional."

## Clarifications

### Session 2026-08-20

- Q: What time format should message timestamps use? → A: 12-hour format with AM/PM (e.g., "10:32 AM"), matching the reference image exactly
- Q: Should the human's icon be personalized (photo/initials) or generic? → A: Always use the generic person icon shown in the reference image, regardless of who the logged-in user is
- Q: Should pending ("thinking") and error states show the full AURA Assistant sender identity (icon/label/timestamp)? → A: No — sender icon/label/timestamp only appear on completed messages; pending and error states show as a plain status indicator with no sender identity block
- Q: Should timestamps include a date when a conversation spans multiple days? → A: No — time-only is always sufficient; no date label is shown even if a conversation technically spans multiple days

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instantly tell who said what (Priority: P1)

A user reviewing a conversation with the AURA Assistant needs to scan the thread and immediately know, for every message, whether it came from them (the human) or from the assistant, without reading the message content first.

**Why this priority**: This is the core problem being fixed. Today the chat renders messages without a clear, consistent visual identity per sender, which makes fast scanning and trust in the assistant's responses harder. This single change delivers the most value on its own.

**Independent Test**: Open a conversation containing at least one human message and one assistant message. Confirm each message row shows a distinct sender icon/avatar and sender label positioned consistently for that role (human vs. assistant), matching the reference layout in `base/chatComponent.jpg`.

**Acceptance Scenarios**:

1. **Given** a conversation with a human message, **When** the chat renders, **Then** the message shows a human avatar/icon and the label "Human" aligned to the same side consistently used for all human messages.
2. **Given** a conversation with an AURA Assistant message, **When** the chat renders, **Then** the message shows the AURA Assistant icon and the label "AURA Assistant" aligned to the same side consistently used for all assistant messages.
3. **Given** a mixed conversation with multiple back-and-forth turns, **When** the user scans the thread, **Then** each message is unambiguously attributable to its sender based on icon, label, and alignment alone (no need to read the text).

---

### User Story 2 - See when each message was sent (Priority: P2)

A user needs to know the time each message was sent so they can understand the pacing and recency of the conversation.

**Why this priority**: Timestamps add necessary context (e.g., "was this answered right away?") but are secondary to knowing who is speaking. This builds directly on User Story 1.

**Independent Test**: Open a conversation and confirm every message (human and assistant) displays a timestamp next to the sender's name, with the identity row (icon + label + timestamp) consistently anchored to the outer edge of that sender's message block — the icon nearest the edge, the timestamp nearest the center.

**Acceptance Scenarios**:

1. **Given** a human message, **When** it renders, **Then** the timestamp appears next to the "Human" label, with the identity row (icon, then label, then timestamp) anchored to the left/outer edge of the human's message block and the icon nearest that edge, matching the reference image.
2. **Given** an AURA Assistant message, **When** it renders, **Then** the timestamp appears next to the "AURA Assistant" label, with the identity row (timestamp, then label, then icon) anchored to the right/outer edge of the assistant's message block and the icon nearest that edge, matching the reference image.
3. **Given** messages from both senders in the same thread, **When** compared side by side, **Then** identity-row placement is uniform and mirrored between the two roles (each identity row is anchored to its own participant's outer edge — icon outermost, timestamp innermost — not both on the same side).

---

### User Story 3 - Perceive the chat as polished and trustworthy (Priority: P3)

A user (or a stakeholder demoing the product) needs the chat surface to look elegant and professional, consistent with the rest of the AURA dashboard, so the tool feels production-ready.

**Why this priority**: Visual polish reinforces trust and adoption but does not block the functional goal of sender/time identification delivered in P1 and P2.

**Independent Test**: Visually compare the rendered chat component against `base/chatComponent.jpg` and the existing AURA design language; confirm consistent spacing, typography, color treatment, and rounded message bubbles with no layout glitches across a short and a long conversation.

**Acceptance Scenarios**:

1. **Given** a conversation of varying message lengths (short one-liners and long multi-paragraph replies), **When** rendered, **Then** message bubbles, spacing, and alignment remain visually consistent and readable.
2. **Given** the chat header showing the assistant name and online status, **When** rendered, **Then** it visually matches the elegant, professional styling shown in the reference image (sparkle icon, "AURA ASSISTANT" title, status indicator).

---

### Edge Cases

- What happens while the AURA Assistant is still composing a reply (pending/loading) or a reply fails (error)? These states MUST render as a plain status indicator (no sender icon, label, or timestamp) since no message has actually been sent yet; the full sender identity block only appears once a message (human question or assistant answer) is complete.
- How does the component handle consecutive messages from the same sender? Each message MUST still show its own sender icon, label, and timestamp so identification never depends on message order.
- How does the layout behave with very long assistant responses (multi-paragraph, lists)? Sender icon/label/timestamp for that message MUST stay pinned to the top of that message block rather than stretching or duplicating.
- How does the layout behave on narrow viewports? Sender identification and timestamp alignment MUST remain legible and not overlap or truncate critical information (sender label, timestamp).
- What happens when the human user has no distinguishable name (generic "Human" role)? The generic human icon/label from the reference image MUST be used as the default identification.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The chat component MUST visually distinguish messages sent by the human from messages sent by the AURA Assistant, using a distinct icon/avatar per role.
- **FR-002**: The chat component MUST display a sender label ("Human" for the user, "AURA Assistant" for the assistant) alongside each message.
- **FR-003**: The chat component MUST display a timestamp for every message, showing the time the message was sent in 12-hour format with an AM/PM indicator (e.g., "10:32 AM"), matching the reference image. No date is shown alongside the time, even for conversations spanning multiple days.
- **FR-004**: The chat component MUST position each message's sender icon, label, and timestamp on the same horizontal line, anchored as a single block to that participant's outer edge of the screen — the sender icon nearest the true outer edge, the timestamp nearest the center (human block anchored to the left edge, reading icon → label → timestamp; assistant block anchored to the right edge, mirrored: timestamp → label → icon).
- **FR-005**: The chat component MUST apply this sender icon, label, and timestamp treatment uniformly to every completed message in the conversation, regardless of message order or length. The one exclusion applies only to the not-yet-resolved assistant answer: while a turn's answer is pending ("thinking") or has errored, that answer MUST NOT show a sender icon, label, or timestamp — it renders as a plain status indicator only, since no assistant message has actually been sent yet. The human question's own identity row is unaffected by its turn's status and always renders once the question is submitted.
- **FR-006**: The chat component MUST render the human avatar/icon and the AURA Assistant icon matching the style shown in `base/chatComponent.jpg` (human: filled circular person icon; assistant: sparkle icon). The human icon is a fixed generic icon and is NOT personalized per logged-in user (no photo, initials, or per-user variation).
- **FR-007**: The chat component MUST preserve existing chat functionality (sending a message, receiving assistant replies, message input field with attachment and send controls) unchanged in behavior — this feature only changes the visual presentation of sender identity and timestamps within the chat message list.
- **FR-008**: The chat component MUST NOT require changes to any other component outside the chat message list/thread area (e.g., risk score panels, dashboard navigation) to satisfy this feature.
- **FR-009**: The visual styling (spacing, colors, bubble shape, typography) MUST read as elegant and professional, consistent with the reference image and the existing AURA Assistant visual identity (purple accent, sparkle branding).

### Key Entities

- **Chat Message**: A single entry in the conversation. Key attributes: sender role (human or AURA Assistant), message text/content, timestamp (time sent), and rendering position (which side of the thread it appears on).
- **Participant**: The two roles that can send messages — the Human (end user) and the AURA Assistant. Each has a fixed icon and label used for every message they send.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can correctly identify the sender of any message in a conversation within 1 second of glancing at it, using only the icon/label/alignment (no need to read message text).
- **SC-002**: 100% of rendered messages display both a sender identity (icon + label) and a timestamp, with zero messages missing this information under normal conditions.
- **SC-003**: Identity-row alignment is consistent across 100% of messages — human identity rows are always anchored to the left/outer edge (icon outermost, timestamp innermost), assistant identity rows are always anchored to the right/outer edge (icon outermost, timestamp innermost), mirrored between the two roles.
- **SC-004**: In a side-by-side visual comparison, stakeholders rate the redesigned chat component as matching the professional/elegant quality of the reference image.

## Assumptions

- The reference image `base/chatComponent.jpg` reflects the target visual design for sender icons, label placement, and timestamp alignment; exact pixel values (fonts, colors, spacing) will follow the existing AURA design system where the image does not specify precise values.
- This feature is scoped strictly to the chat message list/thread rendering (message bubbles, sender icons, labels, timestamps) and the chat header, not to the underlying chat/messaging logic, data storage, or the message input control's functional behavior.
- "Human" is the correct generic label for the end-user role, matching the reference image's "Human" heading, even though a real deployment may know the user's actual name elsewhere in the app.
- Message timestamps are not currently captured or displayed anywhere in the chat; this feature includes recording the time each message is sent/received (client-side, at the moment the message enters the conversation) so it can be displayed — no historical/backend timestamp data needs to be sourced for existing past messages.
- The existing chat online/status indicator and header (assistant name, sparkle icon, options menu) remain in scope only to the extent needed to preserve the "elegant and professional" look shown in the reference image; no new header functionality is required.
