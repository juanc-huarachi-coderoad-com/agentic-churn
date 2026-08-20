# Quickstart: Validating the Aura Orb Heartbeat Redesign

## Prerequisites

- `frontend/` dependencies installed (`npm install` in `frontend/`, if not already done)
- Reference image for visual comparison: `base/aura.png`

## Run the automated checks

From `frontend/`:

```sh
npm run typecheck   # TypeScript, strict — no `any` (constitution: Code Quality)
npm run lint
npm run test         # Vitest — see contracts/aura-risk-orb-component.md for the
                      # expected assertions in aura-risk-orb.test.tsx
```

All three must pass before this feature is considered done (Definition of Done, P11 /
Full-Stack Engineering §1).

## Validate visually in the running app

1. `npm run dev` from `frontend/` and open the dashboard for any client.
2. Locate the Aura orb in Column 1 (`data-testid="aura-risk-orb"`, next to the client name /
   days-to-renewal header, above the Ask bar) — see `dashboard-page.tsx`.
3. Confirm against `base/aura.png`:
   - Glossy sphere look: soft bright highlight, gentle outer glow/bloom, no flat/banded
     gradient edge.
   - No number is printed on or over the orb.
   - The orb continuously, gently pulses (slow scale and/or glow "breathing") without any
     interaction — watch for at least one full cycle (a few seconds).
4. Confirm the numeric score is still visible elsewhere on the same page: the
   `ChurnRiskOverviewCard` score block (large number + band pill) further down the page —
   this is what makes removing the number from the orb safe (research.md Decision 4).
5. Switch bands to compare: use different client records (or temporarily edit fixture/mock
   data for `score_block.band`) to view `healthy`, `watch`, and `at_risk` — confirm only the
   orb's color changes; the glow style and pulse tempo/amplitude stay identical across bands
   (FR-007).

## Validate reduced motion (FR-006)

In Chrome DevTools:

1. Open the Command Menu (Cmd/Ctrl+Shift+P) → "Show Rendering" → enable the "Rendering" tab.
2. Set **Emulate CSS media feature `prefers-reduced-motion`** to `reduce`.
3. Reload the dashboard. Confirm the orb's pulse animation is paused or not applied, while
   the orb itself still renders correctly (glow, color, no number).
4. Reset the emulation to `no-preference` (or "No emulation") and confirm the pulse resumes.

## Validate responsiveness (FR-008)

Resize the browser window (or use DevTools device toolbar) across a few widths and confirm
the orb's glow/highlight scale with it and never clip into or overflow the surrounding
Column 1 layout.
