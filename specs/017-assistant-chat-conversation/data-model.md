# Data Model: Assistant Chat Conversation

No database table is added, changed, or migrated by this feature (`research.md`, "Data-base
impact: none"). Everything below is either **frontend, in-memory, component-scoped state** or a
**wire-format addition** to the existing `POST /api/ask` contract. Where an entity below
corresponds to a `spec.md` Key Entity, its name is unchanged from the spec for traceability.

## Frontend entities (in-memory, `AskBar` component state only)

### Conversation

The whole transcript for the current working session. Not persisted; exists only as long as
`AskBar` stays mounted (`research.md` Decision 1). There is exactly one `Conversation` — no
account key (`research.md` Decision 0).

| Field | Type | Notes |
|---|---|---|
| `turns` | `Turn[]` | Ordered oldest → newest; append-only during a session |

### Turn

One question/answer exchange.

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Client-generated (e.g. `crypto.randomUUID()`), stable React list key |
| `question` | `string` | The exact text the user sent, trimmed |
| `status` | `'pending' \| 'answered' \| 'error'` | `'pending'` from send until a response or error resolves it |
| `response` | `AskResponse \| null` | Set when `status === 'answered'`; the exact `POST /api/ask` response body |
| `error` | `string \| null` | Set when `status === 'error'`; a user-facing message, not a raw exception |

**State transitions:** `pending → answered` (response received) or `pending → error` (request
failed/timed out). Terminal once `answered` or `error` — a turn is never mutated again after that
(a retry, if ever added, would be a new `Turn`, not a resurrection of an old one — out of scope
here; spec.md only requires the user can keep asking afterward, not that the failed turn itself
becomes retriable).

**Validation rule (FR-006):** a `Turn` is only ever created for non-empty, non-whitespace-only
`question` text — enforced before append, not after.

**Send-gating rule (FR-014, `research.md` Decision 6):** the send control is disabled whenever any
`Turn` in `turns` has `status === 'pending'` — since sending is single-flight, this is equivalently
"disabled while the most recent turn is pending."

### Content Piece

Not a separate stored entity — it is however many entries `response.parts` already has
(`ResponsePart` from `frontend/src/ask/types.ts`, unchanged by this feature). Listed here only
because `spec.md`'s Key Entities section names it: each `Turn.response`'s `parts` array (when
`response` is an `AskAnsweredResponse`) is rendered by the existing `AnswerRenderer`, once per
`Turn`, instead of once for a single latest answer (`research.md` — Decision 1's consequence,
implementation detail in `plan.md` Project Structure).

## Wire-format addition: `POST /api/ask` request

Existing `AskRequest` (`backend/app/experience/adapters/ask_router.py`) gains one optional field;
everything else about the request is unchanged.

```jsonc
{
  "question": "what about last quarter?",
  "history": [
    { "question": "why did the score drop?", "answer": { /* prior response body, verbatim */ } }
    // ...up to 5 entries, oldest first
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `history` | `HistoryTurn[]` | Defaults to `[]`. Each `answer` is exactly what a prior `/api/ask` call returned — either an `AskAnsweredResponse` or `AskFallbackResponse` body — resent verbatim, not re-derived. |

**Backend validation (Zero Trust, `research.md` Decision 2):** the server independently truncates
`history` to at most the 5 most recent entries and bounds per-entry size before using it — it does
not trust the client to have already enforced either limit.

**`HistoryTurn` → prompt:** `classify_intent`'s prompt gains a compact, code-serialized (not
LLM-generated) rendering of each accepted history entry — the question text plus a short
representation of the answer (its `fallback_text`, or its `parts`' text/component summary).
`generate_text`'s prompt is unchanged (`research.md` Decision 3) — history never reaches the
fact-checked generation path.

## Backend state addition: `AskAgentState`

`backend/app/experience/application/ports.py`'s `AskAgentState` (`TypedDict`) gains one key:

| Key | Type | Notes |
|---|---|---|
| `history` | `list[dict[str, Any]]` | The validated, truncated history entries, threaded through from the request into the graph's initial state; read only by `classify_intent` |

`AskAgentPort.answer()` gains a corresponding optional parameter:

```python
async def answer(
    self, question: str, *, asked_by_user_id: UUID, history: list[dict[str, Any]] = (),
) -> AskAgentResult: ...
```

## Wire-format addition: `POST /api/ask` response (fallback case)

No field is added. The existing `declined_reason: DeclinedReason | null` (already nullable in
`frontend/src/ask/types.ts`) is now also produced with value `null` by one more path — a matched
greeting/small-talk/capabilities question (`research.md` Decisions 4–5) — distinguishing a
friendly reply from a genuine decline, which the frontend uses to decide whether to show the
"Fallback answer" caption.

## Backend addition: small-talk pattern table

Not a database table — a fixed, in-code mapping (`ask_agent_graph.py`, alongside the existing
`_DECLINE_TEXT` dict), one pre-written reply per matched category:

| Category | Example matches | Reply is fixed, pre-written text |
|---|---|---|
| Greeting | "hi", "hello", "hey", "good morning" | Yes |
| Thanks | "thanks", "thank you", "appreciate it" | Yes |
| Capabilities | "what can you do", "help", "what can you help with" | Yes |
