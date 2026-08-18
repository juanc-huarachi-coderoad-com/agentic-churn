# Quickstart: Validating Ask Agent Flexible Response Formats

This is a validation guide, not a setup guide — see the repo `README.md` for environment setup. Requires the backend running (`docker compose up`) with a seeded account that has active findings across at least a couple of the 8 existing intent categories (score data, open commitments, at least one stakeholder).

## Validate User Story 1 — genuine text answer for a conversational question (P1)

1. `POST /api/ask` with a question phrased conversationally but semantically close to an existing intent, e.g. `"why does this matter for renewal?"` or `"what's driving the risk here?"`.
2. **Expect**: `parts` contains at least one `{"type": "text", "markdown": ...}` part with real, readable prose — not a decline, not only a component.
3. Confirm every number/name in the returned `markdown` also appears in the account's real underlying data (cross-check against `GET /api/dashboard` or the same intent's component-only `component_props`) — this is SC-003's zero-unverified-claim guarantee, checked manually here (an automated version lives in `tasks.md`).
4. `POST /api/ask` with a question containing something that reads like an embedded instruction inside a hypothetical quoted client message (use a seeded fixture with such content if available) — confirm the returned `markdown` only ever quotes it as data, never follows it as an instruction (FR-007).

## Validate User Story 2 — structured questions still render as components, unchanged (P2)

1. `POST /api/ask` with a question matching an existing intent with no conversational framing, e.g. `"why is the score high?"`.
2. **Expect**: `parts` is exactly `[{"type": "component", "component": "delta_breakdown", "component_props": {...}}]`, with `component`/`component_props` values identical to what this same question returned before this feature shipped (SC-002 — zero regression). Confirm the frontend still renders it as the same visual component, and that clicking through to evidence still works exactly as before.

## Validate User Story 3 — a hybrid response combines both (P3)

1. `POST /api/ask` with a question whose best answer needs both an explanation and a visual, e.g. `"what's driving the risk and what should I do?"`.
2. **Expect**: `parts` contains 2+ parts, at least one `text` and at least one `component`, in a sensible order.
3. Confirm the `text` part's claims agree with the `component` part's `component_props` values (FR-008 — built from one consistent snapshot) — they should never contradict each other (e.g. a different point value quoted in prose vs. shown in the component).

## Regression checks

```bash
# Backend
cd backend
pytest tests/experience/  # existing Ask agent test suite, extended, not replaced
pytest tests/narrator/    # fact_check() unit tests — must still pass unmodified,
                           # since this feature imports but does not change that module

# Frontend
cd frontend
pnpm typecheck && pnpm lint && pnpm test
```

Specifically confirm:
- `frontend/src/ask/components/answer-renderer.test.tsx` (from specs/013) still passes — the duplicate-`finding_type` key fix is unrelated to this feature and must not regress.
- Every existing `AskComponentResponse`-shaped test fixture continues to work once updated to the new `parts`-wrapped shape (a one-line wrap, per contracts/ask.md's backward-compatibility guarantee).

## Governance checklist (part of Definition of Done, not optional)

- [ ] `.specify/memory/constitution.md` AI Safety Rule 1's component inventory amended to name the Ask agent as a third prose-generating component, with a version bump and Sync Impact Report (per the constitution's own amendment procedure).
- [ ] `architecture/04-ai-safety-and-model-usage.md`'s model-call inventory table updated with the Ask agent's new third output shape.
- [ ] `architecture/06-error-handling.md` gains the new `text_only`/`hybrid` resilience-budget row (research.md Decision 3).
- [ ] `specs/008-narrator-and-ask-agent/contracts/ask.md` gains a pointer to this feature's `contracts/ask.md` as the current source of truth for the answered-response shape (don't leave two contradictory documents both looking authoritative).

## Definition of Done

- All three user stories' acceptance scenarios pass, verified against a live backend.
- All regression checks pass.
- The governance checklist above is complete — this feature is not done at the code level alone, per its own Complexity Tracking justification.
- `git diff --stat` shows changes confined to `backend/app/experience/`, one new `backend/app/experience/domain/entities.py`, one Alembic migration, `frontend/src/ask/`, and the three governance documents named above — no change to `backend/app/scoring/`, `backend/app/ledger/`, or `backend/app/narrator/` (imported, not modified).
