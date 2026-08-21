# Wara Recovery — bringing the score down from `at_risk` (~99) to `Watch`

**Adds to the installed Wara demo (`INSTALL.md`) — does not modify any
existing file.** Two new files only:

```
demo-wara/
  fixtures/wara-recovery.json   ← new events (the "recovery" stage, Aug 19)
  RECOVERY.md                   ← this runbook
```

Run this only after `INSTALL.md` phases 0–4 have completed and the
dashboard shows a score in `at_risk` (~99).

---

## Why the score can't just be "fixed" with more good data

Verified by reading the scoring code, not assumed:

1. **Findings are immutable.** Readers never retract a finding they already
   emitted (`already_interpreted` guards in `commitment_reader.py`,
   `tone_reader.py`, etc.). Ingesting new events never deletes old findings.
2. **Only 2 of the 12 finding types ever fade on their own:**
   `broken_response_promise` and `commitment_met` (`resolve_lifecycle` in
   `sqlalchemy_repository.py` — the only two that consult `response_pairs`).
   The other 9 — `tone_deterioration`, `escalation_language`,
   `competitive_mention`, `contractual_reference`, `recurring_issue`,
   `usage_deviation`, `csat_deviation`, `contact_absence`,
   `relationship_change`, `meeting_commitment` — stay `open` with
   `recency = 1.0` forever unless you act on them (REQ-M6-10).
3. **The one positive finding type (`commitment_met`) is capped at 25%** of
   the total negative points (REQ-M6-14). It can shave the score, not erase
   it.
4. **`false_alarm` feedback is the only lever that reduces an open
   finding's weight**, and it's a UI action: each `false_alarm` verdict on a
   finding halves its pattern's weight —
   `weight = 0.5^false_alarm_count * 1.15^correct_count` (capped at 1.0,
   `services.py: compute_weight`). Two `false_alarm` clicks → weight 0.25.
5. **Hysteresis:** to leave `at_risk`, the score must stay under 55 for
   **2 consecutive** recompute runs (REQ-M6-18/19).

So the recovery has two parts: (A) ingest events that give the two
lifecycle-aware finding types a real, honest "closed" state and add capped
positive points, and (B) use the dashboard's own **False alarm** button on
the findings the CS lead has reviewed and judged mis-read or no longer
relevant. Nothing here is fabricated outside the app — every action is a
feedback verdict the product itself exposes for exactly this purpose.

**No SQL and no `curl` are needed for the score-adjustment step (R3).** SQL
only shows up in the two verification queries at the very end, and even
those are optional — the dashboard UI shows the same information.

---

## R0 — copy the fixture into the mounted directory

```bash
cp demo-wara/fixtures/wara-recovery.json demo/fixtures/wara-recovery.json
```

## R1 — ingest the recovery events

```bash
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-recovery.json \
  api python scripts/run_collector.py --source simulated
```

This rebuilds `response_pairs`, which is what lets step R2 resolve ticket
#201 and detect the three new fast-resolution tickets.

## R2 — run the readers

```bash
docker compose exec api python scripts/run_readers.py
```

Effects of the ingested events:
- **Ticket #201, resolved Aug 19:** the already-emitted
  `broken_response_promise` finding moves from `open_overdue`
  (recency amplified ~1.5×) to `resolved` (recency → 1.0, then decays over
  its 14-day half-life). This removes the overdue amplifier.
- **Tickets #210/#211/#212, created and resolved inside 40 min (well under
  the 4h SLA):** the CommitmentReader emits 3 new `commitment_met` positive
  findings (~10 pts each, subject to the 25% cap).
- **CSAT 9 and the warm, collaborative email:** atmosphere only. The long,
  friendly email does **not** trigger `tone_deterioration` (not abrupt) and
  resets `last_contact_at`, so no new absence fires. Neither undoes any
  earlier finding — that's not how the reader layer works (see point 1
  above).

## R3 — mark reviewed findings as `false_alarm`, from the dashboard UI

