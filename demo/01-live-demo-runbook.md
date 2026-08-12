# 01 · Live demo runbook

A minute-by-minute script for a 20-minute live demo, built around the same Meridian Logistics scenario used throughout this documentation set (`examples/01-end-to-end-walkthrough.md`), plus a contingency plan for when a live API misbehaves in front of judges — which, at some point, it will.

## Before you start (T-30 minutes)

- Run `data-base/11-seed-data.sql` against a fresh database — clean Meridian profile, 9 finding types, 5 playbook actions, no leftover findings from a prior rehearsal.
- Confirm all MVP sources show `connected` in `sources` (`demo/03-environment-and-fixtures-checklist.md`).
- Have the **replay fixture** loaded and ready but *not yet run* — this is the contingency path, staged so it can fire in one command if needed.
- Open three windows: the dashboard (main screen), a terminal with the replay command ready, and the demo Gmail inbox.

## The script

| Time | What you do | What you say | What the judges see |
|---|---|---|---|
| 0:00–1:30 | Open on the **Healthy** dashboard state | "Nobody is assigned to notice six systems' worth of small signals together — that's the actual problem. Here's the tool, on a healthy account, right now." | A near-empty screen: *"Nothing needs you today."* — deliberately unimpressive (P6). |
| 1:30–3:00 | Narrate the scenario | "Meridian's CTO Ana is about to send a real email — right now, live — that on its own looks unremarkable." | Dashboard still healthy. |
| 3:00–4:00 | **Live action #1** — send the real email from the demo Gmail account | "I'm sending this now, no editing, no pre-staging." | Nothing yet — this is deliberate; narrate what's about to happen while it's in flight. |
| 4:00–4:45 | Wait for the pipeline (~40s budget, `requirements/11-non-functional-requirements.md` REQ-NFR-02) | "The collector picks this up, the ledger appends it, two readers run in parallel, the gate checks the evidence, the scoring engine does plain arithmetic — no step here is scripted for the demo, this is the real pipeline." | Pulse timeline updates first (proves the ledger append), then the score animates from its previous value. |
| 4:45–6:30 | Score has moved — open the **evidence trace panel** on the top contribution bar | "Every number is a door. This didn't just say 'sentiment negative' — it says *why*, and lets you check the math yourself." | Side-by-side baseline-vs-current comparison, the actual quoted email, the arithmetic in plain sentences (spec §11.4). |
| 6:30–8:30 | Type into the **ask bar**: *"Why did the score go up?"* | "This isn't a chatbot bolted on top — it's reading the same numbers you just saw, not recalculating anything." | Delta breakdown component, rendered in under 3 seconds (REQ-M9-08). |
| 8:30–11:00 | Click **"Write to Ana about this"** on the top issue | "Watch what it does and doesn't do." | A generated draft, acknowledging the specific failure first. Point out explicitly: **"Copy draft" and "Log as sent (manual)" — no send button. Not hidden. Not disabled. Not present anywhere in this product."** |
| 11:00–12:30 | **Live action #2** — click "Copy draft," paste it into the real Gmail compose window, send it for real | "A human — me, right now — is the only thing in this system that can make this message leave the building." | The email actually sends. This is the single most important beat in the demo — don't rush it. |
| 12:30–14:00 | Open the **feedback loop** — mark a secondary, less central finding as "false alarm" | "Now watch it learn, without any retraining." | The card updates in place: *"weight reduced — your team flagged this pattern as a false alarm."* |
| 14:00–15:30 | **Live action #3** — trigger a second scoring run (a small follow-up event, or the manual "recompute" affordance in the demo build) | "Same pattern, next time it fires, counts for less. That's the entire learning mechanism — one number, fully explained." | `score_contributions.damping` visibly lower on the next matching card. |
| 15:30–17:00 | Show the **response clock closing** — the sent email lands back through the collector | "It watches whether its own suggestion actually worked." | `response_pairs.state` flips from `open_overdue` toward `resolved`; the ticket-side contribution starts fading on its half-life. |
| 17:00–19:00 | Zoom out — show the healthy state again on a *different*, unrelated seeded account if available, or narrate it | "Same tool, quiet week, and it says so instead of manufacturing concern. That's not a missing feature — that's principle six." | Reinforces P6 without needing new evidence. |
| 19:00–20:00 | Close | "Three things: what's going wrong, why it matters *here*, what to do next. All three, traceable to a real message, in under a minute of real time." | — |

## Real, live actions performable in this demo without violating any product boundary

Everything below is a genuine system action, not a mocked one, and none of it crosses a limit in `requirements/11-non-functional-requirements.md` §Hard product boundaries:

1. **Real collection via API** — the Gmail webhook fires on a real sent email; nothing about ingestion is staged.
2. **Real ledger append** — visible in the pulse timeline within ~1s of the collector firing.
3. **Real recompute** — the score animates from an actual scoring run, not a canned number.
4. **Real draft generation** — an actual LLM call against the live evidence, not a stored string.
5. **Real verdict → damping** — clicking false alarm writes a real `feedback_verdicts` row and recomputes a real `damping_weights` row.
6. **Real response-clock closure** — sending the actual copied draft and having it collected back closes a real `response_pairs` row.

What is **never** live, by design, matching P4: no step in this script includes the system itself sending anything. Step 11:00–12:30 is a human pasting and sending through their own email client — the system's involvement stops at "Copy draft."

## Contingency: replay mode

If the live Gmail/Zendesk API is unreachable, rate-limited, or simply flaky on venue wifi, switch to replay without missing a beat — this is not a degraded fallback, it's a first-class architectural feature (`requirements/02-event-ledger.md` REQ-M2-07, the same replay job that powers profile edits and weight tuning) doing double duty as a demo safety net:

```bash
# Pre-staged fixture: the exact scenario from examples/01-end-to-end-walkthrough.md,
# captured as a sequence of events with real timestamps, replayed at demo speed.
python -m scripts.replay_demo_fixture --fixture demo/fixtures/meridian-week.json --speed live
```

**What to say if you have to switch:** *"I'll switch to replay mode — this is the same replay job the system uses for profile edits and weight tuning, not a special demo mode. It's running the identical scenario against the identical ledger schema; the only thing that's different is where the events came from."* This line matters — it turns an infrastructure hiccup into a demonstration of the bitemporal ledger's honesty (`data-base/03-schema-ledger.md`), which is a stronger flex than the live API working would have been anyway.

The fixture file is generated from `data-base/11-seed-data.sql` plus the six events in `examples/01-end-to-end-walkthrough.md` §5 — see `demo/03-environment-and-fixtures-checklist.md` for how it's built and kept in sync.

## Traceability

`examples/01-end-to-end-walkthrough.md`, `sequences/01-sequence-signal-to-score.md`, `requirements/11-non-functional-requirements.md`, `demo/02-impact-story.md`, `demo/03-environment-and-fixtures-checklist.md`.
