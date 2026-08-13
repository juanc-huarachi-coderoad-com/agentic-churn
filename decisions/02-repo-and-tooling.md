# 02 · Repository and tooling decisions

| | |
|---|---|
| **Document** | Decision record — closes the tooling gaps flagged in the pre-build consistency review |
| **Status** | Approved for Phase 1 build start |
| **Date** | 2026-08-11 |
| **Depends on** | `architecture/03-technology-stack.md` (the stack itself); this document is *how the stack sits in the repo*, not what the stack is |
| **Refined by** | `architecture/09-clean-architecture-and-patterns.md` — the layout below now reflects that document's three-ring layering (Domain / Application / Adapters, package-by-module) |

Everything described here — the monorepo layout, CI pipeline, migrations — is exactly what build order **Phase 1: Project Foundation** (`base/Churn-Sentiment-Agent-Product-Specification.md` §16, v1.2) delivers. This document is that phase's detail; §16 is the one-line summary.

## Monorepo layout

One repository, one Docker Compose stack per deployment (`architecture/03-technology-stack.md`), structured by module (M1–M10, the vocabulary every other document in this repo already uses) with the same three rings inside each module — Domain (pure business rules), Application (use cases + ports), Adapters (everything that touches a framework, database, or SDK). Full rationale: `architecture/09-clean-architecture-and-patterns.md`.

```
/
├── backend/
│   ├── app/
│   │   ├── ingestion/              # M1
│   │   │   ├── application/        # CollectorPort, EventRepositoryPort, IdentityResolver
│   │   │   └── adapters/           # GmailCollector, ZendeskCollector, WarehouseCollector,
│   │   │                           #   SlackCollector, AbsenceCollector, SqlAlchemyEventRepository
│   │   ├── readers/                 # M5, M5a
│   │   │   ├── application/        # Reader subclasses (all 8), ValidationGate, RunReadersUseCase,
│   │   │   │                       #   LLMPort, EmbeddingPort
│   │   │   └── adapters/           # AnthropicLLMAdapter, OpenAIEmbeddingAdapter
│   │   ├── context/                 # M3, M4
│   │   │   ├── domain/             # ClientProfile, Stakeholder, ProductArea, DampingWeight
│   │   │   ├── application/        # ClientProfileRepositoryPort, DampingCalculator caller
│   │   │   └── adapters/           # YAML parser (MVP), SqlAlchemy repository
│   │   ├── scoring/                 # M6 — the module the "zero LLM imports" rule originated in
│   │   │   ├── domain/             # ScoringCalculator, BandClassifier, DampingCalculator,
│   │   │   │                       #   AgeingCalculator, IssueGrouper — zero I/O, zero ports
│   │   │   ├── application/        # FindingRepositoryPort, ScoreRunRepositoryPort,
│   │   │   │                       #   RecomputeScoreUseCase
│   │   │   └── adapters/           # SqlAlchemyFindingRepository, SqlAlchemyScoreRunRepository
│   │   ├── narrator/                # M7
│   │   ├── experience/              # M8, M9, M10 — dashboard read API, ask agent, draft composer
│   │   ├── auth/                    # requirements/14-authentication.md
│   │   └── worker.py                # APScheduler heartbeat + LISTEN/NOTIFY consumer
│   ├── migrations/                  # Alembic
│   └── tests/
├── frontend/
│   └── src/
│       ├── dashboard/        # M8
│       ├── ask/               # M9
│       ├── draft-composer/    # M10
│       └── profile-editor/    # M3, Post-MVP
├── data-base/                 # this documentation folder — DDL/seed data are the schema's source of truth
├── decisions/, requirements/, architecture/, sequences/, examples/  # documentation, unchanged
├── demo/                      # demo/01-live-demo-runbook.md and friends
├── tests/                     # cross-cutting: golden-replay fixtures, integration tests
├── workflows/                 # CI pipeline definition (workflows/ci.yml)
├── .importlinter               # layer-boundary contracts, see §CI enforcement below
├── docker-compose.yml
├── AGENTS.md
└── .env.example
```

Not every module needs all three rings on day one — `narrator/` and `experience/` are thin enough in the MVP that Application and Adapters may be the only two that exist until there's genuine domain logic to isolate. Adding a `domain/` folder before there's a pure business rule to put in it would be exactly the premature abstraction `architecture/09-clean-architecture-and-patterns.md` §YAGNI warns against.

### Module → package mapping

