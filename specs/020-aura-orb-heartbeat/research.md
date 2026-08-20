# Phase 0 Research: Aura Orb Heartbeat Redesign

The feature spec left no `[NEEDS CLARIFICATION]` markers, and the Technical Context above
had no open unknowns after inspecting the existing codebase. This document records the
implementation-approach decisions made while resolving Technical Context, per the plan
workflow.

## Decision 1: Animation mechanism — Tailwind v4 CSS-first `@theme` keyframes

**Decision**: Register the pulse as a Tailwind v4 theme animation variable in
`frontend/src/index.css` (the app's single Tailwind entry point):

```css
@theme {
  --animate-aura-pulse: aura-pulse 4s ease-in-out infinite;
  @keyframes aura-pulse {
    /* subtle scale + glow breathing, defined precisely during implementation */
  }
}
```

and apply it to the orb as a `motion-safe:animate-aura-pulse` utility class.

**Rationale**: The constitution's Frontend/UI & Styling rules (P11; Full-Stack Engineering
§2) restrict styling to Tailwind CSS + the approved component/icon/chart libraries, with no
ad hoc styling or unapproved libraries. `frontend/package.json` has no animation library
(e.g. framer-motion) installed, and Tailwind v4's native `--animate-*` theme variables
(confirmed via the current Tailwind docs) are the first-party, zero-dependency way to
register a reusable custom keyframe animation and expose it as a utility class
(`animate-aura-pulse`).

**Alternatives considered**:
- *framer-motion or another animation library* — rejected: not an approved dependency, and
  unnecessary for a single continuous CSS keyframe loop.
- *Inline `<style>` block with raw `@keyframes` scoped to the component* — rejected: bypasses
  Tailwind's theme system, does not compose with existing `motion-safe:`/`motion-reduce:`
  variants as cleanly, and reads as ad hoc styling rather than a themed, reusable utility.

## Decision 2: Reduced motion — Tailwind `motion-safe:` variant, no JS

**Decision**: Gate the animation class with Tailwind's `motion-safe:` variant
(`motion-safe:animate-aura-pulse`), which maps to the `prefers-reduced-motion: no-preference`
media feature. No JavaScript `matchMedia` listener or React state is introduced.

**Rationale**: This directly and declaratively satisfies FR-006 (respect the reduced-motion
preference) using a first-party Tailwind mechanism, confirmed via current Tailwind docs
(`motion-safe`/`motion-reduce` variants exist precisely for this). A JS-based hook would add
runtime state and a re-render path for a purely presentational, CSS-expressible concern —
contrary to P10 (YAGNI).

**Alternatives considered**:
- *`useReducedMotion` hook backed by `window.matchMedia`* — rejected: adds JS complexity and
  a render dependency for something CSS already expresses natively and reactively (it updates
  automatically if the OS preference changes mid-session, same as the CSS variant).

## Decision 3: Glossy sphere visual — layered CSS on the existing color contract

**Decision**: Build the glossy/glow look (highlight, soft outer bloom) with layered CSS
(`radial-gradient` for the highlight/body, `box-shadow` and/or a blurred pseudo-element for
the outer glow), extending the `--orb-color` CSS custom property pattern the component
already uses. No SVG, canvas, or image asset is introduced.

**Rationale**: The current component already derives its entire look from one CSS custom
property (`--orb-color`) driven by `band`; that pattern is proven, requires no new
dependency, and is trivially recolorable per band. `base/aura.png` sets the *aesthetic
target* (per spec.md Assumptions), not a literal asset to embed.

**Alternatives considered**:
- *SVG-based orb* — rejected: more moving parts than needed for a solid, single-color glossy
  sphere; no capability the CSS approach lacks here.
- *Using `base/aura.png` (or per-band variants of it) as an image texture* — rejected: the
  orb's color must stay dynamically tied to the band (FR-002); a static image can't do that
  without maintaining a separate image per band, which is more fragile than one CSS gradient
  driven by one CSS variable.

## Decision 4: Drop the now-unused `score` prop

**Decision**: Remove `score` from `AuraRiskOrbProps` and from the `<AuraRiskOrb>` call site
in `dashboard-page.tsx`. The orb keeps only `band`.

**Rationale**: In the current implementation, `score` is used *exclusively* to render the
number (`{Math.round(score)}`) — color is already derived from `band` alone
(`BAND_CHART_COLOR[band]`), matching FR-002 as-is. Once the score text is removed (FR-003),
`score` has no remaining use inside the component. Keeping an unused prop "for later" would
violate P10 (YAGNI — no speculative surface area). The numeric score itself is not lost to
users: it continues to render on the same dashboard view via `ScoreBlock`
(`ChurnRiskOverviewCard`, `dashboard-page.tsx:183-186`), which is unaffected by this feature.

**Alternatives considered**:
- *Keep `score` as an unused prop "in case it's needed later"* — rejected per P10; nothing in
  the spec calls for it, and an unused prop is dead surface area a reader has to reason about.
