# 03 · Sequence — Feedback loop (the Learning loop)

Spec §9.3, M4. Traces `REQ-M4-*`. Human-driven; changes future weight, never past scores.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as CS lead
    participant Card as Any card (dashboard / evidence panel / ask answer)
    participant FM as M4 · Feedback memory
    participant Damp as damping_weights table
    participant Scorer as M6 · Scoring engine (next run)

    User->>Card: Clicks verdict: correct / false_alarm / resolved (REQ-M4-01)
    Card->>FM: Submit verdict + finding type + event-signature class
    FM->>FM: Match against existing pattern history (REQ-M4-02)
    FM->>Damp: Upsert damping weight (at most 1.0) for this pattern (REQ-M4-03)

    Note over FM,Damp: No retraining, no fine-tuning — a stored number (REQ-M4-05)

    par Next sense-loop run (any trigger)
        Scorer->>Damp: Read damping weight for matching findings
        Damp-->>Scorer: damping term
        Scorer->>Scorer: points = base x influence x criticality x confidence x magnitude x recency x damping
    end

    Scorer-->>Card: Next display shows: "weight reduced — your team dismissed this pattern twice" (REQ-M4-04)
```

## Key invariant

Feedback never edits a past `score_run` (spec §8.7: the previous score is never an input to the calculation). It only changes the `damping` term used by **future** scoring runs — so history remains an honest record of what was believed at the time.
