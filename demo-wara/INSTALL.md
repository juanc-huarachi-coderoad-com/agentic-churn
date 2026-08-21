# Wara Demo — Stage 1: Install (target score ≈ 55, Watch)

**Stage 1 of 3** in the Wara demo. See `RUNBOOK.md` for the full picture —
this file only covers getting Wara installed and reaching the first
checkpoint: a **Watch**-band score around 55, driven by a small set of
simple, easy-to-read warning signs. Stage 2 (`ESCALATION.md`) pushes the
score up into **Critical / At risk** (≈90+, by design — see that file for
why). Stage 3 (`RECOVERY.md`) brings it back down using a recorded
recovery meeting.

**The story.** Wara is a fictitious e-commerce client. Two of their people
show up throughout: **Juan Huarachi** (CTO, the executive sponsor) and
**Fernando Juarez** (Dev Lead, the day-to-day contact). For a few months
everything is healthy — normal emails, normal support tickets, steady
usage. Then, in one week, four small, unrelated things happen at once:
their inventory sync starts skipping updates, a support survey score dips,
and both Juan and Fernando go quiet. None of it is dramatic on its own —
that's the point. This is what an account starting to drift looks like
before anything breaks.

**No code is modified.** All files live in `demo-wara/`. Two copy steps
move data files into `demo/` (the only directory mounted read-only into
the Docker containers). The canonical Meridian fixtures, seed SQL, and
profile YAML remain in place, untouched.

---

## Prerequisites

### 1. API keys

