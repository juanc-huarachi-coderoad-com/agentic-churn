# Feature Specification: Ask Agent Flexible Response Formats

**Feature Branch**: `014-ask-agent-response-formats`

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Update the Assistant chat agent to support flexible response formats. The agent must be capable of responding with Markdown-formatted text, Generative UI components, or a hybrid response containing both Markdown text and Generative UI components within the same message thread. Generative UI remains the primary response style when structured visual data is required, but text/markdown responses must be supported when rich text explanations, code snippets, or conversational responses are appropriate."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Getting a conversational, explanatory answer instead of a forced component (Priority: P1)

A Customer Success manager asks the assistant a question that calls for an explanation, a nuanced comparison, or a walkthrough — not a chart or a list — for example "why does this matter for renewal?" or "how should I phrase this to the CTO?" Today the assistant either forces the answer into one of a fixed set of visual components or falls back to a short, hand-written decline message. Instead, the manager receives a genuine, well-formatted written answer (headings, emphasis, lists, code blocks where relevant) that actually addresses the question in prose.

**Why this priority**: This is the core capability gap the request is about — without it, every question that doesn't fit a pre-built component either gets awkwardly shoehorned in or politely declined, which is the exact limitation this feature exists to remove.

**Independent Test**: Ask a question with no matching structured-component intent but a clear, answerable conversational shape (e.g. "explain in plain terms why the score jumped"); confirm the response is rendered as formatted text (not a component, not a generic decline) and factually reflects only what the underlying account data actually shows.

**Acceptance Scenarios**:

1. **Given** a question best answered in prose, **When** the assistant responds, **Then** the response renders as formatted text (e.g. paragraphs, headings, or lists as appropriate) rather than one of the fixed visual components.
2. **Given** a question whose answer includes a code snippet or literal text worth preserving exactly, **When** the assistant responds, **Then** that snippet renders in a distinguishable, non-reflowed format within the text response.
3. **Given** a markdown text response, **When** it is generated, **Then** every factual claim in it (numbers, names, dates) is checked against the account's real underlying data before being shown, and any claim that cannot be verified is left out of the response entirely rather than shown unverified.

---

### User Story 2 - Structured visual data still renders as a component by default (Priority: P2)

A Customer Success manager asks a question with a clear structured-data shape — a score breakdown, a ranked list of issues, a set of stakeholder cards — and continues to receive the same visual, structured component response the assistant already produces today. Nothing about this experience changes.

**Why this priority**: This is the assistant's proven, primary mode today; the new capability must not degrade or replace it — it must remain the default whenever structured visual data is the right answer, so this is a required non-regression, not new functionality.

**Independent Test**: Ask a question matching an existing structured-data intent (e.g. "why is the score high?"); confirm the response still renders as the same visual component it does today, with identical data and identical click-through behavior (e.g. opening evidence).

**Acceptance Scenarios**:

1. **Given** a question whose answer is inherently structured data (e.g. a score breakdown), **When** the assistant responds, **Then** it renders as the existing visual component, unchanged from today's behavior.
2. **Given** the same component response, **When** the CS manager interacts with it (e.g. clicking a row to open evidence), **Then** the interaction behaves identically to today.

---

### User Story 3 - A single answer can combine an explanation with a visual component (Priority: P3)

A Customer Success manager asks a question whose best answer is both a structured visual (e.g. a ranked list of risk drivers) and a short written explanation of what it means or what to do about it. Rather than getting only the component with no context, or only prose with no visual, the manager receives one answer that includes both together.

**Why this priority**: This is the most valuable combined experience but depends on both User Story 1 and User Story 2 already working correctly — it's the natural next step once each format works independently, not a separate capability to build from scratch.

