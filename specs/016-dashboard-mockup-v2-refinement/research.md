# Phase 0 Research: Dashboard Mockup V2 Refinement

No `NEEDS CLARIFICATION` markers remain in Technical Context — the three open questions
from `/speckit-specify`/`/speckit-clarify` (signal-type sourcing, icon channel encoding,
`NarratorPanel`/`StakeholderCards`/`CoverageLine` placement) already resolved the
highest-impact product-level ambiguities and are encoded directly in `spec.md`'s
Clarifications, FR-005a, FR-006, and FR-019. What follows are the technical decisions
needed to execute the plan.

## Decision 1: `event_type` is passed through raw; the frontend owns the display mapping

**Decision**: The backend adds `event_type: str` to `PulseEventRecord` → `PulseEventResult`
→ the `PulseEvent` Pydantic schema, populated verbatim from `events.event_type`
(`'message' | 'ticket_state_change' | 'usage_measurement' | 'survey_response' | 'meeting' |
'absence' | 'crm_change'`). No translation, no label, no icon reference crosses the
API boundary. `frontend/src/dashboard/signal-type.ts` owns a closed
`Record<PulseEvent['event_type'], { label: string; icon: LucideIcon }>` map.

**Rationale**: This mirrors exactly how `severity` already works today — the backend
computes/stores a raw classification, and the frontend (`SEVERITY_ICON`/
`SEVERITY_RING_CLASS` in `pulse-timeline.tsx`) owns the visual mapping. Keeping the pattern
identical for `event_type` satisfies P3 (backend doesn't do the frontend's presentation
job) and P7 (no generic scale invented — the real, stored classification is shown, not a
derived one). It also means any future icon/label wording change ships as a frontend-only
change, with no backend deploy.

**Alternatives considered**:
- Backend translates `event_type` directly into a human label (e.g. `"Product Usage"`)
  before sending it — rejected: couples the backend to a presentation concern it has no way
  to also express as an icon choice, and duplicates a mapping the frontend would need
  anyway for the icon; every wording tweak would need a backend deploy.
- Introduce a new backend enum distinct from `events.event_type` scoped to "display
  categories" (e.g. collapsing `meeting`/`absence` into one bucket) — rejected: P10/YAGNI;
  the existing 7-value enum is already closed and specific, and collapsing categories the
  product doesn't ask to collapse would just be an extra layer of indirection with nothing
  behind it.

## Decision 2: One new shared primitive — `components/ui/dialog.tsx`, built on `@radix-ui/react-dialog`

**Decision**: Add `@radix-ui/react-dialog` and a minimal `Dialog`/`DialogContent`/
`DialogOverlay`/`DialogClose` wrapper in `frontend/src/components/ui/dialog.tsx`. Migrate
`EvidencePanel` and `DraftComposerPanel` to render their existing inner content through
`DialogContent` (centered, backdrop-dismissible, focus-trapped, Esc-to-close) instead of
their current hand-rolled `fixed inset-0 z-50 flex justify-end` right-docked `<div>`.

