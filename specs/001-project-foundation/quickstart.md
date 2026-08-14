# Quickstart: Validating Project Foundation

Runnable validation for this feature's acceptance scenarios (`spec.md`). Prerequisites:
Docker installed, nothing else (this is the entire point of User Story 1).

## 1. Reproducible local environment (User Story 1)

```bash
git clone <repo> && cd agentic-churn
docker compose up --build
```

**Expected**: `api`, `worker`, `db`, and `web` containers all report healthy (Compose
healthcheck backed by `contracts/health-check.md`'s `GET /health`).

Verify the schema matches the DDL source of truth exactly:

```bash
docker compose exec api alembic current      # should show the first (and only) revision
docker compose exec db psql -U <user> -d <db> -c "\dt"   # table list should match
  # data-base/10-ddl-appendix.md's CREATE TABLE statements 1:1
```

Apply and verify seed data (schema provisioning is automatic via the `migrate` service;
seeding stays a deliberate separate step, FR-003):

```bash
docker compose exec api python scripts/seed.py
docker compose exec db psql -U <user> -d <db> -c \
  "SELECT count(*) FROM finding_type_config;"   # non-zero — data-base/11-seed-data.sql applied
```

Restart and confirm persistence (Acceptance Scenario 3):

```bash
docker compose down && docker compose up
# re-run the alembic current / table checks above — nothing should re-migrate
```

## 2. CI blocks architectural violations (User Story 2)

Not run locally by hand — validated by `workflows/ci.yml` on every pull request. To spot-
check the two gates this feature adds:

```bash
lint-imports                 # runs the .importlinter contracts locally, same as CI
# a deliberate violation (e.g. importing anthropic inside backend/app/scoring/domain/)
# must make this command exit non-zero
```

## 3. Test-harness scaffolding is present (User Story 3)

```bash
docker compose exec api pytest tests/golden_replay/ tests/scoring/ -v
```

**Expected**: tests collect and run (even if trivially, against empty fixtures) rather than
the paths being absent — confirms the harness `tests/strategy.md` describes is wired into
CI now, ready for Phase 4/5 to add real content into.

## Troubleshooting

- **Port conflict on `docker compose up`**: stop whatever is bound to the `api`/`db`/`web`
  ports locally, or override the host-side port mapping in a local `.env` (see
  `.env.example`) — do not change the container-internal ports, which other services in
  the Compose network depend on.
- **Stale database volume from a previous run**: `docker compose down -v` removes the data
  volume; re-run `docker compose up` for a clean re-provision. This is the documented
  "wipe and reprovision" path referenced in spec.md's Edge Cases.
