<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0

Rationale for 1.1.0 (MINOR): one new principle added (P11, frontend engineering
standards), no existing principle redefined or removed — additive, not breaking.

Modified principles: none

Added principles (this amendment):
  - P11 Frontend: Feature-Oriented, Typed, Spec-Driven — condensed from the team's
    18-section Frontend Engineering Constitution supplied 2026-08-13; only the highest-
    leverage rules were kept (feature-oriented structure, separation of concerns, server/
    client state split, strong typing, design-system discipline, schema-based form
    validation, test hierarchy, accessibility/error handling, Definition of Done). The
    full 18-section source remains the reference for anything this condensed version
    doesn't cover.

Added sections (this amendment):
  - "Technology and Data Standards" gained a one-line frontend data/state-layer entry
    (TanStack Query, Zustand, React Hook Form + Zod) plus an ADR requirement for
    frontend technology swaps.

--- prior report (v1.0.0, initial ratification) ---
Version change: [TEMPLATE, unratified] → 1.0.0
Rationale for 1.0.0 (not 0.1.0): this is the first ratified constitution for the project —
all ten principles, the technology/data standards section, the quality-gates section, and
governance are newly defined, none are a patch/clarification of a prior ratified version.

Modified principles: none (initial ratification — nothing to rename or redefine)

Added principles:
  - P1 Evidence or It Does Not Exist
  - P2 The Model Interprets, Code Calculates
  - P3 Each Component Refuses to Do the Next One's Job
  - P4 A Human Always Sends
  - P5 Admit What We Cannot See
  - P6 Silence Is a Success State
  - P7 Context Over Sentiment
  - P8 Clean Architecture — the Dependency Rule Is Law
  - P9 Test-First Determinism
  - P10 Simplicity Over Speculative Generality (YAGNI)

Added sections:
  - Technology and Data Standards
  - Development Workflow & Quality Gates
  - Governance (fully specified — amendment procedure, versioning policy, compliance review)

Removed sections: none (this is the template's first fill, nothing pre-existed to remove)

Templates requiring updates:
  - .specify/templates/plan-template.md            ✅ compatible — "Constitution Check" gate
    already reads "[Gates determined based on constitution file]" generically; no hardcoded
    principle names to reconcile. No edit made.
  - .specify/templates/spec-template.md             ✅ compatible — generic user-story/
    acceptance-scenario structure, no principle-specific language to reconcile. No edit made.
  - .specify/templates/tasks-template.md            ✅ compatible — generic phase/user-story
    structure; P9's test categories (golden-replay, reconciliation, monotonicity, static
    no-LLM check) map onto the existing "Foundational"/"Polish" phases without template
    changes. No edit made.
  - .claude/skills/speckit-*.md (command definitions) ⚠ pending — not reviewed line-by-line
    in this pass; none reference this project's principles by name today, so no known
    conflict, but a full pass is deferred to the next amendment that touches them.

Follow-up TODOs: none. RATIFICATION_DATE is set to the date this constitution was first
authored and adopted (2026-08-13), which is a real date, not a placeholder.
-->

# Agentic Churn Constitution

Agentic Churn is a dedicated monitoring agent for **one client relationship**. It reads
signals that already exist across email, chat, tickets and product usage, notices when the
relationship is deteriorating, explains why with evidence, and proposes what to do next. A
human always decides and always sends. This constitution governs every design and
engineering decision made in this repository; it is derived verbatim, where marked, from
`base/Churn-Sentiment-Agent-Product-Specification.md` §4 ("Product principles") and
`AGENTS.md` ("Non-negotiable rules"), and extended with coding-level discipline from
`architecture/`.

## Core Principles

### P1 — Evidence or It Does Not Exist

> Every claim links to the actual email, ticket or message that produced it. A finding
> without evidence is discarded by the system before a human ever sees it.
> — *Product Specification §4*

