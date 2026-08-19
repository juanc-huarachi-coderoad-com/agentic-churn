# Feature Specification: Assistant Chat Conversation

**Feature Branch**: `017-assistant-chat-conversation`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Improve and solve the following problem on assistant chatbot. Review of the assistant chatbot found the following problems — this component should behave like a chatbot, with agent/user interaction, mixing text and generative-UI. Problems: (1) sending 'hi' returns a generic fallback ('I don't have a way to answer that yet...') instead of a real reply; (2) the text typed into the input stays in the input box instead of clearing and moving into the conversation; (3) question history disappears — only one question can be asked at a time; (4) the chat should maintain memory across the conversation; (5) responses should mix text and generative-UI."

## Clarifications

### Session 2026-08-18

- Q: Should the assistant's conversation history survive navigating away and back (or a page reload), or is it fine for it to reset once the user leaves the current account/dashboard view? → A: Session only — resets on page reload or leaving the account view; no cross-session persistence.
- Q: Since questions are asked about "this account," should each account have its own separate conversation, or is one global conversation shared across whichever account is currently open? → A: One conversation per account — switching accounts preserves each account's own history within the session.
- Q: How many prior turns of the conversation should the assistant use as context when answering a follow-up question? → A: Last 5 exchanges.
- Q: Should greeting/small-talk replies (e.g. "hi", "thanks") be generated dynamically by the model each time, or come from a small set of fixed, pre-written responses? → A: Fixed, pre-written replies, selected by matching the message against known greeting/small-talk patterns.
- Q: While the assistant is still answering the current question, should the user be able to send the next question right away, or must they wait for the current answer to finish before sending? → A: Block sending until ready — typing stays enabled, but the send action is disabled until the current answer finishes, then unlocks immediately.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask multiple questions in one running conversation (Priority: P1)

A user working the dashboard asks the assistant a question, reads the answer, then asks a follow-up question without losing the first exchange. Every question and its answer stay visible as a running transcript, in the order they happened, for as long as the user is working that account.

**Why this priority**: This is the core defect reported — today only the latest question/answer pair is shown and everything before it vanishes, so the component behaves like a single-shot form instead of a chat. Without this, none of the other fixes (memory, mixed content) matter, because there is no conversation to hold them.

**Independent Test**: Open the assistant, ask a question, wait for the answer, then ask a second, different question. Both the first and second question/answer pairs are visible in the transcript at the same time, with the second appended below the first.

**Acceptance Scenarios**:

1. **Given** the assistant panel is empty, **When** the user asks a first question and receives an answer, **Then** that question and its answer appear in the transcript.
2. **Given** one question/answer pair is already in the transcript, **When** the user asks a second question, **Then** the first pair remains visible and the new question/answer pair is appended below it.
3. **Given** several question/answer pairs are in the transcript, **When** the user scrolls the transcript, **Then** all prior exchanges remain readable (nothing is discarded to make room for new ones) and the view keeps the newest exchange in reach.
4. **Given** the assistant is currently generating an answer to a question, **When** the user views the transcript, **Then** the pending question is already visible with a clear "thinking" indicator, not just a blank state.

---

### User Story 2 - Typed message moves into the conversation immediately (Priority: P1)

A user types a question and sends it. The instant they send it, the input box is empty and ready for the next message, and the question they just typed appears in the transcript as their own turn.

**Why this priority**: Reported directly by the user as broken — the typed text currently stays stuck in the input box, which makes the component look unresponsive and makes it unclear whether the message was actually sent. This is a trust-breaking defect independent of everything else.

**Independent Test**: Type a question into the input, submit it, and confirm the input is empty immediately and the typed text now appears as the user's turn at the bottom of the transcript, before the answer arrives.

**Acceptance Scenarios**:

1. **Given** the user has typed a question into the input, **When** they submit it, **Then** the input box is cleared immediately and the submitted text appears as a new user turn in the transcript.
2. **Given** the input was just cleared after sending, **When** the user starts typing a new message while the previous answer is still being generated, **Then** the input accepts the new text and is not overwritten, but the send action stays disabled until the current answer finishes, at which point it immediately becomes available.
3. **Given** the user submits an empty or whitespace-only message, **When** they press send, **Then** no empty turn is added to the transcript and the input is not cleared.

---

### User Story 3 - Assistant understands greetings and casual messages (Priority: P2)

A user opens the assistant and says "hi" (or "thanks", "what can you help with", etc.). Instead of the generic fallback ("I don't have a way to answer that yet"), the assistant recognizes the message as a greeting or small talk and responds with one of a small set of pre-written, friendly replies that also point toward what it can actually help with.

**Why this priority**: Reported directly by the user as broken and it is the first thing a new user tries, so it sets the tone for whether the assistant feels trustworthy. It's ranked below the two structural transcript/input fixes because a greeting reply is only valuable once there is a real conversation to greet into.

**Independent Test**: Send "hi" as the first message and confirm the reply is a conversational greeting (not the generic fallback string), optionally suggesting example questions the assistant can answer.

**Acceptance Scenarios**:

1. **Given** a new conversation, **When** the user sends a greeting or small-talk message ("hi", "hello", "thanks"), **Then** the assistant responds with one of its pre-written conversational replies instead of returning the generic decline/fallback message.
2. **Given** the user asks something genuinely outside the assistant's supported topics (e.g., asking it to predict the future, or about a data source that isn't connected), **When** the assistant cannot answer, **Then** it still returns the existing, specific decline message for that reason (this fallback behavior for genuinely out-of-scope questions is unchanged — only greetings/small talk are affected).

