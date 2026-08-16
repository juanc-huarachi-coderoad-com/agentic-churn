# Feature Specification: Narrator and Ask Agent

**Feature Branch**: `008-narrator-and-ask-agent`

**Created**: 2026-08-15

**Status**: Draft

## Clarifications

### Session 2026-08-15

- Q: `AskComponentResponse` (`architecture/07-api-spec.md`) only defines 7
  `component` enum values, matching the 7 lookup-and-render intents.
  REQ-M9-02's 8th mapping, "write to X about this," hands off to the draft
  composer (feature 009), which doesn't exist yet — the response schema has no
  representation for this case today. Should this feature (A) classify the
  intent normally and return a distinct handoff response carrying the target
  issue/stakeholder context, ready for feature 009 to wire in later, or (B)
  route it into the "no known intent" fallback until feature 009 ships? → A:
  classify normally and return a distinct handoff response — matches
  `decisions/03-langgraph-for-ask-agent.md`'s own flow diagram, which already
  draws "Handoff" as a terminal node parallel to Decline/Fallback/Render, so
  this makes an already-decided branch representable in the response contract
  rather than deferring it.
- Q: The "is this normal for X?" intent (REQ-M9-02) reuses the Tone reader's
  per-stakeholder baseline (feature 007), which honestly abstains — "no
  history, no opinion" — for anyone with fewer than 5 prior messages. That's a
  different failure mode from REQ-M9-07's "data source isn't connected." What
  should the Ask agent say when asked about a stakeholder with insufficient
  baseline history? → A new, distinct `declined_reason`:
  `insufficient_history` — honest about *why* it can't answer, matching the
  Tone reader's own "no history, no opinion" abstention rather than
  conflating it with a disconnected source.

**Input**: User description: "Narrator and ask agent — build-order Phase 8
(`specs/ROADMAP.md`): the explanation layer. Fills in `requirements/
07-narrator.md` (M7 — turns the scoring engine's already-ranked findings into a
headline, reasons with point contributions and evidence, and a playbook-derived
action list, all mechanically fact-checked before display) and `requirements/
09-ask-agent.md` (M9 — the question box that classifies each question into a
closed set of intents and renders the matching UI component by looking up
already-computed data, never recalculating the score). The Ask agent's
multi-step classify → tool → render orchestration follows the already-ratified
`decisions/03-langgraph-for-ask-agent.md`, decided ahead of this feature so this
spec doesn't re-decide it. Feature 006 (`dashboard-evidence-trace`) explicitly
built the rest of the dashboard around this gap: its own spec drew a boundary
excluding 'the Ask bar' (REQ-M8-02) and 'narrator headline/reasons/actions text'
(REQ-M8-01) because neither module existed yet, leaving `narrator_outputs`
permanently empty and the Ask bar entirely unrendered. This feature closes both
gaps: it's the first time a CS lead sees a plain-language explanation of their
own score, and the first time the question box actually answers anything."

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement
cites the `REQ-<ID>` that is its source of truth (`requirements/07-narrator.md`,
`requirements/09-ask-agent.md`).

**In scope**: the Narrator (headline, reasons, playbook-derived actions,
mechanical fact-check), the Ask agent (intent classification, the seven
lookup-and-render intents plus the draft-composer handoff, the decline and
fallback paths), and the two dashboard surfaces feature 006 explicitly left
unbuilt because they were blocked on this feature — the narrator's
headline/reasons/actions text and the always-present Ask bar
(`Idle`/`Thinking`/`Answered`).

**Explicitly out of scope, with a reason each**:

- **The draft composer itself (M10).** The "write to X about this" intent
  (REQ-M9-02) hands off to it; this feature builds the hand-off trigger only,
  not the draft's generation, tone variants, or pre-display checks
  (`requirements/10-draft-composer.md`, feature 009).
- **Feedback controls' effect on scoring (damping).** The evidence trace panel
  stayed read-only through feature 006 on purpose; `damping_weights`
  (`requirements/04-feedback-memory.md`) is feature 010's territory. Nothing
  in this feature reads or writes feedback verdicts.
