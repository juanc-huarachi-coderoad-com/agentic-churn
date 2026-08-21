# Wara Demo — Runbook (start here)

One client, three stages, one story you can explain in a sentence: **a
small e-commerce account starts drifting, one problem repeats and pushes
it into real risk, and then a normal Friday recovery call brings it back
down.** Everything lives in `demo-wara/`; nothing outside this folder is
ever modified.

| Stage | Goal | Score checkpoint | Detailed doc |
|---|---|---|---|
| 1 — Install | Get Wara running with a healthy history, then a few quiet warning signs | ≈ 55-61 (Watch) | `INSTALL.md` |
| 2 — Escalation | A recurring problem plus everything a frustrated stakeholder tends to say | ≈ 85-97 (Critical / At risk) | `ESCALATION.md` |
| 3 — Recovery | A recorded meeting + a good week bring the score back down | ≈ 55-65 (Watch) | `RECOVERY.md` |

Stage 2 also exercises **all 8 remaining finding types** in one pass —
see "The 12 finding types, end to end" below. That's a deliberate choice:
full functional coverage and a precise mid-70s number are in tension
(more finding types = more points), and this runbook picks full
coverage. `ESCALATION.md` has a lighter alternative if you want a tighter
number instead.

Read this file for the big picture and the copy-paste command sequence.
Read the three stage docs for the full explanation, worked arithmetic,
and troubleshooting behind each step — they're not duplicated here.

---

## The people and the product (unchanged throughout)

- **Wara** — a fictitious e-commerce/retail client (`wara-profile.yaml`).
- **Juan Huarachi** — CTO, the executive sponsor who signs the renewal.
- **Fernando Juarez** — Dev Lead, the daily hands-on contact.
- Two product areas Wara depends on: **`checkout_api`** (critical — this
  is how their customers pay) and **`inventory_sync`** (standard — this
  is how their stock counts stay accurate).

Every finding in every stage below is about one of these two people or
one of these two product areas — nothing new is introduced, matching the
actors already defined in this profile.

---

## Before you start

1. **API keys** in `.env`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
   `READER_MODEL_ID`, `GENERATION_MODEL_ID`. See `INSTALL.md` Prerequisites
   §1 for exact values.
2. **Encryption key** at `secrets/data.key`. See `INSTALL.md`
   Prerequisites §2.
3. `docker compose down -v && docker compose up -d --build`, then confirm
   `docker compose ps` shows everything healthy.

> **⚠️ The #1 way this demo produces a "wrong" score:** the Docker
> containers only ever read files from `demo/`, never from
> `demo-wara/` directly. Every stage below has a `cp demo-wara/... demo/...`
> step — if you skip it, re-run it after editing a fixture, or already
> seeded a database with an older copy, you'll see numbers from stale
> data. If your score is way off from what a stage says to expect
> (especially a jump toward ~99), that's almost always the cause — see
> `INSTALL.md`'s troubleshooting section for the exact diagnostic and fix.

---

## Stage 1 — Install (target ≈ 55, Watch)

**Story:** for a few months everything is normal. Then in one week, four
small, unrelated things happen at once — inventory sync misses some
updates, a support survey score dips, and both Juan and Fernando go
quiet. Nothing dramatic. Just an account starting to drift.

**Files:** `wara-profile.yaml`, `fixtures/wara-healthy.json`,
`fixtures/wara-concerning.json`, `wara-score-history.sql`.

**Full instructions, worked arithmetic, and troubleshooting:**
`INSTALL.md`.

Condensed command sequence (see `INSTALL.md` for what each step does and
what to expect from it):

```bash
# Phase 0-1 — infra, profile
echo "CLIENT_PROFILE_PATH=./demo/wara-profile.yaml" >> .env
docker compose restart api worker
mkdir -p demo/fixtures
cp demo-wara/wara-profile.yaml demo/wara-profile.yaml
cp demo-wara/fixtures/wara-healthy.json demo/fixtures/wara-healthy.json
cp demo-wara/fixtures/wara-concerning.json demo/fixtures/wara-concerning.json
docker compose exec api python scripts/seed.py

TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/profile/reload | python3 -m json.tool

docker compose exec -T db psql -U postgres -d agentic_churn <<'SQL'
UPDATE sources SET display_name = REPLACE(display_name, 'Meridian', 'Wara');
INSERT INTO sources (id, source_type, display_name, auth_scope, status)
SELECT gen_random_uuid(), 'transcripts', 'Wara — Calendar/transcripts',
       'transcripts.readonly', 'connected'
WHERE NOT EXISTS (SELECT 1 FROM sources WHERE source_type = 'transcripts');
SQL

# Phase 2 — healthy baseline
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-healthy.json \
  api python scripts/run_collector.py --source simulated

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

docker compose exec api python -m app.worker --run-once absence
docker compose exec api python scripts/run_readers.py

# Phase 3 — Stage 1 ingestion
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-concerning.json \
  api python scripts/run_collector.py --source simulated
docker compose exec api python scripts/run_readers.py

# Phase 4 — score history + scoring + narration
docker compose exec -T db psql -U postgres -d agentic_churn < demo-wara/wara-score-history.sql
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/run_narrator.py
```

