# Phase 1 Data Model: Aura Orb Heartbeat Redesign

This feature introduces no new data entities, storage, or API payloads — it is a
presentation-only change to one existing frontend component. The only "model" affected is
the component's own view-model (its props contract), documented here in lieu of domain
entities.

## View Model: `AuraRiskOrbProps`

| Field   | Type   | Source                                   | Change in this feature |
|---------|--------|-------------------------------------------|-------------------------|
| `band`  | `Band` (`'healthy' \| 'watch' \| 'at_risk'`, from `./types`) | `dashboard-page.tsx` passes `data.score_block.band` | Unchanged — remains the sole driver of the orb's color via `BAND_CHART_COLOR` (`band-colors.ts`) |
| `score` | `number` | `data.score_block.score` | **Removed** (research.md Decision 4) — was display-only, never influenced color, and has no remaining use once the numeric text is removed |

No new fields are added. `Band` and `BAND_CHART_COLOR` are pre-existing and unchanged
(`frontend/src/dashboard/types.ts`, `frontend/src/dashboard/band-colors.ts`).

## Derived presentation state (not props — internal to the component/CSS)

| Concern | Derivation | Notes |
|---|---|---|
| Orb fill/highlight color | `BAND_CHART_COLOR[band]` → `--orb-color` CSS custom property | Unchanged mechanism, already in place |
| Glossy highlight + outer glow | Layered `radial-gradient`/`box-shadow` off `--orb-color` | New visual layer (research.md Decision 3); still purely a function of `band` |
| Pulse animation | `motion-safe:animate-aura-pulse` Tailwind utility, keyframes registered once globally in `index.css` | Not band-dependent — same tempo/amplitude across all bands (Constitution Check, P6) |

No state transitions, validation rules, or persistence apply — the component is a pure
function of `band` on every render.