Open `http://localhost:5173` and log in as `marta` / `agentic-demo-2026`.

On the dashboard, the **contribution bars** list every finding driving the
score, grouped by finding type. This is the same UI you'd use for the demo
walkthrough — no admin panel, no API calls typed by hand:

1. Click a bar (or, if it shows a `×N` badge, expand it first, then click
   one of the individual entries) to open the **Evidence trace** dialog.
2. Review the evidence (quoted messages, baseline vs. now, arithmetic).
3. Click **False alarm**. The panel re-fetches and shows the pattern's new
   `disclosure_text` confirming the damped weight.
4. Click **False alarm** again on the same finding to reach weight `0.25`
   (two halvings). The button stays enabled between clicks — no need to
   close and reopen the dialog.
5. Close the dialog and repeat for the other open, negative finding types.

The 9 finding types that never fade on their own — the ones worth
reviewing here — are: `tone_deterioration`, `escalation_language`,
`competitive_mention`, `contractual_reference`, `recurring_issue`,
`usage_deviation`, `csat_deviation`, `contact_absence`,
`relationship_change`, `meeting_commitment`. You don't need to touch
`broken_response_promise` (already resolving via R1/R2) or `commitment_met`
(positive, already capped).

**Tune gradually, not all at once:** apply **one** `false_alarm` per
pattern first, then jump to R4 and check the score. `false_alarm` has no
clean UI "undo" — the **Correct** button raises weight by ×1.15 per click
(capped at 1.0), so reversing a double `false_alarm` (weight 0.25) would
take ~10 `Correct` clicks to climb back near 1.0. It's much easier to add a
second `false_alarm` round to a few remaining bars than to walk one back.

## R4 — recompute the score (twice)

Two consecutive runs in the new band are required to leave `at_risk`
(REQ-M6-18/19):

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py
```

## R5 — refresh the narrator and verify, in the UI

```bash
docker compose exec api python scripts/run_narrator.py
```

Reload `http://localhost:5173` and check the dashboard:
- Score/band should now read `watch` (or lower, depending on how many
  `false_alarm` rounds you applied).
- The narrator headline and reasons should reflect the smaller, damped set
  of contributions.
- The contribution bars for the finding types you damped should be smaller
  than before, and the 3 new `commitment_met` positive bars should appear.

---

## Tuning without SQL

All from the dashboard:
- **Still `at_risk` (≥55):** go back to R3 and add a second `false_alarm`
  round to any bar you only damped once, then repeat R4.
- **Dropped below 35 (`healthy`) and you wanted to stay in `Watch`:** avoid
  a second `false_alarm` round in R3 next time — apply it to fewer patterns,
  or only once per pattern, then re-check after R4. (See the note on
  `Correct` above — walking a weight back up is not a clean 1:1 reversal.)

## Optional SQL — verification only, not required

If you want to inspect the raw numbers instead of reading the dashboard:

```sql
-- Score + band of the last few runs
SELECT computed_at, score, band, raw_band FROM score_runs ORDER BY computed_at DESC LIMIT 4;

-- Per-finding contribution and damping after R3/R4
SELECT sc.finding_id, f.finding_type, sc.points_contributed, sc.is_positive, sc.damping
FROM score_contributions sc JOIN findings f ON f.id = sc.finding_id
WHERE sc.score_run_id = (SELECT id FROM score_runs ORDER BY computed_at DESC LIMIT 1)
ORDER BY sc.is_positive, sc.points_contributed DESC;
```

---

## Alternative you didn't pick: a clean reajusted dataset

If at some point you'd rather reach `Watch` deterministically, without
marking most existing findings as false alarms, the other option discussed
was a single reajusted ingestion (`wara-concerning-mild.json`-style) that
keeps only 1–2 moderate signals instead of the full 10. That reaches
`Watch` in one ingestion with no feedback step, but it means not using the
`at_risk` dataset already installed — it's a replacement, not an addition.
Not implemented here since you chose the recovery-on-top approach.
