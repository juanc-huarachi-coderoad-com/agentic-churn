# Quickstart: Validating the Narrator and Ask Agent

Prerequisites: the stack from features 001–007 running, seeded, ingested, read,
scored, and validated (`specs/007-model-findings/quickstart.md`'s steps —
`ANTHROPIC_API_KEY` already configured there for Tone/Intent). This feature
adds one new environment variable and one new Python dependency:

```bash
# New: Narrator/Ask agent's model tier (research.md Decision 1,
# decisions/02-repo-and-tooling.md's Claude model ID pinning table)
echo "GENERATION_MODEL_ID=claude-sonnet-5" >> .env
cd backend && uv add langgraph langchain-anthropic
cd .. && docker compose up --build -d
```

## 1. Narrate the latest score run

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/run_narrator.py
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT headline, fact_check_passed, prompt_version FROM narrator_outputs ORDER BY created_at DESC LIMIT 1;"
```

**Expected**: 1 row, `fact_check_passed = true`, a headline reproducing
`examples/01-end-to-end-walkthrough.md`'s worked example in substance ("We
took 19 hours to reply... we promised 4... Ana is pulling back") — the first
real `narrator_outputs` row this codebase has ever had (table exists since
feature 001, unpopulated until now).

## 2. Confirm the dashboard renders it

```bash
TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:${API_PORT:-8000}/api/dashboard | jq .narrator
```

**Expected**: the same headline/reasons/actions from step 1 —
`DashboardResponse.narrator` (`contracts/dashboard.md`), real for the first
time since `specs/006-dashboard-evidence-trace/spec.md` explicitly shipped
this field permanently blocked on this feature.

## 3. Ask a lookup question — delta breakdown

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "why did the score go up?"}' \
  http://localhost:${API_PORT:-8000}/api/ask | jq .
```

**Expected**: `component = "delta_breakdown"`, `component_props` citing real
`score_contributions` from the last two `score_runs` rows — the first time
`POST /api/ask` has ever returned anything other than 404
(`architecture/07-api-spec.md` documented this route since before this
feature existed; this feature is the first to actually implement it).

## 4. Ask a prediction question — decline, not a guess

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "will Meridian actually cancel?"}' \
  http://localhost:${API_PORT:-8000}/api/ask | jq .
```

**Expected**: `declined_reason = "prediction"`, `fallback_text` states the
system describes today's evidence and doesn't forecast — never a probability
(REQ-M9-05).

## 5. Ask about a stakeholder with insufficient baseline history

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "is this normal for Diego?"}' \
  http://localhost:${API_PORT:-8000}/api/ask | jq .
```

**Expected**: `declined_reason = "insufficient_history"` — Diego has no
`baseline_confirmations` row yet (only Ana's exists, from
`specs/007-model-findings/quickstart.md` step 2), proving the new decline
reason from `/speckit-clarify` is real, not just documented
(`contracts/ask.md`).

## 6. Ask a "write to X" question — the handoff, not an inline answer

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "write to Ana about the ticket delay"}' \
  http://localhost:${API_PORT:-8000}/api/ask | jq .
```

**Expected**: `component = "draft_handoff"`, `component_props` carrying a
real `issue_id`/`stakeholder_id` pair — not answered inline, ready for feature
009's draft composer to consume later (FR-012a).

## 7. Confirm every question was logged

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT question_text, matched_intent, rendered_component, declined_reason, response_time_ms FROM ask_queries ORDER BY created_at DESC LIMIT 5;"
```

**Expected**: 4 rows from steps 3–6, `response_time_ms < 3000` on every row
(REQ-M9-08), `declined_reason` populated only on the decline/fallback rows —
the dataset REQ-M9's ~90% intent-coverage measurement reads from.

## 8. Confirm the read-only tool guarantee mechanically, not by inspection

```bash
cd backend && uv run pytest tests/experience/test_ask_agent_toolkit.py::test_no_write_method_is_ever_registered_as_a_tool -v
```

**Expected**: pass — asserts against the actual registered tool list built
by `AskAgentToolkit.build_tools()`, the same mechanical-not-conventional
guarantee `tests/strategy.md`'s "Ask agent (LangGraph) tests" section
specifies.

## 9. Confirm golden-replay is real for the first time

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:${DB_PORT:-5432}/agentic_churn" \
uv run pytest tests/golden_replay/ -v
```

**Expected**: `test_golden_replay_reproduces_dashboard_exactly` **passes**,
no longer `@pytest.mark.skip` — closing the gap three prior features'
Complexity Tracking tables (004, 005, 007) explicitly deferred to this one by
name (`research.md` Decision 7): snapshot `score_runs`/`score_contributions`/
`narrator_outputs`/the dashboard response, truncate `event_threads`/
`response_pairs`/`rollups`, replay from `events` + `client_profile_versions`
+ `baseline_confirmations` alone, byte-identical reconstruction.

## 10. Confirm a missing model key fails the Narrator honestly, not silently

```bash
docker compose exec api sh -c "GENERATION_MODEL_ID= python scripts/run_narrator.py"
```

**Expected**: an explicit `GENERATION_MODEL_ID is not configured` failure —
never a silent fallback-headline path standing in for a genuine
misconfiguration, the same honest-failure discipline feature 007 already
established for `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`. (The deterministic
fallback headline from step 1's "what if the fact-check fails" path is a
distinct, intentional behavior — this step is about a *configuration* failure,
which must never look identical to it.)

## Automated coverage

Same host-checkout pattern features 004/005/007 established:

```bash
cd backend
uv run ruff check .
uv run mypy app
uv run lint-imports --config ../.importlinter
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:${DB_PORT:-5432}/agentic_churn" \
ENCRYPTION_KEY_PATH="../secrets/data.key" \
CLIENT_PROFILE_PATH="../demo/client-profile.yaml" \
COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \
uv run pytest tests/golden_replay/ tests/narrator/ tests/experience/ tests/readers/ tests/scoring/ tests/unit/ -v
```

**Expected**: every Narrator unit test passes with `LLMPort` faked (fact-check
tested directly against known-good/known-bad sentence/fact-set pairs, no live
Anthropic call needed to prove the pure function is correct); every Ask agent
branch-coverage test (`tests/strategy.md`'s 8-intent-plus-decline-plus-
fallback list) passes with the graph invoked directly against fake ports, no
live model call; the golden-replay suite passes for the first time
(step 9); the full backend suite count grows past feature 007's 157.
