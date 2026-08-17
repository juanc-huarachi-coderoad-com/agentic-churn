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
signal collectors: the first modules with real business logic), **Score Engine**
(Phase 4 — "the checkpoint": per-finding weighting, issue-relative ranking, band
classification with hysteresis, all proven against a hand-authored fixture before any
reader module exists), and **Deterministic Findings** (Phase 5 — the five non-LLM
readers: Commitment, Usage, Recurrence, Absence, Relationship — the first features
to write real, non-fixture `findings` rows). See `specs/ROADMAP.md` for the full
feature-by-feature status.

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

## Deterministic Findings (Phase 5)

Real findings, no model call: Commitment, Usage, Recurrence, Absence, and
Relationship each read the real ledger and emit `Finding`s deterministically —
`ValidationGate`/Tone/Intent (M5a/the LLM-based readers, feature 007 below) now
gate and persist every finding this phase's five readers emit too; Meeting
stays unbuilt (sent to Phase 2, `decisions/01-mvp-scope-and-phasing.md`). One
new environment prerequisite — Recurrence's embedding provider:

```bash
echo "OPENAI_API_KEY=sk-..." >> .env
docker compose up --build -d   # picks up the new env var
```

```bash
docker compose exec api python scripts/run_collector.py --source simulated
docker compose exec api python scripts/run_readers.py
```

**Expected**: a per-reader summary — findings persisted, or (if `OPENAI_API_KEY` is
missing/invalid) Recurrence's own isolated failure message, while the other four
readers' counts are unaffected (FR-014a). Every finding now passes through the
validation gate (feature 007) before persisting — see the next section. Re-running
over an unchanged ledger adds nothing (the REQ-M5-15 cache). See
`specs/005-deterministic-findings/quickstart.md` for the full validation
walkthrough, including the exact worked-example table and the failure-isolation
and cache checks.

## Model Findings (Phase 7)

Tone and Intent — the two LLM-based readers — plus the M5a validation gate that
now runs on every finding from all eight readers, not just these two: schema
valid, cited events real, enough evidence, confidence at or above the type's
floor. A finding that fails is quarantined, tagged with the specific reason, and
never repaired or resubmitted (REQ-M5A-01..04). One new environment
prerequisite — Tone/Intent's model provider:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo "READER_MODEL_ID=claude-haiku-4-5-20251001" >> .env
docker compose up --build -d   # picks up the new env vars
```

Tone needs a human-confirmed baseline before it will ever emit a finding for a
given stakeholder — REQ-M6-CAL-04's "no history, no opinion" abstention floor
(at least 5 prior messages in the confirmed window):

```bash
docker compose exec api python scripts/run_collector.py --source simulated
docker compose exec api python scripts/confirm_baseline.py --stakeholder ana \
  --metric email_style --window-days 60
docker compose exec api python scripts/run_readers.py
```

**Expected**: a per-reader summary including `findings_quarantined` alongside
`findings_persisted`; a missing `ANTHROPIC_API_KEY` reports Tone/Intent's own
isolated failure, the same as Recurrence's missing `OPENAI_API_KEY` — never a
silently-empty, misleadingly-healthy run. `GET /api/coverage`'s `quarantine`
field is real for the first time, reflecting whatever the gate actually
rejected. See `specs/007-model-findings/quickstart.md` for the full validation
walkthrough.

## Narrator and Ask Agent (Phase 8)

The explanation layer: the Narrator turns a score run's ranked findings into a
fact-checked headline/reasons/actions, and the Ask agent — the one genuinely
agentic component, a compiled LangGraph `StateGraph` — answers questions by
looking up already-computed data, never recalculating the score. One new
environment prerequisite — Narrator/Ask agent's model tier (same
`ANTHROPIC_API_KEY` as Tone/Intent, a higher-stakes model):

```bash
echo "GENERATION_MODEL_ID=claude-sonnet-5" >> .env
docker compose up --build -d   # picks up the new env var
```

Narrate the latest score run (a separate manual script, mirroring
`compute_score.py`/`run_readers.py` — no live/chained trigger path exists yet
anywhere in this pipeline):

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/run_narrator.py
```

**Expected**: a headline/reasons/actions summary printed, with `narrator_outputs`
now real for the first time (this table existed, unpopulated, since feature
001) — `GET /api/dashboard`'s `narrator` field renders it, closing the gap
feature 006 explicitly deferred. If every LLM-generated headline candidate
fails its own mechanical fact-check, the dashboard falls back to a
deterministic, non-LLM headline built from the score/band/top-issue alone
(`fact_check_passed = false`) — never a blank dashboard, never an unverified
claim.

