# Wara Demo — Stage 3: Recovery (audio meeting, score down from ≈90+ to ≈55-65 Watch)

**Stage 3 of 3.** Adds to the installed Wara demo (`INSTALL.md` +
`ESCALATION.md`) — does not modify any existing file. Run this only after
Stage 2 is complete and the dashboard shows an At risk (Critical / High
risk) score in the high 80s/90s.

```
demo-wara/
  fixtures/wara-recovery-followup.json  ← new events (Aug 21) — ticket resolution, fast fixes, warm email
  wara-reunion-guion-en.md              ← the meeting script (context for the audio)
  wara-weekly-sync-recovery.m4a         ← the meeting recording — see the ⚠️ note in the script file
  RECOVERY.md                           ← this file
```

**The story.** A week later, Juan and Fernando have their regular Friday
sync. The inventory ticket is fixed. Both admit they'd been heads-down
and out of touch, not upset with each other. Two small tickets get
closed the same hour they're opened. It's an ordinary good week — which
is exactly what a real recovery looks like.

---

## Why "read the audio" alone isn't enough to lower the score

Verified by reading the scoring code, not assumed:

1. **Findings are immutable.** Readers never retract a finding they
   already emitted (`already_interpreted` guards throughout
   `backend/app/readers/`). Ingesting new events — audio included — never
   deletes old findings.
2. **Only 2 of the 12 finding types ever fade on their own:**
   `broken_response_promise` and `commitment_met` — the only two whose
   lifecycle consults `response_pairs` (`resolve_lifecycle` in
   `sqlalchemy_repository.py`). Everything else, `meeting_commitment`
   included, stays `open` at full `recency` forever unless a human acts
   on it (REQ-M6-10).
3. **`meeting_commitment` is a *negative* finding type.** Check
   `backend/app/scoring/domain/entities.py`:
   `POSITIVE_FINDING_TYPES = frozenset({"commitment_met"})` — only
   `commitment_met` subtracts from the score. A verbal commitment
   extracted from a meeting *adds* points (it represents a promise that
   now needs following up on), even when the meeting itself was calm and
   productive. That's why the script in `wara-reunion-guion-en.md`
   deliberately keeps to **two** commitments, not five.
4. **The one positive finding type (`commitment_met`) is capped at 25%**
   of the total negative points (REQ-M6-14). It can shave the score, not
   erase it.
5. **`false_alarm` feedback is the only lever that reduces an open
   finding's weight**, and it's a UI action: each `false_alarm` verdict
   on a finding halves its pattern's weight — `weight = 0.5^false_alarm_
   count × 1.15^correct_count` (capped at 1.0, `services.py:
   compute_weight`).
6. **Hysteresis:** to leave At risk, the score must stay under 55 for
   **2 consecutive** recompute runs (REQ-M6-18/19).

So Stage 3 has three parts, in order: **(A)** ingest the small follow-up
fixture that gives the two lifecycle-aware finding types a real, honest
"closed" state and adds capped positive points; **(B)** ingest the
recorded meeting, which mainly demonstrates the Meeting/Tone/Commitment
readers working on real transcribed audio; **(C)** use the dashboard's
own **False alarm** button on the Stage 1/2 findings that the CS lead —
having heard the meeting — judges no longer relevant. Nothing here is
fabricated outside the app — every action in (C) is a feedback verdict
the product itself exposes for exactly this purpose.

**Because Stage 2 now includes all 8 remaining finding types (≈90+), part
(C) needs more review passes here than a lighter Stage 2 would — see the
worked arithmetic below. Two rounds of `false_alarm` gets close but often
not quite under the At risk line; a third round on the biggest bars is
usually what actually settles it into Watch.**

---

## R0 — copy the follow-up fixture into the mounted directory

```bash
cp demo-wara/fixtures/wara-recovery-followup.json demo/fixtures/wara-recovery-followup.json
```

## R1 — ingest the follow-up events

```bash
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-recovery-followup.json \
  api python scripts/run_collector.py --source simulated