---

### User Story 4 - Assistant remembers earlier turns in the same conversation (Priority: P2)

A user asks a question, gets an answer, then asks a follow-up that refers back to it ("what about last quarter?", "who else on that list?") without repeating the full context. The assistant understands the follow-up using the prior turns of the same conversation.

**Why this priority**: Explicitly requested by the user ("the chat should handle memory in the conversation"). It depends on User Story 1 (a visible transcript) existing first, and is what turns the feature from "a list of independent Q&A" into "a conversation."

**Independent Test**: Ask a question that establishes a subject (e.g., a specific account or metric), then ask a short follow-up question that only makes sense in light of the first ("what caused that?"). Confirm the assistant's answer correctly reflects the earlier context rather than treating the follow-up as a standalone, ambiguous question.

**Acceptance Scenarios**:

1. **Given** the user has already asked a question in the current conversation, **When** they ask a follow-up question that depends on that context, **Then** the assistant's answer reflects the earlier turn (e.g., resolves pronouns/references like "that", "it", "them" against the prior exchange).
2. **Given** an ongoing conversation, **When** the user asks a new, self-contained question unrelated to prior turns, **Then** the assistant answers it correctly without being confused by unrelated earlier context.
3. **Given** the user navigates away from the account/dashboard view or reloads the page, **When** they return, **Then** the prior conversation is not restored — the assistant starts a fresh conversation for that account (conversation memory lasts only for the current, continuous working session).

---

### User Story 5 - Answers mix plain text and rich, generative visual content (Priority: P3)

When the assistant's answer includes structured data (numbers, breakdowns, lists of people, timelines, suggested actions), it renders that data as a purpose-built visual element inside the chat turn, alongside its written explanation — not just as a wall of text.

**Why this priority**: Requested by the user and already partially working for the single most-recent answer today; this story is about making sure every turn in the now-persistent, multi-turn transcript (Story 1) keeps that same mixed text + visual treatment, not just the latest one. Ranked last because it's a consistency/quality improvement on top of a mechanism that already exists, rather than a missing capability.

**Independent Test**: Ask a question whose answer includes structured data (e.g., "why did the score drop"), confirm the turn shows both a written explanation and a corresponding visual element (chart/breakdown/list), then ask a second question of a different kind and confirm its turn also renders correctly with its own text + visual content, without disturbing the first turn's rendering.

