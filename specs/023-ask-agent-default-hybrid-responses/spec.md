# Feature Specification: Ask Agent Default Hybrid Responses

**Feature Branch**: `023-ask-agent-default-hybrid-responses`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "The assistant currently responds to a question either with a generative-ui visual component or with text, but not both. Change this so that whenever the assistant shows a generative-ui component, it also includes a short, plain-language, executive-style text explanation of what the component is showing (or additional useful context) alongside it — a mixed response. This accompanying text must stay short and executive, never long or verbose, so the combined response remains fast and easy for a busy Customer Success manager to read."

## Clarifications

### Session 2026-08-21

- Q: SC-002 says the accompanying text must be "short enough to read in a few seconds," but that isn't a testable number. What should define "short" so it can be verified objectively? → A: Hard cap: at most 3 sentences (or an equivalently short bullet list) — a clean, testable ceiling.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Getting the visual and a plain-language explanation together (Priority: P1)

A Customer Success manager asks a question whose answer is a structured
visual — for example a score breakdown, a ranked list of risk drivers, or a
set of stakeholder cards. Today the manager sometimes gets just the visual
with no context, or (occasionally, when the question happens to be phrased
a certain way) just written text with no visual. Instead, the manager now
consistently receives both together in one reply: the visual, plus a short,
plain-language blurb that explains what it's showing or adds one useful
piece of context — without having to phrase the question specially to get
both.

**Why this priority**: This is the entire premise of the request — every
other scenario exists to make sure this new default behavior doesn't break
anything that already works.

**Independent Test**: Ask a question that matches an existing structured
visual (e.g. "why is the score high?"); confirm the reply contains both the
same visual shown today and a short accompanying explanation, and that the
explanation stays within the 3-sentence cap (not a long write-up).

**Acceptance Scenarios**:

1. **Given** a question whose answer is a structured visual, **When** the
   assistant responds, **Then** the reply includes both the visual and a
   short accompanying text explanation, in the same message.
2. **Given** the accompanying text, **When** the manager reads it, **Then**
   it explains what the visual is showing or adds a useful insight, in
   plain executive language, rather than mechanically restating every data
   point already visible in the visual itself.
3. **Given** the same visual response, **When** the CS manager interacts
   with it (e.g. clicking a row to open evidence), **Then** the interaction
   behaves identically to today — this feature changes what accompanies the
   visual, not the visual itself.

---

### User Story 2 - Purely conversational questions still get a text-only answer (Priority: P2)

A Customer Success manager asks a question that is clearly conversational
or explanatory in nature — one where no visual would make sense — for
example "why does this matter for renewal?" The assistant continues to
answer with a written explanation alone, exactly as it does today; this
feature does not force a visual onto a question that doesn't call for one.

**Why this priority**: This is a required non-regression — the new default
must not turn every answer into a forced visual-plus-text pairing when a
visual genuinely doesn't apply.

**Independent Test**: Ask a clearly conversational, explanation-seeking
question with no natural visual; confirm the response remains text-only,
unchanged from today's behavior.

**Acceptance Scenarios**:

1. **Given** a question that is conversational or explanatory in phrasing
   with no natural matching visual, **When** the assistant responds,
   **Then** it replies with text only, exactly as it does today.

---

### User Story 3 - Drafting a message to a stakeholder stays unaffected (Priority: P3)

A Customer Success manager asks the assistant to draft a message to a
stakeholder. The assistant returns the drafted message, exactly as it does
today — it does not add a separate generic explanatory blurb on top of the
draft, since the draft itself is already the answer.

**Why this priority**: A drafted message is already written prose; layering
a generic "here's what this is showing" explanation on top of it would add
noise rather than value, so this scenario protects against an unwanted side
effect of the new default.

**Independent Test**: Ask the assistant to draft a message to a specific
stakeholder; confirm the reply is the drafted message only, with no
additional explanatory text appended.

**Acceptance Scenarios**:

1. **Given** a request to draft a message to a stakeholder, **When** the
   assistant responds, **Then** the reply contains only the drafted
   message, unchanged from today's behavior.

---

### Edge Cases

- What happens when the accompanying text cannot be produced in time, or
  fails the assistant's existing fact-verification check? The visual is
  still shown on its own — the reply is never delayed, blocked, or shown
  incomplete while waiting on the text.
