# `POST /api/ask` — conversation history + small-talk fast path (specs/017)

Supersedes `specs/014-ask-agent-response-formats/contracts/ask.md`'s request section, and adds one
new response variant to the decline/fallback case. The route, auth, and the answered-case `parts`
shape are **unchanged** — see that document (and `specs/008-narrator-and-ask-agent/contracts/
ask.md`) for those; this document covers only what's new.

## Request — gains optional `history`

```json
{
  "question": "what about last quarter?",
  "history": [
    {
      "question": "why did the score drop?",
      "answer": {
        "fallback_text": "I don't have enough data to answer that yet.",
        "sources": [],
        "declined_reason": "unclear"
      }
    }
  ]
}
```

- `history` defaults to `[]` when omitted — existing callers with no history concept keep working
  unchanged.
- Each `history[i].answer` is exactly a prior `/api/ask` response body, resent verbatim (either
  shape — answered or fallback) — the client never summarizes it itself.
- The server independently keeps at most the 5 most recent `history` entries and bounds their
  size, regardless of how many the client sends (Zero Trust — the backend never assumes the
  client already enforced this).
- `history` only ever influences intent/subject resolution (`classify_intent`). It never reaches
  the fact-checked text-generation call — a follow-up answer's `text` part is still verified only
  against data fetched for *that* question, exactly as before this feature.

## Response (200) — decline/fallback case, new `declined_reason: null` variant

```json
{
  "fallback_text": "Hi! I can help with things like why the score changed, who's gone quiet, or what's been promised to this account — ask away.",
  "sources": [],
  "declined_reason": null
}
```

- Shape is otherwise identical to the existing decline/fallback response
  (`specs/008-narrator-and-ask-agent/contracts/ask.md`).
- `declined_reason: null` means this was a recognized greeting/thanks/capabilities message, not a
  decline — the reply is one of a small, fixed set of pre-written strings, never model-generated
  (`research.md` Decision 4). Every other `declined_reason` value (`prediction`,
  `colleague_judgment`, `source_not_connected`, `insufficient_history`, `unclear`) is unchanged in
  meaning and trigger condition.
- Consumers that only ever checked `'parts' in response` to distinguish answered from
  fallback/decline see no shape change — this is still the same `AskFallbackResponse` shape,
  just with one more legal value for a field that was already nullable.

## Timing

- A matched greeting/thanks/capabilities question **skips `classify_intent`'s LLM call entirely**
  — faster than today's behavior for the same input (today, "hi" still pays for a full classify
  call before landing on the generic fallback). The existing 2.5s/no-retry budget is unaffected
  for every other path.
- Every other timing guarantee (`component_only` 2.5s/no-retry; `text_only`/`hybrid`'s 15s
  text-generation cap) is unchanged — `history` adds prompt length to `classify_intent`'s call
  only, not to any latency-budgeted call.

## Fact-checking guarantee (unchanged, restated)

`history` is never a source of verified facts. Every `text` part in an answered response is still
checked only against the `component_props` fetched for the current question — exactly the
guarantee `specs/014-ask-agent-response-formats/contracts/ask.md` already documents, unaffected by
this feature.

## Logging (unchanged)

A matched greeting/thanks/capabilities turn logs one `ask_queries` row like any other, with
`matched_intent`, `rendered_component`, and `declined_reason` all `NULL` — the same shape the
existing generic fallback path already logs. No column is added.

## Traceability

`specs/017-assistant-chat-conversation/spec.md` FR-007 through FR-009, FR-014; `research.md`
Decisions 0–6; `data-model.md`.
