# UI Contract: `AuraRiskOrb`

This is the only external interface this feature changes: the public React component
contract for `frontend/src/dashboard/aura-risk-orb.tsx`. There is no network/API contract —
this feature is frontend-presentation-only.

## Props

```ts
interface AuraRiskOrbProps {
  band: Band // 'healthy' | 'watch' | 'at_risk' — from './types'
}
```

- `score` is **removed** from this interface (research.md Decision 4). Callers must stop
  passing it. The one existing call site, `frontend/src/dashboard/dashboard-page.tsx`, is
  updated as part of this feature to pass only `band`.

## Rendered output contract

- Root element keeps `data-testid="aura-risk-orb"` (existing consumers/tests rely on this).
- Root element's color is driven by a `--orb-color` CSS custom property set from
  `BAND_CHART_COLOR[band]` (unchanged mechanism).
- **No numeric text node** (score digits or otherwise) is rendered anywhere inside the
  component (FR-003).
- A continuous CSS pulse animation is applied via a Tailwind utility class
  (`motion-safe:animate-aura-pulse` or equivalent), gated by `prefers-reduced-motion` so it
  is absent/inert when the user has requested reduced motion (FR-006).
- The animation utility/class and the glow/highlight layers must not vary by `band` in
  tempo or amplitude — only color varies (FR-007, Constitution Check P6).
- The component remains fully responsive: it fills its parent's `aspect-square` box (as
  today) without the glow or animation clipping into, or overflowing, sibling layout (FR-008).

## Consumer contract

- `dashboard-page.tsx` renders `<AuraRiskOrb band={data.score_block.band} />` when
  `data.score_block` is present — same conditional guard as today, `score` argument dropped.
- No other consumer exists in the codebase today.

## Test contract (`aura-risk-orb.test.tsx`)

Existing assertions that must be removed (they test behavior this feature deliberately
removes):
- `renders the given score` (asserts `screen.getByText('65')`)
- `rounds a fractional score for display` (asserts `screen.getByText('66')`)

Existing assertions that must be preserved (still valid post-redesign):
- `colors the orb from BAND_CHART_COLOR for band %s` — `--orb-color` custom property still
  reflects `BAND_CHART_COLOR[band]` for each band.
- `changes color across different bands` — re-rendering with a different `band` still
  changes `--orb-color`.

New assertions this feature must add:
- No numeric text is present in the rendered orb for any band (guards FR-003 regressions).
- The animation utility class (e.g. `animate-aura-pulse`) is present on the orb root
  regardless of band (guards FR-004/FR-007).
