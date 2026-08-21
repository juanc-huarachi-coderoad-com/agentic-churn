# Quickstart: Validating Ask Agent Default Hybrid Responses

This is a validation guide, not a setup guide — see the repo `README.md` for
environment setup. Requires the backend running (`docker compose up`) with a seeded
account that has active findings across at least a couple of the 8 structured intent
categories (score data, open commitments, at least one stakeholder), plus at least one
stakeholder eligible for a `write_to_stakeholder` draft.

## Validate User Story 1 — visual + short executive text, by default (P1)

1. `POST /api/ask` with a question matching an existing structured intent with no
   special conversational framing, e.g. `"why is the score high?"`.
2. **Expect**: `parts` contains 2 parts — a `text` part followed by a `component`
   part — not just the component alone (contrast with `014`'s prior default).
3. Confirm the `text` part's `markdown` is at most 3 sentences (or an equivalently
   short bullet list) — SC-002 — and reads as an explanation of what the component
   shows or an added insight, not a mechanical restatement of every value already
   visible in `component_props` (FR-003).
4. Confirm every number/name in the `markdown` also appears in the account's real
   underlying data (cross-check against the same `component_props` returned
   alongside it) — the fact-check guarantee from `014`, unchanged and re-verified
   here.
5. Repeat for at least 2 more structured intents (e.g. `"who has gone quiet?"`,
   `"what did we promise them?"`) to confirm the default applies across intents, not
   just one.

## Validate User Story 2 — purely conversational questions stay text-only (P2)

1. `POST /api/ask` with a clearly conversational, explanation-seeking question with
   no natural visual, e.g. `"why does this matter for renewal?"`.
2. **Expect**: `parts` is exactly `[{"type": "text", "markdown": ...}]` — no
   component — unchanged from `014`'s `text_only` behavior (SC-004, zero regression).

## Validate User Story 3 — drafting a message stays draft-only (P3)

1. `POST /api/ask` with a request to draft a message to a specific stakeholder, e.g.
   `"write a message to <stakeholder> about the missed deadline"`.
2. **Expect**: `parts` is exactly one `component` part
   (`component: "draft_handoff"`) — **no accompanying `text` part** — unchanged from
   today's behavior (SC-003, zero regression).

## Validate graceful degradation (unchanged mechanism, now exercised more often)

1. Temporarily force the text-generation call to fail or exceed its 15s budget (e.g.
   a test double / fault injection at the `LLMPort` boundary, not a production
   change).
2. `POST /api/ask` with a structured-intent question under that condition.
3. **Expect**: `parts` is exactly one `component` part — the response still succeeds,
   just without the accompanying text — never a delayed, partial, or corrupted reply
   (FR-007).

## Regression checks

```bash
cd backend
pytest tests/experience/test_ask_agent_graph.py     # updated for the 2-way enum/default
pytest tests/experience/test_ask_agent_latency.py   # updated: no more component_only branch
pytest tests/narrator/                              # fact_check() — imported, not changed;
                                                     # must still pass unmodified
```

No frontend changes are expected — confirm `frontend/src/ask/` regression suite still
passes unmodified as a sanity check that this stayed backend-only:

```bash
cd frontend
pnpm typecheck && pnpm lint && pnpm test
```

## Governance checklist (part of Definition of Done, not optional)

- [X] `.specify/memory/constitution.md` AI Safety Rule 1's response-mode inventory
      sentence updated from `component_only`/`text_only`/`hybrid` to `text_only`/
      `hybrid`, with a version bump (MINOR) and fresh Sync Impact Report, per the
      constitution's own amendment procedure (research.md Decision 7).
- [X] `.specify/memory/constitution.md`'s Resilience budgets paragraph updated to
      retire the `component_only` 2.5s fast-path clause and describe the
      already-shipped 15s-capped text-generation budget as the norm for
      structured-intent answers, not a subset case.
- [X] `architecture/04-ai-safety-and-model-usage.md` / `architecture/06-error-handling.md`
      cross-checked for the same stale `component_only`-as-common-case language, if
      either document independently restates it (grep before considering this item
      done, per this project's own "fix a stale term everywhere it appears" standard).

## Definition of Done

- All three user stories' acceptance scenarios pass, verified against a live backend.
- Graceful degradation still works exactly as before, just triggered more often in
  practice.
- All regression checks pass.
- The governance checklist above is complete.
- `git diff --stat` shows changes confined to
  `backend/app/experience/adapters/ask_agent_graph.py`,
  `backend/tests/experience/test_ask_agent_graph.py`,
  `backend/tests/experience/test_ask_agent_latency.py`, and
  `.specify/memory/constitution.md` (plus any cross-referencing architecture docs
  from the governance checklist) — no change to `backend/app/scoring/`,
  `backend/app/ledger/`, `backend/app/narrator/` (imported, not modified), or any
  `frontend/` file.