**Enforcement (verbatim, `AGENTS.md`):** Every finding cites real event IDs. A finding with
zero citations must be structurally impossible to insert, not just discouraged by
convention (`findings.cited_event_ids` has a non-empty `CHECK` — see
`data-base/10-ddl-appendix.md`).

### P2 — The Model Interprets, Code Calculates

> Language models read language and write language. They never produce the number. All
> scoring is plain arithmetic that a person can verify on paper.
> — *Product Specification §4*

**Enforcement (verbatim, `AGENTS.md`):** `backend/app/scoring/` (M6) must never import an
LLM client, directly or transitively. This is enforced by a CI static check
(`workflows/ci.yml`), not just a lint rule — don't route around it.

### P3 — Each Component Refuses to Do the Next One's Job

> Collectors do not judge. The ledger has no opinions. Readers do not rank. The calculator
> does not guess. This discipline is what makes the system explainable.
> — *Product Specification §4*

**Enforcement (verbatim, `AGENTS.md`):** Collectors don't judge importance. Readers don't
rank. The scoring engine doesn't call a model. If you're tempted to have one module do a
neighboring module's job "just this once," don't — read
`requirements/00-overview-and-glossary.md` §Product principles first.

### P4 — A Human Always Sends

> There is no send capability anywhere in the product. Not disabled — absent.
> — *Product Specification §4*

**Enforcement (verbatim, `AGENTS.md`):** There is no send capability anywhere in this
product, for any module, to any external system — not hidden, not feature-flagged, not
admin-only. If a task description implies adding one, stop and flag it; it contradicts the
spec.

### P5 — Admit What We Cannot See

> A score built on incomplete data must never look identical to a score built on complete
> data.
> — *Product Specification §4*

**Enforcement (verbatim, `AGENTS.md`):** A degraded/incomplete data state must look visibly
different from a complete one, everywhere it matters (dashboard, scores, coverage lines).

### P6 — Silence Is a Success State

> When the client is healthy, the screen is nearly empty and says so. A tool that
> manufactures concern gets ignored.
> — *Product Specification §4*

**Enforcement (verbatim, `AGENTS.md`):** A healthy account should produce a near-empty
screen. Don't add UI elements that manufacture the appearance of concern.

### P7 — Context Over Sentiment

> Who said it and what it was about matters more than how it was phrased.
> — *Product Specification §4*

**Enforcement (verbatim, `AGENTS.md`):** The Tone reader compares against a specific
stakeholder's own baseline, never a generic sentiment scale. Don't "simplify" this into a
universal threshold.

### P8 — Clean Architecture: the Dependency Rule Is Law

Every module (M1–M10) is organized as three rings — **Domain** (entities and pure domain
services), **Application** (use cases and the ports they depend on), **Adapters** (database,
external APIs, LLM providers, HTTP) — packaged by module first and layered within, not
packaged by layer at the top level (`backend/app/scoring/{domain,application,adapters}/`,
and so on for every module). Source-code dependencies point inward only: Adapters may
import Application and Domain; Application may import Domain and its own Ports; **Domain
imports nothing from this codebase except other Domain code, and nothing at all from
FastAPI, SQLAlchemy, the Anthropic SDK, or the OpenAI SDK.** This generalizes the one
CI-enforced boundary P2 already requires for the scoring engine to every module in the
system, via declared `import-linter` contracts, not a hand-rolled AST script per module. An
entity that spans modules (e.g. `Finding`, produced by `readers`, scored by `scoring`, read
by `experience`) is defined once, in the module that owns its lifecycle, and imported by the
others — never redefined per module.

**Why:** domain services being framework-free is what lets `ScoringCalculator`,
`BandClassifier`, and `DampingCalculator` be unit-tested with plain `assert` statements
against plain objects — no database, no HTTP client, no mocked LLM — which is the literal
mechanism behind the property-based reconciliation and monotonicity tests running thousands
of generated cases per CI run (P9). SOLID is not an abstract aspiration here: Single
Responsibility (`ScoringCalculator` only computes), Open/Closed (a 9th reader is one new
class, never an `if reader_type == ...` branch), Liskov Substitution (any `Reader`
abstaining with `[]` is handled identically regardless of why), Interface Segregation
(`LLMPort` has exactly one method), and Dependency Inversion (use cases depend on `LLMPort`,
never on `AnthropicLLMAdapter` directly) each map to a specific class named in
`architecture/09-clean-architecture-and-patterns.md`, not a slogan.