| Module | Package | Notes |
|---|---|---|
| M1 Signal collectors | `backend/app/ingestion/adapters/{gmail,zendesk,warehouse,slack}_collector.py` | One adapter per source, all implementing `Collector`'s template method (`architecture/08-class-diagrams.md`) |
| M2 Event ledger | `backend/app/ingestion/application/event_repository_port.py` + `backend/app/ingestion/adapters/sqlalchemy_event_repository.py` | Projections/replay logic (`events.py`, `projections.py`, `replay.py`, `hash_chain.py`) sit in `ingestion/application/` — they're pure orchestration over the port, not adapter-specific |
| M3 Client profile | `backend/app/context/adapters/yaml_profile_loader.py` | YAML parse + validate (MVP) / API write (Post-MVP) |
| M4 Feedback memory | `backend/app/context/domain/damping_calculator.py` | Implements the damping formula from `requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-03 — pure function, no I/O |
| M5/M5a Readers + gate | `backend/app/readers/application/{commitment,usage,recurrence,absence,relationship,tone,intent,meeting}_reader.py`, `.../validation_gate.py` | Deterministic and LLM readers live side by side but never import each other; only three import `LLMPort` |
| M6 Scoring engine | `backend/app/scoring/domain/scoring_calculator.py` | **`import-linter`-checked (see below) to have zero imports outside `app.scoring.domain`** |
| M7 Narrator | `backend/app/narrator/` | |
| M8/M9/M10 | `backend/app/experience/{dashboard,ask,drafts}.py` | Thin read/orchestration layer behind `architecture/07-api-spec.md` |
| Auth | `backend/app/auth/` | `requirements/14-authentication.md` |

## Package managers

| Layer | Tool | Why |
|---|---|---|
| Python (backend) | **uv** | Fast, single-binary, lockfile-based; replaces pip+venv+pip-tools with one tool — matches "remove the difficulty" |
| JavaScript (frontend) | **pnpm** | Disk-efficient, strict dependency resolution (won't silently let the frontend import a package it didn't declare) |

## ORM and migrations

- **SQLAlchemy 2.0** (async) as the ORM, mapped directly onto the tables in `data-base/10-ddl-appendix.md` — the DDL in that file is the source of truth; SQLAlchemy models are generated to match it, not the other way around.
- **Alembic** for migrations. The very first migration is a straight import of `data-base/10-ddl-appendix.md`'s DDL; every schema change afterward is a new Alembic revision, keeping `data-base/` and the running schema from drifting apart.
- Seed data (`data-base/11-seed-data.sql`) is applied via a dedicated `scripts/seed.py`, never folded into a migration — migrations change structure, seeding changes data, and conflating them makes both harder to reason about.

## Claude model ID pinning

Every LLM call in the system (`architecture/04-ai-safety-and-model-usage.md`) pins an **exact** model ID in config, never a floating alias, so a model-provider-side update can't silently change reader behavior mid-deployment:

| Role | Pinned model ID | Config key |
|---|---|---|
| Tone / Intent / Meeting readers (high-volume, structured output) | `claude-haiku-4-5-20251001` | `READER_MODEL_ID` |
| Narrator / Ask agent / Draft composer (higher-stakes generation) | `claude-sonnet-5` | `GENERATION_MODEL_ID` |

Changing either value is treated exactly like a prompt version change (`architecture/04-ai-safety-and-model-usage.md` Rule 5): tracked, and triggers a full replay so score history stays explainable against the model version that actually produced it.

## Charts: visx vs. Recharts — resolved

`architecture/03-technology-stack.md` left this as an either/or. Resolved: **Recharts.** Reasoning: the dashboard's chart surface area is deliberately tiny (spec §11.7 — sparkline and trend line, nothing else), so visx's lower-level, more composable API buys flexibility the product explicitly doesn't need, at the cost of writing more code for the same two chart types. Recharts' declarative components get the sparkline and trend line built faster with less custom code to maintain.

## Recurrence reader clustering library

**`hdbscan`** (the reference Python implementation), run over OpenAI `text-embedding-3-small` vectors (`architecture/03-technology-stack.md`). Chosen over a from-scratch DBSCAN implementation or k-means because HDBSCAN doesn't require pre-specifying the number of clusters — appropriate here, since the number of "same underlying issue" clusters in a given window is exactly the thing being discovered, not known in advance.

## Warehouse connector

The warehouse source (`requirements/01-signal-collectors.md`) is read via a generic **SQLAlchemy read-only connection string**, not a bespoke SDK — product usage telemetry lives in a client's own analytics warehouse (Snowflake, BigQuery, Postgres, Redshift are all SQLAlchemy-dialect-supported), and the collector only ever needs to run one parameterized query per sync (`SELECT metric, value, window_start, window_end FROM <client-provided view>`). This keeps M1's warehouse adapter a single, source-agnostic implementation instead of one per warehouse vendor.

## CI enforcement of the layer boundary (generalizes the "no LLM in scoring" rule)

This started as a single bespoke AST-walking script scoped to `app.scoring`. `architecture/09-clean-architecture-and-patterns.md` generalizes it: every module's Domain and Application rings get the same guarantee, declaratively, via **`import-linter`** — one `.importlinter` config file at the repo root instead of a hand-rolled script per module:

```ini
# .importlinter
[importlinter]
root_package = app

[importlinter:contract:scoring-domain-purity]
name = Scoring domain never imports adapters or AI SDKs
type = forbidden
source_modules =
    app.scoring.domain
forbidden_modules =
    anthropic
    openai
    sqlalchemy
    fastapi
    app.scoring.adapters

[importlinter:contract:readers-application-purity]
name = Reader application layer depends on ports, never concrete AI SDKs
type = forbidden
source_modules =
    app.readers.application
forbidden_modules =
    anthropic
    openai
    app.readers.adapters

[importlinter:contract:global-dependency-rule]
name = No module's domain or application package imports its own adapters package
type = layers
layers =
    app.*.adapters
    app.*.application
    app.*.domain
```

`workflows/ci.yml` runs `lint-imports` as its own job, in place of the old bespoke script. This is the mechanical enforcement behind REQ-M6-P1 and the engineering acceptance criterion "no model call exists anywhere in the scoring engine" (spec §14.3) — now extended to every module, not just scoring — because a code review can miss an import, and a hand-rolled script only checks the one module someone remembered to write it for.

## Traceability

`architecture/09-clean-architecture-and-patterns.md` (the layering and SOLID/patterns rationale this enforcement implements), `architecture/03-technology-stack.md`, `architecture/04-ai-safety-and-model-usage.md`, `architecture/08-class-diagrams.md`, `data-base/10-ddl-appendix.md`, `requirements/13-scoring-calibration-appendix.md`, `tests/strategy.md`.