**Checkpoint:** open `http://localhost:5173`, log in as `marta` /
`agentic-demo-2026`. Score should read **≈55-61, Watch**.

---

## Stage 2 — Escalation (target ≈ 85-97, Critical / At risk)

**Story:** the inventory hiccup wasn't one-off. Support reopens the same
kind of ticket, and it sits open past the response-time target Wara
agreed on. That same afternoon, frustrated, Juan sends a short run of
plain, everyday messages — blunt, mentions telling his manager, mentions
looking at another provider, asks to double-check what was agreed on for
response times. One repeating technical problem plus how a real person
tends to write when annoyed — together, that's enough to tip the account
into real risk.

**Files:** `fixtures/wara-escalation.json` (the ticket) +
`fixtures/wara-escalation-signals.json` (the four messages) — both
required for full finding-type coverage.

**Full instructions and worked arithmetic:** `ESCALATION.md` (also has a
lighter, ticket-only alternative if you want a tighter mid-70s number
instead of full coverage).

```bash
cp demo-wara/fixtures/wara-escalation.json demo/fixtures/wara-escalation.json
cp demo-wara/fixtures/wara-escalation-signals.json demo/fixtures/wara-escalation-signals.json
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-escalation.json \
  api python scripts/run_collector.py --source simulated
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-escalation-signals.json \
  api python scripts/run_collector.py --source simulated
docker compose exec api python scripts/run_readers.py
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/run_narrator.py
```

**Checkpoint:** reload the dashboard. Score should read **≈85-97,
At risk (Critical / High risk)**.

---

## Stage 3 — Recovery (target ≈ 55-65, back to Watch)

**Story:** a week later, at their regular Friday sync, the ticket is
fixed, both admit they'd just been heads-down and busy (not upset with
each other), and two small tickets get closed the same hour they're
opened. An ordinary good week.

**Files:** `fixtures/wara-recovery-followup.json`,
`wara-reunion-guion-en.md` (meeting script),
`wara-weekly-sync-recovery.m4a` (the recording — see the note below).

**Full instructions, why the audio alone isn't enough, and worked
arithmetic:** `RECOVERY.md`.

```bash
# R0-R1 — follow-up events (ticket resolution + 2 fast fixes + warm email)
cp demo-wara/fixtures/wara-recovery-followup.json demo/fixtures/wara-recovery-followup.json
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-recovery-followup.json \
  api python scripts/run_collector.py --source simulated

# R2 — the meeting recording
mkdir -p demo/meeting-audio/wara-weekly-sync
cp demo-wara/wara-weekly-sync-recovery.m4a demo/meeting-audio/wara-weekly-sync/
docker compose up -d --build
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"series_id":"wara-weekly-sync","status":"granted","all_parties_confirmed":true}' \
  http://localhost:8000/api/meeting-audio/consent
docker compose exec worker python -m app.worker --run-once audio

# R3 — readers
docker compose exec api python scripts/run_readers.py
```

**Then, in the dashboard UI** (`http://localhost:5173`, `marta` /
`agentic-demo-2026`): open the contribution bars for all 9 findings that
don't fade on their own — `usage_deviation`, `csat_deviation`,
`contact_absence`, `relationship_change`, `recurring_issue`,
`tone_deterioration`, `escalation_language`, `competitive_mention`,
`contractual_reference` — and click **False alarm** twice on each. Given
Stage 2's larger full-coverage total, two rounds usually lands you close
to the Watch line but not quite under it — check the score, then go back
and add a third round on the biggest bars if it's still At risk. See
`RECOVERY.md` R4/"Worked arithmetic" for exactly why and the expected
numbers at 2 vs. 3 rounds.

