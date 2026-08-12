# 02 · Impact story

The demo (`demo/01-live-demo-runbook.md`) shows *that* the system works. This document is the quantified case for *why it matters* — three numbers, each traceable to the same worked scenario (`examples/01-end-to-end-walkthrough.md`), plus the one demo trick that turns a claim into a provable fact.

## 1. Lead time: three weeks, and it's provable, not asserted

The product's own success target (spec §14.2) is risk surfaced **≥ 2 weeks before the team would have escalated on their own.** The worked scenario shows why that's realistic, not aspirational:

- All five signals — the slow ticket reply, the second reopen, the 22% usage drop, Ana's terser emails, Diego's Slack silence, the CSAT drop — were **fully visible in the system within the same week**, connected into one story in about 40 seconds of processing time after the last one landed.
- None of the five people who "own" those five systems had a reason to cross-reference the others. The Zendesk queue owner sees a reopened ticket, not a CTO's tone shift. Ana's account contact reads a slightly shorter email, not a CSAT score trending down. **The pattern only exists across systems — and nobody is assigned to look across systems** (spec §2.2).
- In practice, that correlation happens at the next natural checkpoint where someone *does* look broadly — a quarterly business review, a renewal prep call, or a CSAT report that gets read weeks after it's collected. That's routinely **3+ weeks** after the signals themselves existed.

**The demo trick that makes this provable, not just claimed:** the event ledger is bitemporal (`data-base/03-schema-ledger.md`) — every event carries both *when it happened* and *when the system learned of it*. That means you can literally ask the system what it knew at an earlier point in time:

```sql
-- "What did we know as of three weeks before today?"
SELECT * FROM events WHERE recorded_at <= now() - interval '21 days' ORDER BY occurred_at;
```

Run that query live, and the audience sees a materially thinner picture than today's — not because you're describing what the system *would* have shown, but because you're replaying what it *actually* had. This is the single strongest proof point available: the lead-time claim isn't a marketing number, it's a query.

## 2. Hours of manual cross-system review this replaces

A thorough manual check of one account — reading recent tickets, scanning the email thread, checking the shared Slack channel, pulling a usage report, reviewing the latest CSAT response — realistically takes a diligent CS lead **45–60 minutes**, done properly, for a *single* account. Nobody does this routinely across a full book, because it isn't a routine task — it's the thing that only happens reactively, after something has already visibly broken.

That's the actual cost being replaced: not "the system is faster than a human," but **"the system does, continuously and for free, the cross-system check that a human would only ever do after the damage is already visible."** For a CS lead managing 25 accounts, that's a standing ~20 hours/month of deep-dive capability that doesn't currently get spent at all, made available for zero incremental effort per account.

## 3. No single source saw more than a third of the story

Of the 9 validated findings in the worked scenario, no single source contributed more than 3:

| Source | Findings it alone contributed | Share of the total story |
|---|---|---|
| Tickets (Zendesk) | 3 (broken promise, recurrence, positive milestone) | 33% |
| Chat (Slack) | 2 (absence, relationship change) | 22% |
| Email (Gmail) | 2 (tone, intent) | 22% |
| Survey (CSAT) | 1 (satisfaction drop) | 11% |
| Product usage (warehouse) | 1 (usage deviation) | 11% |

More importantly: **zero of the five sources, on their own, touched both of the two real issues** (the tracking-API reliability problem and the Ana/Diego relationship cooling). Each source-owner, looking only at their own system, would see a fragment of one issue at most — never the two-issue picture the dashboard shows in one screen. That's the concrete, countable version of spec §2.1's claim: *"each of these is individually survivable and individually forgettable."*

## Where these numbers come from

Every figure above is derived from `examples/01-end-to-end-walkthrough.md`, not invented for this document — the same scenario the live demo (`demo/01-live-demo-runbook.md`) runs. That's deliberate: the impact story and the demo should never be able to contradict each other, because they're the same data looked at two ways.

## Traceability

`examples/01-end-to-end-walkthrough.md`, `base/Churn-Sentiment-Agent-Product-Specification.md` §2 (The problem), §14.2 (Product success targets), `data-base/03-schema-ledger.md` (bitemporal replay), `demo/01-live-demo-runbook.md`.
