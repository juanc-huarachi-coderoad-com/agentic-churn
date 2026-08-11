# 02 · Component catalog

Detailed responsibility, interface, and technology mapping for every component in the architecture diagram (`01-architecture-overview.md`). Each entry mirrors the discipline of spec §9.2: **owns / must never**.

---

## Tier 1 · Ingestion

### Signal collectors (M1)

| | |
|---|---|
| **Owns** | Fetching, normalizing, and resolving identity for one source system each |
| **Must never** | Judge importance, filter by perceived relevance, write to the source |
| **Technology class** | Deterministic code |
| **Tech** | Per-source SDK/REST client (Zendesk, Jira, Intercom, Gmail API, Microsoft Graph, Slack Web API, Microsoft Teams API, Salesforce REST API, warehouse read connector) behind one shared `Collector` interface (`fetch`, `normalize`, `resolve_identity`, `emit_envelope`) |
| **Interface in** | Source webhook payload or poll response; current client-profile stakeholder list for identity resolution |
| **Interface out** | `Envelope` objects → Event ledger |
| **Key algorithm** | Idempotency key = hash(source, native_record_id); identity match = deterministic address/user-ID lookup, falling back to fuzzy match (e.g. `rapidfuzz`) only to *suggest*, never to auto-resolve below a confidence floor |

### Absence collector (M1a)

| | |
|---|---|
| **Owns** | Detecting non-occurrence of an expected contact |
| **Must never** | Decide that silence is bad — it only reports the absence as a fact |
| **Technology class** | Deterministic code, scheduled |
| **Tech** | Cron-scheduled job comparing expected-contact definitions (from client profile commitments/cadences) against the ledger's latest matching event |
| **Interface in** | Client profile commitments/cadences; ledger latest-contact projection |
| **Interface out** | `absence` event type → Event ledger |

### Event ledger (M2)

| | |
|---|---|
| **Owns** | The single source of truth; append-only, bitemporal, replayable |
| **Must never** | Store an opinion, mutate a row, delete a row (except crypto-shredding) |
| **Technology class** | Relational database |
| **Tech** | PostgreSQL; `events` table is `INSERT`-only (enforced by a `REVOKE UPDATE, DELETE` grant and/or a trigger); materialized/derived projections (`event_threads`, `response_pairs`, `rollups`) rebuilt by a replay job |
| **Interface in** | Envelopes from M1 |
| **Interface out** | Event/projection reads for M5 (interpreters), M8/M9 (evidence lookups) |
| **Key algorithm** | Business-hours response-pair calculation against the profile's working calendar and timezone; hash chaining (`event.hash = H(event.payload + prev_event.hash)`) |

---

## Tier 2 · Context

### Client profile (M3)

| | |
|---|---|
| **Owns** | Severity multipliers (`influence`, `criticality`), communication norms, commitments |
| **Must never** | Contain scoring logic (formulas, thresholds) |
| **Technology class** | Structured config, human-authored |
| **Tech** | YAML source of truth (spec §6.2 format) parsed into versioned relational rows; a profile editor UI writes new versions, never overwrites |
| **Interface in** | CS-lead edits via profile editor UI |
| **Interface out** | Multiplier/context reads for M1 (identity targets), M5 (interpretation context), M6 (scoring multipliers) |

### Feedback memory (M4)

| | |
|---|---|
| **Owns** | Damping weights derived from human verdicts |
| **Must never** | Retrain or fine-tune a model |
| **Technology class** | Deterministic code + relational storage |
| **Tech** | Pattern-matching rule (finding type + event-signature class) mapping verdict history → a stored numeric weight ≤ 1.0; no ML training pipeline involved |
| **Interface in** | Verdict clicks from M8/M9/M10 |
| **Interface out** | Damping weight lookups for M6 |

---

## Tier 3 · Reasoning

### Interpreters / readers (M5)

