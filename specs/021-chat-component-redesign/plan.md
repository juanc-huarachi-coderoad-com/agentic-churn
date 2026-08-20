# Implementation Plan: Chat Component Sender Identification Redesign

**Branch**: `021-chat-component-redesign` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-chat-component-redesign/spec.md`

## Summary

`AskBar`'s `TurnView` (`frontend/src/ask/ask-bar.tsx:154-188`) currently renders a human question
as a bare bold paragraph and an assistant answer as an unlabeled bordered box — there is no
per-message icon, sender label, or timestamp, so a reader must infer "who said this" from styling
alone. This feature adds a per-message sender identity row (icon + label + time) to every
completed turn's question and answer, matching `base/chatComponent.jpg`: a generic person icon
+ "Human" label + time for the question, mirrored as time + "AURA Assistant" label + sparkle icon
for the answer, each anchored to its own participant's outer edge. Pending/error turns keep their
existing plain-status rendering unchanged (clarified 2026-08-20 — no sender identity on
not-yet-complete messages). Timestamps are newly captured client-side, at the moment a question is
submitted and at the moment an answer/error resolves, added to the existing in-memory `Turn`
shape — no persistence, no backend change, no new dependency. Purely presentational: `AskBar`'s
state machine, network calls, and every other dashboard component are untouched (FR-007, FR-008).

## Technical Context

**Language/Version**: TypeScript + React 18 (frontend only) — unchanged, no new language/runtime.

**Primary Dependencies**: `lucide-react` (`User` icon, joining the already-used `Sparkles`) via
the existing `Icon` wrapper (`frontend/src/components/ui/icon.tsx`); Tailwind CSS for layout —
both already adopted, no new package.

**Storage**: N/A — timestamps live only in the existing in-memory `Turn` array
(`frontend/src/ask/types.ts`, `research.md` Decision 1 of `specs/017-assistant-chat-conversation`
carried forward); no database, no migration, no persistence beyond the session.

**Testing**: Vitest + Testing Library, extending `frontend/src/ask/ask-bar.test.tsx` — existing
suite and tooling, no new framework.

**Target Platform**: Web — the existing AURA dashboard, modern evergreen browsers.

**Project Type**: Web application (frontend/backend split already in place) — this feature touches
only the frontend, within the existing `frontend/src/ask/` feature folder.

**Performance Goals**: N/A beyond existing — a few additional DOM nodes and one `Date` read per
message; no measurable rendering cost at this feature's scale (a single conversation transcript).

**Constraints**: No change to chat functional behavior (FR-007); no files outside the chat message
list/header touched (FR-008); icons/styling must use `lucide-react` + Tailwind per constitution
P11 (no other icon/CSS library); no personalized avatar, no date label alongside the time, no
sender identity on pending/error turns (2026-08-20 clarifications).

**Scale/Scope**: One feature folder (`frontend/src/ask/`), ~3 files touched
(`ask-bar.tsx`, `types.ts`, `ask-bar.test.tsx`); no backend, no API contract change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P11 / Full-Stack Engineering §2 (UI & Styling)**: icons MUST be `lucide-react`, styling MUST
  be Tailwind + the existing component system — this plan adds `User` from `lucide-react` via the
  existing `Icon` wrapper and Tailwind flex utilities only. **PASS**.
- **P11 (Feature-oriented structure)**: all changes stay inside the existing `frontend/src/ask/`
  feature folder; no new cross-feature shared component is introduced (a per-message sender row is
  small enough to stay a local subcomponent of `TurnView`, not a shared primitive — YAGNI/P10).
  **PASS**.
- **P11 (Type safety)**: `Turn`'s new timestamp fields are added as typed, non-optional `string`
  (ISO 8601) fields on the existing interface — no `any`. **PASS**.
- **P11 (Accessibility)**: sender identity is conveyed via icon + explicit text label, never color
  alone (WCAG, "Color MUST NOT be the only indicator of state"); icons remain `aria-hidden` (as
  today) since the adjacent text label already names the sender. **PASS**.
- **P11 (Testing)**: `ask-bar.test.tsx` (component tests) is extended to cover the new sender
  row's presence, content, and pending/error exclusion — matching the existing test tier for this
  component (no new E2E needed; this is not a business-critical flow change, FR-007). **PASS**.
- **Backend Clean Architecture / AI safety rules / schema discipline**: not applicable — no
  backend code, no LLM call, no schema touched by this feature.

No violations. Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/021-chat-component-redesign/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this feature introduces no external interface (no new/changed API
endpoint, no new public component consumed outside this feature folder) — it is a purely
presentational change to one already-internal component's rendering.

### Source Code (repository root)

```text
frontend/
└── src/
    └── ask/
        ├── ask-bar.tsx        # TurnView gets a new sender-identity row (icon+label+time);
        │                      # handleSubmit/updateTurn start stamping timestamps on Turn
        ├── types.ts           # Turn gains questionSentAt / respondedAt timestamp fields
        └── ask-bar.test.tsx   # component tests extended for the new sender row
```

**Structure Decision**: Web application, frontend/backend split (existing). This feature is
scoped entirely to the existing `frontend/src/ask/` feature folder (Option 2 pattern already in
use for the codebase) — no backend directory, no new top-level frontend folder.

## Complexity Tracking

*No violations — section not applicable.*
