# Phase 0 Research: Input Connectors View

No `NEEDS CLARIFICATION` markers remain in `spec.md` or in this plan's Technical Context,
so this phase resolves implementation-approach questions rather than open unknowns.

## Decision 1: Brand icons as static assets, not a new icon library

**Decision**: Download official brand SVG marks for connectors that have one (Gmail,
Slack, Zendesk, Microsoft 365, Teams, Salesforce, Jira, Intercom) and bundle them as
static files under `frontend/public/icons/connectors/`, rendered through a small
`brand-icon.tsx` wrapper (`<img src="/icons/connectors/<name>.svg" ... />` or inlined SVG).
Every other icon on the page (the sidebar's connector/plug icon, chevrons, the "Add
Connector" plus icon, and the generic marks for Transcripts, Warehouse, CSAT, Calendar,
NPS, and Contracts, which have no single official public brand mark) continues to use
`lucide-react`, exactly as the rest of the app already does.

**Rationale**: The constitution's "UI & Styling" rule closes icon choice to
`lucide-react` specifically to stop ad hoc icon libraries from creeping in
(`architecture/03-technology-stack.md`). `lucide-react` is a generic icon set — it does not
carry third-party brand marks, and building an "approximate Slack-shaped icon" out of
generic shapes would misrepresent a real brand and fail the mockup's fidelity requirement
(spec FR-010). Treating brand marks as static image assets rather than as a second npm
icon *library* keeps the actual rule (no competing icon-library dependency) intact while
still meeting FR-006's "recognizable icon" requirement.

**Alternatives considered**:
- *A brand icon npm package (e.g. `react-icons`'s `si` set, `simple-icons`)* — rejected:
  introduces a second icon library, which the constitution's UI & Styling rule prohibits
  without explicit approval; static assets need no such exception.
- *Generic `lucide-react` shapes standing in for brand logos* — rejected for the four marks
  below that are actually available; accepted as the fallback for the four that are not
  (see the implementation-time addendum immediately below).
- *Inline `<svg>` markup pasted directly into `connector-card.tsx`* — rejected in favor of
  standalone asset files: keeps the data module (`connectors-data.ts`) free of markup and
  matches how the app already serves static icon assets (`frontend/public/icons.svg`,
  `favicon.svg`).

**Implementation-time addendum (discovered during `/speckit-implement`, not anticipated at
plan time)**: fetching the eight planned brand marks from Simple Icons (pinned to the exact
version resolved at implementation time, `simple-icons@16.28.0`) found only four of the
eight — Gmail, Zendesk, Jira, Intercom — still present in that package's official,
actively-maintained metadata index (`data/simple-icons.json`, which also supplies each
mark's real hex color). Slack, Microsoft 365, Teams, and Salesforce are **not** in that
index at all, even though their old compiled SVG files still happen to respond on the CDN
(a stale/orphaned artifact, not a currently-published icon) — a pattern that usually means
the mark was pulled for a brand/trademark reason. The user, asked directly, chose (over
using the orphaned files, or a plain colored-monogram badge) to render those four as
generic `lucide-react` icons tinted with the brand's own color instead: `MessageSquare`
(Slack, `#4A154B`), `Grid` (Microsoft 365, `#EA3E23`), `Users` (Teams, `#6264A7`), `Cloud`
(Salesforce, `#00A1E0`). The four real logos are baked with their official hex directly
into the static SVG file (`fill="#EA4335"` etc., rather than `currentColor`) since a
downloaded `<img>` cannot be recolored via CSS the way an inlined `lucide-react` icon can —
so no dynamic tinting machinery was needed for the real logos, only for the four stand-ins.
Intercom's current official hex (`#6AFDEF`, a light mint) was swapped for their documented
dark navy brand color (`#0A2540`, "Intercom Blue") for contrast against the page's light
card background — still a real, documented Intercom brand color, just the more legible one
of the two.

## Decision 2: Static local data module, no backend call

**Decision**: Connector list, grouping, and copy live in a single typed TypeScript module
(`connectors-data.ts`) read directly by the page component — no `fetch`, no TanStack Query
hook, no backend endpoint.

**Rationale**: Spec Assumptions state this is a static, informational catalog view with no
new backend integration; FR-009 requires zero effect on existing ingestion/scoring
pipelines. The three status groups (Live/Simulated/Planned) are a product/roadmap
classification, not data that changes per request or per user — a static module is the
simplest thing that satisfies every functional requirement (constitution P10, YAGNI).
This exactly mirrors the existing `nav/destinations.ts` pattern already used for the
sidebar/breadcrumb single source of truth.

**Alternatives considered**:
- *A new `/api/connectors` backend endpoint* — rejected: no requirement calls for this data
  to be dynamic, and adding one would touch the backend and its Clean Architecture layers
  (P8) for a feature explicitly scoped as a static view — a P10 violation with no offsetting
  need.
- *Deriving the list from the backend's existing `source_type` definitions at build time*
  — rejected as unnecessary coupling for this iteration: the backend module's collector
  registry (`backend/app/ingestion/adapters/simulated_collector.py`) and this page's
  "Planned"/roadmap entries are different concerns (implemented source types vs. a
  product roadmap list); keeping them independently maintained, typed data avoids a
  cross-module dependency for a page whose entire purpose is a hand-curated status catalog.

## Decision 3: Group counts derived from the same list they label

**Decision**: Each status group's displayed count (`Live (1)`, `Simulated (6)`,
`Planned (7)`) is computed from `connectors-data.ts`'s array length for that group at
render time — never a separately hand-typed number.

**Rationale**: Directly resolves the edge case in spec.md ("What happens if the counts in
a section header and the number of entries listed under it ever disagree?") by making that
state structurally impossible, the same discipline the constitution applies elsewhere
(P1's non-empty `CHECK` constraint) — here achieved with a `.length` derived from a single
array rather than a database constraint, since there is no database involved.

**Alternatives considered**:
- *Hand-typed count next to a hand-typed list* — rejected: exactly the drift the edge case
  warns against.
