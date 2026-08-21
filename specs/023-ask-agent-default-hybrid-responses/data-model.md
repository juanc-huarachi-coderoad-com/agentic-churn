# Phase 1 Data Model: Ask Agent Default Hybrid Responses

This feature changes one existing internal enum's value set and one default. It adds
no new entity, no new field, no new table/column, and no change to any existing
entity's shape.

## `ResponseMode` (internal, `ask_agent_graph.py`)

| Before (specs/014) | After (this feature) |
|---|---|
| `COMPONENT_ONLY = "component_only"` | *(removed)* |
| `TEXT_ONLY = "text_only"` | `TEXT_ONLY = "text_only"` (unchanged meaning) |
| `HYBRID = "hybrid"` | `HYBRID = "hybrid"` (unchanged meaning; now the default) |

- **Owner**: `backend/app/experience/adapters/ask_agent_graph.py` (Adapters ring,
  M9/Ask-agent module) — not a domain entity, not persisted as a DB enum.
- **Default**: `ClassifyOutput.response_mode` changes from `ResponseMode.COMPONENT_ONLY`
  to `ResponseMode.HYBRID`.
- **Meaning of the two surviving values, unchanged from `014`**:
  - `text_only`: the question is conversational/explanatory in a way no visual would
    suit; the response is exactly one `TextPart`, no component.
  - `hybrid`: the question resolves to one of the 8 structured intents; the response
    is a `TextPart` followed by a `ComponentPart` when text generation succeeds, or
    just the `ComponentPart` alone if text generation fails/times out (unchanged
    graceful-degradation behavior — see Edge Cases in spec.md).
- **Not affected**: `write_to_stakeholder` never produces a `ResponseMode` value at
  all (it routes to `handoff`, which never reaches the classify/render/generate-text
  path that sets this field) — unchanged from `014`.

## `ask_queries.response_mode` (persisted, PostgreSQL)

- **Column**: unchanged — `TEXT`, nullable, additive (migration
  `0005_ask_queries_response_mode.py`). No new migration needed.
- **Value population**: unchanged mechanism — populated for every answered
  (component-bearing) query, `NULL` for decline/fallback, mirroring the existing
  `rendered_component` convention. Going forward, the value logged is one of
  `"text_only"` or `"hybrid"` (or, in the rare full-degradation case where a `hybrid`
  intent's text generation fails, the log still records `"hybrid"` as the *decided*
  mode — matching `014`'s existing precedent that the log records the decision made,
  not the parts that happened to survive fact-checking).
- **Historical rows**: existing rows with `response_mode = "component_only"` are left
  untouched — valid history of a mode that existed before this feature shipped, same
  treatment this column already gives to any other value change over time.

## `AskAgentResult` / `ResponsePart` (`entities.py`, `ports.py`)

No change. `TextPart`/`ComponentPart`/`ResponsePart` (the ordered-parts union) and
`AskAgentResult`'s shape are exactly as `014` defined them — this feature changes
*which* combination of parts gets produced for a given question, never the shape of
a part or the result object itself.

## API response schema (`ask_router.py`)

No change. `AskAnsweredResponse` exposes only `intent` and `parts` — it has never
exposed `response_mode` as a public field (confirmed by direct reading of the
schema). The enum collapse is entirely invisible to API consumers; see
`contracts/ask.md` for the (non-)impact on the wire format.
