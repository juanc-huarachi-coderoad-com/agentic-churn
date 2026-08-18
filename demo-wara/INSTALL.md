# Wara Demo — Installation Guide

**The official demo data package for interactive exploration of the Churn
Sentiment Agent.** Creates a fictitious e-commerce/retail client ("Wara")
with realistic, hand-curated content — a 90-day baseline of routine
customer-comms noise across 6 source types, exercising all 8 readers and 12
finding types, plus a 30-day backdated score history showing a gentle rise
followed by a dramatic decline from healthy to at_risk (the most recent 14
days of which render on the live dashboard sparkline).

**No code is modified.** All files live in `demo-wara/`. Two copy steps move
data files into `demo/` (which is the only directory mounted read-only into
the Docker containers). The canonical Meridian fixtures, seed SQL, and profile
YAML remain in place, untouched — they are internal fixtures the automated
test suite (`backend/tests/...`) reads directly, not a demo dataset for
end-to-end exploration.

---

## Prerequisites

### 1. API keys

The demo requires two LLM API keys in `.env` (copy from `.env.example` if you
haven't already):

```bash
# .env must contain:
OPENAI_API_KEY=sk-...           # Recurrence reader (text-embedding-3-small)
ANTHROPIC_API_KEY=sk-ant-...    # Tone/Intent/Meeting readers + Narrator
READER_MODEL_ID=claude-haiku-4-5-20251001
GENERATION_MODEL_ID=claude-sonnet-5
```

Without these, the model-based readers (Tone, Intent, Meeting, Recurrence)
will abstain or error, and the narrator will not produce a headline.

### 2. Encryption key

The ingestion layer encrypts message bodies with a Fernet key. If you don't
already have one:

```bash
mkdir -p secrets
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/data.key
```

### 3. Files in this package

```
demo-wara/
  INSTALL.md                      ← this file
  wara-profile.yaml               ← client profile (Wara, e-commerce/retail)
  wara-score-history.sql          ← 30 backdated score_runs + band_history
  fixtures/
    wara-healthy.json             ← 76 baseline events (Apr 12 – Aug 7, ~120-day window)
    wara-concerning.json          ← 14 concerning events (Aug 14 – Aug 17, the big ingestion)
```

---

## Installation Steps

### Phase 0 — Reset and infrastructure

```bash
# Fresh start — wipe any prior data
docker compose down -v && docker compose up -d --build

# Wait for all services to be healthy
docker compose ps
# Expected: api=Up (healthy), db=Up (healthy), worker=Up, web=Up (healthy)

# Create the encryption key if it doesn't exist (see Prerequisites §2)
# Then restart to pick it up:
docker compose restart api worker
```

Add the Wara profile path to `.env` (one line — this is the only `.env`
change needed):

```bash
echo "CLIENT_PROFILE_PATH=./demo/wara-profile.yaml" >> .env
docker compose restart api worker
```

### Phase 1 — Copy data files and load the Wara profile

The Docker containers only mount `./demo:/app/demo:ro`. Copy the Wara data
files there so the container can read them. **These are new files — no
existing files are overwritten.**

```bash
# Copy the profile and fixtures into the mounted demo/ directory
cp demo-wara/wara-profile.yaml demo/wara-profile.yaml
cp demo-wara/fixtures/wara-healthy.json demo/fixtures/wara-healthy.json
cp demo-wara/fixtures/wara-concerning.json demo/fixtures/wara-concerning.json
```

Run the seed (loads users, sources, finding_type_config, playbook_actions,
and the Meridian profile as v1):

```bash
docker compose exec api python scripts/seed.py
```

Log in as Marta (cs_lead) to get an auth token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo "Token: $TOKEN"
```

Load the Wara profile (creates version v2, flips Meridian v1 to non-current,
triggers a replay and an initial score recompute):

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/profile/reload | python3 -m json.tool
```

**Expected response:** `version_number: 2`, `client_name: "Wara"`, with
stakeholders `stk_juan` and `stk_fernando`.

Rename the seeded sources from "Meridian" to "Wara" and add the missing
`transcripts` source (used by calendar events). Run this cosmetic SQL via
the database container:

```bash
docker compose exec -T db psql -U postgres -d agentic_churn <<'SQL'
UPDATE sources SET display_name = REPLACE(display_name, 'Meridian', 'Wara');

INSERT INTO sources (id, source_type, display_name, auth_scope, status)
SELECT gen_random_uuid(), 'transcripts', 'Wara — Calendar/transcripts',
       'transcripts.readonly', 'connected'
WHERE NOT EXISTS (SELECT 1 FROM sources WHERE source_type = 'transcripts');
SQL
```

> **Note:** If your `.env` uses different `POSTGRES_USER` / `POSTGRES_DB`
> values, replace `postgres` and `agentic_churn` in the commands above.

### Phase 2 — Ingest the healthy baseline (~120-day window)

This stage seeds 76 events across 6 source types, building the history that
every reader needs to detect deviation later. Juan has 16 email messages in
the window (well above the minimum 5 required by REQ-M6-CAL-04 for the Tone
reader), Fernando has 7 Slack messages, both product areas (`checkout_api`,
`inventory_sync`) have 16 weeks of usage baseline each, CSAT has 6 historical
scores, and there are 6 routine Zendesk ticket lifecycles plus 3 QBR
transcripts.

```bash
# Ingest the healthy fixture
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-healthy.json \
  api python scripts/run_collector.py --source simulated
```

Confirm the Tone baseline with a **fixed** window (Apr 24 – Aug 14). We use
a direct SQL insert instead of `confirm_baseline.py` because that script
sets `window_end = now()`, which would put the concerning events (Aug 14-17)
inside the baseline window instead of after it:

```bash
docker compose exec -T db psql -U postgres -d agentic_churn <<'SQL'
INSERT INTO baseline_confirmations
    (subject_type, subject_id, metric, window_start, window_end, confirmed_by_user_id)
SELECT 'stakeholder'::rollup_subject_type, s.id, 'email_style',
       '2026-04-24T00:00:00+00:00'::timestamptz,
       '2026-08-14T23:59:59+00:00'::timestamptz,
       '00000000-0000-0000-0000-000000000001'::uuid
FROM stakeholders s
JOIN client_profile_versions pv ON pv.id = s.profile_version_id
WHERE pv.is_current AND s.external_id = 'stk_juan';
SQL
```

Run the absence collector manually. At this point `last_contact_at()` is
Aug 7 (Juan's last healthy email), so the 7-day absence window starts at
Aug 10 — Aug 7 < Aug 10 means the absence event fires:

```bash
docker compose exec api python -m app.worker --run-once absence
```

Run the readers (first pass). With only healthy events, the expected
findings are: `commitment_met` x2, `contact_absence` x1,
`relationship_change` x1 (Fernando silent since Jul 18), and
`meeting_commitment` x1. Tone abstains (all messages are inside the
baseline window — no candidates):

```bash
docker compose exec api python scripts/run_readers.py
```

### Phase 3 — The big ingestion (concerning events)

Ingest the 14 concerning events (Aug 14-17): the 10 precisely-tuned events
that trigger the finding types below, plus 2 extra routine Zendesk tickets
(#207, #209) added purely as atmosphere — both resolve inside the "neutral"
SLA window (neither `commitment_met` nor `broken_response_promise`), so they
add ingestion volume without changing which findings fire. These are all
**after** the baseline `window_end` (Aug 14 23:59:59), so the gmail/zendesk
events among them become Tone/commitment candidates and trigger every
remaining reader:

```bash
# Ingest the concerning fixture
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-concerning.json \
  api python scripts/run_collector.py --source simulated
```

Run the readers again (second pass). This is where all 12 finding types
fire:

```bash
docker compose exec api python scripts/run_readers.py
```

### Phase 4 — Score history, scoring, and narration

Backfill the 30-day score history (the dashboard sparkline still only shows
the most recent 14 of them — see "Score history graph" above). This script:
1. Deletes the placeholder `score_run` created by the profile reload
   (score=0, band=healthy — it had no findings to score).
2. Inserts 30 backdated `score_runs` rows (Jul 18-Aug 16) with correct
   hysteresis (`band_history.consecutive_runs_in_band`), so the real
   `compute_score.py` runs see `at_risk, consecutive=2` as the latest
   prior state and continue the streak.

```bash
docker compose exec -T db psql -U postgres -d agentic_churn < demo-wara/wara-score-history.sql
```

Compute the real score from the actual findings. Run **twice** — the
two-consecutive-run rule (REQ-M6-19) requires 2 runs in the same band
for it to settle. With the backfilled history showing `at_risk` as the
latest band, the first run continues the streak (consecutive=3) and the
second confirms it (consecutive=4):

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py
```

Run the narrator (produces the headline, reasons, and playbook actions
for the dashboard):

```bash
docker compose exec api python scripts/run_narrator.py
```

### Phase 5 — Verification and interactive demo

```bash
# ── Dashboard (score, band, 14-day trend, contributions, narrator) ──
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/dashboard | python3 -m json.tool

# ── Coverage (sources read, findings in quarantine) ──
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/coverage | python3 -m json.tool

# ── Ask agent (natural language Q&A about the score) ──
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"why did the score go up?"}' \
  http://localhost:8000/api/ask | python3 -m json.tool
```

Open the frontend in your browser:

```
http://localhost:5173
```

Log in with `marta` / `agentic-demo-2026`. You should see:
- A score in the at_risk band (red)
- A 14-day trend graph showing the decline from healthy (silver) through
  watch (amber) to at_risk (red)
- Contribution bars showing which findings drove the score
- A narrator headline with reasons and recommended actions
- A pulse timeline of events

#### Optional: Draft composer and feedback

```bash
# Get an issue_id and stakeholder_id from the dashboard response, then:
# curl -s -X POST -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"issue_id":"<id>","stakeholder_id":"<id>","tone_variant":"direct"}' \
#   http://localhost:8000/api/drafts | python3 -m json.tool

# Mark a finding as a false alarm:
# curl -s -X POST -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"finding_id":"<id>","verdict":"false_alarm"}' \
#   http://localhost:8000/api/feedback | python3 -m json.tool
```

---

## What the demo demonstrates

### The 12 finding types

| Finding type | Base points | What triggers it | Source event |
|---|---|---|---|
| `tone_deterioration` | 10 | Juan's terse email (12 words, no greeting) deviates from his 6-message baseline | `wara-gmail-007` (Aug 17 09:14) |
| `escalation_language` | 14 | "Board briefing Thursday" — escalation to senior stakeholders | `wara-gmail-007` |
| `competitive_mention` | 14 | "Looking at VTEX as an alternative platform" | `wara-gmail-008` (Aug 17 10:00) |
| `contractual_reference` | 14 | "Revisit our SLA and the service agreement" (no redaction markers) | `wara-gmail-009` (Aug 17 10:30) |
| `broken_response_promise` | 20 | Ticket #201 reopened Aug 14, still unresolved 3 business days later (> 4h SLA) | `wara-zendesk-201-reopened` |
| `commitment_met` | +10 | Ticket #204 resolved in 1 business hour (≤ 4h SLA) — positive finding | `wara-zendesk-204-resolved` |
| `recurring_issue` | 12 | Ticket #201 reopened with identical title to the Jul 9 ticket — embedding cluster | `wara-zendesk-201-reopened` |
| `usage_deviation` | 15 | checkout_api weekly usage -22% vs 8 historical baselines (z-score far beyond 2.0) | `wara-usage-checkout-w33` |
| `csat_deviation` | 10 | CSAT score 6 vs historical 9, 9, 8 (z-score beyond 2.0) | `wara-csat-004` |
| `contact_absence` | 12 | No contact from Aug 7 to Aug 17 — silence after a healthy period | Fires between Phase 2 and Phase 3 |
| `relationship_change` | 8 | Fernando (Dev Lead) inactive since Jul 18 — 30 days of silence | Detected from `wara-slack-002` |
| `meeting_commitment` | 10 | QBR transcript with a verbal commitment from Fernando | `wara-calendar-qbr-w33` |

### Content redaction (principle P1-adjacent)

`wara-gmail-010` contains "Discount and renewal price" — these are markers
for the `commercial_negotiation` exclusion. The ingestion layer redacts the
body to `[REDACTED]` before it reaches the ledger, demonstrating the
exclusion/redaction feature. The email is still collected and counted, but
its content is not stored in plaintext.

In contrast, `wara-gmail-009` uses "SLA" and "service agreement" (not
exclusion markers), so its body is preserved and the Intent reader can
detect `contractual_reference` from the actual text.

### Score history graph (30-day backfill, 14-day visible trend)

`wara-score-history.sql` backfills 30 days of `score_runs` (Jul 18 – Aug 16),
starting with a gentle healthy-band rise before the same dramatic decline
into watch and at_risk:

```
Jul 18 ... Aug 3:  14 15 14 16 15 17 16 18 17 19 18 20 19 21 20 21 21  (healthy, gentle rise)
Aug  4  5  6  7  8  9 10 11 12 13 14 15 16 17
     22 25 28 30 38 42 45 50 55 62 68 72 74 ▓
     ── healthy ──  ──── watch ────  ─ at_risk ─
```

**Only the most recent 14 days (Aug 4-17) render on the live dashboard
sparkline** — `backend/app/experience/application/use_cases.py`'s
`_TREND_DAYS = 14` is intentional backend code, not modified by this demo.
The Jul 18 – Aug 3 prelude exists in the `score_runs` table (useful for
anyone querying it directly, or for a future deeper trend view) but is not
visible in today's UI. The 31st point (Aug 17, today) is the real score
computed by `compute_score.py` from the actual findings — not a backfilled
value.

### Two-stage ingestion (why not all at once?)

The absence detector uses `last_contact_at()` = `SELECT MAX(occurred_at) FROM
events WHERE event_type != 'absence'` — a **global** query, not per-stakeholder.
If all events were ingested at once, `last_contact` would be Aug 17 (the
concerning events), and the absence window (Aug 10) would not flag Aug 7 as
stale — the absence finding would never fire.

By ingesting in two stages (healthy first, then concerning), the absence
collector sees `last_contact = Aug 7` between stages and fires correctly.

---

## Troubleshooting

### `confirm_baseline.py` vs direct SQL

`scripts/confirm_baseline.py` sets `window_end = datetime.now(UTC)`. If you
run it on Aug 17, the concerning events dated Aug 14-17 fall **inside** the
baseline window, making them baseline samples instead of candidates — the
Tone reader would abstain. The direct SQL insert in Phase 2 uses a fixed
`window_end = Aug 14 23:59:59` to ensure all concerning events are
candidates.

### Tone reader abstains ("insufficient_history")

The Tone reader requires ≥5 baseline messages from the stakeholder within
the confirmed window (REQ-M6-CAL-04). If it abstains, check:

```bash
docker compose exec -T db psql -U postgres -d agentic_churn -c "
SELECT COUNT(*) FROM events e
JOIN stakeholders s ON s.id = e.stakeholder_id
WHERE s.external_id = 'stk_juan'
  AND e.event_type = 'message'
  AND e.occurred_at BETWEEN '2026-04-24' AND '2026-08-15';"
```

Expected: 16 (the healthy gmail messages). If it's 0, the baseline
confirmation SQL didn't run or the events weren't ingested.

### `ANTHROPIC_API_KEY` errors

If you see `AuthenticationError` or `401` from the Tone/Intent/Meeting
readers or the narrator, your `ANTHROPIC_API_KEY` is missing or invalid.
The Recurrence reader uses `OPENAI_API_KEY` separately — check both.

### Score graph shows only 1-2 points

The trend query reads `score_runs` from the last 14 days, one point per day
(last run of each day). If the dashboard sparkline shows fewer than 14
points, the backfill SQL may not have run, or the `computed_at` timestamps
are outside the visible 14-day window. Verify:

```bash
docker compose exec -T db psql -U postgres -d agentic_churn -c "
SELECT computed_at, score, band FROM score_runs ORDER BY computed_at ASC;"
```

Expected: 30 backdated rows (Jul 18 – Aug 16) + 2 real rows (Aug 17 from
`compute_score.py`) — 32 total in the table, of which only the most recent
14 days (Aug 4-17) are visible on today's dashboard sparkline (see
"Score history graph" above).

### Calendar events not ingested

Calendar events without `consent_documented: true` are silently dropped by
the `SimulatedCollector` before they reach the ledger (FR-023). Both
calendar events in the Wara fixtures have `consent_documented: true`, so
this should not be an issue. If they're missing, check the fixture file
was copied correctly.

### Identity resolution

Juan's email (`juan.huarachi.sanchez@gmail.com`) resolves to `stk_juan`
via exact match against `stakeholders.identifiers` for all source types
(gmail, csat, transcripts). Fernando's email (`fujuca510@gmail.com`)
resolves to `stk_fernando` for slack. The Zendesk reporter
(`support-desk@wara.zendesk.com`) is deliberately unresolved (matches the
Meridian pattern — REQ-M1-05: the system never guesses).

---

## Cleanup

To reset everything and start over:

```bash
docker compose down -v && docker compose up -d --build
docker compose exec api python scripts/seed.py
```

Then re-run from Phase 1 (profile reload) onward.

To remove the Wara files from `demo/` (restoring the repo to its original
state):

```bash
rm demo/wara-profile.yaml
rm demo/fixtures/wara-healthy.json
rm demo/fixtures/wara-concerning.json
# Remove the CLIENT_PROFILE_PATH line from .env (or set it back to ./demo/client-profile.yaml)
```

The `demo-wara/` directory itself can be kept or deleted — it has no
effect on the application or tests.
