# Wara Demo — Stage 2: Escalation (target score ≈ 90+, Critical / At risk)

**Stage 2 of 3.** Adds to the installed Wara demo (`INSTALL.md`) — does
not modify any existing file. Run this only after Stage 1 is complete and
the dashboard shows a Watch-band score around 55-61.

```
demo-wara/
  fixtures/wara-escalation.json          ← new events (Aug 19) — the ticket saga
  fixtures/wara-escalation-signals.json  ← new events (Aug 19) — 4 things Juan says
  ESCALATION.md                          ← this file
```

**The story.** The small inventory-sync hiccup from Stage 1 wasn't a
one-off. The same kind of ticket comes back — the sync job fails again,
support reopens it, and this time it sits open past the response-time
target Wara agreed on. That same afternoon, frustrated, Juan sends a
short run of messages: one blunt note, one mention that he has to explain
this to his own manager, one mention that Wara has started looking at
another provider "just to be safe," and one asking to double-check what
response times were actually agreed on. None of it is dramatic language —
it's exactly how a real, busy person writes when they're annoyed — but
together it's the full picture of an account tipping into real risk.

**All 8 remaining finding types fire in this stage** (Stage 1 already
covered 4). Nothing here is optional — every finding type the product
supports gets exercised across Stage 1 + Stage 2, so a live demo can show
the complete picture: a recurring technical failure *and* every way a
frustrated stakeholder tends to put that in writing.

---

## Why the score only goes up

`findings` are immutable — no reader ever retracts one it already emitted
(`already_interpreted` guards throughout `backend/app/readers/`).
Ingesting Stage 2's events never deletes or shrinks Stage 1's four
findings; it only adds more on top. This is intentional
(REQ-M6-P4: "adding a negative finding shall never lower the score") — the
whole point of Stage 3 later is to show that *only* two mechanisms bring
a score back down: closing out a lifecycle-aware finding (see below) and
a human reviewer marking a finding `false_alarm` from the dashboard.
Neither happens in this stage.

**Why the target is "90+" and not a tighter number.** Six new finding
types, each with real weight, land on top of Stage 1's four — there is no
way to exercise every finding type the product has *and* land on a
precise mid-70s number; the two goals are in real tension, and 90+ is the
honest arithmetic result of choosing full coverage. If you'd rather stop
at a lower number, see "A lighter version" at the end of this file.

---

## E0 — copy both fixtures into the mounted directory

```bash
cp demo-wara/fixtures/wara-escalation.json demo/fixtures/wara-escalation.json
cp demo-wara/fixtures/wara-escalation-signals.json demo/fixtures/wara-escalation-signals.json
```

## E1 — ingest both

```bash
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-escalation.json \
  api python scripts/run_collector.py --source simulated
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/wara-escalation-signals.json \
  api python scripts/run_collector.py --source simulated
```

This rebuilds `response_pairs` for ticket #209 — needed for the
Commitment reader to see it as reopened-and-overdue in Step E2.

## E2 — run the readers

```bash
docker compose exec api python scripts/run_readers.py
```

Effects of the ingested events:
- **Ticket #209** was created and resolved cleanly at 08:00/10:30 (neutral,
  same pattern as Stage 1's routine tickets), then **reopened** at 14:00
  with the identical title and left open past the 4-business-hour P1
  target (`wara-profile.yaml` commitments). The Commitment reader emits
  `broken_response_promise` for the reopened occurrence.
- The **Recurrence reader** clusters the 10:30 resolution and the 14:00
  reopening — same ticket, same title — into one recurring pattern,
  emitting `recurring_issue`.
- The **Tone reader** flags Juan's blunt one-liner as a sharp break from
  his 16-message warm baseline → `tone_deterioration`.
- The **Intent reader** classifies the other three messages →
  `escalation_language`, `competitive_mention`, `contractual_reference`.

## E3 — recompute the score (twice)

Two consecutive runs in the new band are required to leave Watch and
display At risk (REQ-M6-18/19):