The demo requires two LLM API keys in `.env` (copy from `.env.example` if
you haven't already):

```bash
# .env must contain:
OPENAI_API_KEY=sk-...           # Recurrence reader (text-embedding-3-small)
ANTHROPIC_API_KEY=sk-ant-...    # Tone/Intent/Meeting readers + Narrator
READER_MODEL_ID=claude-haiku-4-5-20251001
GENERATION_MODEL_ID=claude-sonnet-5
```

Without these, the model-based readers (Tone, Intent, Meeting, Recurrence)
will abstain or error, and the narrator will not produce a headline. Stage
1 itself doesn't fire any Tone/Intent findings (those start in Stage 2),
but set both keys now so Stages 2-3 work without a pause.

### 2. Encryption key

The ingestion layer encrypts message bodies with a Fernet key. If you
don't already have one:

```bash
mkdir -p secrets
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/data.key
```

### 3. Files in this package

```
demo-wara/
  RUNBOOK.md                          ← start here: the full 3-stage walkthrough
  INSTALL.md                          ← this file (Stage 1)
  ESCALATION.md                       ← Stage 2
  RECOVERY.md                         ← Stage 3
  wara-profile.yaml                   ← client profile (Wara, e-commerce/retail)
  wara-score-history.sql              ← 30 backdated score_runs + band_history, ending in Watch
  fixtures/
    wara-healthy.json                 ← 76 baseline events (Apr 12 – Aug 7, ~120-day window)
    wara-concerning.json              ← Stage 1: 7 events (Aug 14-17) — 4 score-driving, 3 atmosphere
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
mkdir -p demo/fixtures
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
`transcripts` source (used by calendar/meeting events, needed in Stage 3):

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

This stage seeds 76 events across 6 source types, building the history
every reader needs to detect deviation later. Juan has 16 email messages
in the window (well above the 5-message minimum REQ-M6-CAL-04 requires
for the Tone reader), Fernando has 7 Slack messages, both product areas
(`checkout_api`, `inventory_sync`) have 16 weeks of usage baseline each,
CSAT has 6 historical scores, and there are 6 routine Zendesk ticket
lifecycles plus 3 QBR transcripts. **This file is unchanged from the
original demo package** — it's already simple, and every Stage 1-3
calibration below is computed directly against its numbers, so don't edit
it unless you also intend to redo the arithmetic.

```bash
# Ingest the healthy fixture
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-healthy.json \
  api python scripts/run_collector.py --source simulated
```

Confirm the Tone baseline with a **fixed** window (Apr 24 – Aug 14). We use
a direct SQL insert instead of `confirm_baseline.py` because that script
sets `window_end = now()`, which would put the concerning events (Aug
14-17) inside the baseline window instead of after it:

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

Run the absence collector manually. `last_contact_at()` is a **global**
query across every event, so this must run now — after the healthy
ingestion, before the concerning one — while the last real contact is
still Juan's Aug 7 email:

```bash
docker compose exec api python -m app.worker --run-once absence
```

Run the readers (first pass). With only healthy events, expect at least:
`commitment_met` x2, `contact_absence` x1, and `relationship_change` x1
(Fernando silent since Jul 18). Tone abstains (all messages are inside
the baseline window — no candidates). The 3 QBR transcripts in
`wara-healthy.json` may or may not also produce a `meeting_commitment` or
two, depending on how the Meeting reader judges their status-update-style
dialogue — that's fine either way and isn't part of Stage 1's calibrated
total below (it's small either way, ~5 pts, and only shifts the Stage 1
number slightly):

```bash
docker compose exec api python scripts/run_readers.py
```

### Phase 3 — The Stage 1 ingestion (four simple warning signs)

Ingest the 7 events in `wara-concerning.json` (Aug 14-17). Four of them
drive the score; three are neutral atmosphere (two routine tickets
resolved comfortably inside the SLA, one email demonstrating content
redaction). All of it lands **after** the baseline `window_end` (Aug 14
23:59:59):

```bash
# Ingest the Stage 1 fixture
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-concerning.json \
  api python scripts/run_collector.py --source simulated
```

Run the readers again (second pass):

```bash
docker compose exec api python scripts/run_readers.py
```

### Phase 4 — Score history, scoring, and narration

Backfill the 30-day score history (the dashboard sparkline still only
shows the most recent 14 of them — see "Score history graph" below).
This script:
1. Deletes the placeholder `score_run` created by the profile reload
   (score=0, band=healthy — it had no findings to score).
2. Inserts 30 backdated `score_runs` rows (Jul 18-Aug 16) ending in the
   **Watch** band with correct hysteresis, so the real `compute_score.py`
   run sees `watch, consecutive=8` as the latest prior state and settles
   immediately.

```bash
docker compose exec -T db psql -U postgres -d agentic_churn < demo-wara/wara-score-history.sql
```

Compute the real score from the actual findings. One run is normally
enough here (the backfill already has 8 consecutive Watch runs), but run
it twice to be safe — a second run is always a harmless no-op:

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
- A score in the **Watch** band (amber), approximately **55-61**
- A 14-day trend graph showing a gentle rise from healthy into Watch
- Contribution bars showing four findings driving the score
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

## What Stage 1 demonstrates

### The 4 findings that drive the score — worked arithmetic

Every number below follows `points = base × influence × criticality ×
confidence × magnitude × recency × damping` (`requirements/06-scoring-engine.md`
REQ-M6-01) using the **real reader formulas**, not estimates — read
straight out of `backend/app/readers/domain/services.py` and
`backend/app/readers/application/usage_reader.py`. `influence` comes from
`wara-profile.yaml` (Juan = sponsor = 1.6, Fernando = daily_user = 1.2,
no stakeholder = 1.0); `criticality` from the product area (`checkout_api`
= critical = 1.5, `inventory_sync` = standard = 1.0).

| Finding | Story | base | influence | criticality | confidence | magnitude | recency | points |
|---|---|---|---|---|---|---|---|---|
| `usage_deviation` | Inventory sync missed some scheduled updates — a real, if modest, dip against 16 weeks of steady baseline (z ≈ -2.9) | 15 | 1.0 | 1.0 | 0.90 | 0.73 | 1.0 | **9.86** |
| `csat_deviation` | Juan's team rated support 7 instead of their usual 8-9 (z ≈ -3.2) | 10 | 1.6 | 1.0 | 0.90 | 0.81 | 1.0 | **11.66** |
| `contact_absence` | Nobody from Wara reached out for over a week — no emails, no tickets (global signal, not tied to one person) | 12 | 1.0 | 1.0 | 0.85 | 0.57 | 1.0 | **5.82** |
| `relationship_change` | Fernando has gone quiet in Slack for a month | 8 | 1.2 | 1.0 | 0.70 | 0.50 | 1.0 | **3.36** |
| | | | | | | | **Total** | **≈30.70** |

```
score = 100 × (1 − e^(−30.70 / 33)) ≈ 60.5
```

**Expected dashboard result: approximately 55-61, Watch band.** Real
`confidence`/`magnitude` values for the CSAT/usage z-scores are
deterministic given the fixture data above (they're plain statistics, not
model output), so this table should reproduce almost exactly. Treat the
final number as a checkpoint, not a guarantee — see "Tuning" in
`RUNBOOK.md` if your run lands meaningfully outside 50-65.

### Why these four and not more

Stage 1 deliberately only exercises the four **deterministic, code-based**
readers (Usage, CSAT, Absence, Relationship) — no model call happens for
any of them. That keeps the story simple (quiet numbers, quiet people —
nothing anyone had to *say*) and keeps the math exactly reproducible on
paper. The remaining 8 finding types — 6 introduced in `ESCALATION.md`
(Stage 2: `broken_response_promise`, `recurring_issue`,
`tone_deterioration`, `escalation_language`, `competitive_mention`,
`contractual_reference`) and 2 in `RECOVERY.md` (Stage 3:
`commitment_met`, `meeting_commitment`) — all fire by the end of the
walkthrough. See `RUNBOOK.md` for the full 12-finding-type map.

### Content redaction (principle P1-adjacent)

`wara-gmail-007` mentions "a discount" — this is a marker for the
`commercial_negotiation` exclusion in `wara-profile.yaml`
(`backend/app/ingestion/application/use_cases.py`'s `_EXCLUSION_MARKERS`:
`discount`, `renewal price`, `contract terms`, `negotiat`). The ingestion
layer redacts the body to `[REDACTED]` before it reaches the ledger,
demonstrating the exclusion/redaction feature. The email is still
collected and counted for coverage, but its content is never stored in
plaintext and no finding is produced from it.

### Score history graph (30-day backfill, 14-day visible trend)

`wara-score-history.sql` backfills 30 days of `score_runs` (Jul 18 – Aug
16), ending in the Watch band right before the real Aug 17 computation:

```
Jul 18 ... Aug 3:  14 15 14 16 15 17 16 18 17 19 18 20 19 21 20 21 21  (healthy, gentle rise)
Aug  4  5  6  7  8  9 10 11 12 13 14 15 16     Aug 17
     22 24 26 28 33 38 41 44 47 50 52 54 56    ≈55-61 (real)
     ────── healthy ──────  ──────── watch ────────
```

**Only the most recent 14 days (Aug 4-17) render on the live dashboard
sparkline** (`_TREND_DAYS = 14`, intentional backend code, not modified by
this demo). The Jul 18 – Aug 3 prelude exists in `score_runs` for anyone
querying it directly but isn't visible in today's UI. The 31st point (Aug
17, today) is the real score computed by `compute_score.py` from the
actual findings — not a backfilled value.

### Two-stage ingestion (why not all at once?)

The absence detector's `last_contact_at()` is a **global** query across
every event, not per-stakeholder (`DetectAbsenceUseCase.execute` in
`backend/app/ingestion/application/use_cases.py`). If all events were
ingested at once, `last_contact` would already be Aug 17 (the Stage 1
events) by the time the absence check ran, and the 7-day window would
never see the gap. By ingesting healthy first, then running the absence
collector, then ingesting Stage 1, the collector sees `last_contact = Aug
7` in between and fires correctly.

---

## Troubleshooting

### `confirm_baseline.py` vs direct SQL

`scripts/confirm_baseline.py` sets `window_end = datetime.now(UTC)`. If
you run it on Aug 17 or later, the Stage 1 events (Aug 14-17) fall
**inside** the baseline window, making them baseline samples instead of
candidates. The direct SQL insert in Phase 2 uses a fixed `window_end =
Aug 14 23:59:59` to keep all Stage 1 events as candidates.

### Score lands well above 65 (At risk), close to 99, instead of ~55-61

This almost always means the container is reading a **stale copy** of
`demo/fixtures/wara-concerning.json` — from an earlier run, before this
file's current 7-event version. The Docker container only ever reads
`demo/fixtures/wara-concerning.json` (the deployed copy), never
`demo-wara/fixtures/wara-concerning.json` (the source) directly — if you
ran the `cp` step once, then this source file changed later, the stale
copy in `demo/` is still what gets ingested until you `cp` again. Confirm
you're on the current version:

```bash
diff demo-wara/fixtures/wara-concerning.json demo/fixtures/wara-concerning.json
# No output = they match. Any output = demo/ is stale — re-copy it.
grep -l "VTEX\|ticket_number.: 201" demo/fixtures/*.json 2>/dev/null
# Any match here means an old fixture is still sitting in demo/ — see Cleanup below.
```

If `demo/` was stale, a `cp` alone won't fix an **already-seeded**
database — the events and findings are already in Postgres. Wipe and
redo from Phase 0:

```bash
docker compose down -v && docker compose up -d --build
docker compose exec api python scripts/seed.py
# then re-run from Phase 1 onward, with the fixtures freshly copied
```

Also confirm you only ran the readers **twice** total (once after
healthy, once after Stage 1) — running them a third time before Stage 2
doesn't change anything (`already_interpreted` guards prevent duplicate
findings), but a stray extra fixture copy would.

### Tone reader abstains ("insufficient_history")

The Tone reader requires ≥5 baseline messages from the stakeholder within
the confirmed window (REQ-M6-CAL-04) — not relevant to Stage 1's four
findings (none of them use Tone), but relevant once you reach Stage 2's
`tone_deterioration` finding. If it abstains there, check:

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

The trend query reads `score_runs` from the last 14 days, one point per
day (last run of each day). If the dashboard sparkline shows fewer than
14 points, the backfill SQL may not have run, or `computed_at` timestamps
are outside the visible 14-day window. Verify:

```bash
docker compose exec -T db psql -U postgres -d agentic_churn -c "
SELECT computed_at, score, band FROM score_runs ORDER BY computed_at ASC;"
```

Expected: 30 backdated rows (Jul 18 – Aug 16) + 1-2 real rows from Aug 17
— 31-32 total, of which only the most recent 14 days (Aug 4-17) are
visible on today's dashboard sparkline.

### Calendar events not ingested

Calendar events without `consent_documented: true` are silently dropped
by the `SimulatedCollector` before they reach the ledger (FR-023). Both
calendar events in `wara-healthy.json` have `consent_documented: true`,
so this should not be an issue here — it becomes relevant again for the
real meeting audio in Stage 3.

### Identity resolution

Juan's email (`juan.huarachi.sanchez@gmail.com`) resolves to `stk_juan`
via exact match against `stakeholders.identifiers` for all source types
(gmail, csat, transcripts). Fernando's email (`fujuca510@gmail.com`)
resolves to `stk_fernando` for slack. The Zendesk reporter
(`support-desk@wara.zendesk.com`) is deliberately unresolved — REQ-M1-05:
the system never guesses.

---

## Next

Once the dashboard shows a Watch-band score around 55-61, continue to
**`ESCALATION.md`** (Stage 2) to push it into Critical / At risk (≈90+).

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
