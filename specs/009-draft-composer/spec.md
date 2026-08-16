# Feature Specification: Draft Composer

**Feature Branch**: `009-draft-composer`

**Created**: 2026-08-16

**Status**: Draft

## Clarifications

### Session 2026-08-16

- Q: The base product spec's screen inventory (`base/...md` §11.2) labels
  this screen "Message editing beside its evidence," but
  `requirements/10-draft-composer.md` REQ-M10-08 names exactly two actions
  ("Copy draft," "Log as sent (manual)") and `data-base/
  08-schema-experience.md`'s `draft_messages` table has no edited-text
  column. Does the draft composer allow in-app free-text editing of a
  draft's wording before copy/log, and if so, must an edit re-run the
  pre-display checks? → A: No in-app editing — the draft is copy-only,
  exactly as generated. Any wording change happens only after the CS lead
  pastes it into their own email client, outside this system. The schema's
  silence on an edited-text field and REQ-M10-08's exact two-action list are
  the stronger signal; "message editing" describes interacting with the
  message (tone variants, copy), not literal free-text editing.
- Q: REQ-M10-01 says the draft composer is "given: the top issue and its
  evidence," but `architecture/07-api-spec.md`'s `DraftRequest` schema takes
  an arbitrary `issue_id` with no validation tying it to the current
  #1-ranked issue. Should drafting be restricted to only the single
  top-ranked issue, or accept any issue with cited evidence? → A: Any issue
  with cited evidence. `DraftRequest.issue_id` is a generic, unconstrained
  parameter in the already-ratified contract, with no top-rank validation
  described anywhere in it; REQ-M10-01's "top issue" describes the common,
  motivating case, not a hard restriction this feature should newly enforce.
  (Note, found during `/speckit-plan`: feature 008's `draft_handoff` node,
  `ask_agent_graph.py`'s `handoff()`, in fact always resolves `issue_id`
  from the latest run's top-ranked contribution today — so in practice the
  only existing caller already passes the top issue. This feature still
  must not hard-code that restriction itself, since `DraftRequest` is a
  general-purpose contract this feature owns independently of its one
  current caller.)
