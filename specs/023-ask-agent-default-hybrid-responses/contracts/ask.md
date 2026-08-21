# `POST /api/ask` — response contract (specs/023 update)

Supersedes `specs/014-ask-agent-response-formats/contracts/ask.md`'s **mode-inventory
and timing notes only**. The route, request shape, auth, `parts` wire shape, decline/
fallback shape, and fact-checking guarantee are all **unchanged** — see that document
for those; this document covers only what actually changes.

## What does NOT change

- Request shape, auth (`Bearer`, `asked_by_user_id` from token).
- The `parts` array shape: `{"type": "text", "markdown": ...}` or `{"type":
  "component", "component": ..., "component_props": ...}`, in order.
- Decline/fallback shape (`fallback_text`/`sources`/`declined_reason`) — completely
  untouched.
- The fact-checking guarantee — every `text` part's `markdown` is still sentence-level
  fact-checked before being included.
- `write_to_stakeholder` requests: still return exactly `{"intent":
  "write_to_stakeholder", "parts": [{"type": "component", "component":
  "draft_handoff", "component_props": {...}}]}` — no accompanying text part is ever
  added to this intent's response.
- The API schema (`AskAnsweredResponse`) never exposed `response_mode` as a field, so
  there is nothing in the wire format to version — this was always an internal
  implementation detail, not part of the public contract.

## What changes: the answered-case shape distribution

Before this feature, an answered response to one of the 8 structured intents was
*usually* exactly one `component` part (the `component_only` default), and only
*occasionally* a `text` part followed by a `component` part (`hybrid`, when the
question's phrasing happened to trigger it). After this feature, every one of those
8 intents' successful responses is, by default, a `text` part followed by a
`component` part:

```json
{
  "intent": "top_risk",
  "parts": [
    {
      "type": "text",
      "markdown": "The score dropped mainly because of two missed response commitments this week — both to the same stakeholder."
    },
    {
      "type": "component",
      "component": "ranked_issues",
      "component_props": { "ranked_issues": [ /* unchanged shape */ ] }
    }
  ]
}
```

- The `text` part's `markdown` is now capped at 3 sentences (or an equivalently short
  bullet list) and framed as *explaining the component*, not re-answering the
  question from scratch (spec.md FR-002/FR-003) — a wording/length change to the
  prompt that produces it, not a shape change to the response.
- **Graceful degradation, unchanged**: if text generation fails or times out, the
  response falls back to exactly one `component` part — the same shape the retired
  `component_only` mode always produced. A client reading `parts` generically (by
  `type`, not by counting) sees no difference between "degraded hybrid" and the old
  `component_only` default; this is why no client-side change is required.
- **`text_only` is unchanged**: a genuinely conversational question with no matching
  visual still returns exactly one `text` part, same as `014`.

## Timing (updated)

- There is no longer a distinct, common fast path for the 8 structured intents. Every
  successful component-bearing answer now goes through the classify call *and* the
  text-generation call — the same 15s-capped `asyncio.wait_for` budget `014` already
  shipped and the constitution already accepted, just applying to virtually every
  answered request instead of a subset. This is not a new ceiling; see
  `research.md` Decision 1/7 and plan.md's Constitution Check for the full
  before/after accounting, including the required constitution-text follow-up.
- Decline/fallback timing is unchanged — still typically far faster, since neither
  path calls a tool or the text-generation step.

## Logging (updated)

`ask_queries.response_mode` now defaults to `"hybrid"` (was `"component_only"`) for
any component-bearing answered query whose mode wasn't more specifically resolved to
`"text_only"`. No schema change; see `data-model.md`.
