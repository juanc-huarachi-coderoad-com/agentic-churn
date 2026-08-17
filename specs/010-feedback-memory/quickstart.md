# Quickstart: Validating Feedback Memory

Prerequisites: the stack from features 001–007 running, seeded, ingested,
read, and scored (`specs/007-model-findings/quickstart.md`'s steps — no
Narrator/Ask agent/Draft composer dependency, this feature only needs a
`score_run` with at least one validated finding). No new environment
variable, no new Python dependency, and no migration
(`research.md` — `feedback_verdicts`/`damping_weights` have existed since
feature 001).

```bash
docker compose up --build -d
```

## 1. Pick a real finding from the current dashboard

```bash
TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:${API_PORT:-8000}/api/dashboard \
  | jq '.contribution_bars[0]'
# → {"score_contribution_id": "<sc-id>", "label": "broken_response_promise", "points": -20.0, "is_positive": false}

SC_ID=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:${API_PORT:-8000}/api/dashboard \
  | jq -r '.contribution_bars[0].score_contribution_id')

FINDING_ID=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:${API_PORT:-8000}/api/evidence/$SC_ID \
  | jq -r '.finding_id')
```

**Expected**: `disclosure_text` is `null` on this first fetch — nothing has
ever been said about this pattern yet.

## 2. Submit one `false_alarm` verdict

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"finding_id\":\"$FINDING_ID\",\"verdict\":\"false_alarm\"}" \
  http://localhost:${API_PORT:-8000}/api/feedback
# → 204
```

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT pattern_signature, weight, false_alarm_count, disclosure_text FROM damping_weights;"
```

**Expected**: one row, `weight = 0.500`, `false_alarm_count = 1`,
`disclosure_text` non-empty (REQ-M6-CAL-03a's first worked value).

## 3. Re-fetch the evidence trace — the disclosure is now visible

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:${API_PORT:-8000}/api/evidence/$SC_ID \
  | jq '{finding_id, disclosure_text}'
```

**Expected**: `disclosure_text` is now the plain-language reason (e.g.
"weight reduced — your team dismissed this pattern twice" or the
first-dismissal equivalent) — FR-011, no black box.

## 4. A second `false_alarm` on the same pattern damps further

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"finding_id\":\"$FINDING_ID\",\"verdict\":\"false_alarm\"}" \
  http://localhost:${API_PORT:-8000}/api/feedback

docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT weight, false_alarm_count FROM damping_weights;"
```

**Expected**: `weight = 0.250`, `false_alarm_count = 2` (REQ-M6-CAL-03a's
second worked value).

## 5. A `correct` verdict partially recovers trust

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"finding_id\":\"$FINDING_ID\",\"verdict\":\"correct\"}" \
  http://localhost:${API_PORT:-8000}/api/feedback

docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT weight, false_alarm_count, correct_count FROM damping_weights;"
```

**Expected**: `weight = 0.2875` (`0.5² × 1.15¹`) — not `1.0`, not
unchanged (REQ-M6-CAL-03a's worked recovery value).

## 6. Confirm the fix never touches a past score

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT id, score, created_at FROM score_runs ORDER BY created_at DESC LIMIT 1;"
```

**Expected**: the latest `score_run`'s row is byte-identical to whatever it
was before step 2 — feedback never rewrites history (FR-010,
`sequences/03-sequence-feedback-loop.md`'s key invariant). Trigger a fresh
`RecomputeScoreUseCase` run afterward (e.g. `POST /api/profile/reload`, or
wait for the hourly heartbeat) and confirm the **new** run's contribution
for a matching-pattern finding reads `damping = 0.2875` — proving the
weight change is live for future runs only.

## 7. `false_alarm`/`correct` reject an issue-only target (FR-005a)

```bash
ISSUE_ID=$(docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A \
  -c "SELECT issue_id FROM finding_issue_map WHERE finding_id = '$FINDING_ID' LIMIT 1;")

curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"issue_id\":\"$ISSUE_ID\",\"verdict\":\"false_alarm\"}" \
  http://localhost:${API_PORT:-8000}/api/feedback
# → 422, never 204
```

## 8. No model weights, prompts, or embeddings change (SC-005)

```bash
grep -rl "anthropic\|openai" backend/app/context/ backend/app/scoring/ | grep -v test
```

**Expected**: no match — nothing this feature touches ever imports an LLM
SDK, confirming REQ-M4-05/SC-005 structurally, not just by inspection.

## 9. Backend test suite

```bash
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:${DB_PORT:-5432}/agentic_churn" \
  uv run pytest tests/unit/test_context_damping_calculator.py \
    tests/unit/test_record_feedback_verdict_use_case.py \
    tests/unit/test_feedback_routes_real_db.py \
    tests/unit/test_no_llm_imports.py tests/scoring/ tests/experience/ -v
```

(The `api`/`worker` images are slim runtime builds with no `pytest`/dev
dependencies baked in — matching every prior feature's own quickstart, run
from a host checkout against the same Postgres the stack uses, not inside
the container.)

**Expected**: all pass, including `test_context_damping_calculator.py`
(pure, no DB — the formula's worked values from REQ-M6-CAL-03a as plain
asserts) and the existing `test_recompute_score_use_case.py` suite
unchanged (confirming `research.md` Decision 2's refactor is
behavior-preserving).
