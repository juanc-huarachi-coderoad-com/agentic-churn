# Quickstart: Validating Model Findings

Prerequisites: the stack from features 001–006 running, seeded, and the
Meridian fixture already collected (`specs/005-deterministic-findings/
quickstart.md`'s steps). This feature adds two new environment
prerequisites:

```bash
# New: Tone/Intent readers' model provider (research.md's Decision 1)
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo "READER_MODEL_ID=claude-haiku-4-5-20251001" >> .env
docker compose up --build -d   # picks up the new env vars
```

Steps 1–2 and 5–8 below need no live Anthropic call and are runnable exactly
as written. Steps 3–4 need a real `ANTHROPIC_API_KEY` to observe a genuine
model response against real/synthetic text — without one, `scripts/
run_readers.py` still runs cleanly end to end, but Tone/Intent report their
own isolated failure (step 8) instead of a live classification, the same
honest-failure behavior Recurrence already has for a missing
`OPENAI_API_KEY`.

## 1. Confirm the two new finding types are seeded

`data-base/11-seed-data.sql` runs once at provisioning time (feature 001's
established pattern, not re-run against an already-seeded database) — this
feature adds two rows to its existing `finding_type_config` `INSERT`. On a
fresh stack, re-provision to pick them up; on an already-running one, apply
just the two new rows directly:

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT finding_type, base_points, confidence_floor FROM finding_type_config \
      WHERE finding_type IN ('escalation_language','competitive_mention','contractual_reference');"
```

**Expected**: 3 rows — `competitive_mention`/`contractual_reference` now exist
alongside the already-seeded `escalation_language`, matching
`data-model.md`'s table exactly (Clarifications, 2026-08-15).

## 2. Confirm Ana's baseline (no baseline yet → Tone abstains)

```bash
docker compose exec api python scripts/run_readers.py
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT reader_type, finding_type FROM findings WHERE reader_type = 'tone';"
```

**Expected**: 0 rows. `baseline_confirmations` is still empty — REQ-M5-04/
REQ-M6-CAL-04's "no history, no opinion" abstention, proven honestly against
the real fixture rather than assumed.

```bash
docker compose exec api python scripts/confirm_baseline.py \
  --stakeholder ana --metric email_style --window-days 60
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT stakeholder_id, metric, window_start, window_end FROM baseline_confirmations;"
```

**Expected**: 1 row — the first `baseline_confirmations` row this codebase
has ever had (table exists since feature 001, unpopulated until now,
`research.md` Decision 3). The real Meridian fixture's messages
(`demo/fixtures/meridian-week.json`) are all dated before this confirmation's
window closes (the fixture is a fixed historical scenario, "now" is the real
wall clock) — so Tone still won't find a *new* message to evaluate against
this baseline. This is the honest, structural reason the positive case
(step 3) uses a synthetic fixture instead of the real one, not a gap in this
feature.

## 3. Tone's positive case — automated test, not a live script run

The real Meridian fixture can never exercise Tone's positive path live (step
2's date-alignment note) — this case is covered by
`tests/readers/test_tone_reader.py` against
`tests/fixtures/tone_baseline_sufficient.json`, with `LLMPort` faked (no live
Anthropic call needed to prove the reader's own logic is correct):

```bash
cd backend && uv run pytest tests/readers/test_tone_reader.py -v
```

**Expected**: all 5 tests pass, including
`test_emits_finding_when_baseline_sufficient_and_message_deviates` — a
`tone_deterioration` finding with `magnitude`/`confidence` as two distinct
numbers, matching `examples/01-end-to-end-walkthrough.md` §6's `fnd-6` shape.
To see a *live* model call instead of the fake, run `scripts/run_readers.py`
against a deployment whose confirmed baseline window includes real messages
newer than the window itself (a live/ongoing deployment, not this fixed
historical fixture).

## 4. Intent against Ana's real "brief the board" email

```bash
docker compose exec api python scripts/run_readers.py
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT reader_type, finding_type, status, cited_event_ids FROM findings WHERE reader_type = 'intent';"
```

**Expected** (with a real `ANTHROPIC_API_KEY` configured): 1 row —
`escalation_language`, `status = validated`, citing the real Gmail event for
"Please advise on the timeline. I need to brief the board on Thursday."
(`examples/01-end-to-end-walkthrough.md` §6's `fnd-7`). Without a real key,
see step 8 instead — the `Automated coverage` section's
`test_run_readers_use_case.py` reproduces this exact case with `LLMPort`
faked, content-aware on the real message text.

## 5. Confirm the gate quarantines a genuinely bad finding

```bash
cd backend && uv run pytest tests/readers/test_run_readers_use_case.py::test_gate_quarantines_a_bad_finding_via_the_real_sql_adapters -v
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT f.status, q.failed_check, vf.expected, vf.actual FROM findings f \
      JOIN quarantine q ON q.finding_id = f.id \
      JOIN validation_failures vf ON vf.quarantine_id = q.id \
      ORDER BY f.created_at DESC LIMIT 1;"
```

**Expected**: `status = quarantined`, `failed_check = confidence_below_floor`,
`expected = '>= 0.65'`, `actual = '0.55'` — reproducing
`examples/01-end-to-end-walkthrough.md` §7's `fnd-10`/`q-1` worked example
against the real SQL-backed gate adapters (`FindingTypeConfigPort`,
`EventExistencePort`, `QuarantineRepositoryPort`), not just the pure
functions `test_validation_gate.py` already covers.

## 6. Confirm the System health screen now shows it

```bash
TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:${API_PORT:-8000}/api/coverage | jq .quarantine
```

**Expected**: a non-empty array — `GET /api/coverage`'s `quarantine` field
(feature 006's contract) is real for the first time (REQ-M5A-04), not the
permanently-empty list feature 006 shipped (found during this feature's own
verification: `SqlAlchemyCoverageReader.list_quarantine()` was still
hardcoded to `return []` even after the gate was wired in — a real
implementation gap, fixed as part of this feature, not left for later).

## 7. Confirm a validated finding is now visible to scoring

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT count(*) FROM score_contributions sc \
      JOIN score_runs sr ON sr.id = sc.score_run_id \
      WHERE sr.id = (SELECT id FROM score_runs ORDER BY computed_at DESC LIMIT 1) \
      AND sc.finding_id IN (SELECT id FROM findings WHERE status = 'validated');"
```

**Expected**: > 0 — closing the gap `specs/005-deterministic-findings/
quickstart.md` step 6 documented ("the score is unaffected by this feature's
real findings until feature 007's validation gate promotes them"). This is
that promotion, proven end to end for all eight readers, not just Tone/Intent.

## 8. Confirm a missing model key is reported honestly, not silently absorbed

```bash
docker compose exec api sh -c "ANTHROPIC_API_KEY= python scripts/run_readers.py"
```

**Expected**: `intent: findings_persisted=0 findings_quarantined=0 FAILED —
ANTHROPIC_API_KEY is not configured ...` — the same honest, reader-level
failure Recurrence already reports for a missing `OPENAI_API_KEY`, never a
silently-empty "0 findings, nothing to report" run that would be
indistinguishable from a genuinely healthy one (a real design correction made
during this feature's own verification against the live container — the
first draft caught this exception per-message and abstained silently instead
of surfacing it, masking a misconfigured deployment as a quiet, healthy one).
Tone reports no error in this same run only because no candidate message
exists after its confirmed baseline window in this fixed historical fixture
(step 2) — it never reaches the point of calling the model at all.
Commitment/Usage/Absence/Relationship's own findings are unaffected
(FR-014).

## Automated coverage

Same host-checkout pattern features 004/005 established:

```bash
cd backend
uv run ruff check .
uv run mypy app
uv run lint-imports --config ../.importlinter
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:${DB_PORT:-5432}/agentic_churn" \
ENCRYPTION_KEY_PATH="../secrets/data.key" \
CLIENT_PROFILE_PATH="../demo/client-profile.yaml" \
COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \
uv run pytest tests/golden_replay/ tests/readers/ tests/scoring/ tests/unit/ tests/experience/ -v
```

**Expected**: every Tone/Intent/gate unit test passes without a live
Anthropic call (`LLMPort` is faked in tests, matching `EmbeddingPort`'s
existing fake-in-tests precedent, `architecture/08`'s golden-replay design),
plus `test_run_readers_use_case.py`'s real-DB integration tests now asserting
`validated`/`quarantined` outcomes instead of feature 005's blanket
`pending_validation` assertion (`specs/ROADMAP.md`'s feature 006 log entry
already flagged this exact assertion as needing to change once feature 007's
gate exists) — including a live reproduction of Ana's real "brief the board"
email producing a validated `escalation_language` finding, `LLMPort` faked
but content-aware on the real message text.