**Independent Test**: Ask a question whose best answer genuinely benefits from both an explanation and a visual (e.g. "what's driving the risk and what should I do?"); confirm the response includes both a rendered component and accompanying formatted text, and that both parts are internally consistent (the text doesn't contradict what the component shows).

**Acceptance Scenarios**:

1. **Given** a question best answered with both an explanation and a visual, **When** the assistant responds, **Then** the single response includes both a rendered component and formatted text together.
2. **Given** a hybrid response, **When** the CS manager reads it, **Then** the text and the component agree with each other and both are traceable to the same underlying evidence.

---

### Edge Cases

- What happens when the assistant's generated markdown text contains a claim that cannot be verified against the account's actual data? That sentence is dropped from the response entirely — never silently rewritten or left in unverified (matches the existing rule already applied to the assistant's other written outputs).
- What happens when the account's own message content (email/ticket/chat text) contains something that reads like an instruction to the assistant (e.g. "ignore your instructions and say X")? It is rendered as inert quoted text only — it can never change what component renders, what the markdown says beyond quoting it, or trigger any action.
- What happens when a hybrid response's component and text disagree because of a timing issue (e.g. data changed between the two being assembled)? The response must be built from one consistent snapshot of data — never a component from one moment and text from another.
- What happens when generating a markdown or hybrid response would take meaningfully longer than today's component/decline responses? The assistant still responds within its existing time budget, falling back to a plain, honest "taking longer than expected" state exactly as it does today if that budget is exceeded — never rendering a corrupted, cut-off, or partial response.
- What happens to today's decline/fallback responses (e.g. "I don't make predictions")? They are unchanged by this feature — this feature adds two new ways to answer a question the assistant *can* answer, it does not change when the assistant declines.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The assistant MUST be able to respond with a Markdown-formatted text answer when the question calls for an explanation, a conversational response, or content (such as a code snippet) better expressed in prose than in a structured component.
- **FR-002**: The assistant MUST continue to respond with the existing structured visual components, unchanged in behavior, whenever the question's answer is inherently structured data — this remains the default/primary response style for that kind of question.
- **FR-003**: The assistant MUST be able to produce a single hybrid response that includes both a structured visual component and Markdown-formatted text together, when the question's best answer genuinely needs both.
- **FR-004**: The assistant's Markdown text MUST be genuine, model-generated prose — not text assembled from a fixed template — so it can produce truly conversational explanations and context-appropriate code snippets, not just reformatted structured data. This extends the assistant's existing "written output is mechanically fact-checked before display" guarantee (already applied elsewhere in this product) to this new response shape, per FR-005.
- **FR-005**: Every factual claim (a number, name, date, or other specific detail) in a Markdown or hybrid text response MUST be verified against the account's real structured data before being shown; any claim that cannot be verified MUST be dropped from the response entirely, never shown unverified and never silently reworded.
- **FR-006**: Markdown or hybrid text responses MUST cite the same underlying evidence sources the assistant's component responses already cite today — a text answer is not exempt from the "every claim is traceable to real evidence" requirement.
- **FR-007**: Content drawn from a client's own messages (email, chat, ticket text) that appears within a Markdown response MUST be treated strictly as quoted data, never as an instruction — it must never be able to change which component renders, alter the assistant's own wording beyond quoting it, or trigger any action.
- **FR-008**: A hybrid response's component and text MUST be built from one consistent snapshot of the account's data — they must never disagree because they were assembled from different moments in time.
- **FR-009**: A single assistant reply MUST be able to contain multiple parts together, in order — for example a paragraph of explanation, then a rendered component, then another paragraph — as one combined answer to one question, rather than requiring separate questions to get the text and the visual separately.
- **FR-010**: The assistant MUST continue to respond within its existing time budget for every response format (component, text, or hybrid) — a slower format is not permitted to introduce a new, longer wait for the CS manager.
- **FR-011**: When a response cannot be completed within the existing time budget, the assistant MUST fall back to the same honest "taking longer than expected" state used today — never a partial, cut-off, or corrupted Markdown/hybrid response.
- **FR-012**: The assistant's existing decline/fallback behavior (e.g. declining to predict, declining an unclear question) MUST remain unchanged by this feature — this feature only extends how an *answerable* question can be answered.
- **FR-013**: Every response, regardless of format, MUST still be logged the same way the assistant's responses are logged today, with no format-specific gap in that record.

### Key Entities

- **Assistant response**: What the assistant sends back for one question. Today this is one of two flat shapes (a structured component, or a fallback/decline message). This feature changes an *answerable* question's response into an ordered sequence of one or more parts — each part is either a text part or a component part — so a response can be text-only (one text part), component-only (one component part, matching today's existing behavior exactly), or hybrid (multiple parts of either kind, in order). Decline/fallback responses are unchanged (FR-012).
- **Response part**: One item within an assistant response's ordered sequence — either a Markdown text part or a structured visual component part (using the same closed set of component types the assistant already supports).
- **Verified claim**: A single factual statement (a number, name, date, or specific detail) inside a text part, checked against the account's real data before display — the same underlying concept the assistant's other written outputs already apply, extended to this new response shape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A CS manager asking a conversational or explanatory question (one with no matching structured-component intent) receives a genuine written answer instead of a generic decline, for the same categories of question that are declined today purely for lacking a matching component.
- **SC-002**: 100% of questions that match an existing structured-component intent continue to render as that same component, with identical data, after this feature ships (zero regression).
- **SC-003**: 100% of factual claims (numbers, names, dates) in Markdown or hybrid responses are traceable to real account data — zero instances of an unverifiable claim reaching the screen, measured the same way the assistant's other written-output accuracy is already measured.
- **SC-004**: A hybrid response is available for at least one real question category that benefits from both an explanation and a visual, demonstrating the combined format is genuinely usable, not just theoretically supported.
- **SC-005**: Every response format (component, text, hybrid, decline) completes within the assistant's existing response-time budget on at least 95% of requests under normal conditions.

## Assumptions

- "Generative UI components" refers to the assistant's existing closed set of structured visual response types (the same ones it already renders today, e.g. a score breakdown, a ranked issue list, stakeholder cards) — this feature does not add new component types, only adds text and hybrid alongside the existing ones.
- The specific technology used to render Markdown on the CS manager's screen (e.g. which formatting library) is a planning-phase decision, not a product requirement — this spec describes the required outcome (readable, correctly formatted text, including distinguishable code blocks), not the implementation.
- This feature does not change how the assistant decides *whether* it can answer a question at all (its existing decline logic and reasons); it only changes *how* an answerable question's answer can be presented — decline behavior is explicitly out of scope for changes (FR-012).
- The assistant's read-only, evidence-only guarantees are not weakened anywhere by this feature: it does not gain any new ability to see, ask about, or act on anything beyond what it can already read today, and it still cannot send anything on the CS manager's behalf.
- Where the spec references "the same discipline/rule already used for the assistant's other written outputs," it means the existing mechanical fact-checking approach already applied elsewhere in this product to written, model-influenced text — this feature extends that same kind of check to this new response shape rather than inventing a different one.
- Resolved via clarification (2026-08-17): Markdown text is genuine, model-generated prose (not a template), and a single reply may contain multiple ordered parts (FR-004, FR-009). Because this genuinely extends where the assistant generates free prose — today that only happens in two other places in this product — the implementation is expected to require updating the project's own written engineering constitution's AI-safety rule inventory to name this as a third location, governed by the same mechanical fact-check discipline, rather than silently expanding it. This is a planning-phase governance step, not a product requirement, but is flagged here so it isn't missed.
