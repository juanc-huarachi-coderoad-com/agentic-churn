# Research: Assistant Chat Conversation

Feature: `specs/017-assistant-chat-conversation` (`spec.md`). All Technical Context unknowns
resolved below.

## Decision 0 — Scope confirmation: this is a single-account product

**Finding:** `.specify/memory/constitution.md` states plainly: *"Agentic Churn is a dedicated
monitoring agent for **one client relationship**"* and *"Isolation model: one deployment = one
client = one database schema/tenant... never shared across stacks."* A repo-wide search for
account-switching UI (`accountId`, route params, a switcher component) in `frontend/src` returns
nothing, and `AskBar` is mounted exactly once, in `dashboard-page.tsx`, with no account-scoped
prop. There is no multi-account view to switch between in this product, today or by design.

**Impact on spec.md FR-016 ("separate conversation per account"):** this requirement is real and
correct as written, but is satisfied *vacuously* — there being exactly one account per
deployment, "the conversation for this account" and "the conversation for this session" are the
same thing. Building an `accountId → Conversation` map, a keyed store, or any switching logic
would be exactly the kind of generic-tenancy abstraction constitution P10 explicitly rejects
("a generic multi-tenancy abstraction... is a permanent product constraint, not an MVP shortcut
waiting to be generalized"). **Decision: implement a single conversation, scoped to the `AskBar`
component's own lifetime — no account key, no map, no store keyed by anything.** If a future
feature ever introduces multiple accounts in one session, that is new scope requiring its own
spec, not something to speculatively build room for now.

## Decision 1 — Where the transcript lives: component state, not a global store

**Decision:** The turn transcript is `useState`/`useReducer` state local to `AskBar`, not a
Zustand store.

**Rationale:** Constitution P11: *"No global state by default; state lives as close to its owner
as possible... Zustand only when local state isn't enough."* `AskBar` is mounted once and never
unmounts while the dashboard is open (confirmed by the existing "preserves the last exchange
across scrolling/interacting elsewhere" test — no collapse/remount happens today, and nothing in
this feature changes that). Spec.md's own resolved clarification says navigating away and
reloading **does not** need to restore the conversation — which is exactly what plain component
state already gives for free (it resets on unmount, with no extra code required to enforce that).
A Zustand store would need to be deliberately reset on the same triggers a `useState` already
resets on automatically — solving a problem this design doesn't have.

**Alternatives considered:**
- *Zustand store*: rejected — see above; would be state lifted for no consumer that needs it
  (`AskBar` is the only reader/writer).
- *TanStack Query cache as the transcript*: rejected — `useMutation` naturally models "one
  in-flight request," not "an ordered list that keeps growing." Bending it to hold the whole
  transcript (e.g., via `mutation.data` accumulation) is more contortion than a plain array.

## Decision 2 — Conversation memory: client-resent history, not the LangGraph checkpointer

**Context:** `decisions/03-langgraph-for-ask-agent.md` anticipated exactly this feature —
*"Turning checkpointing on later — for genuine multi-turn 'Ask thread' continuity, if and when
that's actually requested — is a configuration change... not a rewrite."* That decision assumed
a **Postgres-backed** checkpointer for durable, cross-session continuity.

**Decision:** Do **not** turn on LangGraph's checkpointer for this feature. Instead, the frontend
(which must already hold the full transcript to render it — Decision 1) resends the last 5 turns
verbatim as part of each `POST /api/ask` request body; the backend stays stateless between
requests, exactly as `LangGraphAskAgent.answer()` is today, just with one new optional parameter.

**Rationale:** spec.md's resolved clarifications scope memory to *session-only, last 5 turns, no
cross-reload/cross-device persistence*. A Postgres-backed checkpointer solves a harder problem
(durable, resumable-after-restart continuity) than this feature asks for, and introduces
concerns this feature doesn't need: a `thread_id` lifecycle, server-side storage growth, and a
schema migration. An in-memory (`MemorySaver`) checkpointer avoids the migration but still adds
a second, server-side copy of state the client already has, plus its own windowing problem
(LangGraph checkpoints accumulate; nothing built-in enforces "last 5 turns only"). Resending the
client's own transcript is strictly simpler for a requirement this bounded, and keeps
`LangGraphAskAgent` exactly as stateless as `decisions/03-langgraph-for-ask-agent.md` already
documented it to be ("each question answered statelessly") — this feature doesn't need to revisit
that decision, only to pass more context into the same one-shot call.

**Alternatives considered:**
- *Postgres-backed checkpointer* (the decision doc's anticipated path): rejected for now —
  solves for durable/cross-session continuity, which spec.md explicitly says is out of scope.
  Revisit if a future feature asks for conversation history to survive a reload.
- *In-memory (`MemorySaver`) checkpointer keyed by a server-generated thread id*: rejected —
  adds a second source of truth and its own truncation logic for no benefit over the client just
  resending what it already has; also complicates horizontal scaling (a `MemorySaver` is
  per-process, so a second backend worker/replica wouldn't see another worker's threads — a
  concern the client-resend approach doesn't have at all, since there's no server-side thread
  state to be missing).

**Zero Trust note:** per constitution §5 ("the backend MUST NEVER trust frontend validation"),
the backend independently caps accepted history to the 5 most recent entries and bounds the size
of each, regardless of what the client sends — it does not simply trust a client-supplied list to
already be ≤5 items.

## Decision 3 — What "history" carries, and where it's allowed to influence the answer

**Decision:** Each history entry is `{question: str, answer: <verbatim prior /api/ask response
JSON>}` — literally what a previous call already returned, since the frontend already has it
stored for rendering (Decision 1); no new summarization step is invented. On the backend, history
is serialized (code, not a model call — P2/P3) into the **`classify_intent` prompt only**, as
additional context for resolving intent and `subject_hint` (e.g., "that", "who else on that
list"). It is **never** added to the `generate_text` / fact-check prompt.

**Rationale (why generate_text stays untouched):** `_build_verified_facts_from_tool_results`
builds its `VerifiedFactSet` strictly from the *current* turn's freshly fetched
`component_props`. If history text were also fed into `_text_generation_prompt`, the model could
restate an old turn's numbers as if they were newly verified facts, and `fact_check` would
either wrongly pass them (if the old data happens to overlap) or correctly strip them (if not) —
either way, mixing eras of data into one "facts" pool is the exact kind of ambiguity Rule 4 exists
to prevent. Keeping history classify-only preserves the existing fact-check guarantee byte-for-
byte: every generated sentence is still checked only against data fetched for *this* question.

**Prompt-injection note:** history is appended to the classify prompt with the same framing
`_classify_prompt` already uses for the live question — explicitly labeled as data to interpret,
never as instructions to follow (constitution AI safety rule 2, already the pattern for
`question` and `component_props` elsewhere in this file).

## Decision 4 — Greeting/small talk: a pre-classify pattern match, not a model call

**Decision:** A new graph node, `detect_smalltalk`, runs **before** `classify_intent` (i.e., it
becomes the graph's real entry point). It matches the trimmed, lowercased question against a
small fixed set of patterns for three categories — greeting ("hi", "hello", "hey", "good
morning"...), thanks ("thanks", "thank you", "appreciate it"...), and capabilities ("what can you
do", "help", "what can you help with"...) — each mapped to one fixed, pre-written reply string,
matching spec.md's resolved clarification (fixed replies, not model-generated). On a match, the
graph returns immediately with a fallback-shaped result carrying `declined_reason: None` and
skips `classify_intent` (and therefore the LLM call) entirely. On no match, the graph proceeds to
`classify_intent` exactly as it does today — no change to the 8-intent classification behavior,
budget, or the existing generic fallback text for genuinely unrecognized questions.

**Rationale:** Fixed strings are not model output, so they add **no new entry** to constitution AI
safety Rule 1's closed inventory of "where this codebase generates prose" (Narrator, Draft
composer, Ask agent `text_only`/`hybrid`) — no constitution amendment is triggered, unlike a
model-generated greeting would have required. Skipping `classify_intent` for a matched greeting
is strictly *faster* than today's behavior (which already burns a full classify call on "hi" only
to land on `Intent.NONE`), so the existing 2.5s/no-retry resilience budget is left with more
headroom, not less.

**Alternatives considered:**
- *Model-generates the greeting reply* (`text_only`-shaped, reusing the existing
  `generate_text`/fact-check path): rejected per the user's own resolved clarification — adds a
  4th prose-generating location to Rule 1's inventory (a real constitution amendment, precedent
  in this file's own `Sync Impact Report`), plus a second LLM call's worth of latency/cost for
  something a fixed string already serves well.
- *Add a `smalltalk` value to `classify_intent`'s existing closed enum*: rejected — still pays for
  an LLM call on every greeting (no latency win), and `Intent` is REQ-M9-02's fixed 8-intent
  enumeration plus the two decline categories; folding conversational chit-chat into that same
  enum blurs a category that exists for structured-data lookups.

## Decision 5 — Distinguishing a genuine decline from a friendly reply in the UI

**Finding:** Today, `AskFallbackResponse` is used for three different things that all render
identically in `ask-bar.tsx` — a specific decline ("I don't forecast..."), a generic "nothing
matched" fallback, and (as of Decision 4) now also a friendly greeting reply — all captioned
"Fallback answer." Showing that caption under "Hi! I can help you check..." reads as broken,
undermining the very fix spec.md's User Story 3 asks for.

**Decision:** Reuse the existing `declined_reason: DeclinedReason | null` field (`types.ts`
already types it as nullable) as the discriminator: `detect_smalltalk`'s match sets
`declined_reason: null`; every other decline/fallback path is unchanged and keeps a real,
non-null reason. The frontend renders the "Fallback answer" caption only when `declined_reason`
is non-null; a null-reason fallback response renders as a plain conversational turn.

**Rationale:** No new field, no schema/type change (`declined_reason` was already nullable) —
the smallest change that makes the existing envelope tell the two cases apart correctly.

## Decision 6 — Single-flight send is a frontend concern only

**Decision:** "Block sending until ready" (spec.md's resolved clarification) is enforced purely by
disabling the send control while a request is in flight, on the frontend. No backend
concurrency/locking change is needed: the backend already handles one request at a time per call
and has no shared mutable state across requests for a single question. Ordering is guaranteed
because the client physically cannot issue a second request before the first resolves — a
race condition doesn't exist to guard against server-side.

## Data-base impact: none

No table gains a column and no migration is needed. `ask_queries` already logs one row per graph
run with every relevant field nullable (`matched_intent`, `rendered_component`, `declined_reason`
all `NULL`-capable) — a smalltalk-matched turn logs with all three `NULL`, same as today's
generic fallback row, requiring no schema change. Conversation history itself is never persisted
(spec.md: session-only) — there is nothing to store.

## Summary of resolved unknowns

| Area | Resolution |
|---|---|
| Conversation storage | Frontend component state (`AskBar`), not global store, not backend session |
| Multi-turn memory transport | Client resends last-5-turns history per request; backend independently caps at 5 |
| Memory's effect on generation | Classify prompt only; `generate_text`/fact-check untouched |
| Greeting/small talk | Fixed-string pattern match, pre-classify graph node, no LLM call |
| Decline vs. friendly-reply UI | `declined_reason: null` discriminator, already-nullable field |
| Send concurrency | Frontend-only disable-while-pending; no backend change |
| Per-account scoping | Vacuously single — no keying infrastructure built (P10) |
| Schema/migration | None required |