### P9 — Test-First Determinism

Full replay must stay exact. Determinism is not a nice-to-have — it is what makes the
system's audit story real: **same ledger + same versions → identical score, always.**
Every change to `backend/app/ledger/` or `backend/app/scoring/` runs the golden-replay test
(`tests/strategy.md`) before a PR opens: run a fixture once, snapshot the resulting
dashboard state, drop all derived projections, replay from `events` +
`client_profile_versions` + `baseline_confirmations` alone, and assert byte-identical
reconstruction. This is joined by three more mechanically enforced properties, all
blocking merge: **decimal reconciliation** (score contributions sum exactly to the total,
to full `NUMERIC(10,3)` precision, never rounded), **monotonicity** (adding a validated
negative finding never lowers the score, property-tested against thousands of
`hypothesis`-generated cases), and the **static no-LLM check** (an AST-walking or
`import-linter` CI step proving the scoring engine cannot reach an LLM import, per P2 —
a static guarantee, not a runtime mock-and-assert that only proves a mock wasn't called
*this run*). A quarantined or abstaining finding is never silently repaired — quarantine
becomes the reader-quality evaluation dataset, not a queue to fix and resubmit.

### P10 — Simplicity Over Speculative Generality (YAGNI)

Add behavior by adding a class, not by adding a branch or a speculative abstraction layer
for a requirement the product does not have today. This project explicitly documents
patterns it chose **not** to build — a plugin/dynamic-discovery system for readers (there
are eight, fixed by spec, not user-extensible), a generic event-bus/message-broker
abstraction (a 30-second Postgres batch window meets the latency target; don't build the
abstraction layer for a broker you also decided not to run), a `Specification`-object
framework for the validation gate's four fixed checks, CQRS, and a generic multi-tenancy
abstraction (one deployment per client is a permanent product constraint, not an MVP
shortcut waiting to be generalized). The same restraint applies to the interface: no ticket
volume charts, per-message sentiment lines, monthly averages, category pie charts, or any
percentage that would not change a decision — if a number would not change what someone
does next, cut it.

### P11 — Frontend: Feature-Oriented, Typed, Spec-Driven

Condensed from the team's Frontend Engineering Constitution — organize by feature/domain
(components, hooks, API calls, types, schemas, tests together), not by technical layer;
shared code only for genuinely reusable logic.

- **Separation of concerns**: components render; hooks encapsulate behavior; a dedicated
  API layer owns all backend communication — no scattered fetches inside components, no
  domain logic embedded in UI.
- **State**: server state via TanStack Query, client/UI state via Zustand only when local
  state isn't enough. No global state by default; state lives as close to its owner as
  possible.
- **Type safety**: TypeScript everywhere, `any` avoided; domain models, API contracts, and
  component interfaces are strongly typed.
- **Design system**: Tailwind CSS + a Radix-based component system (shadcn/ui), consistent
  with the stack already adopted in `architecture/03-technology-stack.md` — shared design
  tokens, no ad hoc styling.
- **Forms & validation**: React Hook Form + Zod schemas; user input is never trusted
  unvalidated, on the client or before it reaches the API layer.
- **Testing**: every feature ships unit + component tests; business-critical flows get
  end-to-end coverage; tests assert behavior, not implementation detail.
- **Accessibility & errors**: keyboard-accessible, WCAG-aligned, never color-only
  signaling; errors are normalized and user-friendly, never a raw stack trace.
- **Definition of Done**: types pass, lint passes, tests pass, accessibility and
  error/empty states considered, API contracts respected, reviewed — before a frontend
  feature counts as complete.

## Technology and Data Standards

