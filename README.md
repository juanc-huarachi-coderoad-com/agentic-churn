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
scaffold, CI pipeline, Docker Compose stack, database schema), **Dashboard Shell**
(Phase 2 — full authentication and a dashboard shell proving the stack works end to
end), **Ingestion and Context** (Phase 3 — the event ledger, client profile, and
signal collectors: the first modules with real business logic), and **Score Engine**
(Phase 4 — "the checkpoint": per-finding weighting, issue-relative ranking, band
classification with hysteresis, all proven against a hand-authored fixture before any
reader module exists). See `specs/ROADMAP.md` for the full feature-by-feature status.

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

## Ingestion and Context (Phase 3)

One extra one-time setup step beyond the base quickstart above: a local encryption key
for message-body encryption (REQ-M1-P4 — never optional, never deferred).

```bash
mkdir -p secrets
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/data.key
docker compose up --build -d   # picks up the new ./secrets and ./demo mounts
```

The CS lead's hand-authored client profile lives at `demo/client-profile.yaml`; the
signal-collector fixture lives at `demo/fixtures/meridian-week.json`. See
`specs/003-ingestion-and-context/quickstart.md` for the full validation walkthrough —
profile versioning, hash-chain/business-hours arithmetic, `SimulatedCollector` runs
(idempotency, identity resolution, redaction), and absence detection.

## Score Engine (Phase 4)

Findings are still hand-authored/fixture-seeded here — no reader module exists yet
(that's build-order Phase 5). This feature proves `score_runs`/`score_contributions`/
`band_history` computation for real: per-finding weighting, issue-relative ranking with
diminishing rank weight, recency by lifecycle state, the positive-signal cap, the
saturating points→score conversion, and band classification with hysteresis and
2-consecutive-run stickiness.

```bash
docker compose exec api python scripts/run_collector.py --source simulated
docker compose exec api python scripts/seed_score_fixture.py
docker compose exec api python scripts/compute_score.py   # run twice to settle the band
```

Three real recomputation triggers are wired: `manual` (the script above),
`hourly_heartbeat` (`app/worker.py`'s APScheduler job), and `profile_edit_replay`
(fires automatically after a profile edit via `SubmitProfileUseCase`). See
`specs/004-score-engine/quickstart.md` for the full validation walkthrough, including
the exact worked-example numbers and the source-degraded freeze path.
