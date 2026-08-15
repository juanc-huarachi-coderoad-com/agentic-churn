# Quickstart: Validating Dashboard Evidence Trace

Prerequisites: the stack from features 001–005 running, seeded, and the
Meridian fixture collected, findings interpreted, and scored (`specs/005-
deterministic-findings/quickstart.md`'s steps, plus `scripts/seed_score_fixture.py`
+ `scripts/compute_score.py` for at least one `validated` finding to exist —
`contribution_bars`/the evidence panel need at least one real
`score_contributions` row to demonstrate against).

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

## 1. The full dashboard renders real data (User Story 1)

```bash
curl -s http://localhost:8000/api/dashboard -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected**: `state = "normal"`; `score_block.score`/`band` match the latest
`score_runs` row; `contribution_bars` has one entry per real
`score_contributions` row (`contracts/dashboard.md`'s worked example — a
`broken_response_promise` bar at 39.0 points); `pulse_timeline` shows the same
ticket #456 event with `severity = "at_risk"`; `coverage_line.status = "ok"`.

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT score_run_id, count(*) FROM score_contributions GROUP BY 1 ORDER BY 1 DESC LIMIT 1;"
```

**Expected**: the row count matches `contribution_bars`'s length exactly — no
extra, no missing (SC-002/SC-003's "traces to a real row" requirement).

## 2. Every number opens to its proof (User Story 2)

```bash
CONTRIB_ID=$(curl -s http://localhost:8000/api/dashboard -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['contribution_bars'][0]['score_contribution_id'])")
curl -s http://localhost:8000/api/evidence/$CONTRIB_ID -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected**: `data-model.md`'s worked example — `baseline_value`/
`current_value` describe the real 4-hour-promise-vs-50-hour-elapsed comparison,
`arithmetic_explanation` names exactly the non-neutral factors (criticality,
recency), `quoted_messages` includes the ticket's real title, timestamped.

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:8000/api/evidence/00000000-0000-0000-0000-000000000000 \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: `404` — no fabricated response for a nonexistent contribution.

## 3. A quiet score can be trusted, or explained (User Story 3)

```bash
curl -s http://localhost:8000/api/coverage -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected**: real `sources` entries matching `sources.status`; `quarantine`
is an empty array — real, not a stubbed placeholder (`contracts/coverage.md`).

## 4. Stakeholder cards, honest about what's known (User Story 4)

```bash
curl -s http://localhost:8000/api/dashboard -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['stakeholder_cards'])"
```

**Expected**: both Meridian stakeholders render; every card's
`tone_trajectory` is `"unknown"`; the one with no ledger activity within the
last 4 weeks (feature 005's fixture fix, `research.md`) shows
`status = "quiet"`.

## 5. State banners match the real precondition (User Story 5)

Force each state's precondition, one at a time, and re-check `state`:

```bash
# Source down — mark one source disconnected
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "UPDATE sources SET status = 'disconnected' WHERE source_type = 'gmail';"
curl -s http://localhost:8000/api/dashboard -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['state'], d.get('message'))"
```

**Expected**: `source_down`, with `base/...md` §11.5's exact copy pattern.
Revert (`UPDATE sources SET status = 'connected' ...`) before continuing.

## Automated coverage

```bash
docker compose exec api pytest tests/unit/test_dashboard_route.py tests/unit/test_evidence_route.py \
  tests/unit/test_coverage_route.py tests/experience/ -v
docker compose exec web pnpm test        # Vitest — dashboard components, evidence panel
docker compose exec web pnpm test:e2e    # Playwright — dashboard-to-evidence.spec.ts
```

**Expected**: every route test passes against the real, already-scored
database; the pure domain-service tests (`test_state_and_evidence_services.py`)
pass with no DB connection at all.
