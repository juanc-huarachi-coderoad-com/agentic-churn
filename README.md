# Agentic Churn

A dedicated monitoring agent for **one client relationship**. It reads signals that
already exist across email, chat, tickets, and product usage, notices when the
relationship is deteriorating, explains why with evidence, and proposes what to do next.
A human always decides and always sends.

## Where things live

Read `AGENTS.md` first if you're touching code — it points at the actual specification
and lists which rules are non-negotiable. In short:

| Looking for... | Go to |
|---|---|
| What a module (M1–M10) is supposed to do | `requirements/<module>.md` |
| Why a technical decision was made | `architecture/`, `decisions/` |
| Exact table schemas | `data-base/10-ddl-appendix.md` |
| The full product brief | `base/Churn-Sentiment-Agent-Product-Specification.md` |
| Project principles and governance | `.specify/memory/constitution.md` |
| The build order and current feature status | `specs/001-project-foundation/` (this repo's first spec-kit feature; see `AGENTS.md` and the constitution for how later features are structured) |

This repository currently contains **Project Foundation** (build-order Phase 1 — repo
scaffold, CI pipeline, Docker Compose stack, database schema) and **Dashboard Shell**
(Phase 2 — full authentication and a dashboard shell proving the stack works end to
end). No product feature (M1–M10) is implemented yet; that starts in Phase 3 onward. See
`specs/ROADMAP.md` for the full feature-by-feature status.

## Quickstart

Prerequisites: Docker. Nothing else — that's the entire point of this feature
(`specs/001-project-foundation/spec.md` User Story 1).

```bash
git clone <repo> && cd agentic-churn
cp .env.example .env   # edit values for a real deployment; defaults work for local dev
docker compose up --build
```

**Expected**: the `api`, `worker`, `db`, and `web` containers all report healthy —
`docker compose ps` shows `healthy` for each. `web` is served at
`http://localhost:${WEB_PORT:-5173}`, the API health check at
`http://localhost:${API_PORT:-8000}/health`.

### Verify the schema

```bash
docker compose exec api alembic current
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"
```

The table list should match `data-base/10-ddl-appendix.md`'s `CREATE TABLE` statements
1:1. Seed data (`data-base/11-seed-data.sql`) is applied separately:

```bash
docker compose exec api python scripts/seed.py
```

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT count(*) FROM finding_type_config;"   # non-zero once seeded
```

### Login

Once seeded, log in at `http://localhost:${WEB_PORT:-5173}` with username `marta`,
password `agentic-demo-2026` — a local/demo-only credential, never treated as a secret
(`specs/002-dashboard-shell/research.md` §Decision: Regenerating the seeded demo
password hash). You'll land on a dashboard shell showing the seeded client's name and
an honest "still learning" state — see `specs/002-dashboard-shell/quickstart.md` for the
full auth flow (token issuance, revocation, rate limiting) exercised via `curl`.

### Persistence

```bash
docker compose down && docker compose up
```

Schema and seed data persist across a restart — no manual migration step required.

### Reset cleanly

```bash
docker compose down -v   # drops the db_data volume — full reprovision on next `up`
```

See `specs/001-project-foundation/quickstart.md` for the full validation walkthrough,
including the CI-gate and test-harness checks (User Stories 2 and 3).