- **Multi-turn "Ask thread" conversational memory.** The named Ask thread
  screen (`base/...md` §11.2) and `decisions/03-langgraph-for-ask-agent.md`'s
  own design both flag checkpointing as built-for but **off** in the MVP — no
  `REQ-M9` requirement describes cross-question memory today. Each question is
  answered statelessly; the Ask bar's expanded view is this feature's single
  question-and-answer exchange, not a persisted history.
- **The `notifications` table** (`data-base/08-schema-experience.md`,
  band-change/daily-digest alerts). Sitting alongside `narrator_outputs` and
  `ask_queries` in the same schema file invites the assumption that this
  feature populates it, but no `REQ-M7` or `REQ-M9` requirement governs it —
  it remains unassigned to any feature in `specs/ROADMAP.md`, a genuine gap
  worth flagging, not one this feature is positioned to close.
- **Playbook authoring.** `playbook_actions` (`data-base/
  08-schema-experience.md`) is pre-seeded, human-authored data — 3–5 actions
  signed off by the CS lead (`decisions/00-open-questions-resolved.md` Q7).
  This feature reads and personalizes those rows; it does not build an
  authoring or sign-off UI for them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A score's explanation reads like a person wrote it, and every fact in it is checked (Priority: P1)

A CS lead opens the dashboard and, for the first time, sees more than a number:
a headline ("We took 19 hours to reply to a P1 ticket — we promised 4 — and Ana
is pulling back at the same time"), a short list of reasons each carrying its
point value and a link back to the evidence, and a small set of actions each
with a named owner and a date. Nothing in that text was invented — every name
and number traces back to data the scoring engine already computed.

**Why this priority**: This is the entire reason the explanation layer exists —
without it, feature 006's dashboard has contribution bars and a score but no
sentence explaining what to do about them, exactly the gap that feature's own
spec named and deferred here. The mechanical fact-check is also the trust
foundation the Ask agent's fallback answers and the draft composer (feature 009)
both build on next.

**Independent Test**: Run the Narrator against a completed score run's ranked
findings, point contributions, client profile, and the seeded playbook; confirm
it produces a headline, reasons (each with points and an evidence link), and an
action list (each with owner and date), and that the dashboard renders all
three for the first time since feature 006 left this field permanently empty.

**Acceptance Scenarios**:

1. **Given** a completed score run's findings already ranked by the scoring
   engine, **When** the Narrator runs, **Then** it produces one headline, a
   list of reasons (each with its point contribution and an evidence link),
   and a prioritized action list, without altering the findings' order
   (REQ-M7-01, REQ-M7-02).
2. **Given** a generated reason, **When** it is displayed, **Then** it follows
   the pattern "a person, a number, and why it matters here" rather than
   generic sentiment language (REQ-M7-03).
3. **Given** the seeded playbook of human-authored action templates, **When**
   the Narrator proposes an action, **Then** it is a personalization of an
   existing playbook template with real names, ticket numbers, and dates — never
   an action invented outside that set (REQ-M7-04, REQ-M7-P3).
4. **Given** a candidate action missing either an owner or a date, **When** the
   action list is assembled, **Then** that action is not displayed (REQ-M7-05).
5. **Given** the Narrator's generated output, **When** the mechanical fact-check
   runs, **Then** every number and name in it is confirmed to already exist in
   the structured input (findings, point contributions, client profile) before
   anything is shown (REQ-M7-06).
6. **Given** a sentence that fails the mechanical fact-check, **When** the
   Narrator assembles its output, **Then** that specific sentence is discarded
   rather than displayed as an unverifiable claim (REQ-M7-07).
7. **Given** the same finding ranking order fed to the Narrator twice, **When**
   compared against a test harness that swaps the ranking order, **Then** the
   Narrator's emphasis changes accordingly without it ever re-deriving its own
   ranking (REQ-M7-P2).
8. **Given** narration has completed for a score run, **When** the dashboard is
   loaded, **Then** the headline, reasons, and actions render — closing the gap
   feature 006 explicitly deferred because `narrator_outputs` was permanently
   empty until this feature (REQ-M8-01).
9. **Given** the Narrator's model call, **When** it generates text, **Then** it
   uses a versioned, structured-output prompt, and any change to that prompt is
   a tracked, replayable event (REQ-M7-08).

---

### User Story 2 - Questions get answered with the right view, not a paragraph (Priority: P1)

A CS lead types "why did the score go up?" into the Ask bar and gets a delta
breakdown with per-cause points and traces back to the evidence — not a written
explanation they have to parse. The same box answers "who's gone quiet?" with
stakeholder cards, "what's the top risk?" with a ranked issue list, and seven
other specific questions with seven specific views, all built from data the
system already computed.

**Why this priority**: The ask box is explicitly one of the three things a user
gets from this product (`base/...md` §1) and the clearest differentiator from a
generic chatbot bolted onto a dashboard — it never recalculates anything, it
only looks things up and renders the right shape for the answer. This closes
the second gap feature 006 explicitly deferred: the Ask bar has been a documented
but unbuilt dashboard component since that feature shipped.

**Independent Test**: Submit a question matching each of the seven
lookup-and-render intents in REQ-M9-02 against a seeded database; confirm each
is classified correctly, answered exclusively from already-persisted data (no
new score computation triggered), and rendered as its specified component within
the 3-second budget. Submit a "write to X about this" question and confirm it
hands off to the draft composer rather than being answered directly.

**Acceptance Scenarios**:

1. **Given** a question matching one of REQ-M9-02's eight mapped intents,
   **When** it is submitted, **Then** the Ask agent classifies it into that
   intent and renders the specified UI component (REQ-M9-01, REQ-M9-02).
2. **Given** any intent-matched question, **When** it is answered, **Then** the
   answer is built exclusively by looking up already-computed data — the event
   ledger, findings, `score_runs`, `narrator_outputs` — and never triggers a new
   score computation (REQ-M9-03, REQ-M9-P1).
3. **Given** a "write to X about this" question, **When** it is classified,
   **Then** the Ask agent returns a distinct handoff response — not a rendered
   component, not a fallback — carrying enough context (the target issue and
   stakeholder) for the draft composer to pick up later, rather than being
   answered inline (REQ-M9-02, Clarifications).
4. **Given** an intent-matched question, **When** it is answered, **Then** the
   response completes within 3 seconds (REQ-M9-08).
5. **Given** a question submitted through the dashboard's Ask bar, **When** it
   is processed, **Then** the bar visibly transitions through its
   `Idle` → `Thinking` → `Answered` states before the rendered component or
   fallback text appears — the Ask bar component feature 006 documented but
   left entirely unrendered (REQ-M8-02).
6. **Given** any rendered component or fallback text, **When** it is displayed,
   **Then** it carries evidence links or sources back to the data it was built
   from — the Ask agent never answers with an uncited claim (REQ-M9-P3).

---

### User Story 3 - The Ask agent says "I don't know" or "I won't" rather than guessing (Priority: P1)

A CS lead asks "will Meridian actually cancel?" and gets a clear statement that
the system describes today's evidence and doesn't forecast — not a confident-
sounding guess. Someone else asks the agent to judge whether a specific
teammate is handling an account well, and it refuses outright. A third question
doesn't match anything the system knows how to answer, and it says so plainly,
with sources attached to whatever partial context it can offer, rather than
inventing a component that doesn't fit.

**Why this priority**: This is REQ-M9's own Goodhart's-law guardrail
(REQ-M9-P2) and the second half of the requirement's own user story — "so I
don't act on a misread question." An agent that guesses instead of declining is
worse than one that answers nothing, because a wrong-but-confident answer erodes
trust faster than an honest refusal. This is exactly as safety-critical to this
feature as the mechanical fact-check is to the Narrator.

**Independent Test**: Submit a prediction question, a colleague-judgment
question, a question about a data source that isn't connected, and a question
matching no known intent; confirm each produces its specific decline or
fallback response — never a guessed component — and that each is logged with
its `matched_intent`/`declined_reason` for the intent-coverage measurement.

**Acceptance Scenarios**:

1. **Given** a prediction question ("will they cancel?"), **When** it is
   submitted, **Then** the Ask agent declines with an explicit statement that
   it describes today's evidence and does not forecast — never a probability
   or a guess (REQ-M9-05).
2. **Given** a question requesting a judgment or character assessment of a
   colleague or client stakeholder, **When** it is submitted, **Then** the Ask
   agent explicitly refuses (REQ-M9-06, REQ-M9-P2 — it never builds a case
   against an individual).
3. **Given** a question referencing a data source that isn't connected,
   **When** it is submitted, **Then** the response states "that source isn't
   connected" rather than silently omitting the answer (REQ-M9-07).
4. **Given** a question matching no known intent, **When** it is submitted,
   **Then** the Ask agent returns a plain-text fallback answer, clearly marked
   as a fallback, with sources attached — never a fabricated component
   (REQ-M9-04).
5. **Given** any question submitted, **When** it completes — matched, declined,
   or fallback — **Then** the question text, matched intent (or null),
   rendered component (or null), declined reason (if any), response time, and
   asking user are logged, so the fraction of unmatched questions is visible
   for measuring the ~90% intent-coverage target (`data-base/
   08-schema-experience.md`).
6. **Given** an "is this normal for X?" question about a stakeholder with
   fewer than 5 prior messages in their confirmed baseline (the Tone reader's
   own "no history, no opinion" threshold, feature 007), **When** it is
   submitted, **Then** the Ask agent declines with `declined_reason =
   insufficient_history` — distinct from `source_not_connected` — rather than
   guessing at a comparison it has no basis for (Clarifications, 2026-08-15).

---

### Edge Cases

- What happens when the Narrator's *headline itself* fails the mechanical
  fact-check, or every reason does? → The dashboard falls back to a
  deterministic, non-LLM headline built directly from the scoring engine's own
  structured output (`"{score} — {band}. Top issue: {issue.label}
  ({issue.points} pts). See evidence trace for detail."`,
  `architecture/06-error-handling.md`), clearly marked as auto-generated
  rather than narrated — never a headline substituted from an unverified
  candidate, and never a blank dashboard.
- What happens when a score run produces no ranked findings at all (a
  genuinely healthy account)? → The Narrator has nothing to narrate and emits
  no output; the dashboard's existing "Nothing needs you today" healthy state
  (REQ-M8-05) is what's shown, not an empty or placeholder narration.
- What happens when none of the seeded playbook's templates apply to a given
  score run's finding types? → The action list is shorter, or empty — REQ-M7
  never mandates a minimum count, only that every displayed action have both
  an owner and a date.
- What happens when an Ask agent lookup tool would need to read a quarantined
  (never validated) finding to answer a question? → It never can. The Ask
  agent's read-only tools only surface `validated` findings and their
  `score_contributions` — the same distinction the M5a validation gate
  (feature 007) already enforces on the scoring engine itself. A quarantined
  finding is invisible to Ask, exactly as it is to scoring.
- What happens if a user asks a second, unrelated question right after the
  first? → Answered independently and statelessly — this feature does not
  build cross-question memory (see "Explicitly out of scope," above); nothing
  about the first question influences the second.
- What happens when an Ask agent tool call itself fails (e.g. a transient
  database error mid-lookup), separate from "no intent matched"? → The Ask
  agent responds with an error/fallback message rather than hanging, within
  the same 2.5-second no-retry budget `architecture/06-error-handling.md`
  already defines for this component — a tool failure is not a silent timeout.
- What happens when "is this normal for X?" is asked about a stakeholder whose
  baseline has fewer than 5 prior messages? → Declined with
  `declined_reason = insufficient_history`, not answered with a guess and not
  conflated with `source_not_connected` — the source is connected, there just
  isn't enough of *this person's* history yet (Clarifications, 2026-08-15).
- What happens when a question technically matches more than one intent's
  keywords (e.g. mentions both a stakeholder and a risk ranking)? → REQ-M9-01
  requires classification into exactly one intent from the closed set; the
  classifier resolves to its single best match rather than rendering multiple
  components at once — this feature does not build a multi-intent response.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Narrator MUST receive findings/issues already ranked by the
  scoring engine and MUST NOT alter their order (REQ-M7-01, REQ-M7-P2).
- **FR-002**: The Narrator MUST produce, per scoring run, exactly one headline,
  a list of reasons each carrying its point contribution and an evidence link,
  and a prioritized action list (REQ-M7-02).
- **FR-003**: Each generated reason MUST follow the pattern "a person, a
  number, and why it matters here," never generic sentiment language
  (REQ-M7-03).
- **FR-004**: Every proposed action MUST be a personalization of a
  human-authored playbook template — real names, ticket numbers, and dates —
  and MUST NEVER be invented outside that playbook (REQ-M7-04, REQ-M7-P3).
- **FR-005**: An action missing either an owner or a due date MUST NOT be
  displayed (REQ-M7-05).
- **FR-006**: The system MUST mechanically verify that every number and name in
  the Narrator's output already exists in its structured input before display
  (REQ-M7-06).
- **FR-007**: Any sentence that fails the mechanical fact-check MUST be
  discarded rather than displayed (REQ-M7-07).
- **FR-008**: The Narrator MUST use a versioned, structured-output prompt;
  changing that prompt MUST be a tracked, replayable event (REQ-M7-08).
- **FR-009**: The Narrator MUST NEVER introduce a fact, number, or name absent
  from its structured input (REQ-M7-P1).
- **FR-010**: The dashboard MUST render the Narrator's headline, reasons, and
  actions once produced for a score run — closing the gap feature 006 left
  explicitly deferred (REQ-M8-01).
- **FR-011**: The Ask agent MUST classify each incoming question into a closed
  set of intents, each mapped to a specific UI component (REQ-M9-01).
- **FR-012**: The Ask agent MUST support, at minimum, the eight intent
  mappings listed in REQ-M9-02 (seven lookup-and-render components plus the
  hand-off to the draft composer).
- **FR-012a**: A "write to X about this" question MUST classify into its own
  intent and produce a distinct handoff response — separate from both a
  rendered component and a fallback — carrying the target issue and
  stakeholder context, so feature 009's draft composer can consume it once it
  exists (Clarifications, 2026-08-15).
- **FR-013**: The Ask agent MUST answer every question exclusively by looking
  up already-computed data (ledger, findings, `score_runs`, `narrator_outputs`)
  and MUST NEVER trigger a new score computation (REQ-M9-03, REQ-M9-P1).
- **FR-014**: A question matching no known intent MUST fall back to a
  plain-text answer, clearly marked as such, with sources attached — never a
  fabricated component (REQ-M9-04).
- **FR-015**: A prediction question MUST be declined with an explicit statement
  that the system describes today's evidence and does not forecast (REQ-M9-05).
- **FR-016**: A question requesting judgment or a character assessment of a
  colleague or client stakeholder MUST be declined with an explicit refusal
  (REQ-M9-06, REQ-M9-P2).
- **FR-017**: A question referencing a data source that isn't connected MUST
  receive "that source isn't connected" rather than a silently omitted answer
  (REQ-M9-07).
- **FR-017a**: An "is this normal for X?" question about a stakeholder with
  insufficient baseline history (fewer than 5 prior messages, the Tone
  reader's own threshold) MUST be declined with a reason distinct from
  `source_not_connected` — the system is honest about *why* it can't answer,
  not just that it can't (Clarifications, 2026-08-15).
- **FR-018**: The Ask agent MUST respond within 3 seconds for intent-matched
  questions (REQ-M9-08).
- **FR-019**: The Ask agent MUST NEVER recalculate or override the stored score
  (REQ-M9-P1).
- **FR-020**: The Ask agent MUST NEVER build a case against an individual
  employee (REQ-M9-P2).
- **FR-021**: Every rendered component and every fallback or decline text MUST
  carry evidence links or sources — no uncited claim is ever displayed
  (REQ-M9-P3).
- **FR-022**: The dashboard MUST render an always-present Ask bar showing
  `Idle`/`Thinking`/`Answered` states around each question — closing the
  second gap feature 006 explicitly deferred (REQ-M8-02).
- **FR-023**: The system MUST log every Ask agent interaction — question text,
  matched intent (or null/fallback), rendered component (or null), declined
  reason (if any), response time, and the asking user — to support measuring
  the ~90% intent-coverage target (`data-base/08-schema-experience.md`).
- **FR-024**: The Ask agent's data lookups MUST only ever surface `validated`
  findings and their point contributions — a quarantined finding (feature
  007's validation gate) MUST remain invisible to every Ask agent answer, the
  same as it is to the scoring engine.

### Key Entities

- **Narrator output**: One per completed score run — a headline, a list of
  reasons (text, points, evidence event IDs), a list of actions (text, owner,
  due date, playbook reference), whether the mechanical fact-check passed, and
  which prompt version produced it.
- **Playbook action**: One human-authored template in the fixed, signed-off
  action menu the Narrator personalizes from — never a source the Narrator
  writes to.
- **Ask query**: One per question submitted — the question text, which intent
  it matched (if any), which component was rendered (if any), why it was
  declined (if it was), how long it took, and who asked it.
- **Handoff response**: The distinct answer shape for "write to X about this"
  — neither a rendered component nor a fallback — carrying the target issue
  and stakeholder context for feature 009's draft composer to consume later
  (Clarifications, 2026-08-15).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any score run with at least one finding, a CS lead sees a
  plain-language explanation of the score — who's involved and why it moved —
  on the dashboard within the same time it takes the score itself to update.
- **SC-002**: Every number and name a CS lead reads in a displayed narration
  reason can be traced back to real, already-computed data behind it — none is
  ever displayed without that trace existing.
- **SC-003**: Every action a CS lead sees on the dashboard has both a named
  owner and a date attached — no action is ever displayed without both.
- **SC-004**: A CS lead asking any of the eight supported question types
  receives the matching visual answer, not a written paragraph, in under 3
  seconds.
- **SC-005**: A CS lead asking a forecasting question always receives an
  honest "I describe today, I don't predict" answer, never a probability or a
  guess.
- **SC-006**: A CS lead asking for a judgment about a specific colleague's
  performance always receives a refusal, never a character assessment.
- **SC-007**: The proportion of questions the fixed set of intents fails to
  answer is visible and measurable at any time, without querying the database
  directly, so product decisions about expanding the intent set are based on
  real usage.

## Assumptions

- The Narrator is triggered by its own manual script (e.g. `scripts/
  run_narrator.py`, run after `scripts/compute_score.py`), not chained
  automatically inside `RecomputeScoreUseCase` — matching every prior
  feature's own established pattern (`RunCollectorUseCase`, `RunReadersUseCase`,
  `RecomputeScoreUseCase`, and feature 007's `ConfirmBaselineUseCase` are all
  invoked this way; no live, event-driven trigger path exists anywhere in the
  pipeline yet). REQ-M7's "~40s end-to-end score-update budget" is the target
  for a future live-triggered path that doesn't have a caller yet, the same
  status feature 007 already recorded for the Tone/Intent readers' own timing
  budget — not evidence that this feature must build that live path. Exactly
  one `narrator_outputs` row is still produced per `score_runs` row
  (`data-base/08-schema-experience.md`), just on the same manual cadence every
  other pipeline stage already uses.
- `DashboardResponse` (`architecture/07-api-spec.md`) does not yet carry a
  field for the Narrator's headline/reasons/actions or for Ask bar state —
  this feature adds them, the same kind of additive schema change feature 006
  made for `PulseEvent`/`StakeholderCard`, to be reflected back into the
  architecture document during this feature's plan.
- `ask_queries.declined_reason` (`data-base/08-schema-experience.md`) is
  documented today as `ENUM(prediction, colleague_judgment,
  source_not_connected, unclear)`. This feature adds `insufficient_history`
  as a fifth value (Clarifications, 2026-08-15) and extends
  `AskFallbackResponse`'s matching enum in `architecture/07-api-spec.md` —
  the same kind of additive schema change as the `DashboardResponse` note
  above, to be reflected back into both documents during this feature's plan.
  `AskComponentResponse`/`AskFallbackResponse` likewise gain the handoff
  response shape from the first Clarification above.
- The Ask agent's multi-step classify → tool → render orchestration follows
  the already-ratified `decisions/03-langgraph-for-ask-agent.md`; this
  specification does not re-decide orchestration technology, only the
  user-facing behavior REQ-M9 already requires.
- The dashboard's always-present "Ask bar" (`base/...md` §11.3) and the named
  "Ask thread" screen (§11.2) are the same capability at two zoom levels — the
  bar is the entry point and its expanded question-and-answer is the thread —
  not two separately built surfaces.
- The playbook (`playbook_actions`) is pre-seeded, human-authored data already
  signed off per `decisions/00-open-questions-resolved.md` Q7; this feature
  reads and personalizes it, and does not build an authoring or sign-off UI.
- Multi-turn conversational memory across separate questions is out of scope;
  checkpointing stays off per `decisions/03-langgraph-for-ask-agent.md`, and
  each question is answered statelessly.