```

This rebuilds `response_pairs`, which is what lets step R3 resolve ticket
#209 and detect the two new fast-resolution tickets.

## R2 — set up the audio and ingest the meeting

Follow `AUDIO-INGESTION-TESTING.md` Step 0 to place the recording and
grant consent — in short:

```bash
mkdir -p demo/meeting-audio/wara-weekly-sync
cp demo-wara/wara-weekly-sync-recovery.m4a demo/meeting-audio/wara-weekly-sync/
docker compose up -d --build   # picks up the new local-storage mount, if not already running

curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"series_id":"wara-weekly-sync","status":"granted","all_parties_confirmed":true}' \
  http://localhost:8000/api/meeting-audio/consent

docker compose exec worker python -m app.worker --run-once audio
```

## R3 — run the readers

```bash
docker compose exec api python scripts/run_readers.py
```

Effects of R1 + R2's events:
- **Ticket #209, resolved Aug 21:** the already-emitted
  `broken_response_promise` finding moves from `open_overdue` (recency
  amplified) to `resolved` (recency → 1.0, then decays over its 14-day
  half-life). This removes the overdue amplifier.
- **Tickets #210/#211, created and resolved inside 1h each (well under
  the 4h SLA):** the Commitment reader emits 2 new `commitment_met`
  positive findings (~7.5 and ~11.25 pts, subject to the 25% cap).
- **CSAT 9 and the warm email:** atmosphere only. The long, calm email
  does **not** trigger `tone_deterioration` and resets `last_contact_at`,
  so no new `contact_absence` fires. Neither undoes any earlier finding —
  that's not how the reader layer works (see point 1 above).
- **The meeting recording:** 2 new `meeting_commitment` findings citing
  the transcript (Fernando's weekly note, Juan's channel-first habit).

## R4 — mark reviewed findings as `false_alarm`, from the dashboard UI

Open `http://localhost:5173` and log in as `marta` / `agentic-demo-2026`.

On the dashboard, the **contribution bars** list every finding driving
the score, grouped by finding type — the same UI you'd use for the demo
walkthrough, no admin panel, no API calls typed by hand:

1. Click a bar to open the **Evidence trace** dialog.
2. Review the evidence (quoted messages, baseline vs. now, the arithmetic).
3. Click **False alarm**. The panel re-fetches and shows the pattern's
   new `disclosure_text` confirming the damped weight.
4. Click **False alarm** again on the same finding for a second halving
   (weight 0.25), and once more for a third (weight 0.125) — see "Worked
   arithmetic" below for how many rounds each one typically needs. The
   button stays enabled between clicks — no need to close and reopen the
   dialog.
5. Repeat for the other findings below.

Findings worth reviewing here — everything from Stage 1/2 that doesn't
fade on its own: `usage_deviation`, `csat_deviation`, `contact_absence`,
`relationship_change`, `recurring_issue`, `tone_deterioration`,
`escalation_language`, `competitive_mention`, `contractual_reference`.
(Skip `broken_response_promise` — already resolving via R1/R3 — and
`commitment_met` / `meeting_commitment` — positive/new, nothing to review
yet.)

**Tune gradually, not all at once:** apply **two** rounds to every bar
first (that's the baseline this file's arithmetic uses), then jump to R5
and check the score. `false_alarm` has no clean UI "undo" — the
**Correct** button raises weight by ×1.15 per click (capped at 1.0), so
reversing three rounds of `false_alarm` (weight 0.125) would take many
`Correct` clicks to climb back near 1.0. It's much easier to add another
`false_alarm` round to a few remaining bars than to walk one back.

## R5 — recompute the score (twice)

Two consecutive runs in the new band are required to leave At risk
(REQ-M6-18/19):

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py
```

## R6 — refresh the narrator and verify, in the UI

```bash
docker compose exec api python scripts/run_narrator.py
```

Reload `http://localhost:5173` and check the dashboard:
- Score/band should now read **Watch** (or lower, depending on how many
  `false_alarm` rounds you applied).
- The narrator headline and reasons should reflect the smaller, damped
  set of contributions plus the two new `commitment_met` and two new
  `meeting_commitment` bars.
- The evidence trace for `broken_response_promise` should show
  `state: resolved` instead of `open_overdue`.