**Acceptance Scenarios**:

1. **Given** the assistant answers a question that has structured supporting data, **When** the answer is rendered in the transcript, **Then** the turn shows both a short written explanation and a matching visual element for the data (e.g., a breakdown, comparison, list, or checklist), in the order the assistant intended.
2. **Given** multiple past turns already exist in the transcript, **When** a new turn with mixed text + visual content is added, **Then** previously rendered turns (including their visual elements) remain intact and interactive (e.g., any links/buttons within them still work).
3. **Given** an answer is plain conversational text with no structured data behind it (e.g., a greeting), **When** it is rendered, **Then** it appears as a plain text turn without a forced or empty visual element.

---

### Edge Cases

- What happens if the assistant fails to respond (error/timeout) to a question in the middle of an otherwise healthy conversation? The failed turn should show an error state in place, without erasing the turns before it, and the user must be able to continue the conversation afterward.
- What happens if the user tries to send another question while the current one is still being answered? Sending is blocked (though typing is not) until the current answer completes, so answers can never arrive out of order or overwrite each other; the send action re-enables the instant the current turn finishes.
- What happens when the transcript grows very long over a long working session? The transcript must remain scrollable and usable; older turns are not silently deleted during an active session.
- What happens if the user switches to a different account/customer while a conversation is in progress? Each account has its own separate conversation: switching away from an account leaves its conversation intact (not discarded), and switching back to it during the same working session resumes that account's own history rather than continuing the conversation of whichever account was viewed in between.
- What happens if the assistant's memory of the conversation would include a turn that was answered with a decline/fallback message? Follow-up questions should still work normally and not get stuck repeating the same decline.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The assistant MUST display a running transcript of the conversation, showing every question the user has asked and every corresponding answer, in chronological order, within the current conversation.
- **FR-002**: The assistant MUST append each new question/answer pair to the existing transcript rather than replacing the previously displayed pair.
- **FR-003**: The assistant MUST clear the input field immediately upon the user sending a message, and MUST display the sent message as the user's turn in the transcript.
- **FR-004**: The assistant MUST support asking more than one question within the same conversation, with no artificial limit of "one question only."
- **FR-005**: The assistant MUST show a distinct "thinking"/in-progress indicator for a question that has been sent but not yet answered, without hiding or removing previously answered turns.
- **FR-006**: The assistant MUST NOT allow submission of an empty or whitespace-only message, and MUST leave the input and transcript unchanged when that is attempted.
- **FR-007**: The assistant MUST recognize conversational messages (greetings, thanks, small talk, and general "what can you do" questions) and respond with one of a small set of fixed, pre-written conversational replies instead of the generic decline/fallback message.
- **FR-008**: The assistant MUST continue to return its existing specific decline message (with its stated reason) for questions that are genuinely outside its supported scope (predictions, unconnected data sources, colleague judgment calls, etc.) — this decline behavior is preserved, only the "no intent recognized at all" fallback path changes for greetings/small talk.
- **FR-009**: The assistant MUST use up to the 5 most recent prior turns of the current conversation as context when interpreting a new question, so that follow-up questions referring back to those turns (via pronouns or implied subjects) are answered correctly.
- **FR-010**: The assistant MUST correctly answer a new, self-contained question even when unrelated prior turns exist in the conversation (earlier context must not cause incorrect answers to unrelated questions).
- **FR-011**: Each answer in the transcript MUST be able to render as a combination of written text and one or more purpose-built visual elements (e.g., breakdowns, comparisons, lists, checklists), matching the ordering the assistant produced, consistent with the existing mixed text/visual answer format.
- **FR-012**: A purely conversational answer (e.g., a greeting reply) MUST render as plain text, without being forced through a visual/component element it doesn't need.
- **FR-013**: If a question in the conversation fails to get an answer (error/timeout), the assistant MUST show an error state for that specific turn while preserving all prior turns, and MUST allow the user to continue asking further questions afterward.
- **FR-014**: The assistant MUST disable the send action while a question is being answered — typing remains possible, but a new question cannot be sent until the current answer finishes, ensuring each question is always paired with its own matching answer in the order asked.
- **FR-015**: The transcript MUST remain scrollable and MUST NOT silently delete earlier turns during an active session, regardless of how long the conversation grows.
- **FR-016**: The assistant MUST maintain a separate conversation per account: switching to a different account MUST NOT discard or blend the conversation of the account being left, and returning to a previously viewed account during the same working session MUST resume that account's own transcript and memory.
- **FR-017**: Conversation history and memory are scoped to the current working session only — reloading the page or ending the session MUST start a fresh conversation (no requirement to restore prior transcripts after a reload or new session).

