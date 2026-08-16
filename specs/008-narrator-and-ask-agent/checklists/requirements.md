# Specification Quality Checklist: Narrator and Ask Agent

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-15
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Consistent with this repository's established pattern (`specs/ROADMAP.md`'s
  "Per-feature loop"), requirement *content* is not restated in `spec.md` —
  every functional requirement cites the `REQ-<ID>` in
  `requirements/07-narrator.md` or `requirements/09-ask-agent.md` that is its
  source of truth.
- No `[NEEDS CLARIFICATION]` markers were needed on the first `/speckit-specify`
  pass: several open questions (whether `DashboardResponse` needs additive
  fields for narrator/Ask-bar content, whether the Ask bar and the "Ask
  thread" screen are one capability or two, multi-turn memory being out of
  scope) had a reasonable, well-evidenced default and were recorded directly
  in Assumptions.
- **`/speckit-clarify` session (2026-08-15)**: two higher-impact ambiguities
  were found and resolved interactively, both concerning the Ask agent's
  response contract rather than a reasonable default. (1) `AskComponentResponse`
  only defines the 7 lookup-and-render component values, with no
  representation for REQ-M9-02's 8th mapping — the "write to X about this"
  hand-off to the not-yet-built draft composer (feature 009); resolved to a
  distinct handoff response carrying issue/stakeholder context, now FR-012a.
  (2) The "is this normal for X?" intent reuses the Tone reader's
  per-stakeholder baseline (feature 007), which honestly abstains below 5
  prior messages — a failure mode REQ-M9-07's "source isn't connected"
  message doesn't actually describe; resolved to a new, distinct
  `declined_reason = insufficient_history`, now FR-017a. Both are recorded in
  `## Clarifications` in `spec.md` and require additive changes to
  `architecture/07-api-spec.md`'s `AskComponentResponse`/`AskFallbackResponse`
  schemas and `data-base/08-schema-experience.md`'s `declined_reason` enum,
  flagged in Assumptions for `/speckit-plan` to carry through.
- The Ask agent's orchestration technology (LangGraph) is cited only in
  Assumptions, as a pointer to the already-ratified
  `decisions/03-langgraph-for-ask-agent.md` — the functional requirements
  themselves describe only user-facing behavior already mandated by
  `requirements/09-ask-agent.md`, not implementation mechanics.
- Two real gaps this feature closes were identified by reading feature 006's
  own spec, not invented here: `specs/006-dashboard-evidence-trace/spec.md`
  explicitly excluded both "the Ask bar" (REQ-M8-02) and "narrator
  headline/reasons/actions text" (REQ-M8-01) because neither module existed
  yet at that point in the build order — this feature is where both become
  real for the first time.
