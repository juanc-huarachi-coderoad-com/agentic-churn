# `POST /api/ask` — updated response contract (specs/014)

Supersedes `specs/008-narrator-and-ask-agent/contracts/ask.md`'s response-shape section for the *answered* case only. The route, request shape, auth, and the decline/fallback response are **unchanged** — see that document for those; this document covers only what's new.

## Request (unchanged)

```json
{"question": "why is the score high?"}
```

Bearer-auth required; `asked_by_user_id` from the token, never the body.

## Response (200) — answered case, new shape

```json
{
  "intent": "top_risk",
  "parts": [
    {
      "type": "text",
      "markdown": "The score is high mainly because of two broken response promises this week..."
    },
    {
      "type": "component",
      "component": "ranked_issues",
      "component_props": { "ranked_issues": [ /* unchanged shape */ ] }
    }
  ]
}
```

- `parts` is always present and always has at least one element.
- `parts[i].type` is `"text"` or `"component"` — a discriminated union; `markdown` is present iff `type == "text"`, `component`/`component_props` are present iff `type == "component"`.
- **Backward compatibility guarantee**: when `response_mode` was `component_only` (the default whenever the question is best answered by structured data alone — spec.md FR-002), `parts` is *always* exactly `[{"type": "component", "component": ..., "component_props": ...}]`, with `component`/`component_props` values byte-identical to what the old `AskComponentResponse.component`/`.component_props` fields would have returned. Any consumer that only ever read `parts[0]` when `parts.length === 1 && parts[0].type === "component"` sees no behavior change.
- Order within `parts` reflects generation order (a `text` part before a `component` part means the explanation was written to be read first) — the frontend renders parts in list order, no reordering.

## Response (200) — decline/fallback case (UNCHANGED)

```json
{
  "fallback_text": "I don't make judgments or character assessments about people — only what the evidence shows.",
  "sources": [],
  "declined_reason": "colleague_judgment"
}
```

Identical to `specs/008-narrator-and-ask-agent/contracts/ask.md` — no field, value, or trigger condition changes. The 5 `declined_reason` values and their trigger conditions are unchanged.

## Timing

- **`component_only` responses**: unchanged — 2.5s classify budget, no retry, 3s total (REQ-M9-08), exactly as today.
- **`text_only`/`hybrid` responses**: the text-generation call is hard-capped at 15s via `asyncio.wait_for` (research.md Decision 3, revised during implementation from an original 8s target after live-testing against the real model showed that number was consistently too tight — see Decision 3 for the full account, including why the answer is deliberately kept short). If the text-generation call fails or times out after `component_props` was already fetched successfully, the response silently degrades to a `component_only`-shaped `parts` list (one `component` part, no `text` part) — never a partial or corrupted Markdown fragment.
- **Decline/fallback**: unchanged — typically far faster since neither calls a tool.

## Fact-checking guarantee (new)

Every `text` part's `markdown` has already passed a mechanical, sentence-level fact-check (research.md Decision 4) before this response is ever constructed: every number, name, and date-like token in each sentence outside a fenced code block has been verified against the same structured data (`component_props`) generated for that intent. A sentence that fails is silently omitted from `markdown` — this route never returns a `text` part containing an unverified claim, and never returns a `text` part that is empty-after-filtering with no visible content (if every sentence fails, that `text` part is omitted from `parts` entirely, leaving only the `component` part(s), if any; if the whole response would otherwise have zero parts, it falls back to the decline/fallback shape instead of returning an empty answer).

## Logging (extended)

`ask_queries` gains a `response_mode` column (`component_only | text_only | hybrid`, nullable — `NULL` for decline/fallback rows). Every other logged field is unchanged in meaning.

## A guarantee this route still depends on

Unchanged from `specs/008-.../contracts/ask.md`: every finding-lookup answer (component or text) is backed by a `status = 'validated'`-filtered read — a quarantined finding remains structurally unreachable through `/api/ask`, in either response format.

## Traceability

`specs/014-ask-agent-response-formats/spec.md` FR-001 through FR-013; `research.md` Decisions 1–8; `data-model.md`; `.specify/memory/constitution.md` v1.4.0 (AI Safety Rules 1/4 amendment); `architecture/04-ai-safety-and-model-usage.md` and `architecture/06-error-handling.md` (model-call inventory and resilience-budget amendments).
