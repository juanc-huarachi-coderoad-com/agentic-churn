# Implementation Plan: Main Dashboard Visual Redesign

**Branch**: `design/apply-new-mockup` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-dashboard-visual-redesign/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Restyle the existing `/dashboard` page to match `base/mockup-mainPage.jpg`: a left navigation sidebar, a central "Signal Stream" timeline, a consolidated "Churn Risk Overview" card with an area-chart trend, an "Action & Draft Hub" list, and the AI assistant converted from an always-present bottom bar into a floating, collapsible widget. This is presentation-layer only — every `useQuery`/`useMutation` call, every prop shape in `frontend/src/dashboard/types.ts`, `ask/types.ts`, and `draft-composer/types.ts`, and every backend endpoint stays byte-for-byte unchanged (FR-011). The technical approach is to restyle existing components in place (same props, same data flow) and compose them into the new layout inside `dashboard-page.tsx`, adding only two new frontend dependencies the constitution already mandates for this work — `recharts` (charts) and `lucide-react` (icons) — plus a small shared `components/ui/` primitive layer to satisfy the existing "Radix-based component system" rule that today has no home in the codebase.

## Technical Context

**Language/Version**: TypeScript ~6.0, React 18.3 (`frontend/package.json`, unchanged)

**Primary Dependencies**: Existing — Vite, Tailwind CSS v4, TanStack Query, Zustand, React Hook Form + Zod, `@radix-ui/react-slot`, `clsx` + `tailwind-merge`. New (constitution v1.3.0-mandated, not previously present) — `recharts` for the Churn Risk Overview area chart, `lucide-react` for all iconography (sidebar icons, notification bell, launcher icon, etc.)

**Storage**: N/A — no data-layer change; the page continues to consume the existing `GET /api/dashboard` response plus the existing Ask/Evidence/Draft-composer endpoints, unmodified

**Testing**: `vitest` + `@testing-library/react` for component tests (existing suites for `dashboard-page`, `narrator-panel`, `ask-bar`, `draft-composer-panel`, `evidence-panel` updated for new markup, asserting rendered content/behavior, not implementation classnames); `@playwright/test` for the layout/floating-assistant end-to-end checks in `quickstart.md`

**Target Platform**: Web SPA (existing), desktop/laptop viewport primary per spec Assumptions

**Project Type**: Web application — existing `frontend/` + `backend/` split; this feature touches `frontend/` only, zero `backend/` changes

**Performance Goals**: No new target introduced by the spec; the redesign must not regress the existing dashboard's load/interaction responsiveness (informal — no NFR was specified, flagged as low-impact/deferred in `/speckit-clarify`)

**Constraints**: Zero changes to state management, API calls, or data structures — `frontend/src/dashboard/types.ts`, `ask/types.ts`, `draft-composer/types.ts`, `evidence/types.ts`, and every `api.ts` file are read-only for this feature (FR-011, the CRITICAL CONSTRAINT). Icons MUST use `lucide-react`; charts MUST use Recharts; no standard CSS or other component/icon library without approval (constitution, Full-Stack Engineering §2, v1.3.0)

