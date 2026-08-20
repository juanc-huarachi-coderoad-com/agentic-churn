# Quickstart: Chat Component Sender Identification Redesign

Validates the redesigned `AskBar`/`TurnView` chat rendering end-to-end. No backend change is
involved — the assistant's answer is whatever `/api/ask` already returns (mocked in tests, live in
manual verification).

## Prerequisites

- Repo checked out on `021-chat-component-redesign` (or wherever this feature is implemented).
- Frontend dependencies installed: `cd frontend && npm install` (no new dependency added by this
  feature — `lucide-react` is already a dependency).

## Automated validation

```bash
cd frontend
npm test -- ask-bar          # Vitest, runs the extended ask-bar.test.tsx suite
npm run typecheck            # confirms the extended Turn type has no `any`, strict TS holds
npm run lint                 # confirms Tailwind/lucide-react-only usage, no stray CSS
```

**Expected outcome**: all pass. The extended `ask-bar.test.tsx` covers (see spec Acceptance
Scenarios):
- A human question renders a `User` icon, the "Human" label, and a 12-hour `AM/PM` timestamp.
- An assistant answer renders the "AURA Assistant" label, a 12-hour `AM/PM` timestamp, and a
  `Sparkles` icon, mirrored (right-aligned) relative to the human row.
- A pending turn (`status: 'pending'`) shows no sender icon/label/timestamp for the answer side —
  only the existing "Thinking…" indicator.
- An error turn (`status: 'error'`) shows no sender icon/label/timestamp for the answer side —
  only the existing error message.
- Multiple turns in sequence each carry their own independent sender identity (order-independent).

## Manual validation (visual)

1. `cd frontend && npm run dev`, open the dashboard, locate the AURA Assistant panel (column 1).
2. Type a question and submit it.
   - **Expect**: the question immediately shows a person icon + "Human" + a timestamp
     (e.g., "10:47 AM"), left-aligned, before the assistant responds.
3. Wait for the answer.
   - **Expect**: the answer shows a timestamp + "AURA Assistant" + a sparkle icon, right-aligned —
     mirroring the question's row layout, matching `base/chatComponent.jpg`.
4. Ask a second question and compare both turns.
   - **Expect**: identical treatment on both turns; timestamps differ and reflect actual send/
     receive order; no date is shown, only time.
5. Temporarily simulate a network failure (e.g., devtools offline) and submit a question.
   - **Expect**: the question still shows its sender identity row; the error message renders with
     no sender icon/label/timestamp attached to it.

## Out of scope for this validation

- Any change to `/api/ask`'s request/response shape (unchanged — see FR-007/FR-008).
- Any other dashboard panel (risk score, evidence trace, etc.) — untouched by this feature.
