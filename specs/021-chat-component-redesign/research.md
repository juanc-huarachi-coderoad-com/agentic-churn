# Research: Chat Component Sender Identification Redesign

All `[NEEDS CLARIFICATION]` items were resolved during `/speckit-clarify` (see spec.md
Clarifications, session 2026-08-20: time format, human icon personalization, pending/error
state treatment, date display). No open unknowns remain in Technical Context. This document
records the concrete design decisions needed to translate the spec into an implementation,
derived from `base/chatComponent.jpg` and the existing `AskBar`/`TurnView` code.

## Decision 1: Where timestamps are captured

**Decision**: Stamp a question's timestamp at the moment `handleSubmit` creates its `Turn`
(`ask-bar.tsx:68-71`), and stamp the answer's timestamp inside `updateTurn` when the mutation's
`onSuccess`/`onError` callback fires (`ask-bar.tsx:77-83`). Both use `new Date().toISOString()`,
formatted for display with `Intl.DateTimeFormat` (`hour: 'numeric', minute: '2-digit', hour12:
true`) to produce the "10:32 AM" style required by the clarified FR-003.

**Rationale**: These are the only two points in the existing code where a message's content
becomes final — reusing them avoids adding any new state machine or effect. No backend call is
involved, so the timestamp reflects local client time, which is sufficient for a single-session,
non-persisted transcript (spec Assumptions).

**Alternatives considered**: Timestamp inside `TurnView` at render time — rejected, because a
turn can re-render multiple times (pending → answered) and would produce a different, wrong
"sent at" time on each render instead of the true send/receive moment.

## Decision 2: Layout of the sender-identity row (icon + label + time)

**Decision**: Each identity row is a single flex line. For the human question: `[User icon]
["Human" label] [time]`, block left-aligned (icon nearest the left/outer edge, time nearest the
message body/center). For the assistant answer: `[time] ["AURA Assistant" label] [Sparkles
icon]`, block right-aligned (icon nearest the right/outer edge, time nearest the center) — the
mirror image of the human row. This reproduces `base/chatComponent.jpg`, where both rows read
icon-outermost, time-innermost from each participant's own edge inward, and satisfies FR-004
("timestamp placed toward the outer edge... human timestamp aligned outward on the human's side,
assistant timestamp aligned outward on the assistant's side") together with the spec's "uniform"
requirement — the same relative ordering rule (icon→label→time, outer→inner) applies to both
sides, just mirrored.

**Rationale**: A single `justify-between` row containing two inline groups (or two rows, each
individually flush left/right) is the simplest Tailwind construct that reproduces the image
without introducing a new shared layout primitive (P10/YAGNI) — `TurnView` is already the only
place both message types are rendered.

**Alternatives considered**: Two-column grid — rejected as unnecessary complexity for what is a
one-row-per-message label; identical label/time order on both sides (not mirrored) — rejected,
does not match the reference image and reads as backwards on the assistant's (right) side.

## Decision 3: Icon choice

**Decision**: `User` from `lucide-react` for the human (new import), `Sparkles` from
`lucide-react` for the assistant (already imported and used in the header, `ask-bar.tsx:2,94`),
both rendered through the existing `Icon` wrapper (`frontend/src/components/ui/icon.tsx`) with
`aria-hidden` (default), since the adjacent text label already names the sender for assistive
tech.

**Rationale**: Matches the reference image's generic filled-circle person icon and sparkle icon
closely enough within the constitution's closed icon library (`lucide-react` only, P11); reusing
`Icon` keeps stroke width/sizing consistent with the rest of the app instead of a one-off SVG.

**Alternatives considered**: A custom circular-avatar SVG matching the image's filled purple
circle pixel-for-pixel — rejected; the constitution's own reference image needn't be reproduced
pixel-exactly (spec Assumptions: "exact pixel values... follow the existing AURA design system
where the image does not specify precise values"), and a closed icon library is a non-negotiable
constraint (P11) that a custom SVG would sidestep without approval.

## Decision 4: `Turn` shape change

**Decision**: Add two fields to `Turn` (`frontend/src/ask/types.ts:61-67`):
`questionSentAt: string` (ISO 8601, set at creation, never null) and `respondedAt: string | null`
(ISO 8601, `null` while `status === 'pending'`, set once `status` becomes `'answered'` or
`'error'`). No changes to `HistoryTurn` — history resent to the backend does not need timestamps
(the backend never uses them; spec scope is presentation-only, FR-007/FR-008).

**Rationale**: Matches the existing `status`-driven pattern already used for `response`/`error`
(non-null only once resolved) — consistent, typed, no `any`, and keeps the "pending/error turns
show no timestamp" clarification enforceable directly from the type (`respondedAt` is `null`
exactly when there is nothing to display).

**Alternatives considered**: A single `timestamp` field reused for both question and answer —
rejected, a question and its answer are sent at different moments and both need their own
displayed time per FR-003/FR-004.
