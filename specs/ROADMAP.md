# Spec-Kit Roadmap

Tracks progress across this repository's spec-kit features. Updated as each feature moves
through `/speckit-specify` → `/speckit-implement`.

## Why one feature per build-order phase

`requirements/` and `architecture/` already contain more detail (EARS-syntax `REQ-IDs`,
an explicit traceability matrix, ratified architecture decisions) than a typical
greenfield `spec.md` would. Re-deriving that content per module through spec-kit would
duplicate and likely drift from what's already authoritative. Instead:

- **`requirements/*.md` stays the single source of truth** for *what* each module must do
  — spec-kit doesn't re-author it.
- **`spec.md`/`plan.md`/`tasks.md` are a thin, per-build-phase translation layer**:
  `spec.md` turns a slice of already-decided requirements into prioritized,
  independently-testable user stories; `plan.md`'s Technical Context is filled by *citing*
  `architecture/*.md` instead of re-researching it; `tasks.md` is the one genuinely new
  artifact — concrete file-level build tasks.
- Every acceptance criterion cites a `REQ-ID` rather than restates its content.

The product spec's own build order (`base/Churn-Sentiment-Agent-Product-
Specification.md` §16) already segments the system into eleven phases, each of which
"leaves a working system" — exactly spec-kit's definition of an independently
testable/demoable feature slice. That's the feature boundary used below, not one
spec-kit feature per module (M1–M10), which would fragment single working slices.

## Status

| # | Feature | Build-order phase | Status | Primary requirements | Primary architecture |
|---|---|---|---|---|---|
| 001 | [`project-foundation`](001-project-foundation/) | 1 · Foundation | ✅ **Complete** — all 33 tasks implemented and verified against real Docker/Postgres | `requirements/11-non-functional-requirements.md` (CI/determinism criteria) | `architecture/03-technology-stack.md`, `architecture/09-clean-architecture-and-patterns.md`, all of `data-base/` |
| 002 | [`dashboard-shell`](002-dashboard-shell/) | 2 · Vertical slice (login + dashboard) | ✅ **Complete** — all 29 tasks implemented and verified end to end, including a real browser against the containerized production build | `requirements/14-authentication.md`, `requirements/08-health-dashboard.md` (shell only) | `architecture/07-api-spec.md`, `data-base/12-users-and-auth.md` |
| 003 | `ingestion-and-context` | 3 · Ledger + profile | ⬜ Not started — **next up** | `requirements/01-signal-collectors.md`, `02-event-ledger.md`, `03-client-profile.md` | `architecture/01`, `02-component-catalog.md`; `data-base/02,03,04` |
| 004 | `score-engine` | 4 · Scoring engine (checkpoint phase) | ⬜ Not started | `requirements/06-scoring-engine.md`, `13-scoring-calibration-appendix.md` | `data-base/06-schema-scoring.md`; `sequences/06` |
| 005 | `deterministic-findings` | 5 · Findings (no AI) | ⬜ Not started | `requirements/05-interpreters-readers.md` (Commitment/Usage/Recurrence/Absence) | `data-base/05-schema-reasoning.md` |
| 006 | `dashboard-evidence-trace` | 6 · Full dashboard | ⬜ Not started | `requirements/08-health-dashboard.md` (full) | `architecture/07-api-spec.md`, `data-base/08` |
| 007 | `model-findings` | 7 · Tone/Intent + validation gate | ⬜ Not started | `requirements/05-interpreters-readers.md` (Tone/Intent/M5a) | `architecture/04-ai-safety-and-model-usage.md`, `05-agent-catalog.md` |
| 008 | `narrator-and-ask-agent` | 8 · Explanation layer | ⬜ Not started | `requirements/07-narrator.md`, `09-ask-agent.md` | `sequences/02` |
| 009 | `draft-composer` | 9 · The closer | ⬜ Not started | `requirements/10-draft-composer.md` | `sequences/04` |
| 010 | `feedback-memory` | 10 · Learning loop | ⬜ Not started | `requirements/04-feedback-memory.md` | `data-base/07`; `sequences/03` |
| 011 | `production-hardening` | 11 · Hardening | ⬜ Not started | remaining NFRs, `decisions/01-mvp-scope-and-phasing.md` | — |

`requirements/12-traceability-matrix.md` maps REQ-ID → spec section → module →
acceptance test — every `spec.md` and `tasks.md` produced below links into that matrix
rather than reproducing it.

## Per-feature loop

Repeat for each row above, in order:

1. **`/speckit-specify`** — description explicitly cites the REQ-IDs and architecture docs
   in scope; user stories are derived from them, not restated.
2. **`/speckit-clarify`** — expect few findings per feature; most ambiguity is already
   resolved in `decisions/00-open-questions-resolved.md`.
3. **`/speckit-plan`** — Technical Context is filled by citing `architecture/*.md` and the
   relevant `data-base/*.md`; the Constitution Check gate validates against
   `.specify/memory/constitution.md`.
4. **`/speckit-tasks`** — the one net-new artifact: concrete, file-level tasks grouped by
   user story.
5. **`/speckit-analyze`** — cross-checks `spec.md`/`plan.md`/`tasks.md` against each other
   and against `requirements/`/`architecture/` for drift.
6. **`/speckit-implement`** — executes `tasks.md`, verified against real tooling wherever
   possible (not just written and assumed correct).

## Log

- **2026-08-13** — `.specify/memory/constitution.md` ratified at v1.0.0, then amended to
  v1.1.0 (added P11, frontend engineering standards).
- **2026-08-13** — Feature 001 (`project-foundation`) specified, planned, tasked,
  analyzed, and implemented. All 33 tasks complete; stack verified end to end against
  real Docker containers and Postgres 16 (migration round-trip, seed script, CI gates —
  both positive and negative import-linter cases — health checks, restart persistence,
  volume-wipe reprovisioning, and full-stack startup timing against SC-001).
- **2026-08-13** — Feature 002 (`dashboard-shell`) specified, planned, tasked, analyzed,
  and implemented. All 29 tasks complete. Two design adaptations surfaced and documented
  during implementation (both in `specs/002-dashboard-shell/research.md`): the login
  rate limiter is keyed by source IP rather than username (`slowapi`'s key function is
  synchronous, can't safely read the async request body) and counts only failed
  attempts, not every call. Verified against the real, fully containerized stack: the
  full auth lifecycle via `curl` (login, generic failure messages, rate limiting,
  logout/revocation), 10 backend pytest cases and 3 frontend Vitest cases, 4 Playwright
  end-to-end specs, and a real Chrome browser driven against the nginx-served
  production build — screenshotted login → "Meridian Logistics" / "Still learning — 0
  of 6 signal types available." Login-to-dashboard round trip: 0.61s (SC-001 threshold
  5s).
