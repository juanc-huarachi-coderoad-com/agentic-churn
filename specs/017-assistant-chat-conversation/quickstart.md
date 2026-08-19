# Quickstart: Assistant Chat Conversation

Validation guide for `specs/017-assistant-chat-conversation`. Assumes the existing dev setup
already documented for this repo (backend `uvicorn`, frontend `vite`, Postgres running) — nothing
new to provision (`research.md`: no migration, no new service).

## 1. Backend: history-aware classify + small-talk fast path

Run the Ask agent's existing test suite plus the new cases this feature adds:

```bash
cd backend
pytest tests/experience/test_ask_agent_graph.py -v
```

Expected new/updated cases (see `data-model.md` and `contracts/ask.md`):

- A question matching a greeting pattern ("hi", "hello") returns a fallback-shaped result with
  `declined_reason=None` and a fixed reply string, **without** the fake `LLMPort`'s classify call
  ever being invoked (assert the fake's call count, matching the existing `_FakeLLM` pattern
  already used in this file).
- A question matching thanks/capabilities patterns likewise returns their own fixed reply,
  `declined_reason=None`.
- A question that does *not* match any small-talk pattern still reaches `classify_intent`
  unchanged — existing per-intent tests keep passing as-is.
- `AskAgentState["history"]` populated with 1–5 prior turns changes what `classify_intent`'s
  fake `LLMPort` receives as its prompt (assert the prompt text includes the prior question), but
  does **not** change what `generate_text`'s fake receives (assert it's unaffected by `history`
  being present) — the Decision 3 boundary.
- `history` longer than 5 entries is truncated to the 5 most recent before reaching the prompt.

Manually, with the backend running:

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "hi"}'
# Expect: {"fallback_text": "...", "sources": [], "declined_reason": null}

curl -X POST http://localhost:8000/api/ask \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "question": "what about last quarter?",
    "history": [{"question": "why did the score drop?", "answer": {"intent": "score_delta", "parts": [{"type":"component","component":"delta_breakdown","component_props":{"score":61.0,"band":"at_risk","causes":[]}}]}}]
  }'
# Expect: an answer that reflects "last quarter" being a follow-up to the score-delta question,
# not a generic/unclear-intent fallback.
```

## 2. Frontend: transcript, input clearing, mixed content per turn

```bash
cd frontend
npx vitest run src/ask
```

Expected new/updated cases in `ask-bar.test.tsx` (see `spec.md` User Stories 1–3, 5):

- Sending a first question appends a `Turn` to the transcript; sending a second question appends
  a second `Turn` **below** the first — both remain queryable in the DOM simultaneously (today's
  test only ever asserts on the single latest exchange; this changes to asserting on both).
- The input value is asserted empty **immediately** after submit (synchronously, not just
  eventually) — the literal complaint in `spec.md`'s Input section.
- The send button is `disabled` while a turn is `'pending'`, and re-enabled the instant it
  resolves — assert this using the existing `resolveFetch`-deferred-promise pattern already in
  this test file.
- A response with `declined_reason: null` renders **without** the "Fallback answer" caption; a
  response with a non-null `declined_reason` (e.g. `"prediction"`, the existing test case) still
  shows it — both cases covered side by side.
- Two turns, each with different `parts` (one `component_only`, one with a `text` + `component`
  pair), both render correctly and independently when both are present in the transcript at once
  (`AnswerRenderer` invoked once per answered `Turn`).

Manually, in the browser:

1. Open the dashboard, and in the assistant panel type `hi`, press Enter/click Ask.
   - **Expect:** input clears immediately; "hi" appears as your turn; the reply is a friendly
     greeting, not "I don't have a way to answer that yet."
2. Ask a real question (e.g. "why did the score change?"); wait for the answer.
3. Ask a follow-up that only makes sense given the first answer (e.g. "what about last quarter?"
   or "who else is on that list?" if the first answer named people).
   - **Expect:** both exchanges are visible, scrolled naturally; the follow-up's answer reflects
     the earlier context.
4. While a question is still "Thinking…", try to send another.
   - **Expect:** the send control stays disabled until the current answer lands, then re-enables
     immediately; nothing is lost or overwritten.
5. Send an empty message (just spaces).
   - **Expect:** nothing is added to the transcript, input untouched.

## Traceability

Exercises `spec.md` SC-001 through SC-006. Full behavioral detail: `data-model.md`,
`contracts/ask.md`, `research.md`.
