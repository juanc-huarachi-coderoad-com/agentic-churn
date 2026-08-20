# 03 · Technology stack — decision and comparison

| | |
|---|---|
| **Status** | **Adopted stack:** Python/FastAPI, Anthropic Claude, OpenAI embeddings, PostgreSQL, React, Docker Compose |
| **Updated** | 2026-08-17 — Charts narrowed to Recharts only (was "visx or Recharts", already resolved in `decisions/02-repo-and-tooling.md`) and an Icons row added (`lucide-react`), per constitution v1.3.0 |
| **Scope** | Phase 1 (`decisions/01-mvp-scope-and-phasing.md`) — everything here is sized for one-to-a-few single-client deployments, not a multi-tenant fleet |

## Comparison — first proposal vs. the requested stack

The team asked for a specific, simpler stack: **Python/FastAPI, Claude, OpenAI embeddings, Postgres, React, Docker Compose.** Here's how that lines up against the original proposal in this document, layer by layer, and which one wins for Phase 1.

| Layer | Originally proposed | Requested stack | Decision | Why |
|---|---|---|---|---|
| Backend | Python 3.12 + FastAPI | Python/FastAPI | **Same — no change** | Already the right fit; nothing to compare |
| LLM | Anthropic Claude (Sonnet + Haiku split) | Claude | **Same — no change** | Already the right fit |
| Embeddings | Voyage AI (Anthropic's recommended partner) | OpenAI embeddings | **Switched to OpenAI** | See "Embeddings" below |
| Database | PostgreSQL 16 | Postgres | **Same — no change** | Already the right fit |
| Frontend | React + TypeScript | React | **Same — no change** | Already the right fit |
| Hosting | Docker containers on ECS Fargate / Cloud Run / Fly.io, one per client | Docker Compose | **Switched to Docker Compose** | See "Hosting" below |

Four of six layers already matched. The two real deltas — embeddings and hosting — are both changes in the direction of **less infrastructure, not less capability**, which is exactly what "remove the difficulty" (the team's own framing) should mean at this stage. Both are adopted below.

### Embeddings: why OpenAI over Voyage AI

| | Voyage AI (original) | OpenAI (adopted) |
|---|---|---|
| Used for | Recurrence reader only — clustering same-issue tickets/messages | Same, unchanged scope |
| Quality | Slightly better on retrieval-heavy benchmarks | Very good, more than sufficient for clustering a single client's ticket volume (dozens to low hundreds of tickets/year, not millions) |
| Operational cost | A second AI vendor to authenticate, bill, and monitor, on top of Claude | One fewer vendor relationship — if the team is already comfortable with OpenAI's API, that's a real simplicity win, not just a preference |
| Verdict | — | **Adopted.** The quality gap doesn't matter at this data volume, and one fewer vendor is a genuine reduction in operational surface area, which is the actual goal here. |

Nothing else changes: the Recurrence reader still does clustering only (HDBSCAN or similar over the embedding vectors), never a generative call — that boundary (`architecture/02-component-catalog.md`) is about *how* embeddings are used, not which provider generates them.

### Hosting: why Docker Compose over a cloud orchestrator

| | ECS/Cloud Run/Fly.io (original) | Docker Compose (adopted) |
|---|---|---|
| Fits "one deployment = one client"? | Yes, via one container group per client | Yes, even more directly — **one Compose stack per client**, full stop |
| Setup effort | Cloud account, IAM roles, task definitions, load balancer config, per provider | A `docker-compose.yml` and a `.env` file per deployment |
| Auto-scaling / managed failover | Yes | No — a Compose stack is one host, not a cluster |
| Right for Phase 1? | Overbuilt for 1–3 single-client demo deployments | **Yes — this is exactly what Docker Compose is for** |
| Verdict | — | **Adopted for Phase 1.** Revisit only if/when the product needs to run many client deployments simultaneously with independent scaling — a Phase-2-or-later concern the spec explicitly keeps out of v1 scope (§3.2: no multi-client portfolio). |

A Compose stack per deployment still gives every isolation guarantee the spec requires (§6.4) — it's just simpler infrastructure underneath the same guarantee, not a weaker one:

```yaml
# docker-compose.yml — one stack per client deployment
services:
  api:
    build: ./backend        # FastAPI: collectors, ledger, readers, scoring, narrator, ask agent, draft composer
    env_file: .env          # this deployment's source credentials + encryption key — never shared across stacks
    depends_on: [db]
  worker:
    build: ./backend
    command: python -m app.worker   # hourly heartbeat + event-triggered recompute (see sequences/05)
    env_file: .env
    depends_on: [db]
  db:
    image: postgres:16
    volumes: ["./data:/var/lib/postgresql/data"]   # this deployment's data only, on its own volume
    env_file: .env
  web:
    build: ./frontend       # React dashboard
    depends_on: [api]
```

One deployment, one `.env`, one Postgres volume, one set of containers — nothing here is shared with any other client's stack, which is the actual requirement (`requirements/11-non-functional-requirements.md` REQ-NFR-15/21), not the specific orchestrator.

---

## Full adopted stack

| Layer | Choice | Why |
|---|---|---|
| Backend language/framework | **Python 3.12 + FastAPI** | First-class Anthropic SDK support; numpy/pandas/statsmodels cover the statistical readers (Usage, Absence) directly; async support fits webhook ingestion |
| LLM provider | **Anthropic Claude** — Sonnet-class for Narrator / Ask agent / Draft composer, Haiku-class for Tone / Intent / Meeting classification | Matches "structured output everywhere" (spec §12.5); Haiku keeps high-volume per-message interpretation fast and cheap within the ~40s scoring budget |
| Agent orchestration (Ask agent only) | **LangGraph** | The one of six LLM touchpoints that genuinely branches and calls tools rather than making a single structured-output call — full evaluation in `decisions/03-langgraph-for-ask-agent.md`. Tone/Intent/Meeting readers, Narrator, and Draft composer stay on the plain `LLMPort` call shape, unchanged — no orchestration library involved there by design |
| Embeddings (Recurrence reader only) | **OpenAI embeddings** (`text-embedding-3-small`) | Adopted per team request — see comparison above. Fine-tuned quality upgrade to `text-embedding-3-large` is a config change, not an architecture change, if clustering quality ever needs it |
| Database | **PostgreSQL 16** | Spec explicitly states a relational database is sufficient (§9.4) at 50k–200k events/year; JSONB for envelope/finding payloads; `pgcrypto` for column-level encryption |
| Background/scheduled processing | **APScheduler** (in-process, inside the `worker` container) for the hourly heartbeat, plus Postgres `LISTEN/NOTIFY` for event-triggered recompute | No message broker needed at this scale (spec §9.4: "event-sourced in shape, not in tooling") |
| Frontend | **React 18 + TypeScript, Vite** | Component-driven UI matches the dashboard's "everything precomputed, just render" model (M8); TypeScript keeps the Ask agent's closed component-menu contract type-safe end to end |
| UI styling | Tailwind CSS + a restrained component set (Radix primitives). No standard CSS or other component library without explicit approval (constitution, Full-Stack Engineering §2) | "Clinical calm" design direction (spec §11.1) is easier to keep disciplined with utility CSS than a heavy component-library aesthetic |
| Icons | `lucide-react`, closed choice (constitution, Full-Stack Engineering §2) | One consistent icon set across the dashboard rather than mixed icon libraries |
| Charts | Recharts (SVG-based), sparkline + trend line only — resolved over visx in `decisions/02-repo-and-tooling.md` | Spec explicitly forbids ticket-volume charts, pie charts, sentiment-average lines (§11.7); Recharts' declarative components fit the two fixed chart types with less custom code than visx's lower-level API |
| Source connectors (Phase 1) | Gmail API, Zendesk API, a warehouse read connector | Per `decisions/01-mvp-scope-and-phasing.md` — Slack, CSAT, Calendar/transcripts are Phase 2 additions using the same collector interface |
| Meeting audio ingestion (specs/019-meeting-audio-ingestion) | Google Drive API (`google-api-python-client` + `google-auth`) for discovery/download; OpenAI Whisper for transcription; `pyannote.audio` for speaker diarization | The feature's first real external-API collector — every source above it still runs against a committed fixture. Diarization is a distinct step from transcription (Whisper's hosted endpoint doesn't itself label speakers) — see `specs/019-meeting-audio-ingestion/research.md` Decision 7 |
| Identity/fuzzy matching | `rapidfuzz` (Python) | Fast, dependency-light fuzzy matching for *suggesting* — never auto-resolving — identity matches |
| Encryption (Phase 1) | `pgcrypto` column-level encryption, with the data key loaded from the deployment's `.env` file (mounted as a Docker secret, not committed) | Sufficient for Phase 1's manual-retention model (`decisions/00-open-questions-resolved.md` Q5); still gives real crypto-shredding (destroy the key file → bodies unrecoverable, event skeleton survives) |
| Encryption (Phase 2) | Cloud KMS (AWS KMS / GCP Cloud KMS) replacing the `.env`-file key | Upgrades key management once the automated retention/shredding job (Phase 2, Q5) needs programmatic key rotation and destruction, rather than a person handling a file |
| Hosting | **Docker Compose**, one stack per client deployment | See comparison above |
| Observability | Structured JSON logging; **OpenTelemetry traces adopted** (specs/011-production-hardening, User Story 3) — `app.observability.adapters.tracing`, an async `BatchSpanProcessor` exporting via OTLP (never blocking on an unreachable collector, FR-012), with a `ConsoleSpanExporter` fallback | Traces now wrap the collector run and each reader's execution, marking degraded status on an isolated per-reader failure |
| Testing | pytest + a golden-replay test harness (drop projections, replay, diff against a stored golden dashboard state) | Directly encodes the spec §14.3 replay/determinism acceptance criteria |
| CI | GitHub Actions: lint, type-check, unit tests, golden-replay test, a static check that `M6` has no reachable import of the LLM client | The "no model call in scoring" boundary (P2) is enforced mechanically, not just by convention |

## Why not an event-streaming platform (Kafka, etc.)?

The spec is explicit (§9.4): the architecture is event-sourced *in shape* — append-only, bitemporal, replayable — but not in tooling. At 50k–200k events/year (roughly one event every few minutes on average, with bursts), a Postgres table with a 30-second batching window for recompute comfortably meets the < 60s latency target without the operational cost of a broker, schema registry, or consumer-group management. This holds even more strongly now that hosting is Docker Compose rather than a cloud cluster — a broker would be the single most complex thing in the whole stack for no corresponding benefit at this scale.

## Why Anthropic Claude specifically for the LLM layer

- **Structured output / tool use** is a first-class requirement (spec §12.5: "structured output everywhere") — Claude's tool-use and JSON-schema-constrained output support this directly.
- **Prompt injection containment** (spec §12.5, §15): interpreters must have no tools and no side effects; Claude's tool-use model makes it straightforward to grant *zero* tools to the readers (M5) while giving the Ask agent (M9) only read-only lookup tools.
- **Long context + citation discipline**: the Tone/Meeting readers need to compare current text against a stakeholder's historical baseline — long context windows keep this a single call rather than a multi-step retrieval pipeline for a single-client deployment's data volume.

## Per-deployment isolation model (Docker Compose version)

Each client deployment gets:

1. Its own Compose stack — its own Postgres container and data volume, no cross-tenant tables, ever.
2. Its own `.env` file holding its source credentials and its encryption data key — never shared across stacks, never committed to version control.
3. Its own set of OAuth app registrations/API credentials for its connected sources.
4. Independently startable, stoppable, and destroyable — destroying a deployment's Compose stack and its data volume *is* the crypto-shredding/deletion mechanism at the deployment level, not just the row level.

This directly implements spec §6.4's Isolation requirement and `requirements/11-non-functional-requirements.md` REQ-NFR-15/REQ-NFR-21 — with less moving infrastructure than the original cloud-orchestrator proposal, not a weaker guarantee.
