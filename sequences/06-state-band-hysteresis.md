# 06 · State diagram — band hysteresis

Spec §8.6. Traces `REQ-M6-17 … REQ-M6-19`. The gap between the 65-enter and 55-exit thresholds is deliberate hysteresis so the label doesn't flip when the score wobbles; a band change also requires the score to hold across two consecutive runs.

## Diagram

```mermaid
stateDiagram-v2
    [*] --> Healthy

    Healthy --> Watch: score >= 35\n(held 2 consecutive runs)
    Watch --> Healthy: score < 35\n(held 2 consecutive runs)

    Watch --> AtRisk: score >= 65\n(held 2 consecutive runs)
    AtRisk --> Watch: score < 55\n(held 2 consecutive runs)

    Healthy --> Healthy: score stays < 35
    Watch --> Watch: 35 <= score < 65,\nor single-run dip < 35 not yet confirmed
    AtRisk --> AtRisk: score stays >= 55\n(even if it fell from a higher peak)

    note right of AtRisk
        Escalation into At risk can be fast.
        De-escalation out of At risk is
        deliberately slow: score must fall
        below 55, not just below 65.
    end note

    note left of Watch
        The 55-65 gap means a score
        oscillating between 60 and 68
        stays labeled "At risk" the whole time —
        it never flickers back to Watch.
    end note
```

## Worked example (spec §10)

| Run | Score | Raw threshold check | Displayed band |
|---|---|---|---|
| Week 0 | 78 | ≥ 65 | At risk (entered) |
| Week 1 | 61 | ≥ 55, so stays (< 65 alone would not exit) | **At risk** (unchanged — 61 > 55 exit floor) |

The score fell by 17 points, but the band correctly stays "At risk" because 61 is still above the 55 exit threshold — preventing a premature "everything's fine" signal while Diego (unresolved, unfaded) remains the top concern.
