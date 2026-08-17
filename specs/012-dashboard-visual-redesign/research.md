# Phase 0 Research: Main Dashboard Visual Redesign

No `NEEDS CLARIFICATION` markers remain in Technical Context — the three open questions from `/speckit-clarify` (header decorative elements, sidebar scope, assistant default state) already resolved the highest-impact product-level ambiguities and are encoded directly in `spec.md`'s FR-001, FR-007, and FR-013. What follows are the technical decisions needed to execute the plan without touching anything FR-011 protects.

## Decision 1: New dependencies — `recharts` and `lucide-react`

**Decision**: Add `recharts` and `lucide-react` to `frontend/package.json` dependencies.

**Rationale**: The constitution's Full-Stack Engineering §2 "UI & Styling" rule (v1.3.0, amended for this exact feature) requires icons to use `lucide-react` and charts to use Recharts, and forbids other component/icon libraries without approval. `architecture/03-technology-stack.md` already named Recharts as the resolved choice (`decisions/02-repo-and-tooling.md`, visx vs. Recharts). Today's `score-block.tsx` uses a hand-rolled inline `<svg><polyline>` sparkline with a code comment explicitly citing "no chart library" as the old rule — that comment is now stale and will be removed as part of this change, not preserved.

**Alternatives considered**:
- Keep the hand-rolled SVG sparkline and hand-draw an area fill too — rejected: contradicts the constitution's explicit "Charts MUST use Recharts" rule, and reimplementing area-chart interactions (tooltips, responsive sizing) by hand is exactly the kind of avoidable complexity a charting library exists to remove.
- `visx` — rejected: `decisions/02-repo-and-tooling.md` already resolved this in Recharts' favor for this project's chart surface area (sparkline + trend line only).

## Decision 2: A minimal shared `components/ui/` + `lib/utils.ts` layer, not a full shadcn generation

**Decision**: Add `frontend/src/components/ui/{card,button,icon}.tsx` and `frontend/src/lib/utils.ts` (a `cn()` helper over the already-installed `clsx` + `tailwind-merge`), sized to exactly what the four mockup regions need.

**Rationale**: `@radix-ui/react-slot` has been a dependency since before this feature (for exactly this shadcn-style `asChild` pattern) but nothing in the codebase uses it yet — there is currently no shared UI primitive directory at all; every feature folder hand-rolls its own Tailwind markup. P11 already requires "a Radix-based component system (shadcn/ui)"; this feature is the first one that needs enough shared chrome (cards, buttons, nav items) to justify actually building it. Building only three primitives (not running the full shadcn CLI generator, not vendoring a large kit) keeps this consistent with P10/YAGNI.

**Alternatives considered**:
- Run the full `shadcn` CLI generator now, pulling in its complete default component set — rejected: most of that kit (dialogs, dropdowns, tables, etc.) has no user in this feature; P10 explicitly warns against building for requirements the product doesn't have today.
- Keep hand-rolling ad hoc Tailwind classes per component, as today — rejected: this is precisely the "ad hoc styling" P11's Design System bullet already prohibits, and it's what makes four independently-styled regions look like one cohesive redesign hard to achieve consistently.

## Decision 3 (revised during implementation): Action & Draft Hub is built from `contribution_bars`, not `narrator.actions`

**Original decision** (superseded): pair each Action & Draft Hub row with a priority badge derived from an "associated `ContributionBar.points`," implicitly assuming Action & Draft Hub rows come from `narrator.actions` and can be paired with a contribution bar.

**Why it was wrong**: `NarratorAction` (`frontend/src/dashboard/types.ts`) is `{ text, owner, due_date }` — it carries no ID of any kind, and there is no positional or referential guarantee linking a given `narrator.actions[i]` to any particular `contribution_bars[j]`. Assuming a pairing between two independently-sized, independently-ordered arrays would have been fabricating a relationship the data doesn't assert — worse than not showing a priority badge at all.