If the score is still At risk after R5/R6, go back to R4, add one more
`false_alarm` round to the largest remaining bars (usually
`csat_deviation`, `usage_deviation`, and the four language findings), and
repeat R5/R6.

---

## Worked arithmetic

| Finding | Stage 1/2 points | After 2× `false_alarm` (×0.25) | After 3× `false_alarm` (×0.125) |
|---|---|---|---|
| `usage_deviation` | 9.86 | 2.47 | 1.23 |
| `csat_deviation` | 11.66 | 2.92 | 1.46 |
| `contact_absence` | 5.82 | 1.46 | 0.73 |
| `relationship_change` | 3.36 | 0.84 | 0.42 |
| `recurring_issue` | 1.92 | 0.48 | 0.24 |
| `tone_deterioration` | 7.68 | 1.92 | 0.96 |
| `escalation_language` | 9.52 | 2.38 | 1.19 |
| `competitive_mention` | 9.52 | 2.38 | 1.19 |
| `contractual_reference` | 9.52 | 2.38 | 1.19 |
| `broken_response_promise` (resolved, unaffected by `false_alarm`) | 21.60 | 20.00 | 20.00 |
| `meeting_commitment` ×2 (new, from the audio) | — | +11.90 | +11.90 |
| **Negative subtotal** | | **≈49.13** | **≈40.51** |
| `commitment_met` ×2 (new, from the follow-up fixture, capped at 25%) | — | −12.28 | −10.13 |
| **Net total points** | | **≈36.85** | **≈30.38** |
| **Score** | | **≈67.3 (still At risk)** | **≈60.2 (Watch)** |

**Expected dashboard result after three rounds: approximately 55-65,
Watch band.** Two rounds alone usually isn't enough given Stage 2's
full-coverage total — this is expected, not a bug; go back to R4 for a
third round as described above.

---

## Tuning without SQL

All from the dashboard:
- **Still At risk (≥65) after three rounds:** add a fourth round to the
  two or three biggest remaining bars, then repeat R5.
- **Dropped below 35 (Healthy) and you wanted to stay in Watch:** apply
  fewer rounds, or `false_alarm` fewer patterns, then re-check after R5.
  (Walking a weight back up with `Correct` is not a clean 1:1 reversal —
  see point 5 above.)

## Optional SQL — verification only, not required

```sql
-- Score + band of the last few runs
SELECT computed_at, score, band, raw_band FROM score_runs ORDER BY computed_at DESC LIMIT 4;

-- Per-finding contribution and damping after R4/R5
SELECT sc.finding_id, f.finding_type, sc.points_contributed, sc.is_positive, sc.damping
FROM score_contributions sc JOIN findings f ON f.id = sc.finding_id
WHERE sc.score_run_id = (SELECT id FROM score_runs ORDER BY computed_at DESC LIMIT 1)
ORDER BY sc.is_positive, sc.points_contributed DESC;
```

---

## About the audio file

`wara-weekly-sync-recovery.m4a` in this folder was generated from an
**earlier** version of the script (a longer, checkout_api/VTEX/SLA-themed
story). `wara-reunion-guion-en.md` has since been rewritten to match this
demo's simpler Stage 1/2 story (the inventory-sync ticket #209 saga). The
old audio still works for exercising the ingestion *pipeline*
(transcription, diarization, speaker matching, commitment extraction) —
it just won't cite ticket #209 by name. For a fully matching recording,
regenerate the audio from the current script with your own AI voice tool
and save it back to the same filename; see the note at the top of
`wara-reunion-guion-en.md`.

---

## If you used the "lighter version" of Stage 2

If you followed `ESCALATION.md`'s lighter path (only
`wara-escalation.json`, cumulative ≈80-81, not the full ≈90+), Stage 2's
negative subtotal is smaller, so two rounds of `false_alarm` on
`usage_deviation`, `csat_deviation`, `contact_absence`,
`relationship_change`, and `recurring_issue` alone (no
`tone_deterioration`/`escalation_language`/`competitive_mention`/
`contractual_reference` to review, since you never ingested them) is
enough to land in Watch — see this file's git history / `ESCALATION.md`'s
original worked table for that smaller-scale arithmetic.