**Scale/Scope**: One page (`dashboard-page.tsx`) and its existing overlays/bar restyled — `ScoreBlock`, `PulseTimeline`, `ContributionBars`, `NarratorPanel`, `StakeholderCards`, `CoverageLine`, `DraftComposerPanel`, `AskBar`, `EvidencePanel` — plus one new component (sidebar) and one new shared primitive layer; no new routes, no new pages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies how | Status |
|---|---|---|
| P1 Evidence or It Does Not Exist | Signal Stream entries keep their existing evidence links (`score_contribution_id` → Evidence panel); nothing about citation is touched | Pass |
| P2 The Model Interprets, Code Calculates | No scoring code touched; frontend-only feature | Pass (N/A) |
| P3 Each Component Refuses to Do the Next One's Job | Priority badges in the Action & Draft Hub are a pure display mapping over already-computed `points`/ranking (see research.md Decision 3), not a new judgment the frontend is making | Pass |
| P4 A Human Always Sends | Action & Draft Hub still only ever opens the existing draft composer for review — no auto-send is introduced anywhere | Pass |
| P5 Admit What We Cannot See | `CoverageLine`/degraded-data indicators are restyled but not removed or weakened (FR-009) | Pass |
| P6 Silence Is a Success State | `healthy_quiet` near-empty state is explicitly preserved as-is by FR-010 — the new layout never renders around it | Pass |
| P8 Clean Architecture — Dependency Rule | N/A to frontend module rings; the feature-oriented split (P11) is what applies here instead, see below | Pass (N/A) |
| P9 Test-First Determinism | N/A — `backend/app/ledger/`, `backend/app/scoring/` untouched; existing frontend tests updated, not weakened | Pass (N/A) |
| P10 Simplicity Over Speculative Generality | The new `components/ui/` layer holds exactly what the mockup's four regions need (card, button, nav item) — not a full generated shadcn kit or a generic design-system framework (research.md Decision 2) | Pass |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | Feature-oriented dirs preserved (`nav/`, `dashboard/`, `ask/` stay separate); server state stays in TanStack Query, no new global state; TypeScript strict; Tailwind + Radix design system | Pass |
| Full-Stack Engineering §2 "UI & Styling" (v1.3.0) | Icons MUST be `lucide-react`, charts MUST be Recharts, no standard CSS/other libs without approval — this is the rule that makes adding `recharts`/`lucide-react` a constitution-approved requirement, not a deviation | Pass — this feature is what the v1.3.0 amendment was written for |

No violations requiring justification. Complexity Tracking table below is intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/012-dashboard-visual-redesign/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory — see research.md Decision 7 (no new external interface is introduced by this feature).

### Source Code (repository root)

```text
frontend/src/
├── nav/                          # NEW — left navigation sidebar (feature-oriented, per P11)
│   ├── sidebar.tsx
│   └── sidebar.test.tsx
├── components/ui/                # NEW — minimal shared design-system primitives (shadcn-style,
│   ├── card.tsx                  #   built on the already-present @radix-ui/react-slot dependency)
│   ├── button.tsx
│   └── icon.tsx                  # thin lucide-react wrapper for consistent sizing/stroke
├── lib/
│   └── utils.ts                  # NEW — cn() class-merge helper (clsx + tailwind-merge, already deps)
├── dashboard/
│   ├── dashboard-page.tsx        # MODIFIED — layout/composition only; useQuery/useState untouched
│   ├── score-block.tsx           # MODIFIED — Sparkline SVG → Recharts AreaChart; same props
│   ├── pulse-timeline.tsx        # MODIFIED — restyled as "Signal Stream"; same props
│   ├── contribution-bars.tsx     # MODIFIED — restyled as risk-driver rows inside the overview card
│   ├── action-draft-hub.tsx      # NEW — built from contribution_bars only (research.md Decision 3/4/8,
│   │                              #   corrected during implementation — narrator.actions has no ID)
│   ├── narrator-panel.tsx        # MODIFIED — repositioned only; same props, same test, unchanged content
│   ├── stakeholder-cards.tsx     # MODIFIED — restyled; same props
│   ├── coverage-line.tsx         # MODIFIED — restyled; same props
│   └── types.ts                  # UNCHANGED
├── draft-composer/
│   ├── draft-composer-panel.tsx  # MODIFIED — restyled; same props, same api.ts
│   └── types.ts                  # UNCHANGED
├── ask/
│   ├── ask-bar.tsx               # MODIFIED — fixed bottom bar → floating launcher + panel; same
│   │                              #   useMutation/api.ts; starts collapsed per FR-007
│   └── types.ts                  # UNCHANGED
└── evidence/
    ├── evidence-panel.tsx        # MODIFIED — restyled only; same props
    └── types.ts                  # UNCHANGED

backend/                          # UNTOUCHED — no files in this directory change for this feature
```

**Structure Decision**: Existing web-application split (`frontend/` + `backend/`) is unchanged. All work is inside `frontend/src/`, organized feature-first per P11: two new feature-oriented directories (`nav/` for the sidebar, `components/ui/` + `lib/` for shared presentation primitives), and in-place restyles of the existing `dashboard/`, `ask/`, `draft-composer/`, and `evidence/` directories. No file moves across feature boundaries, no new routes in `App.tsx`.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

*(no entries — no violations)*
