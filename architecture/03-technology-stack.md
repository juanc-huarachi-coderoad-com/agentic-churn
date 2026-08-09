# 03 · Technology stack proposal

A concrete, opinionated recommendation. Each choice states its rationale and, where useful, a lighter-weight alternative for a hackathon/demo build. Nothing here is required by the spec except the constraints called out explicitly (relational DB, no model calls in scoring, no send capability).

## Summary table

| Layer | Recommendation | Why | Lightweight alternative |
|---|---|---|---|
| Backend language/framework | Python 3.12 + FastAPI | First-class Anthropic SDK, numpy/pandas/statsmodels for the statistical readers, async support for webhook ingestion | Same — no reason to swap for a hackathon scope |
| LLM provider | Anthropic Claude — **Sonnet** for Narrator / Ask agent / Draft composer (higher-stakes generation), **Haiku** for Tone / Intent / Meeting classification (high-volume, low-latency, structured output) | Matches spec's "structured output everywhere," strong tool-use and JSON-schema adherence; Haiku keeps per-message interpretation cost low at ~40s latency budget | Single model tier (Sonnet everywhere) if volume is low during a demo |
| Embeddings (Recurrence reader only) | Voyage AI embeddings (Anthropic's recommended embedding partner) | Purpose-built for retrieval/clustering quality; keeps the whole AI stack on one vendor for auth/billing simplicity | Open-source `sentence-transformers` (e.g. `all-MiniLM-L6-v2`) run locally — zero external cost for a demo |
| Database | PostgreSQL 16 | Spec explicitly states "a relational database is sufficient" at 50k–200k events/year; JSONB for envelope/finding payloads; native row-level security for per-deployment isolation; `pgcrypto` for column-level encryption | SQLite for a single-deployment local demo only — not recommended beyond that |
| Background/scheduled processing | APScheduler (in-process) for the hourly heartbeat + Postgres `LISTEN/NOTIFY` for event-triggered recompute, or a minimal worker (RQ) if horizontal scaling is needed later | Matches "event-sourced in shape, not in tooling" — no message broker required at this scale | Cron + a single worker process is enough for a hackathon demo |
| Frontend | React 18 + TypeScript, Vite | Component-driven UI matches M8's "everything precomputed, just render" model; TypeScript keeps the Ask agent's closed component-menu contract type-safe end to end | Same |
| UI styling | Tailwind CSS + a restrained component set (Radix primitives) | "Clinical calm" design direction (spec §11.1) — near-white canvas, hairline borders, no gauges/speedometers — is easier to keep disciplined with utility CSS than a heavy component-library aesthetic | — |
| Charts | Lightweight SVG-based (visx or Recharts), sparkline + trend line only | Spec explicitly forbids ticket-volume charts, pie charts, sentiment-average lines (§11.7) — the chart surface area is intentionally small | — |
| Source connectors | Official SDKs/REST: Zendesk API, Jira REST API, Intercom API, Gmail API / Microsoft Graph, Slack Web API, Microsoft Teams API, Salesforce REST API | Read-only scopes available on all; well-documented webhook support for the hybrid sync model | — |
| Identity/fuzzy matching | `rapidfuzz` (Python) | Fast, dependency-light fuzzy string matching for suggesting (never auto-resolving) identity matches | — |
| Encryption | Cloud KMS (AWS KMS / GCP Cloud KMS) for envelope encryption of message bodies; per-deployment key set | Enables crypto-shredding (destroy key → body unrecoverable, event skeleton survives) as specified in §6.4 | Local encryption key file for a demo, explicitly flagged as non-production |
| Hosting | Containerized (Docker) per deployment; one container group per client, deployed on ECS Fargate / Cloud Run / Fly.io | Matches "one deployment, one client, one key set, no shared storage" (§6.4 Isolation) | Single Docker Compose stack for a local/demo run |
| Observability | Structured JSON logging + OpenTelemetry traces (request → collector → ledger → score) | Needed to debug the ~40s event-to-score pipeline and prove the < 60s NFR | Plain logging for a demo |
| Testing | pytest + a golden-replay test harness (drop projections, replay, diff against a stored golden dashboard state) | Directly encodes the spec §14.3 replay/determinism acceptance criteria | — |
| CI | GitHub Actions: lint, type-check, unit tests, golden-replay test, a static check that `M6` has no reachable import of the LLM client | The "no model call in scoring" boundary (P2) is enforced mechanically, not just by convention | — |

## Why not an event-streaming platform (Kafka, etc.)?

The spec is explicit (§9.4): the architecture is event-sourced *in shape* — append-only, bitemporal, replayable — but not in tooling. At 50k–200k events/year (roughly 1 event every few minutes on average, with bursts), a Postgres table with a 30-second batching window for recompute comfortably meets the < 60s latency target without the operational cost of a broker, schema registry, or consumer-group management. Revisit only if a future multi-client platform (explicitly out of scope for v1, §3.2) is built.

## Why Anthropic Claude specifically for the LLM layer

- **Structured output / tool use** is a first-class requirement (spec §12.5: "structured output everywhere") — Claude's tool-use and JSON-schema-constrained output support this directly.
- **Prompt injection containment** (spec §12.5, §15): interpreters must have no tools and no side effects; Claude's tool-use model makes it straightforward to grant *zero* tools to the readers (M5) while giving the Ask agent (M9) only read-only lookup tools.
- **Long context + citation discipline**: the Tone/Meeting readers need to compare current text against a stakeholder's historical baseline — long context windows keep this a single call rather than a multi-step retrieval pipeline for a single-client deployment's data volume.

## Per-deployment isolation model

Each client deployment gets:
1. A dedicated Postgres schema (or database) — no cross-tenant tables, ever.
2. A dedicated KMS key set for envelope encryption.
3. A dedicated set of OAuth app registrations/API credentials for its connected sources.
4. Its own container/task group, independently deployable and independently destroyable (supports crypto-shredding at the deployment level, not just the row level).

This directly implements spec §6.4's Isolation requirement and REQ-NFR-15/REQ-NFR-21.
