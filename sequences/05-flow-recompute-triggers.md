# 05 · Flow — recompute triggers

Spec §8.9. Traces `REQ-M6-20 … REQ-M6-26`. Five distinct triggers, one shared recompute path, plus the four quiet-period behaviors that fall out of the same rules.

## Trigger flow

```mermaid
flowchart TD
    T1["New single event arrives"] --> B{"Burst?\n(events within 30s window)"}
    B -->|No| R1["Recompute end-to-end\n~40s (REQ-M6-21)"]
    B -->|Yes| Batch["Batch into 30s window,\none recompute (REQ-M6-22)"]

    T2["Urgent phrase detected\n(Intent reader closed enum)"] --> Fast["Immediate recompute,\nskip batch window (REQ-M6-23)"]

    T3["Hourly heartbeat"] --> R2["Recompute\n(time itself changes recency/ageing) (REQ-M6-24)"]

    T4["Profile or weight config edited"] --> Full["Full replay\nfrom event log (REQ-M6-25, REQ-M2-07)"]

    Batch --> Engine[["M6 · Scoring engine\nrecompute from zero (REQ-M6-20)"]]
    R1 --> Engine
    Fast --> Engine
    R2 --> Engine
    Full --> Engine

    Engine --> Narr["M7 · Narrator"]
    Narr --> Dash["M8 · Dashboard updates"]

    Source{"Required source\ndegraded/disconnected?"}
    Engine -.-> Source
    Source -->|Yes| Freeze["Freeze score at last value,\nshow staleness banner (REQ-M6-26)"]
    Source -->|No| Dash
```

## Quiet-period behavior matrix (spec §8.9)

| Situation | Score behaviour | Driven by |
|---|---|---|
| Quiet, nothing pending | Drifts slowly down as fixed issues fade | REQ-M6-09 (resolved-state half-life) |
| Quiet, we owe a reply | Climbs daily — the promise ages | REQ-M6-11 (open-and-overdue ageing multiplier) |
| Quiet, client has gone silent | Jumps when the absence threshold is crossed | REQ-M1-06 (absence collector) → REQ-M5-10 (Absence reader) |
| Quiet because a source is broken | Frozen, with a visible warning banner | REQ-M6-26, REQ-NFR-07 |
