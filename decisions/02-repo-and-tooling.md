# 02 · Repository and tooling decisions

| | |
|---|---|
| **Document** | Decision record — closes the tooling gaps flagged in the pre-build consistency review |
| **Status** | Approved for Phase 1 build start |
| **Date** | 2026-08-11 |
| **Depends on** | `architecture/03-technology-stack.md` (the stack itself); this document is *how the stack sits in the repo*, not what the stack is |

## Monorepo layout

One repository, one Docker Compose stack per deployment (`architecture/03-technology-stack.md`), structured by tier:

```
/
├── backend/
│   ├── app/
│   │   ├── ingestion/        # M1 — collectors, absence collector
│   │   ├── ledger/           # M2 — event ledger, projections, replay
│   │   ├── context/          # M3, M4 — client profile, feedback memory
│   │   ├── readers/          # M5, M5a — interpreters, validation gate
│   │   ├── scoring/          # M6 — scoring engine (zero LLM imports, CI-enforced)
│   │   ├── narrator/         # M7
│   │   ├── experience/       # M8, M9, M10 — dashboard read API, ask agent, draft composer
│   │   ├── auth/             # requirements/14-authentication.md
│   │   └── worker.py         # APScheduler heartbeat + LISTEN/NOTIFY consumer
│   ├── migrations/           # Alembic
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
├── docker-compose.yml
├── AGENTS.md
└── .env.example
```

### Module → package mapping

| Module | Package | Notes |
|---|---|---|
| M1 Signal collectors | `backend/app/ingestion/collectors/{gmail,zendesk,warehouse,slack,csat,calendar,salesforce}.py` | One file per source, all implementing the shared `Collector` protocol (`architecture/02-component-catalog.md`) |
| M2 Event ledger | `backend/app/ledger/` | `events.py` (append-only writes), `projections.py`, `replay.py`, `hash_chain.py` |
| M3 Client profile | `backend/app/context/profile.py` | YAML parse + validate (MVP) / API write (Post-MVP) |
| M4 Feedback memory | `backend/app/context/feedback.py` | Implements the damping formula from `requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-03 |
| M5/M5a Readers + gate | `backend/app/readers/{commitment,usage,recurrence,absence,relationship,tone,intent,meeting}.py`, `backend/app/readers/gate.py` | Deterministic and LLM readers live side by side but never import each other |
| M6 Scoring engine | `backend/app/scoring/engine.py` | **CI-checked (see below) to have zero imports of `app.llm` or any Anthropic/OpenAI client** |
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

## CI enforcement of the "no LLM in scoring" boundary

Referenced in `architecture/03-technology-stack.md` but not previously specified as a concrete check. Implemented as a CI step in `workflows/ci.yml`:

```bash
# Fails the build if app.scoring imports anything LLM-related
python -c "
import ast, sys, pathlib
forbidden = {'anthropic', 'openai', 'app.llm'}
for f in pathlib.Path('backend/app/scoring').rglob('*.py'):
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module]
            if any(n and any(n.startswith(f) for f in forbidden) for n in names):
                print(f'FORBIDDEN IMPORT in {f}: {names}'); sys.exit(1)
"
```

This is the mechanical enforcement behind REQ-M6-P1 and the engineering acceptance criterion "no model call exists anywhere in the scoring engine" (spec §14.3) — a code review can miss an import; a CI step can't.

## Traceability

`architecture/03-technology-stack.md`, `architecture/04-ai-safety-and-model-usage.md`, `data-base/10-ddl-appendix.md`, `requirements/13-scoring-calibration-appendix.md`, `tests/strategy.md`.