Ask a question — `POST /api/ask` is real for the first time since
`architecture/07-api-spec.md` documented it:

```bash
TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "why did the score go up?"}' \
  http://localhost:${API_PORT:-8000}/api/ask
```

**Expected**: a rendered component (`delta_breakdown`, `stakeholder_cards`,
etc.) for one of the 7 lookup-and-render intents, a `draft_handoff` response
for "write to X about this," or an honest decline/fallback — a prediction
question always declines rather than guessing, a colleague-judgment question
always refuses, and a stakeholder with fewer than 5 confirmed-baseline
messages declines with `insufficient_history`, distinct from
`source_not_connected`. `GET /api/coverage`'s new `ask_intent_coverage` field
shows the fallback rate without querying the database directly. See
`specs/008-narrator-and-ask-agent/quickstart.md` for the full validation
walkthrough, including the now-real `tests/golden_replay/` suite.

## Draft Composer (Phase 9)

"The closer." Generates a client-facing message from a requested issue's own
evidence, the client profile's communication norms, real thread history, and
the latest run's already-agreed actions — then runs it through five
mechanical pre-display checks (facts, dates, invented causes, internal
leaks, commercial concessions) before it can ever be persisted or displayed.
**No new environment prerequisite** — reuses the same `GENERATION_MODEL_ID`
Sonnet tier the Narrator and Ask agent already use, and no migration: the
`draft_messages` table has existed, unpopulated, since feature 001.

Generate a draft for the worked example's top issue:

```bash
TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"issue_id":"<issue-id>","stakeholder_id":"<stakeholder-id>","tone_variant":"direct"}' \
  http://localhost:${API_PORT:-8000}/api/drafts
```

**Expected**: `200`, `checks_passed: true`, a message opening with the
specific evidence-backed failure, exactly one ask, and every fact traceable
back to real evidence/thread history/profile data. A draft that fails any of
the five checks returns `422` with the same generic message
`architecture/06-error-handling.md` already defines for a generation
error — never a partial draft, never a message naming which check failed.

Copy or log a generated draft as manually sent:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:${API_PORT:-8000}/api/drafts/<draft-id>/copy
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:${API_PORT:-8000}/api/drafts/<draft-id>/log-as-sent
```

**There is no `/send` route — anywhere, in any form (REQ-M10-P1).** A
request against `.../send` returns `404` because no such route is ever
registered; `tests/experience/test_no_external_transport.py` mechanically
confirms no file this feature touches even imports an outbound-transport
client (SMTP, HTTP client used for a third-party send, chat/CRM SDK) — a
structural guarantee, not just an absent route. The Ask agent's
`draft_handoff` response (feature 008) now opens a real panel in the
dashboard instead of a placeholder message. See
`specs/009-draft-composer/quickstart.md` for the full validation walkthrough,
including the scripted red-team case per check.

## Feedback Memory (Phase 10)

"The learning loop." A single-click verdict (`correct`/`false_alarm`/
`resolved`) on any finding-bearing card — the evidence trace panel, reached
from the dashboard or an Ask-agent answer — recomputes that pattern's
damping weight, which every future scoring run reads as a multiplicative
term. No retraining, no fine-tuning: one stored number, always shown with a
plain-language reason. **No new environment prerequisite, no migration** —
`feedback_verdicts`/`damping_weights` have existed, unpopulated, since
feature 001.

Mark a finding a false alarm, twice, then confirm the pattern later:

```bash
TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"finding_id":"<finding-id>","verdict":"false_alarm"}' \
  http://localhost:${API_PORT:-8000}/api/feedback
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"finding_id":"<finding-id>","verdict":"false_alarm"}' \
  http://localhost:${API_PORT:-8000}/api/feedback
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"finding_id":"<finding-id>","verdict":"correct"}' \
  http://localhost:${API_PORT:-8000}/api/feedback
```

**Expected**: three `204`s; `damping_weights` for that finding's pattern
(`reader_type+finding_type`) shows `weight` at `0.500` → `0.250` → `0.2875`
(REQ-M6-CAL-03a's worked values) — losing trust is faster than regaining
it, by design. The pattern's evidence trace (`GET /api/evidence/{id}`) now
carries a non-null `disclosure_text`; a fresh scoring run reads the new
weight, but the `score_run` that existed before any of these calls stays
byte-identical. `false_alarm`/`correct` submitted with only an `issue_id`
(no `finding_id`) return `422` — one click on a multi-reader issue can
never touch several different readers' weights at once (FR-005a). See
`specs/010-feedback-memory/quickstart.md` for the full validation
walkthrough.