**Adopted stack** (`architecture/03-technology-stack.md`): Python 3.12 + FastAPI backend;
Anthropic Claude — Sonnet-class for Narrator, Ask agent, and Draft composer, Haiku-class for
Tone, Intent, and Meeting readers; OpenAI `text-embedding-3-small` embeddings for the
Recurrence reader only (clustering, never a generative call); PostgreSQL 16 with JSONB
envelope/finding payloads and `pgcrypto` column-level encryption; React 18 + TypeScript +
Vite frontend with Tailwind/Radix and SVG-based charts only; APScheduler + Postgres
`LISTEN/NOTIFY` for scheduling (no message broker — the scale is 50k–200k events/year per
deployment); Docker Compose, **one stack per client deployment**, never shared
infrastructure; pytest + `hypothesis` for testing; GitHub Actions for CI.

**Frontend data/state layer:** TanStack Query for server state, Zustand for client state,
React Hook Form + Zod for forms and validation (P11). A frontend technology swap (state
library, UI framework, auth approach) requires an ADR, not a silent change.

**Schema discipline** (verbatim, `AGENTS.md`): Schema changes go through
`data-base/10-ddl-appendix.md` first, then get reflected in the matching prose file
(`02`–`09`, `12`) and an Alembic migration (`decisions/02-repo-and-tooling.md`). Don't let
the DDL and the running schema drift — that's exactly the class of bug a full-repo
consistency review exists to catch, and it's expensive to catch late.

**Ownership columns** (verbatim, `AGENTS.md`): Every table's "who did this" column is a
foreign key to `users`, never free text. See `data-base/12-users-and-auth.md`. If you're
adding a new "authored by" / "submitted by" style column, wire it to `users.id` from the
start.

**Requirement IDs** (verbatim, `AGENTS.md`): Requirements are numbered and stable.
`REQ-<MODULE>-<NN>` IDs are never reused or renumbered. If a requirement is retired, mark it
`RETIRED` in place — don't delete it and don't reuse its number.

**Isolation model:** one deployment = one client = one database schema/tenant = one
encryption key set = one `.env` file, never shared across stacks. Destroying a deployment's
Compose stack and data volume *is* the crypto-shredding/deletion mechanism at the deployment
level, not just the row level.

## Development Workflow & Quality Gates

**AI safety rules** (`architecture/04-ai-safety-and-model-usage.md`, non-negotiable for
every LLM call — Tone, Intent, Meeting readers; Narrator; Ask agent; Draft composer):

1. **Structured output everywhere** — every model call returns a schema-constrained JSON
   object; prose is generated once, at the end, and mechanically checked before display.
2. **Prompt injection defense is architectural, not prompt-level** — client text is
   untrusted data, never instructions. Interpreters have zero tools and zero side effects;
   output is validated against closed enumerations; a finding can never become an
   instruction; the Ask agent's tools are read-only lookups only; the Draft composer has no
   send-capable dependency reachable at all.
3. **Confidence is first-class** — `confidence` and `magnitude` are separate fields, never
   conflated; abstention is a valid, expected output, never a low-confidence guess.
4. **No new facts, mechanically checked** — every number, name, date, and claim in
   Narrator/Draft composer output is verified against the structured input before display;
   any unverifiable sentence is dropped entirely, never silently rephrased.
5. **Versioned prompts** — every prompt template is version-controlled; a run records which
   prompt version produced each output; changing a prompt is a replayable, measurable event,
   never an untracked live string edit.

**Resilience budgets** (`architecture/06-error-handling.md`) — every LLM call has a fixed
timeout and bounded retry policy sized to keep the pipeline inside its latency target:
Tone/Intent/Meeting readers 8s × 2 retries (abstain on exhaustion, never quarantined —
nothing was produced to quarantine); Narrator 10s × 1 retry (falls back to a deterministic,
non-LLM headline built from the scoring engine's own output if every generated sentence
fails its fact-check); Ask agent 2.5s with no retry (a retry would already blow its 3s
budget — falls back to plain text immediately); Draft composer 10s × 1 retry (fails
visibly, never a partial or silently-empty draft). A malformed webhook payload is captured
in `ingestion_failures`, never crashes a collector or silently vanishes — one bad payload
never stops the rest of a sync. A sustained quarantine/abstention rate above 50% over a
rolling 24 hours raises an internal ops alert (an engineering signal, never surfaced to a CS
lead as an account-health problem).

