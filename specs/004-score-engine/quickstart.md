# Quickstart: Validating the Score Engine

Prerequisites: the stack from features 001–003 running, seeded, and the Meridian
fixture already collected (`specs/003-ingestion-and-context/quickstart.md`'s steps 1–3
— a client profile must be current and real MVP-source events must exist in the ledger
before this feature's fixture can cite them).

```bash
docker compose up --build -d
docker compose exec api python scripts/seed.py            # if not already seeded
docker compose exec api python scripts/run_collector.py --source simulated  # if not already run
```

## 1. Load the score-engine proof fixture

```bash
docker compose exec api python scripts/seed_score_fixture.py
```

**Expected**: prints the resolved real event IDs it cited for six of the nine
findings, confirms it triggered `DetectAbsenceUseCase` for a seventh, confirms it
inserted one synthetic `survey_response` event for the CSAT finding, then reports `9
findings inserted, 2 issues, 8 finding_issue_map rows`.

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT finding_type, status, state FROM findings ORDER BY created_at;"
```

**Expected**: 9 rows, all `status = validated`, all `state` currently `NULL` (not
scored yet).

## 2. Compute the score and check the worked example, exactly

```bash
docker compose exec api python scripts/compute_score.py
```

**Expected**: `band=at_risk`. The exact `score`/`total_points` depend on *when* you
run this: `demo/fixtures/meridian-week.json`'s events carry fixed calendar
timestamps (ticket #456 reopened `2026-08-10T07:40:00-05:00`, never resolved in this
static fixture), and `compute_score.py` uses real wall-clock time as `as_of` by
default (REQ-M6-09) — so the longer ticket #456 has been open by the time you run
this, the more overdue it is, and the higher (worse) the score. The pinned,
byte-exact worked example — `as_of` fixed to the exact moment `examples/01` §9's own
narrative describes ("we took 19 hours to respond to ticket #456; we promised 4") —
is `backend/tests/scoring/test_worked_example.py`, which reproduces
`total_negative_points = 68.0140648`, `total_points = 64.0140648`, `score = 85.627`
(stored as `68.014` / `64.014` / `85.63` in `score_runs`' `NUMERIC(10,3)`/
`NUMERIC(5,2)` columns) to the decimal, deterministically, regardless of when the
test suite runs. Every finding *except* `broken_response_promise` (fnd-1, the only
time-sensitive one in this fixture) reproduces those exact figures on a live run
too — only fnd-1's `recency`/`points_contributed` will differ from the pinned test.

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT finding_type, points_contributed, is_positive FROM score_contributions sc \
      JOIN findings f ON f.id = sc.finding_id ORDER BY points_contributed DESC;"
```

**Expected**: 9 rows; `broken_response_promise` highest (exactly `39.000` only if run
within the pinned calibration window above — otherwise higher, up to the `2.0`
ageing cap); `commitment_met` the only `is_positive = true` row at `4.000`; every
other row matches the pinned test exactly (`escalation_language` `9.520`,
`usage_deviation` `6.683`, `contact_absence` `5.141`, `recurring_issue` `2.916`,
`tone_deterioration` `2.765`, `csat_deviation` `1.642`, `relationship_change`
`0.348`).

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT state FROM findings WHERE finding_type = 'broken_response_promise';"
```

**Expected**: `open_overdue` — set by this run, was `NULL` before.

## 3. Confirm the band needs two runs to display, then holds under hysteresis

```bash
docker compose exec api python scripts/compute_score.py   # second consecutive run
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT band, consecutive_runs_in_band FROM band_history ORDER BY created_at;"
```

**Expected**: both rows `band = at_risk` (this fixture's score is decisively above
the 65 threshold from the very first run, so there's no raw-band change to observe
here) — but `consecutive_runs_in_band` reads `1` then `2`: `band_history`'s own
qualifying-streak counter takes two runs to reach `2` regardless of whether the
*displayed* band ever changes (a first-ever run displays its raw band immediately,
per `BandClassifier`'s bootstrap case — see `test_band_classifier.py`'s
`test_first_ever_run_displays_raw_band_immediately`). To see an actual band
*change* gated by the 2-consecutive-run stickiness (REQ-M6-19), you'd need a
pre-existing `healthy`/`watch` `score_runs` row before this fixture's findings push
the score up — `test_band_classifier.py`'s
`test_new_candidate_band_does_not_display_until_second_confirming_run` and
`test_sequences_06_worked_example_week_1_stays_at_risk` exercise that scenario
directly against the domain service, without needing a live multi-day fixture.

## 4. Confirm reconciliation and monotonicity for real (not just the fixture)

The `api`/`worker` images are slim runtime builds (`multi-stage-dockerfile` —
no `pytest`/`hypothesis`/dev dependencies baked in by design), so tests run from a
host checkout against the same Postgres the stack uses, matching `workflows/ci.yml`'s
own pattern exactly:

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:${DB_PORT:-5432}/agentic_churn" \
ENCRYPTION_KEY_PATH="../secrets/data.key" \
CLIENT_PROFILE_PATH="../demo/client-profile.yaml" \
COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \
uv run pytest tests/scoring/ -v
```

**Expected**: `test_reconciliation.py` and `test_monotonicity.py` (previously skipped
placeholders) now pass for real, alongside `test_worked_example.py`,
`test_recompute_score_use_case.py`, `test_scoring_calculator.py`,
`test_band_classifier.py`, `test_ageing_calculator.py`, `test_damping_calculator.py`,
and `test_issue_grouper.py`.

## 5. Confirm the three real recomputation triggers

```bash
# hourly heartbeat — force it rather than waiting an hour
docker compose exec worker python -c "from app.worker import _run_score_recompute; _run_score_recompute()"

# profile-edit trigger
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -X POST http://localhost:8000/api/profile/reload -H "Authorization: Bearer $TOKEN"

docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT trigger, score, band FROM score_runs ORDER BY computed_at;"
```

**Expected**: additional `score_runs` rows appear with `trigger = hourly_heartbeat` and
`trigger = profile_edit_replay`, each recomputed from zero (not derived from the prior
row).

## 6. Confirm the source-degraded freeze

```bash
# Simulate a degraded run by recording a coverage report with sources_read < sources_expected
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "INSERT INTO coverage_reports (collector_run_id, sources_expected, sources_read, gap_reason, complete_to) \
      SELECT id, 3, 2, 'quickstart test', now() FROM collector_runs ORDER BY started_at DESC LIMIT 1;"
docker compose exec api python scripts/compute_score.py
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT is_frozen, source_degraded, score FROM score_runs ORDER BY computed_at DESC LIMIT 1;"
```

**Expected**: `is_frozen = true`, `source_degraded = true`, `score` unchanged from the
prior run's value — not recomputed on the incomplete picture.

## Automated coverage

Same host-checkout pattern as step 4 above (`workflows/ci.yml`'s `lint`/`type-check`/
`test` jobs run these identically, against a fresh, empty database rather than this
walkthrough's populated one):

```bash
cd backend
uv run ruff check .
uv run mypy app
uv run lint-imports --config ../.importlinter
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:${DB_PORT:-5432}/agentic_churn" \
ENCRYPTION_KEY_PATH="../secrets/data.key" \
CLIENT_PROFILE_PATH="../demo/client-profile.yaml" \
COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \
uv run pytest tests/golden_replay/ tests/scoring/ tests/unit/ -v
```