```bash
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py
```

## E4 — refresh the narrator and verify, in the UI

```bash
docker compose exec api python scripts/run_narrator.py
```

Reload `http://localhost:5173` and check the dashboard:
- Score/band should now read **At risk (Critical / High risk)**.
- The narrator headline should mention the reopened ticket and the shift
  in tone.
- Six new contribution bars, alongside Stage 1's four unchanged ones:
  `broken_response_promise`, `recurring_issue`, `tone_deterioration`,
  `escalation_language`, `competitive_mention`, `contractual_reference`.

---

## Worked arithmetic

Same formula as Stage 1 (`points = base × influence × criticality ×
confidence × magnitude × recency × damping`). The two ticket-lifecycle
rows are exact (`evaluate_commitment` in
`backend/app/readers/domain/services.py` fixes confidence at 1.0 for
`broken_response_promise`; `recurrence_magnitude` gives the cluster
magnitude). The four language-model rows are realistic estimates — an
LLM reader's confidence/magnitude for a given message isn't fully
deterministic, so treat those four as "this is the shape of the math,"
not a guaranteed reproduction.

| Finding | Story | base | influence | criticality | confidence | magnitude | recency | rank | points |
|---|---|---|---|---|---|---|---|---|---|
| `broken_response_promise` | Ticket #209 reopened, left open ~8h against the 4h target | 20 | 1.0 | 1.0 | 1.00 | 1.00 | 1.08 | 1st (100%) | **21.60** |
| `recurring_issue` | Same ticket, same title, reopened — a 2-ticket cluster | 12 | 1.0 | 1.0 | ~0.80 | 0.33 | 1.0 | 2nd (60%) | **1.92** |
| `tone_deterioration` | Juan's one-line "This needs to be fixed today" | 10 | 1.6 | 1.0 | ~0.80 | ~0.60 | 1.0 | 1st (100%) | **7.68** |
| `escalation_language` | "I have to explain this to my manager tomorrow" | 14 | 1.6 | 1.0 | ~0.85 | ~0.50 | 1.0 | 1st (100%) | **9.52** |
| `competitive_mention` | "We've started looking at another provider too" | 14 | 1.6 | 1.0 | ~0.85 | ~0.50 | 1.0 | 1st (100%) | **9.52** |
| `contractual_reference` | "Can we double check what we agreed on for response times?" | 14 | 1.6 | 1.0 | ~0.85 | ~0.50 | 1.0 | 1st (100%) | **9.52** |
| | | | | | | | | **Stage 2 addition** | **≈59.76** |

```
cumulative points = 30.70 (Stage 1) + 59.76 (Stage 2) ≈ 90.46
score = 100 × (1 − e^(−90.46 / 33)) ≈ 93.5
```

**Expected dashboard result: approximately 85-97, At risk (Critical /
High risk)** — the score curve flattens hard as it approaches 100
(REQ-M6-16: it mathematically never reaches exactly 100), so don't be
surprised if it lands in the low-to-mid 90s specifically. That's the
honest, full-coverage picture of this account.

---

## A lighter version, if you want a mid-band number instead

If you're presenting the 55 → 77 → recovery arc specifically and don't
need every finding type to fire in Stage 2, ingest **only**
`wara-escalation.json` (skip `wara-escalation-signals.json`). That alone
adds ≈23.52 points (cumulative ≈54.22, score ≈80-81) and still leaves 6
of the 8 Stage 2/3 finding types available to demonstrate individually
later — see each fixture's `_comment` fields for what each message is
for, and ingest `wara-escalation-signals.json` on its own afterward
whenever you want to show it. The full-coverage path above is the
recommended default; this is the alternative if a tighter number matters
more for your specific walkthrough.

---

## Next

Once the dashboard shows an At risk score in the high 80s/90s, continue
to **`RECOVERY.md`** (Stage 3) to bring the score back down using a
recorded recovery meeting.
