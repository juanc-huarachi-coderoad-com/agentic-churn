# Phase 1 Data Model: Input Connectors View

This feature has no database schema, migration, or API payload — it is a static, local
TypeScript data module (research.md Decision 2). This document specifies that module's
shape, which is the closest thing this feature has to a "data model."

## `ConnectorStatus`

A closed enum of the three status groups. Fixed by spec — not user-extensible (constitution
P10: don't build a dynamic/plugin registry for a fixed, spec-defined set).

```ts
type ConnectorStatus = 'live' | 'simulated' | 'planned'
```

| Value       | Group label (UI) | Spec source                          |
|-------------|-------------------|---------------------------------------|
| `live`      | Live               | FR-003                                |
| `simulated` | Simulated          | FR-004                                |
| `planned`   | Planned (roadmap)  | FR-005                                |

## `Connector`

One entry in the catalog.

```ts
interface Connector {
  id: string                // stable slug, e.g. "gmail", "transcripts"
  name: string               // display name, e.g. "Gmail", "Microsoft 365"
  status: ConnectorStatus
  description: string        // one-line subtitle (FR-006), e.g. "Meeting audio"
  pipeline?: string[]        // Live-only: underlying services (FR-003), e.g.
                              // ["local storage", "OpenAI Whisper", "pyannote.ai", "Anthropic"]
  icon:
    | { kind: 'brand'; asset: string; alt: string } // file under /icons/connectors/, own
                                                      // color already baked into the file
    | { kind: 'lucide'; icon: LucideIcon; tintClassName?: string } // generic icon, optionally
                                                      // tinted with a brand color via a
                                                      // Tailwind arbitrary-value class
}
```

Only four connectors (Gmail, Zendesk, Jira, Intercom) ended up as `kind: 'brand'` — the
other four originally-planned brand marks (Slack, Microsoft 365, Teams, Salesforce) are
`kind: 'lucide'` with a brand-colored `tintClassName` instead, per research.md Decision 1's
implementation-time addendum.

**Validation rules** (enforced by a data-level unit test, `connectors-data.test.ts`, since
there is no database `CHECK` to lean on):

- `pipeline` MUST be present only when `status === 'live'` (only Transcripts has one today,
  per FR-003).
- Every `Connector.status` MUST correspond to exactly one of the three `ConnectorGroup`s
  below — no connector is unlisted or double-listed.
- `id` MUST be unique across the full catalog.
- Every `icon` of kind `brand` MUST reference an `asset` filename that actually exists
  under `frontend/public/icons/connectors/` — a typo or rename on either side must fail
  the test, not fail silently at render time.

## `ConnectorGroup`

The rendered grouping, derived — never hand-typed — from the flat `Connector` list
(research.md Decision 3), so the header count can never drift from the list beneath it.

```ts
interface ConnectorGroup {
  status: ConnectorStatus
  label: string              // "Live" | "Simulated" | "Planned (roadmap)"
  connectors: Connector[]    // filtered from the full catalog by status
}

// count shown in the UI is always `connectors.length` — never a separate field
```

## Fixed catalog (spec FR-003–FR-005)

| Status      | Connectors                                                                 | Count |
|-------------|------------------------------------------------------------------------------|-------|
| `live`      | Transcripts                                                                    | 1     |
| `simulated` | Gmail, Zendesk, Warehouse, Slack, CSAT, Calendar                              | 6     |
| `planned`   | Jira, Intercom, Microsoft 365, Teams, NPS, Salesforce, Contracts              | 7     |

## State transitions

None. This is a static, read-only catalog (spec FR-009); connectors do not change status
as a result of any user action on this page. Product/engineering updates the underlying
`connectors-data.ts` module directly when a connector's real-world status changes (e.g.
a "Planned" connector later ships and becomes "Simulated" or "Live") — this is a code
change, not a runtime data mutation.
