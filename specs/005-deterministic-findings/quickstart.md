# Quickstart: Validating Deterministic Findings

Prerequisites: the stack from features 001–004 running, seeded, and the Meridian
fixture already collected and scored (`specs/004-score-engine/quickstart.md`'s
steps). This feature adds one new environment prerequisite:

```bash
# New: Recurrence reader's embedding provider (research.md's Decision)
echo "OPENAI_API_KEY=sk-..." >> .env
docker compose up --build -d   # picks up the new env var
```

## 1. Confirm the fixture gap fix

This feature adds `zendesk-456-created` to `demo/fixtures/meridian-week.json`
(`research.md`'s Decision — real clustering needs two related items, and the
fixture previously only had ticket #456's reopening, never its creation).

```bash
docker compose exec api python scripts/run_collector.py --source simulated
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT re.source_native_id, e.occurred_at FROM events e \
      JOIN raw_envelopes re ON re.id = e.envelope_id \
      WHERE e.structured_payload->>'ticket_number' = '456' ORDER BY e.occurred_at;"
```

**Expected**: two rows — `zendesk-456-created` (earlier) then `zendesk-456-
reopened` (later, already real since feature 003).

## 2. Run all five readers

```bash
docker compose exec api python scripts/run_readers.py
```

**Expected**: prints a per-reader summary (findings emitted, or the isolated
failure message if `OPENAI_API_KEY` is missing — FR-014a; the other four readers'
counts still show real numbers even if Recurrence fails).

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT reader_type, finding_type, status, cited_event_ids FROM findings \
      ORDER BY created_at;"
```

**Expected**: 6 rows, all `status = pending_validation` — `broken_response_
promise` (Commitment), `commitment_met` (Commitment), `usage_deviation` (Usage),
`contact_absence` (Absence), `relationship_change` (Relationship),
`recurring_issue` (Recurrence, citing two events — `data-model.md`'s corrected
citation).

## 3. Confirm rollups were actually computed

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT subject_type, metric, count(*) FROM rollups GROUP BY 1, 2;"
```

**Expected**: non-empty — `rollups` has been unpopulated since feature 001's
migration until this feature's first run (`specs/003-ingestion-and-context/
spec.md`'s documented deferral).

## 4. Confirm the cache — re-run produces nothing new

```bash
docker compose exec api python scripts/run_readers.py
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT count(*) FROM findings;"
```

**Expected**: same count as step 2 — REQ-M5-15's per-`(event, reader_version)`
cache means a second run over an unchanged ledger adds nothing.

## 5. Confirm reader failure isolation

```bash
docker compose exec api sh -c "OPENAI_API_KEY=invalid python scripts/run_readers.py"
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT reader_type, count(*) FROM findings GROUP BY 1;"
```

**Expected**: Recurrence's own findings count doesn't grow (no new ones, since
its API call fails), but Commitment/Usage/Absence/Relationship's counts are
unaffected — the run script reports Recurrence's failure explicitly rather than
crashing or silently succeeding (FR-014a).

## 6. Confirm findings stay invisible to scoring

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT count(*) FROM score_contributions sc \
      JOIN score_runs sr ON sr.id = sc.score_run_id \
      WHERE sr.id = (SELECT id FROM score_runs ORDER BY computed_at DESC LIMIT 1) \
      AND sc.finding_id IN (SELECT id FROM findings WHERE status = 'pending_validation');"
```

**Expected**: `0` — `RecomputeScoreUseCase.list_validated()` correctly ignores
every `pending_validation` finding this feature produces; the score is unaffected
by this feature's real findings until feature 007's validation gate promotes them.

## Automated coverage

Same host-checkout pattern feature 004 established (`api`/`worker` images are
slim runtime builds without dev dependencies):

```bash
cd backend
uv run ruff check .
uv run mypy app
uv run lint-imports --config ../.importlinter
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:${DB_PORT:-5432}/agentic_churn" \
ENCRYPTION_KEY_PATH="../secrets/data.key" \
CLIENT_PROFILE_PATH="../demo/client-profile.yaml" \
COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \
OPENAI_API_KEY="sk-..." \
uv run pytest tests/golden_replay/ tests/readers/ tests/scoring/ tests/unit/ -v
```

**Expected**: every reader's unit tests pass without a live OpenAI call
(`EmbeddingPort` is faked in tests, `research.md`'s Technical Context), plus
`test_run_readers_use_case.py`'s real-DB integration test reproducing
`data-model.md`'s worked-example table.