- What happens when the underlying data is simple enough that there's
  nothing meaningful to add (e.g. a single, self-explanatory number)? The
  accompanying text should surface the single most useful piece of added
  context rather than mechanically repeating the number already visible in
  the visual.
- What happens to the assistant's existing decline/fallback behavior (e.g.
  declining to predict, declining an unclear question)? It is unchanged —
  this feature only changes how an already-answerable, visual-shaped
  question is presented.
- What happens when a question's phrasing is ambiguous between "wants a
  visual" and "wants pure conversation"? The assistant's existing judgment
  of the question's phrasing continues to decide that — this feature does
  not change how that initial judgment is made.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Whenever the assistant's response to a question includes a
  generative-ui visual component, the response MUST also include a short
  accompanying text explanation in that same reply.
- **FR-002**: The accompanying text MUST be short — at most 3 sentences (or
  an equivalently short bullet list) — never a long or verbose write-up.
- **FR-003**: The accompanying text MUST explain, in plain executive
  language, what the visual is showing and why it matters, or surface one
  additional useful insight — not mechanically restate each data point
  already visible in the visual.
- **FR-004**: The assistant MUST continue to support a text-only response,
  with no visual, for questions whose phrasing is conversational or
  explanatory in a way no visual would suit — unchanged from today.
- **FR-005**: A request to draft a message to a stakeholder MUST continue
  to return only the drafted message, with no additional generic
  explanatory text appended.
- **FR-006**: Every factual claim (a number, name, date, or specific
  detail) in the accompanying text MUST continue to be verified against the
  account's real underlying data before being shown; any claim that cannot
  be verified MUST be dropped entirely, never shown unverified.
- **FR-007**: If the accompanying text cannot be produced in time or fails
  verification, the assistant MUST still return the visual on its own
  rather than delay, block, or fail the reply.
- **FR-008**: The assistant's existing decline/fallback behavior for
  questions it cannot answer at all MUST remain unchanged by this feature.
- **FR-009**: Every response, regardless of format, MUST continue to be
  logged with the same completeness as today, with no gap introduced by
  this change.
- **FR-010**: The assistant MUST continue to respond within its existing
  response-time budget for every format — the addition of accompanying
  text must not introduce a new, longer wait for the CS manager.

### Key Entities

- **Assistant response**: What the assistant sends back for one question.
  For a question whose answer is a structured visual, the response now
  consists of that visual plus a short accompanying text explanation
  together, by default, rather than the visual alone or text alone as
  separate, mutually exclusive outcomes.
- **Accompanying text**: The short, plain-language explanation attached to
  a visual — grounded in and verified against the same underlying data the
  visual itself displays, so the two can never disagree.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of responses that successfully render a generative-ui
  visual also include a short accompanying text explanation, except when
  text generation itself fails — in which case the documented visual-only
  fallback applies.
- **SC-002**: The accompanying text stays within a hard cap of 3 sentences
  (or an equivalently short bullet list) per response, measured directly on
  the generated text, across the full range of structured-data questions —
  never a long write-up.
- **SC-003**: 100% of requests to draft a message to a stakeholder continue
  to return only the drafted message, with zero regression from today's
  behavior.
- **SC-004**: 100% of purely conversational, non-visual-shaped questions
  continue to receive a text-only answer, with zero regression from today's
  phrasing-sensitivity.
- **SC-005**: Every response format completes within the assistant's
  existing response-time budget on at least 95% of requests under normal
  conditions, matching today's standard.

## Assumptions

- This feature is a refinement of the assistant's existing ability to
  combine a visual and written text in one reply, and to verify written
  claims against real data before showing them — both of those underlying
  capabilities already exist. This feature changes the *default rule* for
  when the combination is used (from occasional to standard) and the
  *framing* of the accompanying text (explaining the visual, not
  re-answering the question from scratch), not the mechanisms themselves.
- "A question whose answer is a structured visual" refers to the same
  closed set of question categories that already resolve to a visual today
  (e.g. a score breakdown, risk drivers, stakeholder status, commitments, a
  timeline, an action list) — this feature does not add any new visual
  types.
- Deciding whether a question's phrasing is conversational (text-only,
  User Story 2) versus structured (visual, User Story 1) continues to rely
  on the assistant's existing judgment of the question itself — this
  feature does not change how that initial judgment is made, only what
  happens once a visual is warranted.
- No new data sources or evidence are required — the accompanying text is
  grounded only in the same underlying account data already used to
  produce the visual it explains.
