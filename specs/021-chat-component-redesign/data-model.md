# Data Model: Chat Component Sender Identification Redesign

No backend/database entities are introduced or changed (spec Assumptions — presentation-only,
in-memory transcript). The only shape change is to the existing frontend `Turn` type
(`frontend/src/ask/types.ts`), extended per `research.md` Decision 4.

## `Turn` (extended)

One question/answer exchange in the in-memory, session-only transcript
(`specs/017-assistant-chat-conversation`). Existing fields unchanged; two new fields added.

**Entity mapping**: spec.md's Key Entities describe a single-sender "Chat Message" (one sender,
one timestamp, one identity row). At the implementation level, a `Turn` is not itself a Chat
Message — it is the container for exactly two: its `question` (the human's Chat Message,
`questionSentAt`) and, once resolved, its `response`/`error` (the assistant's Chat Message,
`respondedAt`). `TurnView` renders one identity row per Chat Message side, i.e. up to two per
`Turn`, per the validation rule below.

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Unchanged. |
| `question` | `string` | Unchanged. |
| `status` | `'pending' \| 'answered' \| 'error'` | Unchanged. |
| `response` | `AskResponse \| null` | Unchanged. |
| `error` | `string \| null` | Unchanged. |
| `questionSentAt` | `string` (ISO 8601) | **New.** Set once, at `Turn` creation (`handleSubmit`). Never null — a question always has a send time. |
| `respondedAt` | `string \| null` (ISO 8601) | **New.** `null` while `status === 'pending'`. Set exactly when `status` transitions to `'answered'` or `'error'` (`updateTurn`'s `onSuccess`/`onError`). |

**Validation rules**:
- `respondedAt` MUST be `null` if and only if `status === 'pending'` — this is what the rendering
  layer uses to decide whether an answer's sender-identity row (time + label + icon) is shown at
  all (clarified 2026-08-20: pending/error states before completion show no sender identity; once
  `status` is `'error'`, no answer sender row is shown either, since no assistant message was
  actually produced — only the question's own identity row renders for that turn).
- Both fields are ISO 8601 strings (not `Date` objects) — consistent with the rest of the app's
  JSON-serializable state and avoids a `Date` object living in component state.

## `Participant` (conceptual, not a code type)

Not a data entity — a fixed, hardcoded pair of presentation constants used by `TurnView`, matching
the spec's Key Entities section:

| Participant | Icon | Label | Row alignment |
|---|---|---|---|
| Human | `User` (`lucide-react`) | `"Human"` | Left — icon outermost-left, time innermost. |
| AURA Assistant | `Sparkles` (`lucide-react`) | `"AURA Assistant"` | Right — icon outermost-right, time innermost. |

No per-user or per-deployment variation (clarified 2026-08-20: human icon is always the generic
icon, never personalized).

## State transitions (unchanged, timestamp behavior noted)

```
create Turn (status: pending, questionSentAt: now, respondedAt: null)
        │
        ├─ onSuccess → status: answered, respondedAt: now
        └─ onError   → status: error,    respondedAt: now
```

This mirrors the existing `status` transition already implemented in `updateTurn`
(`ask-bar.tsx:53-55`) — no new transition, only an additional field stamped at the same two call
sites (`research.md` Decision 1).
