# Implementation Plan: Aura Orb Heartbeat Redesign

**Branch**: `020-aura-orb-heartbeat` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/020-aura-orb-heartbeat/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Redesign `AuraRiskOrb` (`frontend/src/dashboard/aura-risk-orb.tsx`) from a flat gradient
circle with a printed score number into a glossy, glowing sphere (matching the reference
`base/aura.png` look) that continuously animates a slow, elegant "heartbeat" pulse and no
longer displays the numeric score. Color remains the orb's only score-derived signal, driven
by the existing `band`→color mapping (`band-colors.ts`) — unchanged. Purely a frontend
presentation change: no new dependencies, no backend/API changes, no new data.

## Technical Context

**Language/Version**: TypeScript ~6.0.2, React 18.3.1 (existing `frontend/` app, unchanged)

**Primary Dependencies**: Tailwind CSS v4 (`@tailwindcss/vite`, CSS-first `@theme` config in
`frontend/src/index.css`) — no new npm dependency added. No animation library (e.g.
framer-motion) is installed or needed; Tailwind v4's native `--animate-*` theme variables
cover this animation (see research.md Decision 1).

**Storage**: N/A — presentation-only change, no data model changes

**Testing**: Vitest + `@testing-library/react` (existing pattern in
`aura-risk-orb.test.tsx`)

**Target Platform**: Web browser — existing dashboard SPA, no new platform

**Project Type**: Web application — frontend-only change within the existing `frontend/`
package; no backend touched

**Performance Goals**: Animation runs smoothly (no visible jank) as a GPU-friendly CSS
transform/opacity animation, not a JS-driven re-render loop

**Constraints**: No new npm dependencies (constitution P11 / Full-Stack Engineering §2:
closed Tailwind/shadcn/lucide-react/Recharts choices, no ad hoc styling libraries); must
respect `prefers-reduced-motion` (FR-006); color must not become the *only* signal of risk
band anywhere on screen — verified against `dashboard-page.tsx`, where `ChurnRiskOverviewCard`
(via `ScoreBlock`) already renders the numeric score and a text band pill on the same page
(research.md Decision 4)

**Scale/Scope**: Single component (`aura-risk-orb.tsx`), its test file, and the shared
Tailwind entry stylesheet (`index.css`) for the new keyframe registration; no other files
change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P6 — Silence Is a Success State**: The pulse animation is uniform across all three bands
  (only color differs); it does not manufacture extra visual urgency for `at_risk` beyond
  its existing color, and a `healthy` orb still reads as calm. **PASS.**
- **P11 / Full-Stack Engineering §2 — Frontend, UI & Styling**: Uses only Tailwind CSS
  (v4 CSS-first `@theme` keyframes) — no new component/animation/icon library. **PASS.**
- **P11 — Accessibility, color not the only indicator of state**: The orb itself becomes
  color-only after the score text is removed, but the *system* still exposes the band via
  text elsewhere on the same dashboard view (`ScoreBlock`'s band pill and numeric score in
  `ChurnRiskOverviewCard`, `dashboard-page.tsx:183-186`) — the orb was never the sole band
  indicator. **PASS**, documented as an explicit design constraint, not a gap.
- **P11 — Testing**: `aura-risk-orb.test.tsx` will be updated to assert the new contract
  (no score text, color still band-driven, animation class present) as part of this
  feature's tasks — unit/component coverage per Definition of Done. **PASS (planned).**
- **P10 — YAGNI**: No new abstraction, prop, or component introduced; `score` prop is
  dropped from `AuraRiskOrbProps` because it becomes fully unused once display text is
  removed (color was already `band`-only) — see research.md Decision 4. **PASS.**
- **P1–P5, P8, P9 (scoring/ledger/evidence/clean-architecture gates)**: Not applicable —
  no backend, scoring, or domain code is touched by this feature.

No violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/020-aura-orb-heartbeat/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── index.css                        # Tailwind v4 entry point — add the
│   │                                     # --animate-aura-pulse @theme keyframe
│   │                                     # here (research.md Decision 1)
│   └── dashboard/
│       ├── aura-risk-orb.tsx             # component being redesigned
│       ├── aura-risk-orb.test.tsx        # existing tests, updated for the new
│       │                                 # contract (no score text, animation
│       │                                 # class, dropped `score` prop)
│       ├── band-colors.ts                # existing band→color map — reused,
│       │                                 # unchanged
│       └── dashboard-page.tsx            # existing consumer — update the one
│                                          # call site to drop the `score` prop
```

No backend, API, or database changes. No new files/directories beyond what's listed above.

**Structure Decision**: Single existing web application (`frontend/`) — this feature edits
one presentation component, its test file, and the shared Tailwind stylesheet in place. No
new project, package, or top-level directory is introduced.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