**CI gates that block merge** (`architecture/09-clean-architecture-and-patterns.md`,
`tests/strategy.md`): `import-linter` contracts enforcing the Dependency Rule across every
module (P8); the static no-LLM-in-scoring check (P2, P9); golden-replay byte-identical
reconstruction (P9); decimal reconciliation to full precision (P9); monotonicity across
thousands of generated cases (P9). Golden-replay and monotonicity failures are treated as
non-negotiable blockers, matching the spec's own Phase 4 checkpoint: if the score cannot be
explained and defended with hand-written findings, no amount of AI will fix it.

**Mermaid diagrams** (verbatim, `AGENTS.md`) — this repository has been bitten by two
parser gotchas enough times to state them explicitly: never put a semicolon (`;`) inside
diagram text (node labels, sequence messages, edge labels) — Mermaid treats it as a
statement terminator and silently truncates the diagram; never put a bare `<`, `>`, `<=`, or
`>=` inside diagram text — Mermaid tries to parse `<` as the start of an HTML tag. Spell out
"at least," "below," "at most," or use `≤`/`≥` only in prose outside a `mermaid` fence. Run
this self-check before committing a new or edited diagram:

```bash
awk '/^```mermaid/{f=1;next} /^```$/{f=0} f && (/;/ || /<=|>=/){print FILENAME":"FNR": "$0}' path/to/file.md
```

**Documentation and commit style** (verbatim, `AGENTS.md`): keep everything in English,
matching the rest of the repository, regardless of what language a request arrives in; no
emoji unless explicitly asked for; when you fix a cross-file inconsistency, fix it
everywhere it appears — a grep for the stale term/field name across the whole repo before
considering the fix done is standard practice here, not extra credit.

## Governance

This constitution supersedes every other practice document in this repository for any
conflict about *how* engineering decisions get made. It does not supersede
`base/Churn-Sentiment-Agent-Product-Specification.md` as the source of *what* is being
built: the base spec is the original product brief, and everything else in the repository
derives from it (verbatim, `AGENTS.md`). **If a requirement, this constitution, or any
architecture document ever seem to disagree with the base spec, that is a bug to fix, not a
judgment call to make silently — flag it.**

**Amendment procedure:** propose the change, update this file (including a fresh Sync
Impact Report at the top), propagate the change to every dependent artifact listed in the
Sync Impact Report's "Templates requiring updates" checklist, and record the version bump
with its rationale. Amendments are reviewed the same way code is: as a pull request, not a
silent edit.

**Versioning policy** (semantic versioning applied to this document):
- **MAJOR** — a backward-incompatible removal or redefinition of a principle (e.g. relaxing
  P1's evidence requirement, or permitting a send capability under P4).
- **MINOR** — a new principle or materially expanded section added (e.g. a new module's
  quality gate).
- **PATCH** — clarifications, wording, typo fixes, non-semantic refinements.

**Compliance review:** every plan produced by `/speckit-plan` must pass the Constitution
Check gate before Phase 0 research and again after Phase 1 design; any violation of a Core
Principle must be justified in that plan's Complexity Tracking table or the plan does not
proceed. Every PR that touches `backend/app/ledger/` or `backend/app/scoring/` must show a
passing golden-replay run (P9) before merge. `AGENTS.md` remains the living, contributor-
facing companion to this constitution — read it before touching code; where it states a
mechanical enforcement detail (a `CHECK` constraint, a CI script, a foreign-key rule), that
detail is binding, not illustrative.

**Version**: 1.1.0 | **Ratified**: 2026-08-13 | **Last Amended**: 2026-08-13