**Rationale**: `@radix-ui/react-slot` has been a dependency since before 012, activated only
when a feature had a real need for it (012's `research.md` Decision 2); `@radix-ui/react-dialog`
is the same story for this feature — the first one whose spec (FR-013, "elegant modal"
replacing a side panel) requires real dialog semantics (focus trap, Esc, backdrop click)
that the current hand-rolled overlay doesn't reliably provide. P11 already names "a
Radix-based component system (shadcn/ui)" as the design system; this activates a primitive
it already licenses, not a new library choice requiring an ADR.

**Alternatives considered**:
- Re-center the existing hand-rolled overlay `<div>` without adopting Radix — rejected:
  FR-016 requires the new modal pattern to at least match today's accessibility behavior,
  and today's overlay has no tested focus-trap or Esc-to-close; hand-rolling that correctly
  is exactly the kind of solved problem a primitive exists to avoid re-solving.
- Run the full shadcn CLI generator now — rejected, same P10/YAGNI reasoning 012's Decision
  2 already established: build only the primitive this feature needs.

## Decision 3: "One modal at a time" is enforced globally, not only within Signal Stream/Action Hub reselection

**Decision**: `dashboard-page.tsx` keeps `selectedContributionId` and `draftHandoff` as
today, but the two modals (`EvidencePanel`, `DraftComposerPanel`) are treated as mutually
exclusive once converted to centered dialogs: opening one closes the other if it was open.

**Rationale**: FR-014 requires "at most one detail modal visible at a time" for Signal
Stream/Action Hub reselection. Extending that same rule to cover
`EvidencePanel`-vs-`DraftComposerPanel` simultaneity is a direct consequence of both now
being centered dialogs — two centered dialogs cannot coexist legibly the way two
independent side-docked/floating panels could. This is safe to do now specifically because
012's edge case requiring Evidence/Draft-Composer to stay usable *simultaneously* with the
Assistant was about the *floating* Assistant overlapping a side panel; the Assistant is no
longer an overlay at all (Decision 5 below / spec FR-004), so that original motivating
conflict no longer exists, and nothing in this spec asks for two detail dialogs open at
once.

**Alternatives considered**:
- Leave `EvidencePanel` and `DraftComposerPanel` independently toggleable, risking two
  overlapping centered dialogs — rejected: directly undermines FR-013's "elegant modal"
  requirement, and the only reason that simultaneity used to matter (the floating
  Assistant) no longer applies.

## Decision 4: `NarratorPanel` / `StakeholderCards` / `CoverageLine` — relocated, not modified

**Decision**: These three components keep their existing props, internal markup, and tests
unchanged. Only `dashboard-page.tsx`'s layout changes: they move from "left column of a
two-column grid" to "appended below `PulseTimeline`, inside column 2 of the new
three-column grid" (Clarifications 2026-08-18, FR-019).

**Rationale**: This is the option the user selected — lowest risk, nothing removed or
demoted, everything stays reachable by scrolling column 2 exactly where P5 (`CoverageLine`)
and the existing narrative/stakeholder synthesis need to remain visible.

**Alternatives considered**: Moving `CoverageLine` next to the score in column 3 — offered
as an option, not chosen; would have required `ChurnRiskOverviewCard` to take on a new
prop/dependency it doesn't have today for no requirement-driven reason.

## Decision 5: Company title and the Assistant move into column 1; the decorative top bar stays

**Decision**: `client_header.client_name` and `client_header.days_to_renewal` move from
`dashboard-page.tsx`'s current full-width header row into column 1, above the new AURA
risk orb, per the mockup. The decorative "Last 30 days" / "Live" / bell controls
(spec 012 FR-013, still decorative, still no new state) remain in a full-width bar above
all three columns — only the client name/renewal text leaves that row.

**Rationale**: Matches the mockup's actual layout (title inside the branding column, not
the top bar) with a minimal, purely positional change — no new data, no field read that
wasn't already fetched and rendered today.

**Alternatives considered**: Duplicating the client name in both the top bar and column 1
— rejected: redundant, and the mockup shows it once, in column 1.

## Decision 6: AURA risk orb reuses the existing band color values; no new thresholds

**Decision**: `aura-risk-orb.tsx` takes `score: number` and `band: Band` (already fetched
via `score_block`) and renders a soft radial-gradient circle colored from the same
`healthy`/`watch`/`at_risk` palette `score-block.tsx`'s `BAND_CHART_COLOR` already defines
(extracted to a shared constant both components import, so the two visual score
treatments — orb and card — never drift out of sync).

**Rationale**: Spec Assumptions are explicit: reuse existing risk-band colors, introduce no
new thresholds. `BAND_CHART_COLOR`'s three hex values are already the canonical "chart-safe"
version of the band palette (`score-block.tsx` lines 20-27); duplicating a second
independently-chosen palette for the orb would risk exactly the drift P10 warns against.

**Alternatives considered**: A continuous score→color gradient (e.g. interpolating hue by
`score` value) instead of the three discrete band colors — rejected: would introduce a new,
unspecified color rule not backed by any requirement, and would visually contradict
`ChurnRiskOverviewCard`'s discrete band pill shown right next to it.

## Decision 7: Score trend chart gains a real `XAxis` and an unhidden, `%`-suffixed `YAxis`

**Decision**: `score-block.tsx`'s `AreaChart` adds `<XAxis dataKey="index" />` (the same
zero-based sequence index already used as the `dataKey`, now surfaced as tick labels) and
changes `<YAxis domain={['dataMin','dataMax']} hide />` to a visible axis with
`tickFormatter={(v) => \`${v}%\`}`.

**Rationale**: Directly satisfies FR-010 (Y axis percentage, X axis historical sequence,
visible without hovering) using the exact same `trend: number[]` data already fetched —
no new field, no timestamp that doesn't exist in the data (012's `data-model.md` already
noted no timestamps exist for trend points, and none are added here either).

**Alternatives considered**: Adding real dates to the X axis — rejected: `score_block.trend`
has never carried timestamps (012's `research.md`/`data-model.md`), and inventing one here
would be fabricating data precision FR-015 doesn't authorize.

## Decision 8: A `contracts/` directory is included this time

**Decision**: Unlike 012 and 015 (both frontend-only, contract-free), this feature adds a
`contracts/dashboard.md` documenting the one additive field on `GET /api/dashboard`.

**Rationale**: The plan template's guidance to skip `contracts/` applies only to purely
internal, no-external-interface changes (012's Decision 7, 015's Project Structure note).
This feature does change the shape of a real external interface — `pulse_timeline[].event_type`
is new on the response every frontend consumer of `GET /api/dashboard` receives — so the
same reasoning that excluded `contracts/` before now includes it.

**Alternatives considered**: None — this follows directly from whether the feature touches
an external contract, which 012/015 didn't and this one does.