| Reader | Technology class | Tech |
|---|---|---|
| Commitment | Deterministic code | Business-hours arithmetic against M2 response pairs and M3 commitments |
| Usage | Statistics | Time-series anomaly detection (e.g. rolling z-score / STL decomposition via `statsmodels`) against each metric's own historical distribution |
| Recurrence | Embeddings + clustering | Text embeddings (OpenAI `text-embedding-3-small`, see `architecture/03-technology-stack.md`) + density clustering (HDBSCAN) to group same-issue tickets/messages — **not** a generative LLM decision |
| Absence | Statistics | Expectation-window comparison (cadence/commitment vs. latest observed contact) |
| Relationship | Graph diff | Set-diff of active participants over a rolling window vs. profile stakeholder roster |
| **Tone** | **LLM** | Structured-output classification (deviation from a frozen per-stakeholder baseline), Anthropic Claude with a closed JSON schema |
| **Intent** | **LLM** | Structured-output classification against a closed enum (`escalation`, `competitive_mention`, `contractual_reference`, `none`) |
| **Meeting** | **LLM** | Structured extraction of verbal commitments from consented transcripts, closed schema (`who`, `what`, `by_when`, `source_segment`) |

| | |
|---|---|
| **Owns** | Structured findings, each citing event IDs |
| **Must never** | Rank findings, call external tools, treat client text as instructions |
| **Interface in** | Event/projection reads from M2; context from M3 |
| **Interface out** | `finding` records → M5a |

### Validation gate (M5a)

| | |
|---|---|
| **Owns** | Rejecting unproven claims before they can reach the score |
| **Must never** | Repair or auto-correct a failing finding |
| **Technology class** | Deterministic code |
| **Tech** | Four sequential checks: JSON-schema validation → cited-event existence query against M2 → evidence-count floor per finding type → confidence-floor comparison |
| **Interface in** | Findings from M5 |
| **Interface out** | Validated findings → M6; quarantined findings → `quarantine` table (System health screen only) |

### Scoring engine (M6)

| | |
|---|---|
| **Owns** | The number — deliberately unintelligent |
| **Must never** | Call a model, use the previous score as an input |
| **Technology class** | Deterministic arithmetic |
| **Tech** | Plain application code (no ML/LLM dependency reachable from this module — enforced by module/dependency boundaries in the codebase and a CI check) |
| **Interface in** | Validated findings (M5a), multipliers (M3), damping (M4) |
| **Interface out** | `score_runs`, `score_contributions`, `band_history` → M7, M8, M9 |

### Narrator (M7)

| | |
|---|---|
| **Owns** | Turning the calculated breakdown into readable sentences |
| **Must never** | Add a fact not present in its input |
| **Technology class** | LLM, structured output → mechanically fact-checked prose |
| **Tech** | Anthropic Claude (Sonnet-class) with structured input (ranked findings/issues JSON) → structured output (headline/reasons/actions JSON) → deterministic post-generation fact-check pass comparing every number/name against the input before display |

---

## Tier 4 · Experience

### Health dashboard (M8)

| | |
|---|---|
| **Owns** | Display of precomputed state |
| **Must never** | Calculate anything |
| **Technology class** | Read-only UI |
| **Tech** | React/TypeScript SPA reading from a thin read API backed directly by `score_runs`/`narrator_outputs`/`rollups` tables — no aggregation in the request path |

### Ask agent (M9)

| | |
|---|---|
| **Owns** | Lookup and rendering |
| **Must never** | Recalculate the score |
| **Technology class** | LLM (intent classification + lookup orchestration), structured output |
| **Tech** | Anthropic Claude with tool-use restricted to **read-only lookup tools** (query ledger, query findings, query score_runs) against a closed intent menu; component selection is a closed enum, never free-form UI generation |

### Draft composer (M10)

| | |
|---|---|
| **Owns** | Client-facing text |
| **Must never** | Send anything |
| **Technology class** | LLM, structured output, mechanically checked |
| **Tech** | Anthropic Claude generating draft content from evidence + profile communication norms; deterministic post-generation checks (fact membership, no-invented-dates, no-internal-leak, no-other-client-mention) block display on failure. **No send-capable dependency (SMTP client, chat-post API credential) is present in this component's runtime at all** — the absence is architectural, not a permissions check |

---

## Where AI is and is not used (spec §12.4)

| Function | AI? |
|---|---|
| Collecting, storing, timing, counting | No |
| Commitment, usage, absence, relationship readers | No |
| Recurrence clustering | Embeddings only, no generative call |
| Tone, intent, meeting readers | **Yes — structured-output LLM** |
| Validation gate, scoring engine | No |
| Narrator, ask agent, draft composer | **Yes — structured-output LLM, mechanically checked** |

> The AI reads language and writes language. It never counts, never scores, and never sends.
