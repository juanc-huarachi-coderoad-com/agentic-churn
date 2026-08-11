# 02 · Sequence — Ask agent (the Ask loop)

Spec §9.3, §12.2. Traces `REQ-M9-*`. Never recomputes the score — explains the one that already exists.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as CS lead
    participant Ask as M9 · Ask agent (LLM)
    participant Ledger as M2 · Event ledger (read-only tool)
    participant Score as M6 output · score_runs (read-only tool)
    participant UI as M8 · Dashboard UI

    User->>Ask: "Why did the score go up?"
    Ask->>Ask: Classify intent (closed enum) (REQ-M9-01)

    alt Intent matched: score delta
        Ask->>Score: Read-only lookup: latest 2 score_runs + contributions
        Score-->>Ask: Per-cause point deltas + evidence_ids
        Ask->>UI: Render "Delta breakdown" component (REQ-M9-02)
    else Intent matched: "is this normal for Ana?"
        Ask->>Ledger: Read-only lookup: Ana's baseline vs current window
        Ledger-->>Ask: Baseline + current samples
        Ask->>UI: Render "Baseline vs current" component
    else Intent = prediction ("will they cancel?")
        Ask->>UI: Decline: "I describe today, I don't forecast." (REQ-M9-05)
    else Intent = colleague judgment
        Ask->>UI: Decline: character/performance judgments not given (REQ-M9-06)
    else No intent match
        Ask->>UI: Fallback plain text, clearly marked, with sources attached (REQ-M9-04)
    end

    UI-->>User: Rendered component or decline message (under 3s, REQ-M9-08)
```

## Key invariant

At no point in this flow does the Ask agent call the Scoring engine (M6) to produce a new number — every branch either reads already-persisted `score_runs`/`findings`/`events` or declines. This is enforced by granting the Ask agent's LLM tool-use **only read-only lookup tools** (see `architecture/04-ai-safety-and-model-usage.md`).
