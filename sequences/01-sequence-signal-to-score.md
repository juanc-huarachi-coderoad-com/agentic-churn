# 01 · Sequence — signal to score (the Sense loop)

Spec §10, end-to-end walkthrough: one email, from arrival to screen. Traces `REQ-M1-*` → `REQ-M2-*` → `REQ-M5-*` → `REQ-M5A-*` → `REQ-M6-*` → `REQ-M7-*` → `REQ-M8-*`.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Ana as Ana (CTO, client)
    participant Collector as M1 · Email collector
    participant Ledger as M2 · Event ledger
    participant Readers as M5 · Interpreters
    participant Gate as M5a · Validation gate
    participant Scorer as M6 · Scoring engine
    participant Narrator as M7 · Narrator
    participant Dash as M8 · Dashboard

    Ana->>Collector: Sends email: "Please advise on the timeline.\nI need to brief the board on Thursday."
    Collector->>Collector: Resolve Ana -> stk_ana (REQ-M1-04)
    Collector->>Ledger: Emit envelope (REQ-M1-10)
    Ledger->>Ledger: Append event, open response clock (REQ-M2-01, REQ-M2-05)
    Ledger->>Ledger: Update rollup — 14 words vs 47-word baseline, no greeting

    Ledger-->>Readers: Queue only the affected windows for re-reading

    par Tone reader (LLM)
        Readers->>Readers: Deteriorating, magnitude 0.6, confidence 0.8, 5 events cited (REQ-M5-06)
    and Intent reader (LLM)
        Readers->>Readers: Escalation language: board briefing, stated deadline (REQ-M5-13)
    end

    Readers->>Gate: Submit findings (REQ-M5-05)
    Gate->>Gate: Check schema, cited events, evidence floor, confidence floor (REQ-M5A-01)
    Note over Gate: A third finding citing a non-existent event is quarantined (REQ-M5A-02)
    Gate-->>Scorer: 2 findings pass

    Scorer->>Scorer: Recalculate from zero across all live findings (REQ-M6-20)
    Note over Scorer: Issue A (tracking tool) 39.0 + Issue B (people) 14.4 - positive 4.0 = 49.4 pts -> score 78

    Scorer->>Narrator: Ranked findings + point contributions
    Narrator->>Narrator: Write headline, reasons, plan (REQ-M7-02, mechanically fact-checked REQ-M7-06)

    Narrator->>Dash: Store narrator_output + score_run
    Dash-->>Dash: Next dashboard read shows 78 - At risk - up 12, five clickable reasons (REQ-M8-01)
```

## Timing budget (spec §10, §8.9)

| Step | Elapsed | NFR reference |
|---|---|---|
| Email arrives → envelope emitted | ~1s | — |
| Envelope → ledger append | ~1s | — |
| Ledger → readers dispatch | ~1s | Only affected windows queued |
| Readers → findings ready | ~34s | Two LLM calls (Tone, Intent) in parallel |
| Validation gate | < 1s | Deterministic checks |
| Scoring engine | < 1s | Deterministic arithmetic |
| Narrator | ~1s | Structured generation + fact-check |
| **Total** | **~38s** | Within REQ-NFR-02 (< 60s target ~40s) |