```bash
# R5-R6 — recompute and narrate
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/run_narrator.py
```

**Checkpoint:** reload the dashboard. Score should read **≈55-65,
Watch** — down from ≈85-97 (Critical / At risk).

> **⚠️ About the audio file.** `wara-weekly-sync-recovery.m4a` was
> generated from an earlier, longer script about a different story
> (checkout_api, a competitor mention, an SLA discussion). It still
> works for exercising the ingestion *pipeline* — transcription,
> diarization, speaker matching, commitment extraction — but it won't
> literally say "ticket 209." For a recording that matches this runbook's
> story word for word, regenerate the audio from
> `wara-reunion-guion-en.md` with your own AI voice tool (nothing in this
> repository can synthesize audio) and save it back to the same
> filename. Everything else in Stage 3 works either way.

---

## The 12 finding types, end to end

| Finding type | Stage | What it needs to fire |
|---|---|---|
| `usage_deviation` | 1 | A product-area usage metric statistically outside its own baseline |
| `csat_deviation` | 1 | A CSAT score statistically outside a stakeholder's own baseline |
| `contact_absence` | 1 | No contact from anyone at the client for longer than the commitment cadence |
| `relationship_change` | 1 | A named stakeholder inactive for 28+ days |
| `broken_response_promise` | 2 | A support ticket still open past its response-time commitment |
| `recurring_issue` | 2 | Two or more tickets with near-identical titles (embedding cluster) |
| `tone_deterioration` | 2 | A message from a stakeholder with ≥5 baseline messages, abruptly different in style |
| `escalation_language` | 2 | A message mentioning escalating to a manager/leadership |
| `competitive_mention` | 2 | A message mentioning an alternative provider |
| `contractual_reference` | 2 | A message referencing agreed terms, without tripping the redaction markers |
| `commitment_met` | 3 | A support ticket resolved well inside its response-time commitment (positive, capped) |
| `meeting_commitment` | 3 | A verbal commitment extracted from a meeting transcript (owner + deadline) |

Plus one feature that isn't a finding type but is demonstrated
throughout: **content redaction** — Stage 1's `wara-gmail-007` mentions
"a discount," matching the `commercial_negotiation` exclusion in
`wara-profile.yaml`, and its body is stored as `[REDACTED]` (see
`INSTALL.md`'s "Content redaction" section).

---

## What you can try once all three stages are loaded

- **Dashboard** — score, band, 14-day trend, contribution bars, narrator
  headline.
- **Evidence trace** — click any contribution bar to see the quoted
  message/ticket/transcript, the baseline-vs-now numbers, and the exact
  arithmetic (matches the worked tables in `INSTALL.md`/`ESCALATION.md`/
  `RECOVERY.md`).
- **False alarm / Correct feedback** — used in Stage 3, but you can try
  it on any finding at any stage.
- **Draft composer** — `POST /api/drafts` with an `issue_id` and
  `stakeholder_id` from the dashboard response, to see a suggested
  outreach email for one of the open issues.
- **Ask agent** — `POST /api/ask` with a natural-language question like
  "why did the score go up?" or "what's still open with Fernando?".
- **Coverage** — `GET /api/coverage` to see every source read and
  anything sitting in quarantine.

---

## Cleanup / start over

```bash
docker compose down -v && docker compose up -d --build
docker compose exec api python scripts/seed.py
```

Then re-run from Stage 1 onward. **Always do this — not just a re-`cp`
— if you change any `demo-wara/fixtures/*.json` file after already
seeding once.** The container only ever reads the deployed copy in
`demo/`, and Postgres keeps whatever was already ingested; copying an
updated fixture over an old one does not retroactively fix an
already-seeded database. See `INSTALL.md`'s troubleshooting entry "Score
lands well above 65 ... instead of ~55-61" for the diagnostic command.

To remove the Wara files from `demo/` (restoring the repo to its original
state):

```bash
rm -f demo/wara-profile.yaml
rm -f demo/fixtures/wara-healthy.json demo/fixtures/wara-concerning.json \
      demo/fixtures/wara-escalation.json demo/fixtures/wara-escalation-signals.json \
      demo/fixtures/wara-recovery-followup.json
rm -rf demo/meeting-audio/wara-weekly-sync
# Remove the CLIENT_PROFILE_PATH line from .env (or set it back to ./demo/client-profile.yaml)
```

The `demo-wara/` directory itself can be kept or deleted — it has no
effect on the application or tests.