- Q: When a generated draft fails a pre-display check (REQ-M10-07), what
  does the CS lead see? `architecture/06-error-handling.md` already defines
  a generic failure message for generation errors/timeouts ("Couldn't
  generate a draft — try again"), but doesn't say whether a checks-failure
  is treated the same way. → A: The same generic message — no distinction
  between "the model errored" and "the model produced something that failed
  validation," and no automatic silent retry beyond the one already defined
  for generation errors. The CS lead is never told which specific check
  failed or why, the safer default that avoids any chance of a
  failure-reason itself hinting at internal-only content.

**Input**: User description: "Draft composer — build-order Phase 9
(`specs/ROADMAP.md`): the closer. Fills in `requirements/10-draft-composer.md`
(M10 — generates the client-facing message from the top ranked issue and its
evidence (M6/M7 output), the client profile's communication norms (M3), and
real thread history (M2); offers tone variants; runs mechanical pre-display
checks that block rendering on any unverifiable fact, invented date, or
internal-data leak; provides only 'Copy draft' and 'Log as sent (manual)' — no
send capability of any kind exists anywhere in the system, an architectural
absence per REQ-M10-P1). Traces `sequences/04-sequence-draft-composer.md` (Ask
agent → Composer handoff via feature 008's already-built `draft_handoff`
response, evidence/profile fetch, generate, automatic checks, render-or-block,
and the out-of-system human-send step that later re-enters as a normal
collected event closing the response clock per REQ-M10-09). Cites
`architecture/04-ai-safety-and-model-usage.md` and `05-agent-catalog.md` for
the plain `LLMPort` design already scoped to this touchpoint by
`decisions/03-langgraph-for-ask-agent.md` (LangGraph stays scoped to the Ask
agent only), and `data-base/08-schema-experience.md`'s already-defined
`draft_messages` table (note: no `sent_at`/`sent_by` column exists by design —
schema-level enforcement of the no-send boundary, not just UI-level). Explicit
prohibitions REQ-M10-P1..P6 (no send capability, no blame language, no
invented dates/causes, no discounts/concessions, no mention that the
relationship is monitored/scored, no mention of any other client) are hard
constraints on every user story."

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement
cites the `REQ-<ID>` that is its source of truth (`requirements/
10-draft-composer.md`).

**In scope**: generating a client-facing draft from the requested issue
(commonly, but not exclusively, the top-ranked one) + its evidence (feature
005/007 output), the client profile's `communication_norms`
(feature 003), and real thread history (`event_threads`/`response_pairs`,
feature 003); offering tone variants (`direct`/`formal`/`brief`, already fixed
by `architecture/07-api-spec.md`'s `DraftRequest`/`DraftResponse` schemas);
the automatic pre-display checks that block rendering on any unverifiable
fact, invented date, or internal-data leak; the "Copy draft" and "Log as sent
(manual)" actions and their `draft_messages` bookkeeping; and consuming the
`draft_handoff` response (`{issue_id, stakeholder_id}`) that feature 008's Ask
agent already produces for "write to X about this."

**Explicitly out of scope, with a reason each**:

- **The Ask agent's classification of "write to X about this."** Feature 008
  already built this — the intent match and the `draft_handoff` response
  shape (`AskComponentResponse.component = draft_handoff`,
  `component_props = {issue_id, stakeholder_id}`) are pre-existing inputs to
  this feature, not something it builds or modifies.
- **Any send capability, in any form.** REQ-M10-P1 makes this an
  architectural absence, not a feature to build and then gate — there is
  nothing to design here beyond confirming no such path is ever introduced.
- **The human's own email/chat client and the collector event that later
  observes the sent message.** REQ-M10-09's "close the response clock" is
  M1's (`requirements/01-signal-collectors.md`) existing collector pipeline
  doing its normal job on a normal outbound event; this feature does not
  modify M1, it only stops at "Copy draft"/"Log as sent (manual)."
- **Playbook action generation.** The Narrator's action list
  (`requirements/07-narrator.md`, feature 008) is a distinct artifact from a
  draft message — this feature may read the same top issue and evidence the
  Narrator already ranked, but it does not generate or personalize playbook
  actions itself.
- **Feedback controls' effect on scoring (damping).** `damping_weights`
  (`requirements/04-feedback-memory.md`) is feature 010's territory; nothing
  in this feature reads or writes feedback verdicts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A draft acknowledges the specific failure first, with exactly one ask (Priority: P1)

A CS lead clicks "Write to Ana about this" beside the top-ranked issue and, a
few seconds later, sees a message open beside the evidence that already led
them to click: "Ana — we took 19 hours to respond to ticket #456; we promised
4. Engineering is on it today, and I'll call you before Thursday." It names
the specific failure first, makes exactly one request of the reader, and
reads like someone who actually knows this account wrote it — not a generic
apology template.

**Why this priority**: This is REQ-M10-01/02/03's entire purpose and the
reason the module exists at all — "the closer" (`specs/ROADMAP.md`, build-order
Phase 9). Every other requirement in this feature (tone variants, pre-display
checks, copy/log actions) only matters once a draft this specific and this
disciplined already exists to act on.

**Independent Test**: Trigger a draft from a seeded top issue with its cited
evidence, client profile, and real thread history; confirm the generated
draft's first sentence states the specific failure found in the evidence
(not a generic opener), the message contains exactly one request, and every
name/date/fact in it traces back to the supplied evidence, profile, or
thread history.

**Acceptance Scenarios**:

1. **Given** an issue and its cited evidence (feature 005/007's already-
   validated findings) — commonly, but not exclusively, the top-ranked
   issue — the client's communication norms, and real thread history,
   **When** a draft is requested, **Then** the system generates a message
   built from those four inputs and no others (REQ-M10-01, Clarifications,
   2026-08-16).
2. **Given** a generated draft, **When** it opens, **Then** its first
   substantive sentence states a concrete fact drawn from the evidence — not
   a generic apology or greeting (REQ-M10-02).
3. **Given** a generated draft, **When** it is reviewed, **Then** it contains
   exactly one request of the reader, never zero and never more than one
   (REQ-M10-03).
4. **Given** a stakeholder whose profile marks them as short/terse
   (`communication_norms`), **When** a draft is generated for them, **Then**
   the draft is noticeably shorter and more direct than one generated for a
   stakeholder without that norm, matching the client's own communication
   rhythm (REQ-M10-04).
5. **Given** an issue whose appropriate response is a call rather than a
   written message, **When** a draft is requested, **Then** the system says
   so explicitly and returns talking points instead of message text
   (REQ-M10-06).

---

### User Story 2 - Every draft is mechanically checked before a human ever sees it (Priority: P1)

Before any draft is displayed, the system runs it through automatic checks:
every fact stated must already exist in the evidence, no dated promise may
appear unless a human actually supplied that date, and nothing internal —
scores, internal notes, other clients — may leak into the text. A draft that
fails any check is never shown; the CS lead never has to be the one who
catches a hallucinated fact.

**Why this priority**: This is the same trust discipline the Narrator's
mechanical fact-check (`requirements/07-narrator.md`, feature 008) already
established for internal-facing text — here it protects something a human is
about to send to a paying client, which raises the stakes further, not
lower. REQ-M10-07 explicitly requires the check to block display, not
silently strip content.

**Independent Test**: Generate a draft, then inject a fabricated fact/date
not present in the evidence and a piece of internal-only data (e.g. a score
number) into a copy of it; confirm both variants are blocked from display
while the original, clean draft renders normally.

**Acceptance Scenarios**:

1. **Given** a generated draft, **When** it is submitted for the pre-display
   check, **Then** every factual claim in it is verified against the
   evidence, profile, and thread history it was built from before any
   rendering occurs (REQ-M10-07).
2. **Given** a draft containing a dated promise or a causal claim
   ("because...", "due to..."), **When** the pre-display check runs,
   **Then** that date is confirmed to have been supplied by a human (via an
   existing commitment or thread history record) and that cause is
   confirmed to name only entities already present in the evidence — never
   invented by the generation step (REQ-M10-07, REQ-M10-P3).
3. **Given** a draft, **When** the pre-display check runs, **Then** it
   confirms no internal-only data (scores, internal notes, mentions of any
   other client) appears in the text (REQ-M10-07, REQ-M10-P5, REQ-M10-P6),
   and no discount or commercial-concession term appears in the text
   (REQ-M10-07, REQ-M10-P4).
4. **Given** a draft that fails any pre-display check, **When** the check
   completes, **Then** the draft is blocked from display entirely — not
   auto-edited or silently stripped down to only its verified sentences
   (REQ-M10-07's own "blocks display, does not silently strip content"),
   and the CS lead sees the same generic failure message already defined
   for a generation error or timeout ("Couldn't generate a draft — try
   again," `architecture/06-error-handling.md`) — never a message naming
   which specific check failed, and never a silent automatic retry beyond
   the one already defined for generation errors (Clarifications,
   2026-08-16).
5. **Given** a draft that passes every check, **When** it is displayed,
   **Then** it never offers a discount or commercial concession —
   mechanically verified (REQ-M10-P4) — and never contains blame language
   directed at the client — prompt-enforced, not mechanically checked
   (REQ-M10-P2, `research.md` Decision 6).

---

### User Story 3 - Tone variants, then copy or log — never send (Priority: P2)

Once a draft passes its checks, the CS lead can request a more formal or more
direct rewrite of the same underlying content without starting over, then
either copy the finished text into their own email client or mark it as
manually sent for their own records. There is no button, menu item, or API
route anywhere that transmits the message on the CS lead's behalf — pasting
and sending happens entirely in the human's own tool, outside this system.

**Why this priority**: This is where REQ-M10-08 resolves the original
mockup's "Send & Log to CRM" affordance and where product principle P4 ("a
human always sends") becomes a concrete, testable UI/API boundary rather than
a policy statement. It's P2 relative to Story 1/2 because a correct,
well-checked draft with no variant/copy/log actions still delivers most of
the value; those actions make it usable, not correct.

**Independent Test**: Request a tone variant for an already-generated,
checks-passed draft and confirm every fact present in the new variant is
still one the original evidence supports (not necessarily an identical set
to the first variant — SC-006, `/speckit-analyze` finding I1); click "Copy
draft" and confirm only `copied_at` is
stamped; separately click "Log as sent (manual)" and confirm only
`logged_manually_at` is stamped and no outbound network call to any external
system occurs.

**Acceptance Scenarios**:

1. **Given** a checks-passed draft, **When** the CS lead requests a
   different tone variant, **Then** the system generates a new, independent
   draft in the requested tone from the same evidence, profile, and
   thread-history inputs — every fact in it still traceable to that
   evidence, though not necessarily an identical fact set to the first
   variant (REQ-M10-05, SC-006).
2. **Given** a displayed, checks-passed draft, **When** the CS lead clicks
   "Copy draft," **Then** the system records that the draft was copied and
   performs no other action (REQ-M10-08).
3. **Given** a displayed, checks-passed draft, **When** the CS lead clicks
   "Log as sent (manual)," **Then** the system records an internal-only flag
   in this system's own storage and makes no connection to any external
   system, including the CRM (REQ-M10-08).
4. **Given** the entire draft composer surface — UI and API — **When**
   inspected for a send capability, **Then** none exists in any form: no
   send button (not disabled, absent), no send API route, no scheduled-send
   feature (REQ-M10-P1).
5. **Given** a displayed, checks-passed draft, **When** the CS lead looks
   for a way to change its wording in-app, **Then** no such control exists —
   the only available actions are tone-variant selection, "Copy draft," and
   "Log as sent (manual)" (REQ-M10-08, Clarifications, 2026-08-16).
6. **Given** a draft the CS lead sent themselves through their own email
   client, **When** that outbound message is later picked up by the email
   collector (M1) as a normal event, **Then** the response clock for the
   related commitment closes and subsequent scoring runs can observe whether
   the message worked (REQ-M10-09).

---

### Edge Cases

- What happens when no fact in the evidence is strong enough to open the
  draft with (an issue with thin evidence)? → The draft either isn't
  generated (no draft with an unverifiable opening claim is ever produced)
  or generation is declined with a clear reason — the pre-display check
  (REQ-M10-07) never has to catch a weak-but-technically-true opener because
  generation itself is disciplined to the evidence it was given (REQ-M10-P1
  narrator's discipline applied here to REQ-M10-01/02).
- What happens when a draft is requested for an issue that is not the
  system's current #1-ranked issue? → It is generated normally, as long as
  the issue has cited evidence — the caller (the Ask agent's
  `draft_handoff`) decides which issue, and this feature does not enforce a
  top-rank-only restriction (Clarifications, 2026-08-16).
- What happens when the client profile has no `communication_norms` recorded
  for a stakeholder? → The draft defaults to a neutral, professional register
  rather than guessing at a rhythm no human ever declared (REQ-M3-P2's "never
  auto-inferred" discipline extends to how this feature reads that field).
- What happens when a draft is requested for an issue with zero evidence
  events? → No draft is generated; `evidence_event_ids`'s non-empty
  constraint (`data-base/08-schema-experience.md`) makes an evidence-less
  draft structurally unrepresentable, matching `findings.cited_event_ids`'s
  existing discipline.
- What happens when `stakeholder_id` doesn't resolve to a stakeholder on
  the current client profile? → `404`, the same not-found handling
  `issue_id` already gets — a draft is never generated for an unknown
  recipient (`/speckit-analyze` finding U3, 2026-08-16).
- What happens when a draft fails a pre-display check specifically (as
  opposed to a model timeout/error)? → The CS lead sees the exact same
  generic failure message as a generation error — the system never
  distinguishes "the model errored" from "the model produced something that
  failed validation," and never auto-retries beyond what's already defined
  for generation errors (Clarifications, 2026-08-16).
- What happens when every tone variant of a draft fails the pre-display
  check (e.g. the underlying content itself has a problem, not the tone)? →
  All variants are blocked from display; the CS lead sees no draft rather
  than a partially-checked one, and can retry the request once the
  underlying issue's evidence changes.
- What happens when a CS lead wants to tweak a draft's wording before
  sending it? → There is no in-app editing control; they copy the text into
  their own email client and edit it there, entirely outside this system's
  checks and this feature's scope (Clarifications, 2026-08-16).
- What happens if the CS lead clicks "Log as sent (manual)" without ever
  clicking "Copy draft" first? → Allowed independently; the two actions are
  not sequenced or gated on each other, since a CS lead might have already
  sent similar wording from memory rather than pasting verbatim.
- What happens when a call, not a message, is the appropriate response
  (REQ-M10-06), but the CS lead still asks for a written draft? → The system
  states explicitly that a call is the appropriate action for this issue and
  supplies talking points instead of substituting a written message anyway —
  it does not silently comply with a request that conflicts with its own
  judgment about the right medium.
- What happens when the human's sent email is picked up by the collector but
  doesn't match any open commitment (e.g. they wrote something unrelated)? →
  Outside this feature's boundary; REQ-M10-09's clock-closing behavior is the
  collector/commitment-matching logic M1/M2 already own, not new matching
  logic this feature introduces.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST generate a draft from exactly four inputs: the
  requested issue and its cited evidence, the client profile's communication
  norms, real thread history, and actions the team has actually agreed to
  (REQ-M10-01). The requested issue is whichever issue the caller (the Ask
  agent's `draft_handoff`) references — commonly the top-ranked issue, but
  not exclusively; the system MUST NOT reject a request for a lower-ranked
  issue that still has cited evidence (Clarifications, 2026-08-16).
- **FR-002**: A generated draft MUST open by acknowledging a specific,
  evidence-backed failure — never a generic apology (REQ-M10-02).
- **FR-003**: A generated draft MUST contain exactly one ask (REQ-M10-03).
  Prompt-enforced only, not mechanically checked — a reliable "exactly one
  ask" detector would need genuine intent parsing, not a pattern this
  codebase's keyword/regex-based checks can catch without a high
  false-positive rate; the same accepted trade-off `tests/strategy.md`
  already applies to "draft quality" broadly (`/speckit-analyze` finding
  U2, 2026-08-16).
- **FR-004**: A generated draft MUST match the client's declared
  communication rhythm from the profile's communication norms (REQ-M10-04).
- **FR-005**: The system MUST offer tone variants of the same underlying
  content, at minimum `direct`, `formal`, and `brief`
  (`architecture/07-api-spec.md` `DraftRequest.tone_variant`) (REQ-M10-05).
- **FR-006**: WHEN the appropriate action for an issue is a call rather than
  a written message, THE SYSTEM MUST say so explicitly and provide talking
  points instead of draft message text (REQ-M10-06).
- **FR-007**: THE SYSTEM MUST run automatic pre-display checks on every
  generated draft: every stated fact exists in the supplied evidence, no
  dated promise or causal claim appears unless supported by the evidence,
  nothing internal (scores, internal notes, other clients) appears in the
  text, and no discount or commercial concession appears in the text
  (REQ-M10-07; the concession check is an additive fifth check beyond
  REQ-M10-07's original three-item list, closing FR-014's own guarantee —
  `/speckit-analyze` finding G1, 2026-08-16).
- **FR-008**: A draft that fails any pre-display check MUST be blocked from
  display entirely — never auto-edited or silently stripped to a partial,
  passing subset (REQ-M10-07). The CS lead MUST see the same generic
  failure message already defined for a draft-generation error or timeout,
  never a message naming which specific check failed and never a silent
  automatic retry beyond the one already defined for generation errors
  (Clarifications, 2026-08-16).
- **FR-009**: THE SYSTEM MUST provide only two actions on a displayed draft:
  "Copy draft" (stamps `copied_at`) and "Log as sent (manual)" (stamps
  `logged_manually_at`, an internal-only flag) (REQ-M10-08).
- **FR-009a**: THE SYSTEM MUST NOT provide any in-app free-text editing
  capability for a draft's message text — the text displayed is exactly the
  text that passed the pre-display checks; any wording change happens only
  after the CS lead pastes it into their own email client, outside this
  system (Clarifications, 2026-08-16).
- **FR-010**: "Log as sent (manual)" MUST write only to this system's own
  storage and MUST NEVER open a connection to any external system, including
  the CRM (REQ-M10-08).
- **FR-011**: THE SYSTEM MUST NEVER provide, render, or expose via any API a
  send capability of any kind — no send button (disabled or otherwise), no
  send API endpoint, no scheduled-send feature (REQ-M10-P1).
- **FR-012**: A draft MUST NEVER contain blame language directed at the
  client (REQ-M10-P2).
- **FR-013**: A draft MUST NEVER contain an invented date or cause not
  present in the evidence (REQ-M10-P3). Both halves are mechanically
  checked: invented dates by the date-verification check, invented causes
  by a check that confirms every causal clause ("because...", "due to...")
  names only entities already present in the evidence (`/speckit-analyze`
  finding U1, 2026-08-16).
- **FR-014**: A draft MUST NEVER contain a discount or commercial concession
  (REQ-M10-P4). Mechanically checked against a closed denylist of
  commercial-concession terms (`/speckit-analyze` finding G1, 2026-08-16) —
  the one REQ-M10-P2/P4 prohibition specific enough to keyword-check
  reliably; blame language (FR-012) stays prompt-enforced only, since a
  blame denylist would false-positive on genuine apologies far more often
  (`research.md` Decision 6).
- **FR-015**: A draft MUST NEVER mention, hint at, or allude to the fact
  that the client relationship is being monitored or scored (REQ-M10-P5).
- **FR-016**: A draft MUST NEVER mention any other client (REQ-M10-P6).
- **FR-017**: WHEN a human sends the drafted message through their own
  email/chat client and it is later picked up by a collector (M1) as a
  normal outbound event, THE SYSTEM MUST close the response clock for the
  related commitment so subsequent scoring runs can observe whether the
  suggestion worked (REQ-M10-09).
- **FR-018**: THE SYSTEM MUST consume the Ask agent's `draft_handoff`
  response (`{issue_id, stakeholder_id}`, feature 008,
  `architecture/07-api-spec.md`) as the entry point for "write to X about
  this," rather than requiring a separate trigger path.

### Key Entities

- **Draft message**: One per generation request — the message text, its
  tone variant, the issue it addresses, the intended stakeholder, the
  evidence event IDs it cites (non-empty by constraint), whether it passed
  the pre-display checks, whether and when it was copied, and whether and
  when the CS lead logged it as manually sent. The message text is
  immutable once generated — there is no in-app edit action, only copy/log
  (Clarifications, 2026-08-16). No field on this entity ever represents
  "sent to the client" — that state does not exist in this system by
  design.
- **Pre-display check result**: The pass/fail outcome of REQ-M10-07's five
  checks (facts exist in evidence, no invented dates, no invented causes,
  no internal leak, no discount/commercial concession — `/speckit-analyze`
  findings G1/U1, 2026-08-16) for a given draft — a failing result blocks
  that draft from ever being rendered.
- **Talking points**: The alternative output produced instead of message
  text when the appropriate action is a call (REQ-M10-06) — a list of
  points grounded in the same evidence a written draft would have cited.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A CS lead who clicks "Write to X about this" sees a
  ready-to-use draft, or an explicit call-and-talking-points response,
  within the same order of time it takes to open the evidence behind it —
  no manual drafting from a blank page.
- **SC-002**: Every fact a CS lead reads in a displayed draft can be traced
  back to real evidence, profile data, or thread history — none is ever
  displayed without that trace existing, verified by a scripted red-team
  test that a draft referencing a fabricated fact is blocked before
  display.
- **SC-003**: No draft ever displayed contains a discount, a commercial
  concession, or any reference — direct or implied — to the fact that the
  relationship is being scored or monitored; each is mechanically verified
  before display, never left to prompt discipline alone (`/speckit-analyze`
  finding G1, 2026-08-16). Blame language directed at the client is
  prompt-enforced only — not mechanically checked, the one prohibition in
  this list a keyword-based check would false-positive on too often to be
  reliable (`research.md` Decision 6).
- **SC-004**: A code-level review — an automated scan of every file this
  feature adds or extends, confirming none imports an outbound-transport
  client (SMTP, HTTP client used for a third-party send, chat/CRM SDK) —
  confirms zero code paths, UI elements, or API routes anywhere in the
  system that could transmit a drafted message to an external recipient —
  a structural guarantee, not a UI-only one (`/speckit-analyze` finding G2,
  2026-08-16: this scan is now a real, mechanically-run task, not a manual
  inspection step).
- **SC-005**: "Log as sent (manual)" never results in a network call to any
  system outside this one, including the CRM, in 100% of exercised cases.
- **SC-006**: A CS lead can obtain a different tone variant of an
  already-generated, checks-passed draft without it ever contradicting a
  fact present in the original evidence — each variant is independently
  generated and independently fact-checked against the same evidence, so a
  shorter variant may omit a fact a longer one includes, but neither can
  ever state something the evidence doesn't support (`/speckit-analyze`
  finding I1, 2026-08-16 — softened from an earlier, stronger "loses no
  facts" wording that overstated what independently-generated variants can
  structurally guarantee).

## Assumptions

- The Ask agent's "write to X about this" intent classification and its
  `draft_handoff` response shape are feature 008's already-shipped output
  (`AskComponentResponse.component = draft_handoff`,
  `component_props = {issue_id, stakeholder_id}`,
  `architecture/07-api-spec.md`); this feature is the first consumer of
  that response, not a modification of the Ask agent itself.
- `POST /api/drafts`, `POST /api/drafts/{id}/copy`, and
  `POST /api/drafts/{id}/log-as-sent` (`architecture/07-api-spec.md`) are
  already-specified routes this feature implements against; there is no
  `/send` route in that specification, matching REQ-M10-P1 exactly, and this
  feature introduces none.
- The plain `LLMPort` design (not LangGraph) applies to this touchpoint, per
  `decisions/03-langgraph-for-ask-agent.md`'s explicit scoping of LangGraph
  to the Ask agent only — this feature's plan does not re-decide
  orchestration technology.
- `draft_messages` (`data-base/08-schema-experience.md`) is already fully
  specified, including the deliberate absence of `sent_at`/`sent_by`; this
  feature populates that existing table and does not alter its schema.
- The client profile's `communication_norms` field
  (`data-base/04-schema-context.md`) is free text supplied as context, not a
  structured rhythm/tone taxonomy; "matching the client's communication
  rhythm" (REQ-M10-04) means the generation step reads and honors that free
  text, not that this feature introduces new structured profile fields.
- "Real thread history" (REQ-M10-01) refers to the `event_threads`/
  `response_pairs` projections M2 (`requirements/02-event-ledger.md`)
  already maintains — this feature reads them and does not build new
  thread-reconstruction logic.
- Tone variant generation is a fresh, independent generation call over the
  *same* evidence/profile/thread-history inputs, re-checked from scratch —
  not an edit of the first variant's text and not guaranteed to restate an
  identical set of facts, only guaranteed to never state one the evidence
  doesn't support (`/speckit-analyze` finding I1, 2026-08-16 — corrects an
  earlier, stronger wording here that implied text reuse across variants).
- Talking points (REQ-M10-06) are subject to the same pre-display checks as
  message drafts (REQ-M10-07) — the requirement doesn't exempt the
  call-instead-of-message path from the fact-verification discipline, and
  no reasonable reading of REQ-M10-07/P1-P6 would exempt it either.
