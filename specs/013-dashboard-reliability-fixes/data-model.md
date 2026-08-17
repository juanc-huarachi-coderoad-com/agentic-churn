# Phase 1 Data Model: Dashboard Reliability Fixes

This feature introduces **no new entities, fields, or data structures**. It changes which already-existing field two frontend components use as a React rendering key, and adjusts two test locators/assertions. There is nothing to model beyond what's already documented in feature 012's `data-model.md` and the existing `Cause` interface.

## The one relevant existing shape (unchanged)

```ts
// frontend/src/ask/components/answer-renderer.tsx — unchanged by this feature
interface Cause {
  finding_type: string          // a category — can repeat across rows
  points: number
  is_positive: boolean
  score_contribution_id: string // unique per underlying finding — now used as the render key
}
```

## What changes

- **Nothing in the type**. `Cause` already declares `score_contribution_id`; this feature only changes which field two `.map()` calls pass to `key={...}`.
- **No state transitions, no validation rules, no new relationships.**