**Revised decision**: The Action & Draft Hub is built directly from `contribution_bars: ContributionBar[]` — the one dashboard field that already has everything a "prioritized action" row needs and nothing invented: a real identity (`score_contribution_id`), a label, and a real magnitude (`points`) to rank by. `priorityTierFromPoints(Math.abs(points))` (unchanged from the original Decision 3's threshold logic) still applies, just to the correct source array. Selecting a row calls the same `onSelect(scoreContributionId)` pattern `ContributionBars`/`PulseTimeline` already use today to open `EvidencePanel` — a real, already-existing interaction, not a new one.

`NarratorPanel` (headline + reasons + actions) is **not modified or folded into the hub** — it keeps rendering exactly what it renders today, from the same `narrator` prop, with the same test (`narrator-panel.test.tsx`) unchanged. Only where it sits in the page layout changes. This avoids ever displaying `narrator.actions` twice and avoids inventing IDs it doesn't have.

**Alternatives considered**:
- Add a new `priority`/linking field to the backend — rejected: violates FR-011 and the CRITICAL CONSTRAINT.
- Pair `narrator.actions[i]` with `contribution_bars[i]` positionally as a best-effort guess — rejected: silently wrong pairing is worse than an honest, ID-backed alternative; a future backend change to either array's ordering would silently corrupt the mapping with no test able to catch it.

## Decision 4 (revised during implementation): the hub opens Evidence, not the Draft Composer — no fabricated preview

**Original decision** (superseded): assumed selecting a hub item could trigger the same on-demand draft-generation call `DraftComposerPanel` makes, requiring an `issue_id`/`stakeholder_id` per row.

**Why it was wrong**: no field available to the Action & Draft Hub (`contribution_bars`, per the revised Decision 3) carries an `issue_id` or `stakeholder_id`. `DraftRequest` (`draft-composer/types.ts`) requires both. The *only* place in the app that already produces those two IDs together is the Ask agent's structured tool response, handled today by `AskBar`'s `onOpenDraftComposer` callback. Wiring a hub row to open the composer would require inventing IDs that don't exist anywhere in `contribution_bars` or `narrator.actions` — a correctness bug (a wrong or fabricated ID reaching `postDraft`), not a visual choice.

**Revised decision**: Selecting an Action & Draft Hub row opens the **existing `EvidencePanel`** via the real `score_contribution_id` it already carries — the same interaction `ContributionBars` provides today, just from the hub's new visual position. The mockup's "Drafted outreach" preview card is **not reproduced** as a live, data-backed element for hub rows, since no draft exists for any of them ahead of time and none can be honestly generated without IDs the data doesn't have. `DraftComposerPanel` remains reachable exactly as it is today — only through the Ask agent's `onOpenDraftComposer` handoff, itself preserved unchanged by US3's floating-assistant conversion.

**Alternatives considered**:
- Eagerly fetch/preview drafts for all listed items on load — rejected in the original decision and still rejected: no IDs to fetch with, and would be a new, non-idempotent call pattern regardless.
- Fabricate a plausible-looking `issue_id`/`stakeholder_id` pairing to "make the mockup work" — rejected outright: this is exactly the kind of silent, undetectable correctness bug FR-011 exists to prevent (a wrong draft could reach the wrong stakeholder).
- Omit the hub's click interaction entirely — rejected: `EvidencePanel` is a real, already-wired interaction available on this exact data; removing it would be a regression, not a redesign.

## Decision 5: Floating assistant reuses `AskBar`'s existing state and hooks verbatim

**Decision**: The floating assistant is `ask-bar.tsx`'s existing `useMutation`/`postAsk` logic, unchanged, wrapped in a new collapsible shell. Only the outer container changes — from `fixed inset-x-0 bottom-0 z-40` (full-width bar) to a corner launcher + panel — starting collapsed on every page load per FR-007, and kept at a z-index below the existing `z-50` Evidence/Draft-composer overlays (today's `z-40` convention) so those overlays still take visual precedence when open, satisfying the "both remain usable" edge case.

**Rationale**: `AskBar` today is single-exchange (idle → thinking → answered off one `useMutation`), not a persisted multi-turn thread — there is no message-history array anywhere in its state. FR-008 ("must not discard existing conversation state/history") is satisfied by not resetting that single mutation's data on collapse/expand; it does not require building new multi-turn history storage, which would itself be new state and out of scope. Implementers should not read the mockup's multi-message thread illustration as a requirement to add a persisted conversation log — that would violate FR-011.

**Alternatives considered**:
- Add a persisted multi-turn conversation history to match the mockup's illustrated thread exactly — rejected: requires new state not present today, directly conflicting with FR-011 and the CRITICAL CONSTRAINT; also out of this spec's Assumptions ("no new data").

## Decision 6: Sidebar links to the three existing routes via `react-router`'s `NavLink`

**Decision**: The sidebar renders exactly three icon entries — Dashboard (`/dashboard`), Coverage (`/coverage`), Profile (`/profile`) — using `NavLink` from the already-installed `react-router`, whose built-in active-route matching satisfies FR-002 with no new state.

**Rationale**: Resolves the clarified FR-001 scope (exactly the app's existing destinations, no placeholder icons). `App.tsx`'s route table is not modified.

**Alternatives considered**: none needed — this was the resolved `/speckit-clarify` answer, not an open design question.

## Decision 7: No `contracts/` artifact for this feature

**Decision**: Skip generating a `contracts/` directory for Phase 1.

**Rationale**: This feature exposes no new interface to any external caller or system — it is a pure internal frontend presentation change consuming backend contracts that already exist and remain untouched (`architecture/07-api-spec.md`). The plan template's own guidance is to skip contracts for purely internal changes.

## Decision 8 (revised — see Decision 3): `contribution_bars` alone backs the Action & Draft Hub

**Decision**: The Action & Draft Hub's list content is sourced entirely from the existing `contribution_bars: ContributionBar[]` field already present in `DashboardResponse` — no new field is read from anywhere else, and `narrator.actions` is *not* pulled into the hub (see the revised Decision 3 for why).

**Rationale**: `ContributionBar` is the only field in today's `DashboardResponse` that is simultaneously identity-bearing (`score_contribution_id`), rankable (`points`), and already wired to a real interaction (`onSelect` → `EvidencePanel`) — matching the spec's Key Entity description ("a prioritized recommended action") without requiring any invented linkage between arrays.

**Alternatives considered**: merging `narrator.actions` in as well — rejected per Decision 3/4 (no ID to make those rows interactive or draft-linkable; would either be dead rows or a fabricated pairing).