### Key Entities

- **Conversation**: The ongoing exchange between the user and the assistant for the current working context (e.g., the account/dashboard currently in view). Holds an ordered sequence of turns and is the unit that carries "memory" between questions.
- **Turn**: A single question/answer exchange within a conversation. Composed of the user's message, an in-progress/answered/error status, and — once answered — an ordered sequence of content pieces (text and/or visual elements) that make up the assistant's reply.
- **Content Piece**: A single unit of an answer — either a block of written text or a specific visual element carrying structured data (e.g., a breakdown, comparison, list, or checklist) — combined in order to form one turn's full answer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can ask at least 10 consecutive questions in one sitting and see all 10 question/answer pairs simultaneously visible (via scrolling) in the transcript, with zero pairs lost or overwritten.
- **SC-002**: 100% of sent messages result in an immediately empty input field and an immediately visible user turn in the transcript (no delay, no leftover text).
- **SC-003**: Common greeting/small-talk messages ("hi", "hello", "thanks", "what can you ask me") no longer produce the generic fallback response — they receive a relevant conversational reply instead, in effectively all cases tested.
- **SC-004**: In a follow-up question that depends on any of the 5 most recent turns, the assistant's answer correctly reflects that prior context in at least 9 out of 10 test conversations covering common follow-up phrasing.
- **SC-005**: Answers containing structured data render with both an explanatory text portion and a matching visual element in the same turn, for every turn in a multi-turn conversation — not only the most recent one.
- **SC-006**: Zero question/answer pairs are lost, overwritten, or answered out of order across every tested conversation, including attempts to send a new question before the current one finishes.

## Assumptions

- The assistant's ability to produce mixed text + generative-UI content per answer already exists at the single-answer level (structured intents already return an ordered sequence of text and component pieces); the gap being closed here is making sure this rendering persists correctly across a growing multi-turn transcript, not building the mixed-content mechanism from nothing.
- "Memory" means the assistant uses prior turns of the same conversation as conversational context when interpreting new questions (e.g., resolving "that", "it", implied subjects) — not that it permanently learns or retrains from past conversations across sessions.
- Conversation history needs to persist only for the duration of the user's active working session in the current browser context; it resets on page reload and does not need to be available on a different device or after the session ends. Confirmed with the user.
- Each account maintains its own separate conversation for the duration of the session; switching between accounts preserves each one's own history rather than sharing one global conversation. Confirmed with the user.
- The existing specific decline/fallback behavior for genuinely out-of-scope questions (predictions, unconnected sources, judgment calls, unclear questions) is intentional and correct — this feature only changes what happens for greetings/small talk that currently gets mistaken for an out-of-scope question.
- The 5 most recent turns are enough conversation context to resolve follow-up questions; the assistant is not expected to reference turns older than that in a very long-running conversation. Confirmed with the user.
- Greeting/small-talk replies come from a small, fixed set of pre-written responses rather than being freshly generated per message; this is simpler, instant, and avoids adding a new place where the assistant generates free text. Confirmed with the user.
- Sending is single-flight per conversation: only one question can be in progress at a time, and the send action is disabled (not hidden) until the current answer completes. Confirmed with the user.
