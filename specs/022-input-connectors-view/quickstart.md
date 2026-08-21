# Quickstart: Input Connectors View

Validates the feature end-to-end once implemented, per `spec.md`'s acceptance scenarios.
See `data-model.md` for the `Connector`/`ConnectorGroup` shapes and `research.md` for the
icon-sourcing and static-data decisions this relies on.

## Prerequisites

- Node deps installed: `cd frontend && npm install` (if not already).
- No backend or database setup required — this feature is frontend-only (plan.md
  Technical Context).

## Run the app and view the page

```bash
cd frontend
npm run dev
```

1. Log in (existing auth flow) and confirm the sidebar shows a new destination (plug icon)
   alongside Dashboard / Coverage / Profile.
2. Click it, or navigate directly to the new route, and confirm the page renders three
   grouped sections — Live (1), Simulated (6), Planned (7) — matching
   `base/mockupInputConectors.jpg`, and that all three group headings/counts are visible
   without scrolling (SC-001).
3. Confirm the Live section shows "Transcripts" with "Meeting audio" and the pipeline
   services (local storage, OpenAI Whisper, pyannote.ai, Anthropic).
4. Confirm the Simulated section lists exactly: Gmail, Zendesk, Warehouse, Slack, CSAT,
   Calendar — each with a recognizable icon and short description.
5. Confirm the Planned section lists exactly: Jira, Intercom, Microsoft 365, Teams, NPS,
   Salesforce, Contracts — each labeled as a roadmap item.
6. Confirm an "Add Connector" action is visible near the top of the page.
7. Confirm every status badge shows a text label (not color alone) — check with a
   grayscale/color-vision simulation if available.

## Automated checks

```bash
cd frontend
npm run typecheck   # strict TS, no `any` (constitution P11)
npm run lint
npm test -- input-connectors   # unit + component tests for the new feature directory
```

Expected: `connectors-data.test.ts` asserts every group's rendered count equals its
`connectors.length` (data-model.md's derived-count rule) and that the catalog matches the
fixed table in `data-model.md` (1 live / 6 simulated / 7 planned, no duplicates, `pipeline`
present only on the live entry).

## Regression check (FR-009)

```bash
cd backend && python -m pytest   # or the project's existing backend test command
cd frontend && npm test           # full suite, not just the new directory
```

Expected: 100% of pre-existing tests still pass unmodified — this feature must not change
any ingestion, scoring, or other existing pipeline behavior (SC-004).
