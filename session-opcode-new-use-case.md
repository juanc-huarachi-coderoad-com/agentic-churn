# Revisión del proyecto y nuevos eventos Gmail

**Session ID:** ses_fee4cd68effeLx9LbLwczvvEpB
**Created:** 8/17/2026, 5:49:09 PM
**Updated:** 8/17/2026, 5:52:33 PM

---

## User

revisar este proyecto, y ayudame a encontrar la manera para adicionar nuevos eventos de gmail, u otra fuente para probar la funcionalidad de la aplicacion por favor

---

## Assistant (Plan · GLM-5.2 · 5.2s)

_Thinking:_

The user wants me to review this project and help them find a way to add new Gmail events, or another source, to test the functionality of the application. I'm in Plan Mode, so I'm read-only. Let me explore the project structure to understand it.

Let me start by exploring the repository structure.

Voy a explorar el proyecto para entender su estructura y encontrar cómo añadir nuevos eventos para probar la funcionalidad.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn</path>
<type>directory</type>
<entries>
.agents/
.claude/
.dockerignore
.DS_Store
.env
.env.example
.git/
.gitignore
.importlinter
.pytest_cache/
.specify/
AGENTS.md
architecture/
backend/
base/
CLAUDE.md
CONTRIBUTING.md
data-base/
decisions/
demo/
docker-compose.yml
docker-compose/
examples/
frontend/
README.md
requirements/
secrets/
sequences/
skills-lock.json
spec-kit-per-build-order-phase.md
specs/
tests/
workflows/

(33 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/AGENTS.md"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/AGENTS.md</path>
<type>file</type>
<content>
1: # AGENTS.md
2: 
3: Conventions for anyone — human or AI — working in this repository. If you're an AI coding agent, read this file before touching code; it tells you where the actual specification lives and which rules are non-negotiable versus stylistic.
4: 
5: ## Where things live
6: 
7: | You're looking for... | Go to |
8: |---|---|
9: | What a module (M1–M10) is supposed to do | `requirements/<module>.md` — EARS-syntax, testable, one file per module |
10: | Why a technical decision was made | `architecture/`, `decisions/` |
11: | Exact table schemas | `data-base/10-ddl-appendix.md` is the source of truth; `data-base/02`–`data-base/12` are the annotated, example-driven companion docs |
12: | A worked example of the whole pipeline running once | `examples/01-end-to-end-walkthrough.md` — read this first if you're new here |
13: | What's in the first buildable release vs. deferred | `decisions/01-mvp-scope-and-phasing.md` |
14: | Sequence/flow diagrams | `sequences/` |
15: 
16: **`base/Churn-Sentiment-Agent-Product-Specification.md` is the original product brief (v1.2).** Everything else in this repo derives from it. If a requirement and the base spec ever seem to disagree, that's a bug to fix, not a judgment call to make silently — flag it.
17: 
18: ## Non-negotiable rules (product principles P1–P7)
19: 
20: These break every tie. Do not "improve" around them:
21: 
22: 1. **Evidence or it does not exist.** Every finding cites real event IDs. A finding with zero citations must be structurally impossible to insert, not just discouraged by convention (`findings.cited_event_ids` has a non-empty `CHECK` — see `data-base/10-ddl-appendix.md`).
23: 2. **The model interprets, code calculates.** `backend/app/scoring/` (M6) must never import an LLM client, directly or transitively. This is enforced by a CI static check (`workflows/ci.yml`), not just a lint rule — don't route around it.
24: 3. **Each component refuses to do the next one's job.** Collectors don't judge importance. Readers don't rank. The scoring engine doesn't call a model. If you're tempted to have one module do a neighboring module's job "just this once," don't — read `requirements/00-overview-and-glossary.md` §Product principles first.
25: 4. **A human always sends.** There is no send capability anywhere in this product, for any module, to any external system — not hidden, not feature-flagged, not admin-only. If a task description implies adding one, stop and flag it; it contradicts the spec.
26: 5. **Admit what we cannot see.** A degraded/incomplete data state must look visibly different from a complete one, everywhere it matters (dashboard, scores, coverage lines).
27: 6. **Silence is a success state.** A healthy account should produce a near-empty screen. Don't add UI elements that manufacture the appearance of concern.
28: 7. **Context over sentiment.** The Tone reader compares against a specific stakeholder's own baseline, never a generic sentiment scale. Don't "simplify" this into a universal threshold.
29: 
30: ## Working in this repo
31: 
32: - **Requirements are numbered and stable.** `REQ-<MODULE>-<NN>` IDs are never reused or renumbered. If a requirement is retired, mark it `RETIRED` in place — don't delete it and don't reuse its number.
33: - **Schema changes go through `data-base/10-ddl-appendix.md` first**, then get reflected in the matching prose file (`02`–`09`, `12`) and an Alembic migration (`decisions/02-repo-and-tooling.md`). Don't let the DDL and the running schema drift — that's exactly the class of bug a full-repo consistency review exists to catch, and it's expensive to catch late.
34: - **Every table's "who did this" column is a foreign key to `users`, never free text.** See `data-base/12-users-and-auth.md`. If you're adding a new "authored by" / "submitted by" style column, wire it to `users.id` from the start.
35: - **Full replay must stay exact.** If you touch anything in `backend/app/ledger/` or `backend/app/scoring/`, run the golden-replay test (`tests/strategy.md`) before opening a PR — a change that makes replay non-deterministic breaks the audit story the entire architecture is built around.
36: 
37: ## Mermaid diagrams in this repo
38: 
39: This repository has been bitten by the same two Mermaid parser gotchas enough times that they're worth stating explicitly:
40: 
41: - **Never put a semicolon (`;`) inside diagram text** (node labels, sequence messages, edge labels). Mermaid treats it as a statement terminator and silently truncates the diagram — use an em dash or a comma instead.
42: - **Never put a bare `<`, `>`, `<=`, or `>=` inside diagram text.** Mermaid tries to parse `<` as the start of an HTML tag. Spell out "at least," "below," "at most" instead, or use the multi-character unicode `≤`/`≥` only in prose *outside* a `mermaid` code fence, never inside one.
43: 
44: Before committing a new or edited diagram, a quick self-check that catches both:
45: 
46: ```bash
47: awk '/^```mermaid/{f=1;next} /^```$/{f=0} f && (/;/ || /<=|>=/){print FILENAME":"FNR": "$0}' path/to/file.md
48: ```
49: 
50: Empty output means clean.
51: 
52: ## Commit and documentation style
53: 
54: - Keep everything in English, matching the rest of the repository, regardless of what language a request arrives in.
55: - No emoji unless explicitly asked for.
56: - When you fix a cross-file inconsistency, fix it everywhere it appears — a grep for the stale term/field name across the whole repo before considering the fix done is standard practice here, not extra credit.

(End of file - total 56 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 2.2s)

_Thinking:_

Let me explore the project structure further to understand the collectors (M1) and how events are ingested.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend</path>
<type>directory</type>
<entries>
.dockerignore
.hypothesis/
.import_linter_cache/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.venv/
alembic.ini
app/
demo/
Dockerfile
migrations/
pyproject.toml
scripts/
secrets/
tests/
uv.lock

(17 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/requirements"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/requirements</path>
<type>directory</type>
<entries>
00-overview-and-glossary.md
01-signal-collectors.md
02-event-ledger.md
03-client-profile.md
04-feedback-memory.md
05-interpreters-readers.md
06-scoring-engine.md
07-narrator.md
08-health-dashboard.md
09-ask-agent.md
10-draft-composer.md
11-non-functional-requirements.md
12-traceability-matrix.md
13-scoring-calibration-appendix.md
14-authentication.md

(15 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/examples"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/examples</path>
<type>directory</type>
<entries>
01-end-to-end-walkthrough.md

(1 entries)
</entries>
```

---

## Assistant (Plan · GLM-5.2 · 1.7s)

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
auth/
config.py
context/
db.py
experience/
ingestion/
main.py
narrator/
observability/
readers/
scoring/
worker.py

(14 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/requirements/01-signal-collectors.md"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/requirements/01-signal-collectors.md</path>
<type>file</type>
<content>
1: # 01 · Signal collectors (M1)
2: 
3: Tier 1 · Ingestion — spec §7 (M1), §6.1, §13.2
4: 
5: > **Phasing note:** this module's requirements are source-agnostic by design — the same collector interface (REQ-M1-01) serves every source, Phase 1 or Phase 2. What differs by phase is *which* sources are actually connected: **Phase 1** ships Gmail, Zendesk, and warehouse telemetry; **Phase 2** adds Slack Connect, CSAT, and Calendar/transcripts. See `decisions/01-mvp-scope-and-phasing.md` for the full rationale, including why chat and meeting transcripts specifically wait for Phase 2.
6: 
7: ## Purpose
8: 
9: Get material out of source systems and onto the event ledger, without interpreting it. One adapter per source, all implementing the same interface, plus a dedicated collector for the absence of expected contact.
10: 
11: ## User stories
12: 
13: - As a **CS lead**, I want every ticket, email, chat message and usage change captured automatically, so that nothing depends on someone remembering to log it.
14: - As the **system**, I need identity resolution so that a message from `ana.reyes@meridian.com` is recognized as stakeholder `stk_ana`, not an anonymous sender.
15: - As a **CS lead**, I want to know what the system *could not* see, so that I never mistake silence-because-broken for silence-because-healthy (P5, P6).
16: 
17: ## Functional requirements
18: 
19: | ID | Requirement |
20: |---|---|
21: | REQ-M1-01 | THE SYSTEM SHALL implement one adapter per connected source (tickets, email, chat, product usage, surveys, meetings, CRM/contracts), each conforming to a single common collector interface (`fetch`, `normalize`, `emit_envelope`). |
22: | REQ-M1-02 | WHEN a source supports webhooks, THE SYSTEM SHALL subscribe for near-real-time delivery, AND SHALL additionally run scheduled polling for correctness. |
23: | REQ-M1-03 | WHEN a collector runs (webhook or poll), THE SYSTEM SHALL fetch a deliberate overlap window with the previous run and de-duplicate using an idempotency key derived from the source's native record ID. |
24: | REQ-M1-04 | WHEN a raw signal is normalized, THE SYSTEM SHALL attempt to resolve each participant address/user ID to a stakeholder in the current client profile version. |
25: | REQ-M1-05 | IF a participant cannot be resolved to a known stakeholder, THEN THE SYSTEM SHALL emit the envelope with `identity_status = unresolved` rather than guessing a match. |
26: | REQ-M1-06 | THE SYSTEM SHALL run a scheduled **absence collector** that emits an `absence` event type when an expected contact (e.g. a promised weekly sync, an overdue response) does not occur within its defined window. |
27: | REQ-M1-07 | WHEN each collector run completes, THE SYSTEM SHALL produce a **coverage report** stating which sources were read, the time window covered, and the reason for any gap. |
28: | REQ-M1-08 | WHEN a source's credentials fail or the source is unreachable, THE SYSTEM SHALL mark that source `disconnected` in the coverage report and continue operating on the remaining sources (graceful degradation, never all-or-nothing). |
29: | REQ-M1-09 | THE SYSTEM SHALL redact sensitive data (per the client profile's `exclusions` list, e.g. `legal_threads`, `commercial_negotiation`) at the collector, before the envelope is persisted, and SHALL record that a redaction occurred. |
30: | REQ-M1-10 | THE SYSTEM SHALL wrap every raw signal in a standard **envelope** (source, native ID, occurred-at timestamp, resolved/unresolved participants, redaction flags, raw payload reference) before handing it to the event ledger (M2). |
31: 
32: ## Explicit prohibitions
33: 
34: | ID | Prohibition |
35: |---|---|
36: | REQ-M1-P1 | Collectors SHALL NOT assign severity, priority, or importance to any signal. |
37: | REQ-M1-P2 | Collectors SHALL NOT filter signals based on perceived importance — filtering by exclusion rules only. |
38: | REQ-M1-P3 | Collectors SHALL NOT interpret what a product area or stakeholder role means — that belongs to M3. |
39: | REQ-M1-P4 | Collectors SHALL NOT write to, or take any action in, a source system (read-only scopes only). |
40: | REQ-M1-P5 | The identity resolver SHALL NOT guess a stakeholder match below a defined confidence threshold — it must abstain and mark `unresolved`. |
41: 
42: ## Inputs / Outputs
43: 
44: - **Input:** source-system APIs/webhooks (Zendesk, Jira, Intercom, Gmail, Microsoft 365, Slack Connect, Teams, product telemetry warehouse, CSAT/NPS tools, calendar/transcripts, Salesforce/contract store); current version of the client profile (M3) for identity resolution targets and `exclusions`.
45: - **Output:** envelopes appended to the event ledger (M2); one coverage report per run persisted for M8's coverage line.
46: 
47: ## Non-functional constraints
48: 
49: - Read-only, narrowest available OAuth/API scopes per source, documented per source (spec §6.4).
50: - Message bodies encrypted at rest immediately on ingestion; keys scoped per deployment.
51: - Running any collector twice MUST produce no duplicate events (spec §14.3 engineering acceptance criterion).
52: 
53: ## Acceptance criteria
54: 
55: - [ ] Re-running a collector over an overlapping window produces zero duplicate ledger entries.
56: - [ ] An unresolved sender never silently attaches to an existing stakeholder.
57: - [ ] A coverage report exists for every run, including runs where a source failed.
58: - [ ] Disconnecting one source does not stop collection from the others.
59: - [ ] Every excluded thread type is verifiably absent from stored envelopes.
60: 
61: ## Traceability
62: 
63: Spec §7 M1, §6.1 (Sources), §6.3 (data deliberately not collected), §6.4 (privacy/security), §13.2 (honest limitations), §14.3 (no-duplicates criterion).

(End of file - total 63 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 1.9s)

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
adapters/
application/
domain/

(5 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/examples/01-end-to-end-walkthrough.md"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/examples/01-end-to-end-walkthrough.md</path>
<type>file</type>
<content>
1: # End-to-end worked example — five signals, one score
2: 
3: | | |
4: |---|---|
5: | **Purpose** | Show the *entire* system running once, from raw signals arriving to the number on screen, using real (invented but realistic) data — table by table, process by process. |
6: | **Audience** | Anyone who wants to understand the system without already knowing it — no prior familiarity with the spec, the modules, or the database is assumed. |
7: | **How to read it** | Top to bottom, in order. Each step says: *what happens*, *which table(s) it writes to*, *what process/component does the writing*, and *why*. Every table name is a link back to its full definition in `data-base/`. |
8: 
9: If you only read one document to understand how this product works end to end, read this one.
10: 
11: ---
12: 
13: ## 0. Five words you need before we start
14: 
15: The system's own vocabulary, defined in plain terms (full glossary: `requirements/00-overview-and-glossary.md`):
16: 
17: | Word | Plain meaning |
18: |---|---|
19: | **Event** | One fact that happened, stored forever, never edited — "Ana sent this email at 09:14." |
20: | **Finding** | One structured *observation* built from one or more events — "Ana's tone has gotten worse." A finding is an opinion; an event is a fact. |
21: | **Issue** | A bundle of findings that all point at the same underlying problem, so we don't count one broken feature five times. |
22: | **Score** | The single 0–100 number, recomputed from zero every time, that summarizes how the relationship is doing. |
23: | **Evidence / trace** | The clickable path from the score, back through the finding, back to the original message — nothing is ever asserted without a receipt. |
24: 
25: The system is built in four layers ("tiers"), and information only ever flows forward through them:
26: 
27: ```mermaid
28: flowchart LR
29:     T1["Tier 1\nIngestion\nget the facts"] --> T2["Tier 2\nContext\nwho/what matters"]
30:     T2 --> T3["Tier 3\nReasoning\nturn facts into a number"]
31:     T3 --> T4["Tier 4\nExperience\nshow it to a human"]
32: ```
33: 
34: This document walks one real pass through all four tiers.
35: 
36: > **Which phase is this?** This walkthrough deliberately shows the system at **full strength** — all five source types connected — so every reader and every table in this database gets exercised at least once. Per `decisions/01-mvp-scope-and-phasing.md`, the actual **Phase 1** ("first solution") build ships with only 3 of these 5 sources (Email, Tickets, Product usage); Chat and Survey are **Phase 2** additions. The source table in §1 below tags each row with its phase. If you want to see what a *Phase 1* run looks like, mentally remove sources 4 and 5 — Issue B would then rest on Ana's tone, intent, and CSAT-free evidence alone, and Diego's absence/relationship findings wouldn't exist yet (no chat to observe them in).
37: 
38: ---
39: 
40: ## 1. The scenario
41: 
42: **Client:** Meridian Logistics (the same example client used throughout `base/Churn-Sentiment-Agent-Product-Specification.md` and this repo's other documents).
43: 
44: **People who matter, as defined in the client profile** (see `data-base/04-schema-context.md`):
45: 
46: | Stakeholder | Role | Influence | Why it matters |
47: |---|---|---|---|
48: | Ana Reyes | CTO | `sponsor` (multiplier **1.6**) | She signs the renewal. Anything she says or does is weighted heaviest. |
49: | Diego Marín | Dev lead | `daily_user` (multiplier **1.2**) | Uses the product daily; his engagement is a strong health signal. |
50: 
51: **Product areas:**
52: 
53: | Area | Criticality | Why it matters |
54: |---|---|---|
55: | `tracking_api` | `critical` (multiplier **1.5**) | The client's core workflow depends on it. |
56: | `reporting` | `standard` (multiplier **1.0**) | Useful, not load-bearing. |
57: 
58: **The week we're examining:** five different systems each report something, on their own schedule, with no coordination between them — exactly as it would happen in real life. This is the whole point of the product: nobody at Meridian or at the vendor sees all five things at once. The system does.
59: 
60: | # | Source | Phase | What happened | Who/what it's about |
61: |---|---|---|---|---|
62: | 1 | **Email** (Gmail) | **1** | Ana writes: *"Please advise on the timeline. I need to brief the board on Thursday."* — short, no greeting, mentions the board. | Ana · relationship tone |
63: | 2 | **Tickets** (Zendesk) | **1** | Ticket #456 "Slow API response" is reopened for the **second time**; first response took **19 business hours** against a **4-hour** promise. Separately, ticket #398 (a minor CSV-export request) is resolved in 2 hours — well inside SLA. | `tracking_api` · a broken promise, and a kept one |
64: | 3 | **Product usage** (warehouse telemetry) | **1** | Daily active usage of `tracking_api` is down **22%** over the last 3 weeks compared to the prior 8-week average. | `tracking_api` · behavior, not words |
65: | 4 | **Chat** (Slack Connect) | **2** | Diego, who normally posts ~5×/week in the shared channel, has posted **zero** times in 12 days, and skipped the weekly sync twice. | Diego · going quiet |
66: | 5 | **Survey** (CSAT) | **2** | Ana's CSAT response drops from **9** (three months ago) to **6** (this week), with the comment *"Support has been slower than we'd like lately."* | Ana · a number this time, not just words |
67: 
68: Sources 1–3 are what a real Phase 1 deployment sees today. Sources 4–5 (and the fuller-strength Absence/Relationship readings they enable) are Phase 2 — included here so this document can double as the complete architectural reference, not just the Phase 1 demo script.
69: 
70: None of these five facts, alone, would trigger an escalation. Together, they will.
71: 
72: ---
73: 
74: ## 2. The big picture
75: 
76: ```mermaid
77: flowchart TB
78:     S1["Email\nGmail"] --> COL["M1 · Collectors\nnormalize + resolve identity"]
79:     S2["Tickets\nZendesk"] --> COL
80:     S3["Product usage\nwarehouse"] --> COL
81:     S4["Chat\nSlack"] --> COL
82:     S5["Survey\nCSAT"] --> COL
83: 
84:     COL --> LEDGER[("M2 · Event ledger\none immutable timeline")]
85:     LEDGER --> READERS["M5 · Readers\n7 of 8 readers fire this run"]
86:     READERS --> GATE{"M5a · Validation gate\nevidence checked"}
87:     GATE -->|"1 finding rejected"| QUAR["Quarantine\nnever scored"]
88:     GATE -->|"8 findings pass"| ISSUES["Grouped into\n2 issues"]
89:     ISSUES --> SCORE["M6 · Scoring engine\nplain arithmetic"]
90:     SCORE --> NARRATOR["M7 · Narrator\nwrites the explanation"]
91:     NARRATOR --> DASH["M8 · Dashboard"]
92:     NARRATOR --> ASK["M9 · Ask agent"]
93:     NARRATOR --> DRAFT["M10 · Draft composer\nno send button"]
94: ```
95: 
96: We now walk through every box, left to right, and open up the database tables behind each one.
97: 
98: ---
99: 
100: ## 3. Step 1 — Five raw signals arrive
101: 
102: Nothing is stored yet. Five independent systems each have new data sitting in their own APIs, waiting to be fetched. There is no table for this step — it is simply "the world," outside the system's boundary.
103: 
104: ---
105: 
106: ## 4. Step 2 — Collectors turn raw signals into envelopes
107: 
108: **Who does this:** Module **M1 · Signal collectors** — one small adapter program per source. Each adapter's only job is: fetch, figure out who sent it, wrap it consistently, and hand it off. It is *not allowed* to decide whether something matters (see `requirements/01-signal-collectors.md`).
109: 
110: ### 4.1 `sources` — one row already exists per connected system
111: 
112: This table was set up once, when Meridian was onboarded. We just read it here to know *where* to fetch from.
113: 
114: | id | source_type | display_name | status |
115: |---|---|---|---|
116: | src-email | `gmail` | Meridian — Email | connected |
117: | src-tickets | `zendesk` | Meridian — Support | connected |
118: | src-usage | `warehouse` | Meridian — Product usage | connected |
119: | src-chat | `slack` | Meridian — Slack Connect | connected |
120: | src-survey | `csat` | Meridian — CSAT | connected |
121: 
122: ### 4.2 `collector_runs` — one row every time an adapter runs
123: 
124: Each source polls (or receives a webhook) independently. Five sources firing this week means five separate collector runs, at five different times:
125: 
126: | id | source_id | trigger | envelopes_emitted | duplicates_skipped |
127: |---|---|---|---|---|
128: | run-1 | src-email | webhook | 1 | 0 |
129: | run-2 | src-tickets | poll | 2 | 0 |
130: | run-3 | src-usage | poll | 1 | 0 |
131: | run-4 | src-chat | poll | 1 | 0 |
132: | run-5 | src-survey | webhook | 1 | 0 |
133: 
134: `duplicates_skipped` stays at 0 here, but this is the column that proves the "running a collector twice never creates duplicates" guarantee (`requirements/01-signal-collectors.md` REQ-M1-03) — if this poll re-fetched something it already saw, it would be counted and thrown away here, not appended twice to the ledger.
135: 
136: ### 4.3 `identity_map` — who is this, really?
137: 
138: Before anything can be scored with the right weight, the system has to know *who* sent it. This table is the phone book.
139: 
140: | source_identifier | source_type | stakeholder_id | resolved_by |
141: |---|---|---|---|
142: | ana.reyes@meridian.com | gmail | stk-ana | exact_match |
143: | (Zendesk reporter contact) | zendesk | *(unresolved — generic support contact, not a named stakeholder)* | unresolved |
144: | diego@meridian.com | slack | stk-diego | exact_match |
145: | ana.reyes@meridian.com | csat | stk-ana | exact_match |
146: 
147: Notice the ticket reporter resolves to **nobody in particular** — that's fine and expected (REQ-M1-05): the system never guesses an identity match just to fill a field. The ticket will still be scored, just without a stakeholder-influence multiplier attached (we'll see this matter in Step 7).
148: 
149: ### 4.4 `raw_envelopes` — the standard wrapper, one row per fetched item
150: 
151: Every source's output gets forced into the same shape here, before it's allowed anywhere near the ledger. This is also where message bodies are **encrypted** (`payload_encrypted` + `data_key_ref`) and where any excluded content would be stripped (`redacted_fields`) — neither applies to this batch.
152: 
153: | id | collector_run_id | source_native_id | idempotency_key | occurred_at | identity_status |
154: |---|---|---|---|---|---|
155: | env-1 | run-1 | gmail-msg-8831 | hash(gmail, 8831) | Mon 09:14 | resolved |
156: | env-2 | run-2 | zendesk-456 | hash(zendesk, 456) | Mon 07:40 | unresolved |
157: | env-3 | run-2 | zendesk-398 | hash(zendesk, 398) | Tue 11:02 | unresolved |
158: | env-4 | run-3 | usage-tracking_api-w34 | hash(warehouse, w34) | Wed 00:00 | resolved *(product-level, not personal)* |
159: | env-5 | run-4 | slack-absence-diego-12d | hash(slack, absence-diego) | Thu 08:00 | resolved |
160: | env-6 | run-5 | csat-resp-5521 | hash(csat, 5521) | Fri 10:15 | resolved |
161: 
162: `idempotency_key` is what makes REQ-M1-03 real: it carries a database `UNIQUE` constraint, so even a bug that re-fetches `zendesk-456` tomorrow cannot insert a second row here.
163: 
164: **What happens next:** each envelope is handed, one at a time, to the event ledger. This is the moment raw material crosses from "temporary staging" into "permanent record."
165: 
166: ---
167: 
168: ## 5. Step 3 — The ledger appends immutable events
169: 
170: **Who does this:** Module **M2 · Event ledger** (`requirements/02-event-ledger.md`). This is the single most important table in the whole system: **`events`**. Nothing is ever updated or deleted here — only appended. If a correction is needed later, a *new* row is added that references the old one; the old one stays exactly as it was written.
171: 
172: ### 5.1 `events` — six new rows, one per envelope
173: 
174: | id | envelope_id | event_type | occurred_at | recorded_at | stakeholder_id | product_area_id | structured_payload (summary) |
175: |---|---|---|---|---|---|---|---|
176: | evt-1 | env-1 | message | Mon 09:14 | Mon 09:14:03 | stk-ana | — | "Please advise on the timeline. I need to brief the board on Thursday." |
177: | evt-2 | env-2 | ticket_state_change | Mon 07:40 | Mon 07:41 | *(null)* | tracking_api | {ticket: 456, title: "Slow API response", reopen_count: 2} |
178: | evt-3 | env-3 | ticket_state_change | Tue 11:02 | Tue 11:03 | *(null)* | reporting | {ticket: 398, title: "Add CSV export", resolved_in_hours: 2} |
179: | evt-4 | env-4 | usage_measurement | Wed 00:00 | Wed 00:05 | — | tracking_api | {metric: weekly_active_usage, value: -22%} |
180: | evt-5 | env-5 | absence | Thu 08:00 | Thu 08:00 | stk-diego | — | {expected: weekly_sync, missed_count: 2, silent_days: 12} |
181: | evt-6 | env-6 | survey_response | Fri 10:15 | Fri 10:16 | stk-ana | — | {score: 6, previous_score: 9, comment: "Support has been slower than we'd like lately."} |
182: 
183: Two things worth pausing on, because they're easy to miss and they matter a lot:
184: 
185: - **Two different timestamps.** `occurred_at` is *when the thing really happened* (e.g. the email was sent Monday at 09:14). `recorded_at` is *when our system found out about it* (a few seconds later, once the collector ran). Normally these are seconds apart, like above — but if a source was down for two days and we only found out about a Monday email on Wednesday, `occurred_at` would still say Monday while `recorded_at` says Wednesday. This is what lets the system honestly answer "what did we know as of last Tuesday?" (`data-base/03-schema-ledger.md`).
186: - **Nothing here says anything is wrong.** `evt-2` records "19 hours elapsed, second reopen" as a plain fact. It does **not** say "this is bad." That judgment doesn't exist yet — it gets made in Step 4, by a completely different, more accountable part of the system. This separation (facts here, opinions later) is deliberate and is one of the product's core rules (`requirements/02-event-ledger.md` REQ-M2-P1).
187: 
188: ### 5.2 `response_pairs` — turning ticket #456 into a measurable promise
189: 
190: A **projection** (a derived table, rebuildable at any time from `events` alone — see `data-base/01-database-overview.md`). It pairs a client message with its reply and measures the gap in *business hours*, using Meridian's own working calendar (08:00–18:00, America/Bogota, per the client profile).
191: 
192: | id | client_event_id | commitment_id | business_hours_elapsed | state |
193: |---|---|---|---|---|
194: | rp-1 | evt-2 (ticket #456) | commitment (first_response, P1, 4h) | 19.0 | `open_overdue` |
195: | rp-2 | evt-3 (ticket #398) | commitment (first_response, P1, 4h) | 2.0 | `resolved` |
196: 
197: This is pure arithmetic — no judgment yet, just "19 hours against a 4-hour promise" and "2 hours against the same promise." Whether 19 hours is *bad* is decided next.
198: 
199: ### 5.3 `rollups` — updating what "normal" looks like
200: 
201: | subject_type | subject_id | metric | value | is_baseline |
202: |---|---|---|---|---|
203: | stakeholder | stk-ana | avg_words_per_message | 14 (this message) vs. 47 (baseline) | false |
204: | stakeholder | stk-ana | greeting_rate | 0 of last 3 messages had a greeting, vs. 11 of 12 historically | false |
205: | product_area | tracking_api | weekly_active_usage | −22% vs. 8-week average | false |
206: | account | — | csat_score | 6, previous 9 | false |
207: 
208: These rollups exist so that readers (next step) never have to scan the whole history every time — they just compare "now" against a pre-computed "normal."
209: 
210: ### 5.4 `coverage_reports` — proving nothing was missed
211: 
212: | collector_run_id | sources_expected | sources_read | complete_to |
213: |---|---|---|---|
214: | run-1..5 | 5 | 5 | Fri 10:16 |
215: 
216: All five sources reported in. If one had failed (say, Slack), this table would show `sources_read: 4` and the dashboard's coverage line would say so honestly — the score would freeze rather than pretend it saw everything (`requirements/11-non-functional-requirements.md` REQ-NFR-07).
217: 
218: **What happens next:** the ledger tells the readers "these six new events, and the rollup windows they touched, need a fresh look."
219: 
220: ---
221: 
222: ## 6. Step 4 — Readers turn events into findings
223: 
224: **Who does this:** Module **M5 · Interpreters**, a set of eight independent specialists (`requirements/05-interpreters-readers.md`). Each one answers exactly *one* question, using only the events relevant to that question. Three of them use a language model (Tone, Intent, Meeting); the rest are ordinary code or statistics. None of them can see or influence each other.
225: 
226: Here is what fires this week:
227: 
228: | Reader | Type | Question it asks | Fires this week? | Needs a Phase 2 source? |
229: |---|---|---|---|---|
230: | **Commitment** | code | Did a reply exceed the promised response time? | ✅ ticket #456 | No — Phase 1 |
231: | **Recurrence** | embeddings + clustering | Is this the same problem coming back? | ✅ ticket #456 (2nd reopen) | No — Phase 1 |
232: | **Usage** | statistics | Has activity deviated from normal? | ✅ `tracking_api` usage, ✅ CSAT score | Usage-on-warehouse: no. Usage-on-CSAT: **yes, Phase 2** |
233: | **Absence** | statistics | Is expected contact missing? | ✅ Diego | **Yes, Phase 2** (chat-based silence — Phase 1's version only sees missed email/ticket replies) |
234: | **Relationship** | graph diff | Has the cast of people changed? | ✅ Diego stepping back | **Yes, Phase 2** (needs the Slack participant graph) |
235: | **Tone** | LLM | Is this person writing differently than *they* normally do? | ✅ Ana's email | No — Phase 1 (email) |
236: | **Intent** | LLM | Escalation / competitive / contractual language? | ✅ Ana's "board" mention | No — Phase 1 (email) |
237: | **Meeting** | LLM | What was verbally promised, by when? | ⚪ *abstains — no transcript this week* | N/A — idle until Phase 2 connects a transcript source |
238: 
239: The Meeting reader producing **nothing** is not a bug — it is the correct behavior when there's no material to work from (REQ-M5-04). A system that invents a finding just to have something to say would be actively dangerous here; "no history, no opinion" is a design principle, not a gap.
240: 
241: ### `findings` — one row per observation, each with a receipt
242: 
243: Every single row below carries `cited_event_ids` pointing back to Step 3's `events` table — a finding that cannot point to a real event is not just discouraged, it is **impossible to insert** (the database rejects an empty citation list, `data-base/05-schema-reasoning.md`).
244: 
245: | id | reader_type | finding_type | magnitude | confidence | cited_event_ids | about |
246: |---|---|---|---|---|---|---|
247: | fnd-1 | commitment | `broken_response_promise` | 1.00 | 1.00 | [evt-2] | ticket #456, 19h vs 4h |
248: | fnd-2 | recurrence | `recurring_issue` | 0.60 | 0.75 | [evt-2] | this is the 2nd reopen of the same root cause |
249: | fnd-3 | usage | `usage_deviation` | 0.55 | 0.90 | [evt-4] | tracking_api usage down 22% |
250: | fnd-4 | absence | `contact_absence` | 0.70 | 0.85 | [evt-5] | Diego silent 12 days, missed sync ×2 |
251: | fnd-5 | relationship | `relationship_change` | 0.40 | 0.70 | [evt-5] | Diego effectively inactive in the channel |
252: | fnd-6 | tone | `tone_deterioration` | 0.60 | 0.80 | [evt-1] | Ana: shorter, no greeting, vs. her own baseline |
253: | fnd-7 | intent | `escalation_language` | 0.50 | 0.85 | [evt-1] | "brief the board" — an escalation phrase |
254: | fnd-8 | usage | `csat_deviation` | 0.50 | 0.95 | [evt-6] | Ana's CSAT: 9 → 6 |
255: | fnd-9 | commitment | `commitment_met` *(positive)* | 0.40 | 1.00 | [evt-3] | ticket #398 resolved in 2h, well inside SLA |
256: | fnd-10 | tone | `tone_deterioration` | 0.55 | **0.55** | [evt-5] | *attempted:* Diego's tone in Slack — but only 1 historical sample exists |
257: 
258: `fnd-1` through `fnd-9` are solid. `fnd-10` was attempted — the Tone reader tried to say something about *how* Diego wrote in Slack, not just *that* he went quiet — but it only had one prior message to compare against, so its own confidence came out low (0.55). That finding is about to be caught by the next step, on purpose.
259: 
260: Notice also what did **not** happen: no reader tried to guess *why* Ana's CSAT score dropped, or build any narrative about Diego's personal situation. Readers report *what changed*, never *why* — causal storytelling is explicitly out of scope (`requirements/05-interpreters-readers.md` REQ-M5-P3, spec §13.2).
261: 
262: **What happens next:** all ten attempted findings go to the validation gate before any of them are allowed anywhere near a score.
263: 
264: ---
265: 
266: ## 7. Step 5 — The validation gate checks the receipts
267: 
268: **Who does this:** Module **M5a · Validation gate** (`requirements/05-interpreters-readers.md`). Four checks, no exceptions, no repairs: (1) is it shaped correctly, (2) do the cited events actually exist, (3) is there enough evidence for this type of finding, (4) does its confidence clear that finding type's minimum bar. This bar is set per finding type in `finding_type_config`:
269: 
270: | finding_type | confidence_floor | min_evidence_count |
271: |---|---|---|
272: | `tone_deterioration` | 0.65 | 3 |
273: | `broken_response_promise` | 0.50 | 1 |
274: | *(others similar — omitted for brevity)* | | |
275: 
276: Running `fnd-10` (Diego's Slack tone, confidence 0.55) against `tone_deterioration`'s floor of 0.65: **it fails.**
277: 
278: ### `quarantine` — where failed findings go to be remembered, not fixed
279: 
280: | id | finding_id | failed_check | detail |
281: |---|---|---|---|
282: | q-1 | fnd-10 | `confidence_below_floor` | confidence 0.55 < required 0.65 for `tone_deterioration` |
283: 
284: ### `validation_failures` — the specific reason, logged
285: 
286: | quarantine_id | check_name | expected | actual |
287: |---|---|---|---|
288: | q-1 | confidence_floor | ≥ 0.65 | 0.55 |
289: 
290: Nobody edits `fnd-10` to "fix" it and try again — that is explicitly forbidden (REQ-M5A-03). It sits in quarantine permanently, visible on the internal "System health" screen, as part of an honest record of what the readers get wrong — which is exactly the dataset a team would use later to decide whether the Tone reader needs a higher evidence bar in general.
291: 
292: **Findings that pass and move forward:** fnd-1 through fnd-9 — **nine** findings, all validated.
293: 
294: **What happens next:** validated findings get grouped before scoring, so one broken feature can't be counted five separate times.
295: 
296: ---
297: 
298: ## 8. Step 6 — Grouping findings into issues
299: 
300: **Who does this:** still Module **M5/M6** boundary — clustering is a scoring-adjacent step (`requirements/06-scoring-engine.md` REQ-M6-06). The question being asked here is simple: *do several of these findings actually describe the same underlying problem?* If yes, only the loudest one counts at full strength; the rest count for progressively less. This is what stops "the tracking API is broken" from being counted once for the ticket, once again for the reopen, and a third time for the usage drop.
301: 
302: Looking at our nine findings, two natural clusters emerge:
303: 
304: - **Issue A — "tracking_api is broken":** the ticket breach, the recurrence, and the usage drop are all downstream of one real problem.
305: - **Issue B — "the relationship with Meridian's decision-makers is cooling":** Ana's tone, Ana's escalation language, Ana's CSAT drop, and Diego pulling back are all downstream of one real pattern — even though they involve two different people and three different sources.
306: 
307: `fnd-9` (the positive: ticket #398 resolved fast) doesn't belong to either negative story — it stands alone, which is fine; not every finding needs a cluster.
308: 
309: ### `issues`
310: 
311: | id | label | cluster_method |
312: |---|---|---|
313: | iss-A | Issue A — tracking_api reliability | shared_entity *(same ticket / same product area)* |
314: | iss-B | Issue B — Ana & Diego disengaging | embedding_similarity *(different words, same underlying story)* |
315: 
316: ### `finding_issue_map`
317: 
318: | finding_id | issue_id | rank_within_issue |
319: |---|---|---|
320: | fnd-1 (broken promise) | iss-A | 1 |
321: | fnd-2 (recurrence) | iss-A | 2 |
322: | fnd-3 (usage down) | iss-A | 3 |
323: | fnd-7 (Ana escalation) | iss-B | 1 |
324: | fnd-4 (Diego absence) | iss-B | 2 |
325: | fnd-6 (Ana tone) | iss-B | 3 |
326: | fnd-8 (Ana CSAT) | iss-B | 4 |
327: | fnd-5 (Diego relationship) | iss-B | 5 |
328: 
329: `rank_within_issue` is what makes the "diminishing returns" rule from the next step possible — the biggest contributor in an issue counts fully, the next one counts for 60% of its own value, then 36%, then 22%, and so on. We'll see exactly how in a moment.
330: 
331: **What happens next:** these ranked, grouped findings — plus `fnd-9`, standing alone — are handed to the one component in the entire system that is deliberately, strictly *not* smart.
332: 
333: ---
334: 
335: ## 9. Step 7 — The scoring engine computes the number
336: 
337: **Who does this:** Module **M6 · Scoring engine** (`requirements/06-scoring-engine.md`). This is plain arithmetic — **no model call happens anywhere in this step.** Every number below can be checked on a calculator. The formula, from `requirements/06-scoring-engine.md` REQ-M6-01:
338: 
339: ```
340: points = base × influence × criticality × confidence × magnitude × recency × damping
341: ```
342: 
343: Then, within each issue, the ranked findings are multiplied again by a diminishing factor (1st = 100%, 2nd = 60%, 3rd = 36%, 4th = 22%, 5th ≈ 13% — each step is ×0.6 of the last, REQ-M6-07).
344: 
345: ### 9.1 Where each multiplier comes from
346: 
347: - **base** — a fixed point value per finding type, from `finding_type_config` (e.g. a broken response promise is worth more than a relationship blip).
348: - **influence** — 1.6 for Ana (sponsor), 1.2 for Diego (daily user), **1.0** for anything not tied to a specific stakeholder (like the ticket, whose reporter never resolved to a named person back in Step 2 — a good example of why identity resolution mattered).
349: - **criticality** — 1.5 for `tracking_api` (critical), 1.0 for anything not tied to a product area (people-related findings).
350: - **confidence** and **magnitude** — copied straight from the finding (Step 4) — how sure the reader was, and how big the change was.
351: - **recency** — 1.0 normally; **1.3** for ticket #456 specifically, because it's not just open, it's *overdue* (`open_overdue` from Step 5.2) — the clock ageing against us.
352: - **damping** — 1.0 for everything this week. Nobody has given feedback yet, so nothing is being discounted. (Step 12 shows this changing.)
353: 
354: ### 9.2 Issue A — tracking_api reliability
355: 
356: | Finding | base | influence | criticality | confidence | magnitude | recency | rank factor | points |
357: |---|---|---|---|---|---|---|---|---|
358: | fnd-1 broken promise | 20 | 1.0 | 1.5 | 1.00 | 1.00 | 1.3 | 1.00 (1st) | **39.00** |
359: | fnd-2 recurrence | 12 | 1.0 | 1.5 | 0.75 | 0.60 | 1.0 | 0.60 (2nd) | **4.86** |
360: | fnd-3 usage down | 15 | 1.0 | 1.5 | 0.90 | 0.55 | 1.0 | 0.36 (3rd) | **4.01** |
361: | | | | | | | | **Issue A total** | **47.87** |
362: 
363: *(fnd-1's number — 39.00 — deliberately matches the worked example in the product spec itself, §10: the same finding type, computed the same way, always gives the same answer. That consistency is the point of Module M6 being "deliberately unintelligent.")*
364: 
365: ### 9.3 Issue B — Ana & Diego disengaging
366: 
367: | Finding | base | influence | criticality | confidence | magnitude | recency | rank factor | points |
368: |---|---|---|---|---|---|---|---|---|
369: | fnd-7 Ana escalation | 14 | 1.6 | 1.0 | 0.85 | 0.50 | 1.0 | 1.00 (1st) | **9.52** |
370: | fnd-4 Diego absence | 12 | 1.2 | 1.0 | 0.85 | 0.70 | 1.0 | 0.60 (2nd) | **5.14** |
371: | fnd-6 Ana tone | 10 | 1.6 | 1.0 | 0.80 | 0.60 | 1.0 | 0.36 (3rd) | **2.76** |
372: | fnd-8 Ana CSAT | 10 | 1.6 | 1.0 | 0.95 | 0.50 | 1.0 | 0.22 (4th) | **1.67** |
373: | fnd-5 Diego relationship | 8 | 1.2 | 1.0 | 0.70 | 0.40 | 1.0 | 0.13 (5th) | **0.35** |
374: | | | | | | | | **Issue B total** | **19.44** |
375: 
376: Notice `fnd-4` (Diego's absence) actually has *more* raw weight than `fnd-6` (Ana's tone) before ranking — but because it landed in 2nd place in the issue, it's discounted to 60%, while a smaller-but-first-ranked finding would count fully. The ranking is decided by raw size, but paid out by position — this is exactly the mechanism that stops five symptoms of one problem from outscoring three separate real problems.
377: 
378: ### 9.4 The positive finding
379: 
380: | Finding | base | influence | criticality | confidence | magnitude | recency | points |
381: |---|---|---|---|---|---|---|---|
382: | fnd-9 ticket #398 resolved fast | 10 | 1.0 | 1.0 | 1.00 | 0.40 | 1.0 | **4.00** |
383: 
384: Positive points are capped at 25% of the negative total, so goodwill can soften a score but never erase real damage (REQ-M6-14):
385: 
386: ```
387: total_negative_points = 47.87 + 19.44 = 67.31
388: cap = 25% of 67.31 = 16.83
389: positive_points_applied = min(4.00, 16.83) = 4.00   ← under the cap, so it applies in full
390: ```
391: 
392: ### 9.5 From points to the number on screen
393: 
394: ```
395: total_points = 67.31 − 4.00 = 63.31
396: score = 100 × (1 − e^(−63.31 / 33)) ≈ 85.3
397: ```
398: 
399: ### `score_runs` — one row for this entire computation
400: 
401: | id | trigger | total_negative_points | total_positive_points | positive_points_applied | total_points | score | raw_band | band |
402: |---|---|---|---|---|---|---|---|---|
403: | run-score-1 | `burst_batch` | 67.310 | 4.000 | 4.000 | 63.310 | **85.30** | at_risk | **at_risk** |
404: 
405: *(All five signals landed within the same 30-second batching window as far as the scoring engine is concerned, so this is one `burst_batch`-triggered run, not five separate recomputations — see `sequences/05-flow-recompute-triggers.md`.)*
406: 
407: ### `score_contributions` — nine rows, reconciling to the decimal
408: 
409: Every single number from the two tables above is stored as its own row here — `base`, `influence`, `criticality`, `confidence`, `magnitude`, `recency`, `damping`, `rank_within_issue_factor`, and the final `points_contributed`. Summing the `points_contributed` column for all nine rows (39.00 + 4.86 + 4.01 + 9.52 + 5.14 + 2.76 + 1.67 + 0.35 + 4.00, with the positive row subtracted) reproduces `total_points` **exactly**, to the decimal — this reconciliation is a hard engineering requirement (`requirements/11-non-functional-requirements.md` REQ-NFR-30), not a nice-to-have. It's what lets a skeptical CS lead check the system's math on paper and be shown to be right to trust it.
410: 
411: ### `band_history`
412: 
413: | score_run_id | band | consecutive_runs_in_band | notified |
414: |---|---|---|---|
415: | run-score-1 | at_risk | 2 *(this account was already at 70+ last week)* | true |
416: 
417: Because the account was already trending high, this is the **second** consecutive run above the 65 "enter" threshold — so the band confirms as **At risk** rather than waiting (the hysteresis rule, `sequences/06-state-band-hysteresis.md`). If this had been an isolated one-run spike from a healthy account, the displayed band would have stayed at `watch` for one more run before flipping.
418: 
419: **What happens next:** a number alone (85.30, At risk) isn't useful to a person. It needs words.
420: 
421: ---
422: 
423: ## 10. Step 8 — The narrator writes the explanation
424: 
425: **Who does this:** Module **M7 · Narrator** (`requirements/07-narrator.md`) — the first place a language model is allowed to touch the *presentation* of this run (readers used models too, back in Step 4, but only to produce structured data, never sentences). The narrator receives the ranked findings and their point values exactly as computed in Step 7 — it is not allowed to re-rank or re-weigh anything. Every name, number, and date it writes is mechanically checked against that input before anyone sees it; a sentence that invents a fact is silently dropped, never shown (REQ-M7-06/07).
426: 
427: ### `narrator_outputs`
428: 
429: | score_run_id | headline | fact_check_passed |
430: |---|---|---|
431: | run-score-1 | "We took 19 hours to reply to a P1 ticket — we promised 4 — and Ana is pulling back at the same time." | true |
432: 
433: `reasons` (JSON, one entry per issue, each pointing at real evidence):
434: 
435: ```json
436: [
437:   { "text": "We took 19 hours to reply. We promised 4. This is the second time this issue has come back.",
438:     "points": 47.87, "evidence_event_ids": ["evt-2"] },
439:   { "text": "Ana stopped greeting us and mentioned briefing the board — and she signs the renewal. Diego has gone quiet for 12 days.",
440:     "points": 19.44, "evidence_event_ids": ["evt-1", "evt-5", "evt-6"] }
441: ]
442: ```
443: 
444: `actions` (JSON — every action has an owner and a date, pulled from the human-written `playbook_actions` table, never invented):
445: 
446: ```json
447: [
448:   { "text": "Escalate ticket #456 with engineering today", "owner": "Support lead", "due_date": "today", "playbook_id": "pb-escalate-p1" },
449:   { "text": "Call Ana before Thursday's board meeting — don't email", "owner": "CS lead", "due_date": "Wed", "playbook_id": "pb-call-sponsor" }
450: ]
451: ```
452: 
453: ### `playbook_actions` (the two templates used above already existed, human-authored, before this run)
454: 
455: | id | template_text | applies_to_finding_type | default_owner_role |
456: |---|---|---|---|
457: | pb-escalate-p1 | "Escalate {ticket_ref} with engineering {when}" | `broken_response_promise` | Support lead |
458: | pb-call-sponsor | "Call {stakeholder_name} before {deadline} — don't email" | `escalation_language` | CS lead |
459: 
460: The narrator filled in the placeholders with real names and dates from this run's data; it did not write these action templates itself.
461: 
462: **What happens next:** everything computed so far — the score, the reasons, the actions — is now sitting in the database, ready to be *read*, not recalculated, by three different screens.
463: 
464: ---
465: 
466: ## 11. Step 9 — The dashboard shows it
467: 
468: **Who does this:** Module **M8 · Health dashboard** (`requirements/08-health-dashboard.md`). This step writes **no new table** — it is a pure read of everything produced above. That's the point: the dashboard loads in under a second because it never computes anything, it only displays `score_runs`, `narrator_outputs`, and `rollups` as they already sit in the database.
469: 
470: What the CS lead sees, matching `base/mockup-mainPage.jpg`'s layout:
471: 
472: - **Score block:** 85 · **At risk** · animates up from last week's number.
473: - **Contribution bars:** "Broken response promise +39", "Recurring issue +4.9", "Usage down +4.0", "Escalation language +9.5", "Diego's absence +5.1", "Ana's tone +2.8", "CSAT drop +1.7", "Diego stepping back +0.3", and in green, "Ticket #398 resolved fast −4.0."
474: - **Pulse timeline:** the six events from Step 3, each with its quoted text and a severity dot.
475: - **Stakeholder cards:** Ana (tone trajectory: deteriorating), Diego (status: quiet, last seen 12 days ago).
476: - **Coverage line:** "Reading 5 of 5 sources · complete to 10:16" — because `coverage_reports` (Step 5.4) says so.
477: 
478: Every number here is a clickable door back to Step 7's `score_contributions`, and from there to Step 3's `events` — the full evidence trace, in two clicks, exactly as required by `requirements/08-health-dashboard.md` REQ-M8-08.
479: 
480: ---
481: 
482: ## 12. Step 10 — Someone asks a question
483: 
484: **Who does this:** Module **M9 · Ask agent** (`requirements/09-ask-agent.md`). The CS lead types: *"Why did the score go up?"*
485: 
486: The agent does **not** recompute anything — it matches the question to one of a small, fixed set of known question types, then looks up already-stored data to answer it.
487: 
488: ### `ask_queries`
489: 
490: | question_text | matched_intent | rendered_component | response_time_ms |
491: |---|---|---|---|
492: | "Why did the score go up?" | `score_delta` | Delta breakdown (per-cause points, from `score_contributions`) | 1,840 |
493: 
494: The answer shown is literally Step 9.5's arithmetic, re-rendered as a component — not a new calculation, and not a new model call.
495: 
496: ---
497: 
498: ## 13. Step 11 — Drafting a reply (and stopping there)
499: 
500: **Who does this:** Module **M10 · Draft composer** (`requirements/10-draft-composer.md`). The CS lead clicks "Write to Ana about this." The composer reads Issue A's evidence, Ana's communication style from the client profile (direct, brief), and writes:
501: 
502: ### `draft_messages`
503: 
504: | id | issue_id | stakeholder_id | draft_text (excerpt) | tone_variant | checks_passed | logged_manually_at | copied_at |
505: |---|---|---|---|---|---|---|---|
506: | draft-1 | iss-A | stk-ana | *"Ana — we took 19 hours to respond to ticket #456; we promised 4. Engineering is on it today, and I'll call you before Thursday."* | direct | true | *(null)* | *(null)* |
507: 
508: The CS lead reads it, likes it, and clicks **"Copy draft"** — `copied_at` gets a timestamp. That is the *only* thing that happens inside this system. **There is no send button** — not hidden, not disabled, structurally absent (`requirements/10-draft-composer.md` REQ-M10-P1). Look again at the table above: there is no `sent_at` column to fill in, even if someone wanted to. The CS lead pastes the text into their own email client and sends it themselves — a human, always, per product principle P4.
509: 
510: If they'd instead clicked **"Log as sent (manual),"** `logged_manually_at` would be stamped — that's a flag in this table only, so the dashboard knows the draft was acted on. It writes nothing to the CRM or anywhere else outside this system; that boundary is what keeps `requirements/11-non-functional-requirements.md` REQ-NFR-18 ("never request write access to a source system") true without exception.
511: 
512: ---
513: 
514: ## 14. Step 12 — A week later: feedback changes the future, not the past
515: 
516: **Who does this:** Module **M4 · Feedback memory** (`requirements/04-feedback-memory.md`). It turns out `fnd-5` (Diego "stepping back" from the channel) was a false alarm — Diego was on pre-announced parental leave the whole time, something the CS lead happened to know. They open that card and click **false alarm**.
517: 
518: ### `feedback_verdicts` — one new row, this is all that happens right now
519: 
520: | finding_id | verdict | submitted_by | pattern_signature |
521: |---|---|---|---|
522: | fnd-5 | `false_alarm` | cs.lead@vendor.com | relationship+relationship_change |
523: 
524: ### `damping_weights` — the pattern's future weight drops
525: 
526: | pattern_signature | weight | false_alarm_count | disclosure_text |
527: |---|---|---|---|
528: | relationship+relationship_change | **0.500** | 1 | "weight reduced — your team flagged this pattern as a false alarm" |
529: 
530: **Nothing about last week's score of 85.30 changes.** `score_runs` row `run-score-1` is untouched — history is never rewritten (`requirements/06-scoring-engine.md` REQ-M6-20: the previous score is never an input to anything). But the *next* time this pattern shows up — say, another `relationship_change` finding about someone going quiet — `damping` in its `score_contributions` row will be **0.500** instead of **1.000**, cutting that finding's contribution in half, and the card will visibly say why. This is what "learning the user can read" means in practice: one new number in one table, fully explained, no retraining, no black box.
531: 
532: ```mermaid
533: flowchart LR
534:     Click["CS lead clicks\nfalse alarm"] --> FV[("feedback_verdicts\n+1 row")]
535:     FV --> DW[("damping_weights\nweight: 1.000 to 0.500")]
536:     DW -.->|"read on next matching finding"| Next["Next week's score_contributions\nfor this pattern"]
537: ```
538: 
539: ---
540: 
541: ## 15. Quick reference — every table, its step, and its process
542: 
543: | Table | Populated in step | By which process | Trigger |
544: |---|---|---|---|
545: | `sources` | *(setup, once)* | Onboarding | Deployment created |
546: | `collector_runs` | 4.2 | M1 · Collectors | Webhook / scheduled poll |
547: | `identity_map` | 4.3 | M1 · Identity resolution | Every new sender seen |
548: | `raw_envelopes` | 4.4 | M1 · Collectors | Every fetched item |
549: | `events` | 5.1 | M2 · Event ledger | Every accepted envelope |
550: | `event_threads` | *(not used this example)* | M2 · Thread stitching | Cross-channel message linking |
551: | `response_pairs` | 5.2 | M2 · Ledger projection | A ticket/message awaiting or receiving reply |
552: | `rollups` | 5.3 | M2 · Ledger projection | Any new event in a tracked window |
553: | `coverage_reports` | 5.4 | M1 · Collectors | End of every collector run |
554: | `finding_type_config` | *(setup, once)* | Product configuration | Weight tuning workshop |
555: | `findings` | 6 | M5 · Readers | New/changed events in their window |
556: | `quarantine` | 7 | M5a · Validation gate | A finding fails any of 4 checks |
557: | `validation_failures` | 7 | M5a · Validation gate | Same as above, one row per failed check |
558: | `issues` | 8 | M6 · Clustering | Validated findings share a root cause |
559: | `finding_issue_map` | 8 | M6 · Clustering | Same as above |
560: | `score_runs` | 9.5 | M6 · Scoring engine | New event, burst batch, urgent phrase, hourly heartbeat, or profile/weight edit |
561: | `score_contributions` | 9.5 | M6 · Scoring engine | Every scoring run, one row per finding |
562: | `band_history` | 9.5 | M6 · Scoring engine | Every scoring run |
563: | `narrator_outputs` | 10 | M7 · Narrator | Every scoring run |
564: | `playbook_actions` | *(setup, once)* | Human authoring | Playbook sign-off |
565: | `ask_queries` | 12 | M9 · Ask agent | Every question asked |
566: | `draft_messages` | 13 | M10 · Draft composer | "Write to X" request |
567: | `feedback_verdicts` | 14 | M4 · Feedback memory | A verdict click |
568: | `damping_weights` | 14 | M4 · Feedback memory | Recomputed after each verdict |
569: | `notifications` | *(not used this example)* | M8 · Dashboard | Band change or daily digest |
570: 
571: ---
572: 
573: ## 16. What this example proves
574: 
575: - **Five sources, zero coordination, one coherent story.** No single system (Zendesk, Gmail, Slack, the warehouse, the CSAT tool) had enough information on its own to justify an escalation. The pattern only exists *across* them — which is exactly the gap described in spec §2.2: "nobody is assigned to notice the shape of them together."
576: - **Every number traces to a receipt.** From 85.30 on the dashboard, back through `score_contributions`, back through `findings.cited_event_ids`, back to the literal email and ticket rows in `events` — at no point does a number exist without a path back to real data.
577: - **Abstention and rejection are normal, not failures.** The Meeting reader said nothing (no material). The Tone reader's second attempt was caught and quarantined (not enough history). Neither broke the run — the other nine findings scored just fine.
578: - **Feedback changes tomorrow, never yesterday.** Marking one finding a false alarm updated exactly one row in one table (`damping_weights`) and left every historical score exactly as it was computed.

(End of file - total 578 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 4.3s)

_Thinking:_

Now let me explore the ingestion adapters to understand how collectors are implemented and how events get into the system.

Excelente. Ahora exploraré los adapters de ingestion y los scripts demo para entender cómo se añaden eventos.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/adapters"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/adapters</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
encryption.py
key_store.py
simulated_collector.py
sqlalchemy_repositories.py

(6 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/application"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/application</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
collector.py
ports.py
use_cases.py

(5 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/domain"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/domain</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
business_hours.py
envelope.py
hash_chain.py
retention.py
thread_stitching.py

(7 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts</path>
<type>directory</type>
<entries>
__pycache__/
compute_score.py
confirm_baseline.py
run_collector.py
run_narrator.py
run_readers.py
seed_score_fixture.py
seed.py

(8 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo</path>
<type>directory</type>
<entries>
01-live-demo-runbook.md
02-impact-story.md
03-environment-and-fixtures-checklist.md
client-profile.yaml
fixtures/

(5 entries)
</entries>
```

---

## Assistant (Plan · GLM-5.2 · 1.9s)

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/adapters/simulated_collector.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/adapters/simulated_collector.py</path>
<type>file</type>
<content>
1: """`SimulatedCollector` (FR-009) — the one concrete `Collector` this feature ships,
2: reading a committed fixture file instead of a live source API. Stands in for a real
3: Gmail/Zendesk/warehouse adapter, proving the same interface end to end
4: (demo/03-environment-and-fixtures-checklist.md's documented approach).
5: """
6: 
7: import json
8: from datetime import datetime
9: from pathlib import Path
10: from typing import Any
11: 
12: from app.ingestion.application.collector import Collector
13: from app.ingestion.domain.envelope import Envelope
14: 
15: _SOURCE_DISPLAY_NAMES = {
16:     "gmail": "Meridian — Email",
17:     "zendesk": "Meridian — Support",
18:     "warehouse": "Meridian — Product usage",
19:     "slack": "Meridian — Chat",
20:     "csat": "Meridian — CSAT/NPS",
21:     "transcripts": "Meridian — Calendar/transcripts",
22: }
23: 
24: 
25: def _normalize_gmail(item: dict[str, Any]) -> Envelope:
26:     return Envelope(
27:         source_type="gmail",
28:         source_native_id=item["source_native_id"],
29:         occurred_at=datetime.fromisoformat(item["occurred_at"]),
30:         identity_status="unresolved",  # resolved later, by RunCollectorUseCase
31:         resolved_stakeholder_id=None,
32:         redacted_fields=[],
33:         payload_text=item["text"],
34:         structured_payload={"participant": item["from"]},
35:     )
36: 
37: 
38: def _normalize_zendesk(item: dict[str, Any]) -> Envelope:
39:     return Envelope(
40:         source_type="zendesk",
41:         source_native_id=item["source_native_id"],
42:         occurred_at=datetime.fromisoformat(item["occurred_at"]),
43:         identity_status="unresolved",
44:         resolved_stakeholder_id=None,
45:         redacted_fields=[],
46:         payload_text=item["title"],
47:         structured_payload={
48:             "participant": item["reporter"],
49:             "ticket_number": item["ticket_number"],
50:             "title": item["title"],
51:             "state": item["state"],
52:             "product_area": item.get("product_area"),
53:         },
54:     )
55: 
56: 
57: def _normalize_warehouse(item: dict[str, Any]) -> Envelope:
58:     return Envelope(
59:         source_type="warehouse",
60:         source_native_id=item["source_native_id"],
61:         occurred_at=datetime.fromisoformat(item["occurred_at"]),
62:         identity_status="unresolved",
63:         resolved_stakeholder_id=None,
64:         redacted_fields=[],
65:         payload_text=f"{item['metric']} {item['value_delta_pct']:+d}%",
66:         structured_payload={
67:             "metric": item["metric"],
68:             "product_area": item.get("product_area"),
69:             "value_delta_pct": item["value_delta_pct"],
70:         },
71:     )
72: 
73: 
74: def _normalize_slack(item: dict[str, Any]) -> Envelope:
75:     # `_event_type_for_source` has no "slack" branch — Slack messages fall
76:     # through to its "message" default, the same event_type Gmail already
77:     # produces, so Absence/Relationship (and, incidentally, Tone/Intent) pick
78:     # up Slack activity via the exact same source-agnostic `events` queries
79:     # they already run for email (FR-021, confirmed during implementation to
80:     # need zero reader-code changes — see research.md Decision 5).
81:     return Envelope(
82:         source_type="slack",
83:         source_native_id=item["source_native_id"],
84:         occurred_at=datetime.fromisoformat(item["occurred_at"]),
85:         identity_status="unresolved",
86:         resolved_stakeholder_id=None,
87:         redacted_fields=[],
88:         payload_text=item["text"],
89:         structured_payload={"participant": item["from"]},
90:     )
91: 
92: 
93: def _normalize_csat(item: dict[str, Any]) -> Envelope:
94:     # The written comment (if any) is the only sensitive text here — it goes
95:     # through the same encrypted `payload_text` path every other source's
96:     # body uses. The numeric score is not sensitive and lives in
97:     # `structured_payload` (plaintext JSONB) alongside `has_comment`, a
98:     # boolean marker `SqlAlchemyMessageEventRepository` uses to decide
99:     # whether a survey_response row is worth decrypting as a Tone candidate,
100:     # without ever needing to decrypt score-only responses just to check.
101:     comment = item.get("comment")
102:     return Envelope(
103:         source_type="csat",
104:         source_native_id=item["source_native_id"],
105:         occurred_at=datetime.fromisoformat(item["occurred_at"]),
106:         identity_status="unresolved",
107:         resolved_stakeholder_id=None,
108:         redacted_fields=[],
109:         payload_text=comment if comment else f"CSAT score: {item['score']}",
110:         structured_payload={
111:             "participant": item["respondent"],
112:             "score": item["score"],
113:             "has_comment": bool(comment),
114:         },
115:     )
116: 
117: 
118: def _normalize_calendar(item: dict[str, Any]) -> Envelope:
119:     # `source_type="transcripts"` (the enum value), not the fixture's own
120:     # `"calendar"` dispatch key — `sources.source_type` is looked up as a
121:     # singleton per value (`get_or_create_source`), and `"calendar"` is
122:     # already claimed by `DetectAbsenceUseCase.ABSENCE_SOURCE_TYPE` for its
123:     # internally-generated absence events. `source_type` (data-base/10-ddl-
124:     # appendix.md's enum) deliberately carries both `calendar` and
125:     # `transcripts` as distinct values for exactly this reason.
126:     return Envelope(
127:         source_type="transcripts",
128:         source_native_id=item["source_native_id"],
129:         occurred_at=datetime.fromisoformat(item["occurred_at"]),
130:         identity_status="unresolved",
131:         resolved_stakeholder_id=None,
132:         redacted_fields=[],
133:         payload_text=item["transcript"],
134:         structured_payload={
135:             "participant": item["attendee"],
136:             "series_id": item["series_id"],
137:             "consent_documented": item["consent_documented"],
138:         },
139:     )
140: 
141: 
142: _NORMALIZERS = {
143:     "gmail": _normalize_gmail,
144:     "zendesk": _normalize_zendesk,
145:     "warehouse": _normalize_warehouse,
146:     "slack": _normalize_slack,
147:     "csat": _normalize_csat,
148:     "calendar": _normalize_calendar,
149: }
150: 
151: 
152: class SimulatedCollector(Collector):
153:     source_type = "simulated"
154: 
155:     def __init__(self, fixture_path: Path) -> None:
156:         self._fixture_path = fixture_path
157: 
158:     async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
159:         items: list[dict[str, Any]] = json.loads(self._fixture_path.read_text())
160:         # FR-023: "THE SYSTEM SHALL NEVER collect a transcript for a series
161:         # lacking [documented, all-party] consent" — stronger than "the
162:         # Meeting reader abstains on it" (confirmed against
163:         # tests/ingestion/test_post_mvp_sources_real_db.py's own assertion of
164:         # zero `raw_envelopes` rows for a non-consented series): a
165:         # non-consented calendar item is dropped here, before normalize()
166:         # ever builds an Envelope for it, so it never reaches insert_envelope
167:         # at all — not merely a MeetingReader-side abstention.
168:         items = [
169:             item
170:             for item in items
171:             if item["source_type"] != "calendar" or item.get("consent_documented") is True
172:         ]
173:         # Chronological order is a hard requirement of the hash chain (see
174:         # EventRepositoryPort.append's docstring) — the fixture's own array order
175:         # deliberately isn't sorted (item 2 occurs before item 1), to prove this sort
176:         # is load-bearing rather than an accident of fixture authoring.
177:         return sorted(items, key=lambda item: item["occurred_at"])
178: 
179:     def normalize(self, raw_item: dict[str, Any]) -> Envelope:
180:         return _NORMALIZERS[raw_item["source_type"]](raw_item)
181: 
182:     @staticmethod
183:     def display_name(source_type: str) -> str:
184:         return _SOURCE_DISPLAY_NAMES.get(source_type, source_type)

(End of file - total 184 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/application/collector.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/application/collector.py</path>
<type>file</type>
<content>
1: """The `Collector` interface (REQ-M1-01) — Template Method: every source-specific
2: adapter (real or simulated) implements `fetch`/`normalize`/`resolve_identity`, and
3: shares the same `run()` orchestration a concrete `RunCollectorUseCase` drives.
4: `architecture/09-clean-architecture-and-patterns.md`'s pattern catalog entry.
5: """
6: 
7: from abc import ABC, abstractmethod
8: from datetime import datetime
9: from typing import Any
10: 
11: from app.ingestion.domain.envelope import Envelope
12: 
13: 
14: class Collector(ABC):
15:     source_type: str
16: 
17:     @abstractmethod
18:     async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
19:         """Raw items from the source, in `occurred_at` order — callers append to the
20:         ledger in the order `fetch()` yields, and the hash chain requires that order to
21:         be chronological (EventRepositoryPort.append's docstring)."""
22:         ...
23: 
24:     @abstractmethod
25:     def normalize(self, raw_item: dict[str, Any]) -> Envelope:
26:         """Raw item -> the standard `Envelope` shape (REQ-M1-10) — before identity
27:         resolution, which `RunCollectorUseCase` performs separately (it needs the
28:         current client profile, which a normalizer has no business depending on:
29:         REQ-M1-P3)."""
30:         ...

(End of file - total 30 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 2.3s)

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/run_collector.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/run_collector.py</path>
<type>file</type>
<content>
1: """Manual `SimulatedCollector` trigger (research.md's Decision: `SimulatedCollector`
2: triggered by a script, not a route or a timer) — mirrors `scripts/seed.py`'s pattern.
3: 
4: Run after ``alembic upgrade head`` and ``scripts/seed.py``:
5:     uv run python scripts/run_collector.py --source simulated
6: """
7: 
8: import argparse
9: import asyncio
10: import sys
11: from datetime import UTC, datetime
12: from pathlib import Path
13: 
14: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
15: 
16: from app.config import settings  # noqa: E402
17: from app.db import async_session_factory  # noqa: E402
18: from app.ingestion.adapters.encryption import BucketedFernetEncryption  # noqa: E402
19: from app.ingestion.adapters.key_store import FileKeyStore  # noqa: E402
20: from app.ingestion.adapters.simulated_collector import SimulatedCollector  # noqa: E402
21: from app.ingestion.adapters.sqlalchemy_repositories import (  # noqa: E402
22:     SqlAlchemyClientProfileContext,
23:     SqlAlchemyCollectorRunRepository,
24:     SqlAlchemyEventRepository,
25: )
26: from app.ingestion.application.use_cases import ReplayUseCase, RunCollectorUseCase  # noqa: E402
27: from app.observability.adapters.tracing import traced  # noqa: E402
28: 
29: 
30: async def run(source: str) -> None:
31:     if source != "simulated":
32:         raise SystemExit(f"Unknown --source {source!r} — only 'simulated' exists in this feature")
33: 
34:     key_store = FileKeyStore(settings.data_keys_dir)
35:     encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
36:     async with async_session_factory() as session:
37:         use_case = RunCollectorUseCase(
38:             collector_runs=SqlAlchemyCollectorRunRepository(session),
39:             events=SqlAlchemyEventRepository(session),
40:             profile_context=SqlAlchemyClientProfileContext(session),
41:             encryption=encryption,
42:             key_store=key_store,
43:         )
44:         collector = SimulatedCollector(Path(settings.collector_fixture_path))
45:         window_end = datetime.now(UTC)
46:         with traced("collector_run"):
47:             result = await use_case.execute(
48:                 collector, window_start=window_end, window_end=window_end
49:             )
50:         print(
51:             f"envelopes_emitted={result.envelopes_emitted} "
52:             f"duplicates_skipped={result.duplicates_skipped} "
53:             f"coverage_report_id={result.coverage_report_id}"
54:         )
55: 
56:         replay = ReplayUseCase(
57:             events=SqlAlchemyEventRepository(session),
58:             profile_context=SqlAlchemyClientProfileContext(session),
59:             encryption=encryption,
60:         )
61:         replay_run_id = await replay.execute(trigger="manual")
62:         print(f"replay_run_id={replay_run_id}")
63: 
64: 
65: if __name__ == "__main__":
66:     parser = argparse.ArgumentParser()
67:     parser.add_argument("--source", default="simulated")
68:     args = parser.parse_args()
69:     asyncio.run(run(args.source))

(End of file - total 69 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/seed.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/seed.py</path>
<type>file</type>
<content>
1: """Applies data-base/11-seed-data.sql — kept separate from the schema migration
2: (decisions/02-repo-and-tooling.md §ORM and migrations, FR-003).
3: 
4: Run after ``alembic upgrade head``:
5:     uv run python scripts/seed.py
6: """
7: 
8: import asyncio
9: import sys
10: from pathlib import Path
11: 
12: # Allows `uv run python scripts/seed.py` to find the `app` package regardless of
13: # invocation style (Python adds the script's own directory to sys.path, not backend/).
14: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
15: 
16: import asyncpg  # noqa: E402
17: 
18: from app.config import settings  # noqa: E402
19: 
20: SEED_FILE = Path(__file__).resolve().parents[2] / "data-base" / "11-seed-data.sql"
21: 
22: 
23: async def seed() -> None:
24:     dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
25:     sql = SEED_FILE.read_text()
26:     connection = await asyncpg.connect(dsn)
27:     try:
28:         # No bind parameters, so asyncpg's simple query protocol runs the whole
29:         # multi-statement script (BEGIN ... COMMIT) in one call — unlike SQLAlchemy's
30:         # asyncpg dialect (see migrations/versions/0001_initial_schema.py's docstring),
31:         # a parameterless asyncpg.Connection.execute() is not restricted to one command.
32:         await connection.execute(sql)
33:     finally:
34:         await connection.close()
35:     print(f"Seeded from {SEED_FILE}")
36: 
37: 
38: if __name__ == "__main__":
39:     asyncio.run(seed())

(End of file - total 39 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/fixtures"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/fixtures</path>
<type>directory</type>
<entries>
meridian-week-phase1-only.json
meridian-week.json
score-engine-findings.json

(3 entries)
</entries>
```

---

## Assistant (Plan · GLM-5.2 · 1.9s)

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/fixtures/meridian-week.json"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/fixtures/meridian-week.json</path>
<type>file</type>
<content>
1: [
2:   {
3:     "source_type": "gmail",
4:     "source_native_id": "gmail-msg-8831",
5:     "occurred_at": "2026-08-10T09:14:00-05:00",
6:     "from": "ana.reyes@meridian.com",
7:     "text": "Please advise on the timeline. I need to brief the board on Thursday."
8:   },
9:   {
10:     "source_type": "gmail",
11:     "source_native_id": "gmail-msg-8790",
12:     "occurred_at": "2026-07-01T10:00:00-05:00",
13:     "from": "diego@meridian.com",
14:     "text": "Looping in on the tracking_api integration questions from our side."
15:   },
16:   {
17:     "source_type": "zendesk",
18:     "source_native_id": "zendesk-456-created",
19:     "occurred_at": "2026-08-06T09:15:00-05:00",
20:     "reporter": "support-desk@meridian.zendesk.com",
21:     "ticket_number": 456,
22:     "title": "Slow API response",
23:     "product_area": "tracking_api",
24:     "state": "created"
25:   },
26:   {
27:     "source_type": "zendesk",
28:     "source_native_id": "zendesk-456-reopened",
29:     "occurred_at": "2026-08-10T07:40:00-05:00",
30:     "reporter": "support-desk@meridian.zendesk.com",
31:     "ticket_number": 456,
32:     "title": "Slow API response",
33:     "reopen_count": 2,
34:     "product_area": "tracking_api",
35:     "state": "reopened"
36:   },
37:   {
38:     "source_type": "zendesk",
39:     "source_native_id": "zendesk-398-created",
40:     "occurred_at": "2026-08-11T11:02:00-05:00",
41:     "reporter": "support-desk@meridian.zendesk.com",
42:     "ticket_number": 398,
43:     "title": "Add CSV export",
44:     "product_area": "reporting",
45:     "state": "created"
46:   },
47:   {
48:     "source_type": "zendesk",
49:     "source_native_id": "zendesk-398-resolved",
50:     "occurred_at": "2026-08-11T13:02:00-05:00",
51:     "reporter": "support-desk@meridian.zendesk.com",
52:     "ticket_number": 398,
53:     "title": "Add CSV export",
54:     "product_area": "reporting",
55:     "state": "resolved"
56:   },
57:   {
58:     "source_type": "zendesk",
59:     "source_native_id": "zendesk-512-created",
60:     "occurred_at": "2026-08-12T15:20:00-05:00",
61:     "reporter": "support-desk@meridian.zendesk.com",
62:     "ticket_number": 512,
63:     "title": "Login page displays wrong company logo",
64:     "product_area": "reporting",
65:     "state": "created"
66:   },
67:   {
68:     "source_type": "warehouse",
69:     "source_native_id": "usage-tracking_api-w29",
70:     "occurred_at": "2026-07-08T00:00:00-05:00",
71:     "metric": "weekly_active_usage",
72:     "product_area": "tracking_api",
73:     "value_delta_pct": -2
74:   },
75:   {
76:     "source_type": "warehouse",
77:     "source_native_id": "usage-tracking_api-w30",
78:     "occurred_at": "2026-07-15T00:00:00-05:00",
79:     "metric": "weekly_active_usage",
80:     "product_area": "tracking_api",
81:     "value_delta_pct": 1
82:   },
83:   {
84:     "source_type": "warehouse",
85:     "source_native_id": "usage-tracking_api-w31",
86:     "occurred_at": "2026-07-22T00:00:00-05:00",
87:     "metric": "weekly_active_usage",
88:     "product_area": "tracking_api",
89:     "value_delta_pct": -3
90:   },
91:   {
92:     "source_type": "warehouse",
93:     "source_native_id": "usage-tracking_api-w32",
94:     "occurred_at": "2026-07-29T00:00:00-05:00",
95:     "metric": "weekly_active_usage",
96:     "product_area": "tracking_api",
97:     "value_delta_pct": 2
98:   },
99:   {
100:     "source_type": "warehouse",
101:     "source_native_id": "usage-tracking_api-w33",
102:     "occurred_at": "2026-08-05T00:00:00-05:00",
103:     "metric": "weekly_active_usage",
104:     "product_area": "tracking_api",
105:     "value_delta_pct": -1
106:   },
107:   {
108:     "source_type": "warehouse",
109:     "source_native_id": "usage-tracking_api-w34",
110:     "occurred_at": "2026-08-12T00:00:00-05:00",
111:     "metric": "weekly_active_usage",
112:     "product_area": "tracking_api",
113:     "value_delta_pct": -22
114:   },
115:   {
116:     "source_type": "gmail",
117:     "source_native_id": "gmail-msg-8845",
118:     "occurred_at": "2026-08-13T14:30:00-05:00",
119:     "from": "ana.reyes@meridian.com",
120:     "text": "Separately — I'm forwarding the contract dispute thread to our legal team, please hold off on that topic until they weigh in."
121:   },
122:   {
123:     "source_type": "slack",
124:     "source_native_id": "slack-msg-4471",
125:     "occurred_at": "2026-08-07T16:05:00-05:00",
126:     "from": "diego@meridian.com",
127:     "text": "quick one in here — anyone seen the reporting export job fail overnight?"
128:   },
129:   {
130:     "source_type": "slack",
131:     "source_native_id": "slack-msg-4502",
132:     "occurred_at": "2026-08-12T09:20:00-05:00",
133:     "from": "ana.reyes@meridian.com",
134:     "text": "thanks for the quick turnaround on ticket 398, team noticed"
135:   },
136:   {
137:     "source_type": "csat",
138:     "source_native_id": "csat-resp-2201",
139:     "occurred_at": "2026-08-09T12:00:00-05:00",
140:     "respondent": "ana.reyes@meridian.com",
141:     "score": 6,
142:     "comment": "Support has been slower to resolve things lately, and the reopened ticket didn't help."
143:   },
144:   {
145:     "source_type": "csat",
146:     "source_native_id": "csat-resp-2214",
147:     "occurred_at": "2026-08-12T12:00:00-05:00",
148:     "respondent": "diego@meridian.com",
149:     "score": 9
150:   },
151:   {
152:     "source_type": "calendar",
153:     "source_native_id": "calendar-series-qbr-2026w32",
154:     "occurred_at": "2026-08-11T15:00:00-05:00",
155:     "attendee": "ana.reyes@meridian.com",
156:     "series_id": "meridian-qbr",
157:     "consent_documented": true,
158:     "transcript": "Ana: We need the CSV export fix live before the board review. Diego: Understood — engineering will ship the reporting CSV export by next Friday."
159:   },
160:   {
161:     "source_type": "calendar",
162:     "source_native_id": "calendar-series-standup-2026w32",
163:     "occurred_at": "2026-08-11T09:00:00-05:00",
164:     "attendee": "diego@meridian.com",
165:     "series_id": "meridian-standup",
166:     "consent_documented": false,
167:     "transcript": "Diego: internal standup notes, no client consent on record for this recurring series."
168:   }
169: ]

(End of file - total 169 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/client-profile.yaml"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/client-profile.yaml</path>
<type>file</type>
<content>
1: # The CS lead edits this file directly (decisions/00-open-questions-resolved.md Q2) —
2: # POST /api/profile/reload re-reads it and creates a new client_profile_versions row.
3: # Mirrors data-base/11-seed-data.sql's seeded Meridian profile (spec §6.2's format).
4: client: Meridian Logistics
5: renewal_date: 2026-11-08
6: contract_value_band: strategic
7: 
8: business_goals:
9:   - reduce delivery disputes by 30% this year
10: 
11: stakeholders:
12:   - id: stk_ana
13:     name: Ana Reyes
14:     role: CTO
15:     influence: sponsor
16:     signs_renewal: true
17:     identifiers: [ana.reyes@meridian.com]
18:   - id: stk_diego
19:     name: Diego Marín
20:     role: Dev lead
21:     influence: daily_user
22:     identifiers: [diego@meridian.com]
23: 
24: product_areas:
25:   - key: tracking_api
26:     criticality: critical
27:   - key: reporting
28:     criticality: standard
29: 
30: commitments:
31:   - type: first_response
32:     priority: P1
33:     threshold_business_hours: 4
34:   - type: recurring_sync
35:     cadence: weekly
36: 
37: communication:
38:   working_hours: 08:00-18:00
39:   timezone: America/Bogota
40:   languages: [es, en]
41:   norms: >
42:     Direct communicators. Brevity is habitual, not hostile.
43:     Formality rises when senior people are present.
44: 
45: exclusions:
46:   - legal_threads
47:   - commercial_negotiation
48: 
49: history:
50:   - date: 2026-03-02
51:     event: major outage on tracking_api, improvement plan agreed with Ana

(End of file - total 51 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 2.5s)

_Thinking:_

Now I have a great understanding. Let me look at a few more important files to understand the complete picture, including the use_cases and how the demo runs.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/application/use_cases.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/ingestion/application/use_cases.py</path>
<type>file</type>
<content>
1: """Ingestion application use cases: AppendEventUseCase, response-pair/event-thread
2: computation, ReplayUseCase (T020-T022); identity resolution, redaction,
3: RunCollectorUseCase (T031-T033, T035); DetectAbsenceUseCase (T040);
4: RunRetentionUseCase (specs/011-production-hardening, FR-001). One file — tasks.md
5: groups these together since they share ports.py/sqlalchemy_repositories.py and
6: read as one coherent "what happens to a signal after it's collected" pipeline.
7: """
8: 
9: import logging
10: from collections.abc import Callable
11: from dataclasses import dataclass
12: from datetime import UTC, datetime, timedelta
13: from uuid import UUID
14: 
15: from app.ingestion.application.collector import Collector
16: from app.ingestion.application.ports import (
17:     ClientProfileContext,
18:     ClientProfileContextPort,
19:     CollectorRunRepositoryPort,
20:     CommitmentLookupPort,
21:     EncryptionPort,
22:     EventRecord,
23:     EventRepositoryPort,
24:     EventThreadRow,
25:     KeyStorePort,
26:     NewEvent,
27:     ResponsePairRow,
28:     RetentionJobRepositoryPort,
29:     RetentionJobRunResult,
30:     RollupRow,
31: )
32: from app.ingestion.domain.business_hours import WorkingCalendar, compute_business_hours_elapsed
33: from app.ingestion.domain.envelope import Envelope
34: from app.ingestion.domain.retention import is_bucket_expired
35: from app.ingestion.domain.thread_stitching import (
36:     ANCHOR_CONFIDENCE,
37:     TICKET_REFERENCE_CONFIDENCE,
38:     find_ticket_references,
39:     thread_key_for_ticket,
40: )
41: 
42: logger = logging.getLogger(__name__)
43: 
44: # ---------------------------------------------------------------------------
45: # T020 — append
46: # ---------------------------------------------------------------------------
47: 
48: 
49: class AppendEventUseCase:
50:     """Builds an event's canonical fields and appends it (REQ-M2-01, REQ-M2-02,
51:     REQ-M2-03 for `supersedes_event_id`)."""
52: 
53:     def __init__(self, events: EventRepositoryPort, key_store: KeyStorePort) -> None:
54:         self._events = events
55:         self._key_store = key_store
56: 
57:     async def execute(self, event: NewEvent) -> UUID:
58:         data_key_ref = self._key_store.current_bucket_id()
59:         return await self._events.append(event, data_key_ref=data_key_ref)
60: 
61: 
62: # ---------------------------------------------------------------------------
63: # T021 / T024 — response-pair + thread-stitching computation (shared by ReplayUseCase
64: # and, indirectly, by RunCollectorUseCase, which triggers a replay after collection)
65: # ---------------------------------------------------------------------------
66: 
67: 
68: def _rebuild_projections(
69:     events: list[EventRecord],
70:     *,
71:     calendar: WorkingCalendar,
72:     commitment_id: UUID | None,
73:     threshold_business_hours: float | None,
74:     profile_version_id: UUID,
75:     as_of: datetime,
76:     decrypt: Callable[[bytes], str],
77: ) -> tuple[list[EventThreadRow], list[ResponsePairRow]]:
78:     threads: list[EventThreadRow] = []
79:     pairs: list[ResponsePairRow] = []
80: 
81:     open_pairs: dict[int, tuple[UUID, datetime]] = {}
82:     ticket_threads: dict[int, str] = {}
83: 
84:     for record in events:
85:         if record.event_type == "ticket_state_change":
86:             ticket_number = record.structured_payload.get("ticket_number")
87:             state = record.structured_payload.get("state")
88:             if ticket_number is None:
89:                 continue
90:             thread_key = thread_key_for_ticket(ticket_number)
91:             ticket_threads[ticket_number] = thread_key
92:             threads.append(
93:                 EventThreadRow(
94:                     thread_key=thread_key,
95:                     event_id=record.id,
96:                     stitch_confidence=ANCHOR_CONFIDENCE,
97:                     stitch_method="ticket_reference",
98:                 )
99:             )
100:             if state in ("created", "reopened"):
101:                 open_pairs[ticket_number] = (record.id, record.occurred_at)
102:             elif state == "resolved" and ticket_number in open_pairs:
103:                 client_event_id, client_occurred_at = open_pairs.pop(ticket_number)
104:                 elapsed = compute_business_hours_elapsed(
105:                     client_occurred_at, record.occurred_at, calendar
106:                 )
107:                 pairs.append(
108:                     ResponsePairRow(
109:                         client_event_id=client_event_id,
110:                         reply_event_id=record.id,
111:                         commitment_id=commitment_id,
112:                         business_hours_elapsed=elapsed,
113:                         state="resolved",
114:                         profile_version_id=profile_version_id,
115:                     )
116:                 )
117:         elif record.event_type == "message" and record.body_encrypted is not None:
118:             body_text = decrypt(record.body_encrypted)
119:             for ticket_number in find_ticket_references(body_text):
120:                 if ticket_number in ticket_threads:
121:                     threads.append(
122:                         EventThreadRow(
123:                             thread_key=ticket_threads[ticket_number],
124:                             event_id=record.id,
125:                             stitch_confidence=TICKET_REFERENCE_CONFIDENCE,
126:                             stitch_method="ticket_reference",
127:                         )
128:                     )
129: 
130:     for _ticket_number, (client_event_id, client_occurred_at) in open_pairs.items():
131:         elapsed = compute_business_hours_elapsed(client_occurred_at, as_of, calendar)
132:         state = (
133:             "open_overdue"
134:             if threshold_business_hours is not None and elapsed > threshold_business_hours
135:             else "open"
136:         )
137:         pairs.append(
138:             ResponsePairRow(
139:                 client_event_id=client_event_id,
140:                 reply_event_id=None,
141:                 commitment_id=commitment_id,
142:                 business_hours_elapsed=elapsed,
143:                 state=state,
144:                 profile_version_id=profile_version_id,
145:             )
146:         )
147: 
148:     return threads, pairs
149: 
150: 
151: # ---------------------------------------------------------------------------
152: # T022 — replay
153: # ---------------------------------------------------------------------------
154: 
155: 
156: class ReplayUseCase:
157:     """Truncates `event_threads`/`response_pairs` and rebuilds both from the full
158:     `events` history (REQ-M2-07). Also what makes response_pairs/event_threads correct
159:     after an ordinary collection run (RunCollectorUseCase calls this too, trigger=
160:     "manual") — on this ledger, "replay" and "bring derived state current" are the
161:     same operation, so there's exactly one implementation of each, not two."""
162: 
163:     def __init__(
164:         self,
165:         events: EventRepositoryPort,
166:         profile_context: ClientProfileContextPort,
167:         encryption: EncryptionPort,
168:     ) -> None:
169:         self._events = events
170:         self._profile_context = profile_context
171:         self._encryption = encryption
172: 
173:     async def execute(self, *, trigger: str, as_of: datetime | None = None) -> UUID:
174:         as_of = as_of or datetime.now(UTC)
175:         all_events = await self._events.list_all_ordered()
176:         try:
177:             profile = await self._profile_context.get_current()
178:             threads, pairs = _rebuild_projections(
179:                 all_events,
180:                 calendar=profile.working_calendar,
181:                 commitment_id=(
182:                     profile.first_response_commitment.id
183:                     if profile.first_response_commitment
184:                     else None
185:                 ),
186:                 threshold_business_hours=(
187:                     profile.first_response_commitment.threshold_business_hours
188:                     if profile.first_response_commitment
189:                     else None
190:                 ),
191:                 profile_version_id=profile.profile_version_id,
192:                 as_of=as_of,
193:                 decrypt=self._encryption.decrypt,
194:             )
195:             await self._events.truncate_projections()
196:             await self._events.bulk_rebuild_projections(threads, pairs)
197:         except Exception as exc:
198:             await self._events.record_replay_run(
199:                 trigger=trigger, events_replayed_count=0, status="failed", error=str(exc)
200:             )
201:             raise
202:         return await self._events.record_replay_run(
203:             trigger=trigger,
204:             events_replayed_count=len(all_events),
205:             status="succeeded",
206:             error=None,
207:         )
208: 
209: 
210: # ---------------------------------------------------------------------------
211: # T031/T032 — identity resolution + redaction
212: # ---------------------------------------------------------------------------
213: 
214: # REQ-M1-09's exclusions are topic *labels* (e.g. "legal_threads"), not a per-word
215: # dictionary a human maintains — a small fixed marker-phrase list per topic is enough
216: # to prove the redaction path for real against this feature's fixture, without
217: # building a general text-classification model no reader yet needs (constitution
218: # P10/YAGNI; a real NLP-based exclusion matcher is a documented follow-up).
219: _EXCLUSION_MARKERS: dict[str, tuple[str, ...]] = {
220:     "legal_threads": ("legal team", "legal counsel", "lawsuit", "contract dispute"),
221:     "commercial_negotiation": ("discount", "renewal price", "contract terms", "negotiat"),
222: }
223: 
224: 
225: def redact(payload_text: str, exclusions: tuple[str, ...]) -> tuple[str, list[str]]:
226:     """Strips `payload_text` entirely and records which exclusion(s) matched, if any
227:     marker phrase for an excluded topic appears (REQ-M1-09)."""
228:     text_lower = payload_text.lower()
229:     matched = [
230:         exclusion
231:         for exclusion in exclusions
232:         if any(marker in text_lower for marker in _EXCLUSION_MARKERS.get(exclusion, ()))
233:     ]
234:     if matched:
235:         return "[REDACTED]", matched
236:     return payload_text, matched
237: 
238: 
239: def _match_product_area(envelope: Envelope, profile: ClientProfileContext) -> UUID | None:
240:     key = envelope.structured_payload.get("product_area")
241:     if key is None:
242:         return None
243:     for area in profile.product_areas:
244:         if area.key == key:
245:             return area.id
246:     return None
247: 
248: 
249: def _event_type_for_source(source_type: str) -> str:
250:     if source_type == "zendesk":
251:         return "ticket_state_change"
252:     if source_type == "warehouse":
253:         return "usage_measurement"
254:     if source_type == "csat":
255:         return "survey_response"
256:     if source_type == "transcripts":
257:         return "meeting"
258:     return "message"  # gmail, slack
259: 
260: 
261: # ---------------------------------------------------------------------------
262: # T033/T035 — RunCollectorUseCase
263: # ---------------------------------------------------------------------------
264: 
265: 
266: @dataclass(frozen=True)
267: class CollectorRunResult:
268:     envelopes_emitted: int
269:     duplicates_skipped: int
270:     coverage_report_id: UUID
271: 
272: 
273: class RunCollectorUseCase:
274:     """Orchestrates fetch -> normalize -> resolve_identity -> redact -> encrypt ->
275:     persist, per source, plus coverage reporting including the degraded/source-failure
276:     path (REQ-M1-07, REQ-M1-08). One `collector_runs` row per real source_type
277:     present in the batch (matching data-base/02-schema-ingestion.md's per-source
278:     design) even though `SimulatedCollector` is a single Python object standing in for
279:     all of them — coverage reporting is about provenance, which stays real regardless
280:     of how many source-specific classes exist yet.
281:     """
282: 
283:     _MVP_SOURCE_TYPES = ("gmail", "zendesk", "warehouse")
284:     # Post-MVP sources (User Story 6, FR-021/022/023) are deliberately absent
285:     # from `_MVP_SOURCE_TYPES` — that tuple drives an unconditional
286:     # collector_runs row (and therefore a `coverage_reports.sources_expected`
287:     # slot) per entry, every single run, which is exactly right for the three
288:     # Phase 1 sources (a Phase 1 source that goes silent is a real, honest
289:     # gap) but wrong for a Post-MVP one: since there's no "connected" flag
290:     # anywhere in the schema (data-model.md's Decision — fixture-driven, not
291:     # a new entity), the only signal this codebase has for "is Slack/CSAT/
292:     # Calendar connected for this client" is "did this run's fixture data
293:     # actually contain any." Treating them as unconditionally expected would
294:     # make every client — including the ones in `demo/fixtures/meridian-
295:     # week-phase1-only.json` that connect none of them — show a permanent,
296:     # spurious coverage gap, which is exactly what FR-024 forbids.
297:     _POST_MVP_SOURCE_TYPES = ("slack", "csat", "transcripts")
298: 
299:     def __init__(
300:         self,
301:         collector_runs: CollectorRunRepositoryPort,
302:         events: EventRepositoryPort,
303:         profile_context: ClientProfileContextPort,
304:         encryption: EncryptionPort,
305:         key_store: KeyStorePort,
306:     ) -> None:
307:         self._runs = collector_runs
308:         self._events = events
309:         self._profile_context = profile_context
310:         self._encryption = encryption
311:         self._key_store = key_store
312: 
313:     async def execute(
314:         self,
315:         collector: Collector,
316:         *,
317:         window_start: datetime,
318:         window_end: datetime,
319:         fail_sources: frozenset[str] = frozenset(),
320:     ) -> CollectorRunResult:
321:         raw_items = await collector.fetch(window_start, window_end)
322:         # `fetch()` returns items in occurred_at order (Collector's docstring) — that
323:         # global order MUST be preserved all the way to `events.append()`, since the
324:         # hash chain requires appends in occurred_at order across the WHOLE run, not
325:         # just within one source. Grouping by source_type and processing each group to
326:         # completion (the earlier version of this method) silently reorders envelopes
327:         # across sources — e.g. a day-4 gmail item would get appended before a day-1
328:         # zendesk item — which corrupts the chain even though each source's own items
329:         # stay individually ordered. `envelopes` below stays in `fetch()`'s original
330:         # order; only the per-source bookkeeping (collector_runs rows, counts) groups
331:         # by source, not the actual event-append sequence.
332:         envelopes = [collector.normalize(item) for item in raw_items]
333:         profile = await self._profile_context.get_current()
334: 
335:         # The three Phase 1 sources are always expected; a Post-MVP source
336:         # only joins `source_types` (and therefore `coverage_reports.
337:         # sources_expected`) when this run's own envelopes actually contain
338:         # it — see `_POST_MVP_SOURCE_TYPES`'s docstring for why.
339:         present_post_mvp = [
340:             s for s in self._POST_MVP_SOURCE_TYPES if any(e.source_type == s for e in envelopes)
341:         ]
342:         source_types = self._MVP_SOURCE_TYPES + tuple(present_post_mvp)
343: 
344:         run_id_by_source: dict[str, UUID] = {}
345:         emitted_by_source: dict[str, int] = dict.fromkeys(source_types, 0)
346:         duplicates_by_source: dict[str, int] = dict.fromkeys(source_types, 0)
347:         sources_read = 0
348:         gap_reasons: list[str] = []
349: 
350:         for source_type in source_types:
351:             source_id = await self._runs.get_or_create_source(
352:                 source_type=source_type,
353:                 display_name=f"Meridian — {source_type}",
354:                 auth_scope=f"{source_type}.readonly",
355:             )
356:             run_id = await self._runs.start_run(
357:                 source_id=source_id,
358:                 trigger="manual",
359:                 window_start=window_start,
360:                 window_end=window_end,
361:             )
362:             run_id_by_source[source_type] = run_id
363: 
364:             if source_type in fail_sources:
365:                 await self._runs.finish_run(
366:                     run_id=run_id,
367:                     envelopes_emitted=0,
368:                     duplicates_skipped=0,
369:                     error=f"{source_type} source unreachable (simulated failure)",
370:                 )
371:                 gap_reasons.append(f"{source_type} unreachable")
372:             else:
373:                 sources_read += 1
374: 
375:         latest_occurred_at = window_start
376:         for envelope in envelopes:
377:             source_type = envelope.source_type
378:             if source_type in fail_sources or source_type not in run_id_by_source:
379:                 continue
380:             run_id = run_id_by_source[source_type]
381: 
382:             if await self._runs.envelope_exists(envelope.idempotency_key):
383:                 duplicates_by_source[source_type] += 1
384:                 continue
385: 
386:             participant = envelope.structured_payload.get("participant")
387:             stakeholder_id = (
388:                 await self._runs.resolve_identity(
389:                     source_identifier=participant, source_type=source_type
390:                 )
391:                 if participant
392:                 else None
393:             )
394: 
395:             redacted_text, redacted_fields = redact(envelope.payload_text, profile.exclusions)
396:             payload_encrypted = self._encryption.encrypt(redacted_text)
397:             data_key_ref = self._key_store.current_bucket_id()
398: 
399:             envelope_id = await self._runs.insert_envelope(
400:                 collector_run_id=run_id,
401:                 source_native_id=envelope.source_native_id,
402:                 idempotency_key=envelope.idempotency_key,
403:                 occurred_at=envelope.occurred_at,
404:                 identity_status="resolved" if stakeholder_id else "unresolved",
405:                 redacted_fields=redacted_fields,
406:                 payload_encrypted=payload_encrypted,
407:                 data_key_ref=data_key_ref,
408:             )
409: 
410:             event_id = await self._events.append(
411:                 NewEvent(
412:                     envelope_id=envelope_id,
413:                     event_type=_event_type_for_source(source_type),
414:                     occurred_at=envelope.occurred_at,
415:                     stakeholder_id=stakeholder_id,
416:                     product_area_id=_match_product_area(envelope, profile),
417:                     body_encrypted=payload_encrypted,
418:                     structured_payload=envelope.structured_payload,
419:                 ),
420:                 data_key_ref=data_key_ref,
421:             )
422:             await self._runs.link_envelope_to_event(envelope_id, event_id)
423:             emitted_by_source[source_type] += 1
424:             latest_occurred_at = max(latest_occurred_at, envelope.occurred_at)
425: 
426:         latest_run_id: UUID | None = None
427:         for source_type in source_types:
428:             if source_type in fail_sources:
429:                 continue
430:             run_id = run_id_by_source[source_type]
431:             latest_run_id = run_id
432:             await self._runs.finish_run(
433:                 run_id=run_id,
434:                 envelopes_emitted=emitted_by_source[source_type],
435:                 duplicates_skipped=duplicates_by_source[source_type],
436:                 error=None,
437:             )
438: 
439:         # Every source failed — no non-failed run to attach coverage to; fall back to
440:         # whichever run was created last (still a real row, still an honest report).
441:         if latest_run_id is None:
442:             latest_run_id = run_id_by_source[source_types[-1]]
443: 
444:         coverage_report_id = await self._runs.record_coverage(
445:             collector_run_id=latest_run_id,
446:             sources_expected=len(source_types),
447:             sources_read=sources_read,
448:             gap_reason="; ".join(gap_reasons) or None,
449:             complete_to=latest_occurred_at,
450:         )
451: 
452:         return CollectorRunResult(
453:             envelopes_emitted=sum(emitted_by_source.values()),
454:             duplicates_skipped=sum(duplicates_by_source.values()),
455:             coverage_report_id=coverage_report_id,
456:         )
457: 
458: 
459: # ---------------------------------------------------------------------------
460: # T040 — absence collector
461: # ---------------------------------------------------------------------------
462: 
463: _CADENCE_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}
464: 
465: 
466: def _parse_cadence_days(cadence: str) -> int | None:
467:     return _CADENCE_DAYS.get(cadence.strip().lower())
468: 
469: 
470: class DetectAbsenceUseCase:
471:     """Compares each recurring commitment's cadence against the ledger's latest
472:     contact; appends an `absence` event when overdue (REQ-M1-06). Still goes through
473:     the standard envelope pipeline — `events.envelope_id` is `NOT NULL` — so the
474:     absence collector needs a `sources` row too; `calendar` is the closest-fitting
475:     existing `source_type` value for "the scheduler itself noticed silence" (the enum
476:     has no generic/internal option, data-base/10-ddl-appendix.md)."""
477: 
478:     ABSENCE_SOURCE_TYPE = "calendar"
479: 
480:     def __init__(
481:         self,
482:         commitments: CommitmentLookupPort,
483:         collector_runs: CollectorRunRepositoryPort,
484:         events: EventRepositoryPort,
485:         encryption: EncryptionPort,
486:         key_store: KeyStorePort,
487:     ) -> None:
488:         self._commitments = commitments
489:         self._runs = collector_runs
490:         self._events = events
491:         self._encryption = encryption
492:         self._key_store = key_store
493: 
494:     async def execute(self, *, as_of: datetime | None = None) -> list[UUID]:
495:         as_of = as_of or datetime.now(UTC)
496:         appended: list[UUID] = []
497:         last_contact = await self._commitments.last_contact_at()
498: 
499:         for commitment in await self._commitments.list_recurring_commitments():
500:             cadence_days = _parse_cadence_days(commitment.cadence)
501:             if cadence_days is None:
502:                 continue
503:             window_start = as_of - timedelta(days=cadence_days)
504:             if last_contact is not None and last_contact >= window_start:
505:                 continue  # cadence satisfied — no absence event
506: 
507:             idempotency_key = f"absence:{commitment.id}:{window_start.date().isoformat()}"
508: 
509:             source_id = await self._runs.get_or_create_source(
510:                 source_type=self.ABSENCE_SOURCE_TYPE,
511:                 display_name="Internal — Absence monitor",
512:                 auth_scope="internal",
513:             )
514:             run_id = await self._runs.start_run(
515:                 source_id=source_id, trigger="poll", window_start=window_start, window_end=as_of
516:             )
517: 
518:             if await self._runs.envelope_exists(idempotency_key):
519:                 await self._runs.finish_run(
520:                     run_id=run_id, envelopes_emitted=0, duplicates_skipped=1, error=None
521:                 )
522:                 continue
523: 
524:             payload_encrypted = self._encryption.encrypt(
525:                 f"No contact matching commitment {commitment.id} since {last_contact}"
526:             )
527:             data_key_ref = self._key_store.current_bucket_id()
528:             envelope_id = await self._runs.insert_envelope(
529:                 collector_run_id=run_id,
530:                 source_native_id=idempotency_key,
531:                 idempotency_key=idempotency_key,
532:                 occurred_at=as_of,
533:                 identity_status="unresolved",
534:                 redacted_fields=[],
535:                 payload_encrypted=payload_encrypted,
536:                 data_key_ref=data_key_ref,
537:             )
538:             event_id = await self._events.append(
539:                 NewEvent(
540:                     envelope_id=envelope_id,
541:                     event_type="absence",
542:                     occurred_at=as_of,
543:                     body_encrypted=payload_encrypted,
544:                     structured_payload={
545:                         "commitment_id": str(commitment.id),
546:                         "cadence": commitment.cadence,
547:                         "window_start": window_start.isoformat(),
548:                         "last_contact_at": last_contact.isoformat() if last_contact else None,
549:                     },
550:                 ),
551:                 data_key_ref=data_key_ref,
552:             )
553:             await self._runs.link_envelope_to_event(envelope_id, event_id)
554:             await self._runs.finish_run(
555:                 run_id=run_id, envelopes_emitted=1, duplicates_skipped=0, error=None
556:             )
557:             appended.append(event_id)
558: 
559:         return appended
560: 
561: 
562: # ---------------------------------------------------------------------------
563: # ComputeRollupsUseCase (REQ-M2-06) — feature 005's first real implementation;
564: # deferred since feature 003 specifically because no reader consumed a baseline
565: # yet (specs/003-ingestion-and-context/spec.md's documented boundary)
566: # ---------------------------------------------------------------------------
567: 
568: _ROLLUP_SAMPLE_WINDOW_DAYS = 7
569: 
570: 
571: class ComputeRollupsUseCase:
572:     """Truncates and rebuilds `rollups` from `events` alone (the same "projection,
573:     rebuildable from events" shape `event_threads`/`response_pairs` already have,
574:     `data-base/01-database-overview.md`'s Principle 3) — one row per
575:     `usage_measurement` or `survey_response` event, scoped to exactly what the
576:     Usage reader consumes (`spec.md`'s Assumptions plus FR-022's CSAT
577:     extension), not a general analytics engine. `rollups.value` is each
578:     event's own `value_delta_pct` (warehouse) or `score` (CSAT) reading
579:     (`research.md`'s Decision — the real event schema carries these directly,
580:     not a separate absolute value)."""
581: 
582:     def __init__(self, events: EventRepositoryPort) -> None:
583:         self._events = events
584: 
585:     async def execute(self) -> int:
586:         all_events = await self._events.list_all_ordered()
587:         rows = [
588:             RollupRow(
589:                 subject_type="product_area",
590:                 subject_id=record.product_area_id,
591:                 metric=record.structured_payload.get("metric", "unknown"),
592:                 window_start=record.occurred_at - timedelta(days=_ROLLUP_SAMPLE_WINDOW_DAYS),
593:                 window_end=record.occurred_at,
594:                 value=float(record.structured_payload.get("value_delta_pct", 0)),
595:             )
596:             for record in all_events
597:             if record.event_type == "usage_measurement"
598:         ]
599:         # FR-022: CSAT numeric scores are the Usage reader's second tracked
600:         # metric, alongside the existing warehouse one — `subject_type=
601:         # "stakeholder"` (not "product_area"), since a CSAT score is a
602:         # per-respondent reading, not a per-product-area one
603:         # (`rollup_subject_type`'s enum already anticipated this value).
604:         rows += [
605:             RollupRow(
606:                 subject_type="stakeholder",
607:                 subject_id=record.stakeholder_id,
608:                 metric="csat_score",
609:                 window_start=record.occurred_at - timedelta(days=_ROLLUP_SAMPLE_WINDOW_DAYS),
610:                 window_end=record.occurred_at,
611:                 value=float(record.structured_payload.get("score", 0)),
612:             )
613:             for record in all_events
614:             if record.event_type == "survey_response"
615:         ]
616:         await self._events.truncate_rollups()
617:         await self._events.bulk_insert_rollups(rows)
618:         return len(rows)
619: 
620: 
621: # ---------------------------------------------------------------------------
622: # Retention job (specs/011-production-hardening, FR-001/002/003/004a)
623: # ---------------------------------------------------------------------------
624: 
625: 
626: class RunRetentionUseCase:
627:     """Daily crypto-shredding (`research.md` Decision 1). Resolves every bucket
628:     still active in `KeyStorePort`, destroys the ones whose entire UTC day is
629:     older than the retention window, nulls their `events.body_encrypted` rows,
630:     and records one `retention_job_runs` row either way. FR-004a: a failure
631:     partway through is logged (independent of User Story 3's tracing — this
632:     use case alone fully satisfies FR-004a) and re-raised so the caller's own
633:     schedule naturally retries on the next run (FR-003's idempotency makes a
634:     partial run always safe to redo)."""
635: 
636:     def __init__(
637:         self,
638:         key_store: KeyStorePort,
639:         retention_repo: RetentionJobRepositoryPort,
640:         retention_window_days: int,
641:     ) -> None:
642:         self._key_store = key_store
643:         self._retention_repo = retention_repo
644:         self._retention_window_days = retention_window_days
645: 
646:     async def execute(self, *, now: datetime | None = None) -> RetentionJobRunResult:
647:         now = now or datetime.now(UTC)
648:         started_at = now
649:         buckets_evaluated = 0
650:         buckets_shredded = 0
651:         try:
652:             for bucket_id in self._key_store.list_active_buckets():
653:                 buckets_evaluated += 1
654:                 if is_bucket_expired(
655:                     bucket_id, retention_window_days=self._retention_window_days, now=now
656:                 ):
657:                     self._key_store.destroy(bucket_id)
658:                     await self._retention_repo.shred_bucket(bucket_id)
659:                     buckets_shredded += 1
660:         except Exception as exc:
661:             logger.error(
662:                 "retention job failed after evaluating %d bucket(s), %d shredded: %s",
663:                 buckets_evaluated,
664:                 buckets_shredded,
665:                 exc,
666:             )
667:             await self._retention_repo.record_run(
668:                 started_at=started_at,
669:                 completed_at=datetime.now(UTC),
670:                 buckets_evaluated=buckets_evaluated,
671:                 buckets_shredded=buckets_shredded,
672:                 status="failed",
673:                 error_detail=str(exc),
674:             )
675:             raise
676: 
677:         run_id = await self._retention_repo.record_run(
678:             started_at=started_at,
679:             completed_at=datetime.now(UTC),
680:             buckets_evaluated=buckets_evaluated,
681:             buckets_shredded=buckets_shredded,
682:             status="succeeded",
683:             error_detail=None,
684:         )
685:         return RetentionJobRunResult(
686:             id=run_id,
687:             buckets_evaluated=buckets_evaluated,
688:             buckets_shredded=buckets_shredded,
689:             status="succeeded",
690:         )

(End of file - total 690 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/01-live-demo-runbook.md"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/01-live-demo-runbook.md</path>
<type>file</type>
<content>
1: # 01 · Live demo runbook
2: 
3: A minute-by-minute script for a 20-minute live demo, built around the same Meridian Logistics scenario used throughout this documentation set (`examples/01-end-to-end-walkthrough.md`), plus a contingency plan for when a live API misbehaves in front of judges — which, at some point, it will.
4: 
5: ## Before you start (T-30 minutes)
6: 
7: - Run `data-base/11-seed-data.sql` against a fresh database — clean Meridian profile, 9 finding types, 5 playbook actions, no leftover findings from a prior rehearsal.
8: - Confirm all MVP sources show `connected` in `sources` (`demo/03-environment-and-fixtures-checklist.md`).
9: - Have the **replay fixture** loaded and ready but *not yet run* — this is the contingency path, staged so it can fire in one command if needed.
10: - Open three windows: the dashboard (main screen), a terminal with the replay command ready, and the demo Gmail inbox.
11: 
12: ## The script
13: 
14: | Time | What you do | What you say | What the judges see |
15: |---|---|---|---|
16: | 0:00–1:30 | Open on the **Healthy** dashboard state | "Nobody is assigned to notice six systems' worth of small signals together — that's the actual problem. Here's the tool, on a healthy account, right now." | A near-empty screen: *"Nothing needs you today."* — deliberately unimpressive (P6). |
17: | 1:30–3:00 | Narrate the scenario | "Meridian's CTO Ana is about to send a real email — right now, live — that on its own looks unremarkable." | Dashboard still healthy. |
18: | 3:00–4:00 | **Live action #1** — send the real email from the demo Gmail account | "I'm sending this now, no editing, no pre-staging." | Nothing yet — this is deliberate; narrate what's about to happen while it's in flight. |
19: | 4:00–4:45 | Wait for the pipeline (~40s budget, `requirements/11-non-functional-requirements.md` REQ-NFR-02) | "The collector picks this up, the ledger appends it, two readers run in parallel, the gate checks the evidence, the scoring engine does plain arithmetic — no step here is scripted for the demo, this is the real pipeline." | Pulse timeline updates first (proves the ledger append), then the score animates from its previous value. |
20: | 4:45–6:30 | Score has moved — open the **evidence trace panel** on the top contribution bar | "Every number is a door. This didn't just say 'sentiment negative' — it says *why*, and lets you check the math yourself." | Side-by-side baseline-vs-current comparison, the actual quoted email, the arithmetic in plain sentences (spec §11.4). |
21: | 6:30–8:30 | Type into the **ask bar**: *"Why did the score go up?"* | "This isn't a chatbot bolted on top — it's reading the same numbers you just saw, not recalculating anything." | Delta breakdown component, rendered in under 3 seconds (REQ-M9-08). |
22: | 8:30–11:00 | Click **"Write to Ana about this"** on the top issue | "Watch what it does and doesn't do." | A generated draft, acknowledging the specific failure first. Point out explicitly: **"Copy draft" and "Log as sent (manual)" — no send button. Not hidden. Not disabled. Not present anywhere in this product."** |
23: | 11:00–12:30 | **Live action #2** — click "Copy draft," paste it into the real Gmail compose window, send it for real | "A human — me, right now — is the only thing in this system that can make this message leave the building." | The email actually sends. This is the single most important beat in the demo — don't rush it. |
24: | 12:30–14:00 | Open the **feedback loop** — mark a secondary, less central finding as "false alarm" | "Now watch it learn, without any retraining." | The card updates in place: *"weight reduced — your team flagged this pattern as a false alarm."* |
25: | 14:00–15:30 | **Live action #3** — trigger a second scoring run (a small follow-up event, or the manual "recompute" affordance in the demo build) | "Same pattern, next time it fires, counts for less. That's the entire learning mechanism — one number, fully explained." | `score_contributions.damping` visibly lower on the next matching card. |
26: | 15:30–17:00 | Show the **response clock closing** — the sent email lands back through the collector | "It watches whether its own suggestion actually worked." | `response_pairs.state` flips from `open_overdue` toward `resolved`; the ticket-side contribution starts fading on its half-life. |
27: | 17:00–19:00 | Zoom out — show the healthy state again on a *different*, unrelated seeded account if available, or narrate it | "Same tool, quiet week, and it says so instead of manufacturing concern. That's not a missing feature — that's principle six." | Reinforces P6 without needing new evidence. |
28: | 19:00–20:00 | Close | "Three things: what's going wrong, why it matters *here*, what to do next. All three, traceable to a real message, in under a minute of real time." | — |
29: 
30: ## Real, live actions performable in this demo without violating any product boundary
31: 
32: Everything below is a genuine system action, not a mocked one, and none of it crosses a limit in `requirements/11-non-functional-requirements.md` §Hard product boundaries:
33: 
34: 1. **Real collection via API** — the Gmail webhook fires on a real sent email; nothing about ingestion is staged.
35: 2. **Real ledger append** — visible in the pulse timeline within ~1s of the collector firing.
36: 3. **Real recompute** — the score animates from an actual scoring run, not a canned number.
37: 4. **Real draft generation** — an actual LLM call against the live evidence, not a stored string.
38: 5. **Real verdict → damping** — clicking false alarm writes a real `feedback_verdicts` row and recomputes a real `damping_weights` row.
39: 6. **Real response-clock closure** — sending the actual copied draft and having it collected back closes a real `response_pairs` row.
40: 
41: What is **never** live, by design, matching P4: no step in this script includes the system itself sending anything. Step 11:00–12:30 is a human pasting and sending through their own email client — the system's involvement stops at "Copy draft."
42: 
43: ## Contingency: replay mode
44: 
45: If the live Gmail/Zendesk API is unreachable, rate-limited, or simply flaky on venue wifi, switch to replay without missing a beat — this is not a degraded fallback, it's a first-class architectural feature (`requirements/02-event-ledger.md` REQ-M2-07, the same replay job that powers profile edits and weight tuning) doing double duty as a demo safety net:
46: 
47: ```bash
48: # Pre-staged fixture: the exact scenario from examples/01-end-to-end-walkthrough.md,
49: # captured as a sequence of events with real timestamps, replayed at demo speed.
50: python -m scripts.replay_demo_fixture --fixture demo/fixtures/meridian-week.json --speed live
51: ```
52: 
53: **What to say if you have to switch:** *"I'll switch to replay mode — this is the same replay job the system uses for profile edits and weight tuning, not a special demo mode. It's running the identical scenario against the identical ledger schema; the only thing that's different is where the events came from."* This line matters — it turns an infrastructure hiccup into a demonstration of the bitemporal ledger's honesty (`data-base/03-schema-ledger.md`), which is a stronger flex than the live API working would have been anyway.
54: 
55: The fixture file is generated from `data-base/11-seed-data.sql` plus the six events in `examples/01-end-to-end-walkthrough.md` §5 — see `demo/03-environment-and-fixtures-checklist.md` for how it's built and kept in sync.
56: 
57: ## Traceability
58: 
59: `examples/01-end-to-end-walkthrough.md`, `sequences/01-sequence-signal-to-score.md`, `requirements/11-non-functional-requirements.md`, `demo/02-impact-story.md`, `demo/03-environment-and-fixtures-checklist.md`.

(End of file - total 59 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 3.9s)

_Thinking:_

Now I have a very thorough understanding. Let me also look at the demo environment checklist and the demo runbook, plus the README and the phase1-only fixture to understand differences. Let me also look at the demo's `run_collector.py` and how the config exposes the fixture path.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/03-environment-and-fixtures-checklist.md"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/03-environment-and-fixtures-checklist.md</path>
<type>file</type>
<content>
1: # 03 · Demo environment and fixtures checklist
2: 
3: Everything the live demo (`demo/01-live-demo-runbook.md`) needs that **isn't a document** — accounts, credentials, seeded history, and a backup environment. None of this can be prepared by writing more markdown; it's the physical/account-setup work that has to happen before the runbook is rehearsable. Owner and status columns are here so this checklist functions as the actual pre-demo punch list, not just a description of what's needed.
4: 
5: ## Why the Gmail account needs weeks of history *before* demo day
6: 
7: The Tone reader is baseline-relative by design (spec P7, REQ-M5-06) and abstains below 5 historical samples (`requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-04). If the demo Gmail account is created the morning of the demo, the Tone reader has nothing to compare against — it will correctly, honestly abstain, and the single most compelling part of the demo (the score moving on live evidence) won't fire. **This has to be seeded from day one of demo prep, not day-of.** Budget 4–6 weeks of realistic back-and-forth email history between "Ana" and the vendor side before it's usable as a baseline.
8: 
9: ## Checklist
10: 
11: | # | Item | Detail | Owner | Status |
12: |---|---|---|---|---|
13: | 1 | Demo Gmail account created | A real Gmail address acting as `ana.reyes@meridian.com` for the demo | — | ☐ |
14: | 2 | 4–6 weeks of "healthy" email history seeded | Realistic message rhythm, greeting rate, average length — this *is* the Tone reader's baseline window (`data-base/03-schema-ledger.md` `baseline_confirmations`) | — | ☐ |
15: | 3 | Baseline windows confirmed | A human (`REQ-M6-CAL-04`) confirms the healthy window via `baseline_confirmations` before demo day — an unconfirmed baseline means `rollups.is_baseline` stays false and the Tone reader has nothing to compare against even with enough raw history | — | ☐ |
16: | 4 | Google Cloud OAuth app registered | Gmail API, read-only scope (`requirements/01-signal-collectors.md` REQ-M1-P4) | — | ☐ |
17: | 5 | Zendesk trial/sandbox account | Seeded with ticket #456 (reopened, breach) and #398 (resolved fast) matching `examples/01-end-to-end-walkthrough.md` §4 | — | ☐ |
18: | 6 | Anthropic API key | Pinned to the model IDs in `decisions/02-repo-and-tooling.md` (`claude-haiku-4-5-20251001`, `claude-sonnet-5`) | — | ☐ |
19: | 7 | OpenAI API key | Embeddings only (`text-embedding-3-small`), per `architecture/03-technology-stack.md` | — | ☐ |
20: | 8 | Domain + hosting for a stable demo URL | Not `localhost` — a real, reachable URL survives a laptop restart or a projector-handoff mid-demo | — | ☐ |
21: | 9 | Warehouse fixture data | Synthetic `tracking_api` usage series, 8-week trailing baseline plus the 3-week, 22% drop (`requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-06) | — | ☐ |
22: | 10 | CSAT fixture data | Ana's prior response (score 9) and the current one (score 6, with the comment) | — | ☐ |
23: | 11 | Slack Connect sandbox | Diego's 12-day silence and two missed syncs, seeded relative to demo day (not a fixed past date that ages out) | — | ☐ |
24: 
25: ## The Meridian dataset as versioned fixtures
26: 
27: `examples/01-end-to-end-walkthrough.md` already contains the full scripted scenario — 6 events, 9 findings, worked arithmetic, all consistent with `data-base/11-seed-data.sql`. That scenario is the **single source of truth** for three different consumers, and all three must be regenerated together whenever the scenario changes, never edited independently:
28: 
29: ```mermaid
30: flowchart LR
31:     Doc["examples/01-end-to-end-walkthrough.md\n(the scenario, in prose)"] --> Seed["data-base/11-seed-data.sql\n(profile, config, playbook)"]
32:     Doc --> Fixture["demo/fixtures/meridian-week.json\n(the 6 events, for SimulatedCollector\nand replay-mode contingency)"]
33:     Doc --> Golden["tests/fixtures/golden-dashboard.json\n(expected end-state, for golden-replay tests)"]
34: ```
35: 
36: A `SimulatedCollector` (implementing the same `Collector` interface as the real Gmail/Zendesk adapters, `architecture/02-component-catalog.md`) reads `demo/fixtures/meridian-week.json` and emits envelopes exactly as a real collector would — this is what powers both the golden-replay test suite (`tests/strategy.md`) and the demo's contingency path (`demo/01-live-demo-runbook.md` §Contingency), from the same fixture file. Keeping the scenario, the seed data, and the fixture in sync is a single regeneration script, not three manual edits.
37: 
38: ## Redundant demo environment
39: 
40: The live demo depends on network connectivity for the live-API portions (`demo/01-live-demo-runbook.md` steps involving the real Gmail send). Two independent failure points need a plan each:
41: 
42: | Risk | Mitigation |
43: |---|---|
44: | Venue wifi is unreliable or blocked | A **local** deployment (the same Docker Compose stack, run on the presenter's laptop, `architecture/03-technology-stack.md`) as a hot spare — replay mode works fully offline since it never calls a live source API, only the LLM providers, which need internet regardless |
45: | The hosted demo URL goes down (host issue, not network) | A second, independently-deployed Compose stack (different host/region) with the same seed data, switchable via a pre-tested bookmark, not a live redeploy |
46: | Both LLM providers are unreachable | No good live fallback exists for this one — the readers and narrator genuinely need Claude, and Recurrence needs OpenAI embeddings. Mitigation is entirely preventive: verify both providers' status pages the morning of the demo, and have `demo/01-live-demo-runbook.md`'s error-handling behavior (`architecture/06-error-handling.md` — readers abstain, narrator falls back to deterministic template) ready to narrate honestly as a feature, not hidden as a failure |
47: 
48: ## Traceability
49: 
50: `demo/01-live-demo-runbook.md`, `demo/02-impact-story.md`, `examples/01-end-to-end-walkthrough.md`, `data-base/11-seed-data.sql`, `requirements/13-scoring-calibration-appendix.md`, `architecture/06-error-handling.md`.

(End of file - total 50 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/fixtures/meridian-week-phase1-only.json"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/demo/fixtures/meridian-week-phase1-only.json</path>
<type>file</type>
<content>
1: [
2:   {
3:     "source_type": "gmail",
4:     "source_native_id": "gmail-msg-8831",
5:     "occurred_at": "2026-08-10T09:14:00-05:00",
6:     "from": "ana.reyes@meridian.com",
7:     "text": "Please advise on the timeline. I need to brief the board on Thursday."
8:   },
9:   {
10:     "source_type": "gmail",
11:     "source_native_id": "gmail-msg-8790",
12:     "occurred_at": "2026-07-01T10:00:00-05:00",
13:     "from": "diego@meridian.com",
14:     "text": "Looping in on the tracking_api integration questions from our side."
15:   },
16:   {
17:     "source_type": "zendesk",
18:     "source_native_id": "zendesk-456-created",
19:     "occurred_at": "2026-08-06T09:15:00-05:00",
20:     "reporter": "support-desk@meridian.zendesk.com",
21:     "ticket_number": 456,
22:     "title": "Slow API response",
23:     "product_area": "tracking_api",
24:     "state": "created"
25:   },
26:   {
27:     "source_type": "zendesk",
28:     "source_native_id": "zendesk-456-reopened",
29:     "occurred_at": "2026-08-10T07:40:00-05:00",
30:     "reporter": "support-desk@meridian.zendesk.com",
31:     "ticket_number": 456,
32:     "title": "Slow API response",
33:     "reopen_count": 2,
34:     "product_area": "tracking_api",
35:     "state": "reopened"
36:   },
37:   {
38:     "source_type": "zendesk",
39:     "source_native_id": "zendesk-398-created",
40:     "occurred_at": "2026-08-11T11:02:00-05:00",
41:     "reporter": "support-desk@meridian.zendesk.com",
42:     "ticket_number": 398,
43:     "title": "Add CSV export",
44:     "product_area": "reporting",
45:     "state": "created"
46:   },
47:   {
48:     "source_type": "zendesk",
49:     "source_native_id": "zendesk-398-resolved",
50:     "occurred_at": "2026-08-11T13:02:00-05:00",
51:     "reporter": "support-desk@meridian.zendesk.com",
52:     "ticket_number": 398,
53:     "title": "Add CSV export",
54:     "product_area": "reporting",
55:     "state": "resolved"
56:   },
57:   {
58:     "source_type": "zendesk",
59:     "source_native_id": "zendesk-512-created",
60:     "occurred_at": "2026-08-12T15:20:00-05:00",
61:     "reporter": "support-desk@meridian.zendesk.com",
62:     "ticket_number": 512,
63:     "title": "Login page displays wrong company logo",
64:     "product_area": "reporting",
65:     "state": "created"
66:   },
67:   {
68:     "source_type": "warehouse",
69:     "source_native_id": "usage-tracking_api-w29",
70:     "occurred_at": "2026-07-08T00:00:00-05:00",
71:     "metric": "weekly_active_usage",
72:     "product_area": "tracking_api",
73:     "value_delta_pct": -2
74:   },
75:   {
76:     "source_type": "warehouse",
77:     "source_native_id": "usage-tracking_api-w30",
78:     "occurred_at": "2026-07-15T00:00:00-05:00",
79:     "metric": "weekly_active_usage",
80:     "product_area": "tracking_api",
81:     "value_delta_pct": 1
82:   },
83:   {
84:     "source_type": "warehouse",
85:     "source_native_id": "usage-tracking_api-w31",
86:     "occurred_at": "2026-07-22T00:00:00-05:00",
87:     "metric": "weekly_active_usage",
88:     "product_area": "tracking_api",
89:     "value_delta_pct": -3
90:   },
91:   {
92:     "source_type": "warehouse",
93:     "source_native_id": "usage-tracking_api-w32",
94:     "occurred_at": "2026-07-29T00:00:00-05:00",
95:     "metric": "weekly_active_usage",
96:     "product_area": "tracking_api",
97:     "value_delta_pct": 2
98:   },
99:   {
100:     "source_type": "warehouse",
101:     "source_native_id": "usage-tracking_api-w33",
102:     "occurred_at": "2026-08-05T00:00:00-05:00",
103:     "metric": "weekly_active_usage",
104:     "product_area": "tracking_api",
105:     "value_delta_pct": -1
106:   },
107:   {
108:     "source_type": "warehouse",
109:     "source_native_id": "usage-tracking_api-w34",
110:     "occurred_at": "2026-08-12T00:00:00-05:00",
111:     "metric": "weekly_active_usage",
112:     "product_area": "tracking_api",
113:     "value_delta_pct": -22
114:   },
115:   {
116:     "source_type": "gmail",
117:     "source_native_id": "gmail-msg-8845",
118:     "occurred_at": "2026-08-13T14:30:00-05:00",
119:     "from": "ana.reyes@meridian.com",
120:     "text": "Separately — I'm forwarding the contract dispute thread to our legal team, please hold off on that topic until they weigh in."
121:   }
122: ]

(End of file - total 122 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/config.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/config.py</path>
<type>file</type>
<content>
1: from pydantic_settings import BaseSettings, SettingsConfigDict
2: 
3: 
4: class Settings(BaseSettings):
5:     """Per-deployment configuration, sourced from the environment (.env in Compose).
6: 
7:     One deployment = one client = one .env file, never shared across stacks
8:     (architecture/03-technology-stack.md, constitution "Isolation model").
9:     """
10: 
11:     model_config = SettingsConfigDict(env_file=".env", extra="ignore")
12: 
13:     database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_churn"
14: 
15:     # Role passwords for the app_role/shredder_role grants in
16:     # data-base/10-ddl-appendix.md — that document's psql :'var' syntax is a psql-client
17:     # substitution feature with no asyncpg equivalent, so the initial migration
18:     # (migrations/versions/0001_initial_schema.py) substitutes these client-side instead,
19:     # replicating exactly what psql would have done before sending the DDL to the server.
20:     app_role_password: str = "app_role_dev_password"
21:     shredder_role_password: str = "shredder_role_dev_password"
22: 
23:     # The frontend's origin, for CORS (specs/002-dashboard-shell T004) — `api` and `web`
24:     # are served on different ports (docker-compose.yml), so the browser enforces CORS
25:     # on every request from the dashboard to the API.
26:     web_origin: str = "http://localhost:5173"
27: 
28:     # Bearer token lifetime — requirements/14-authentication.md's default (12 hours).
29:     token_lifetime_hours: int = 12
30: 
31:     # Message-body encryption (specs/003-ingestion-and-context, REQ-M1-P4). One active
32:     # Fernet key per deployment in Phase 1 — encryption_key_id is a fixed label stored
33:     # in data_key_ref columns, never the key itself (research.md).
34:     encryption_key_path: str = "./secrets/data.key"
35:     encryption_key_id: str = "local-v1"
36: 
37:     # Client profile YAML (specs/003-ingestion-and-context, REQ-M3-01) — the CS lead
38:     # edits this file directly in the MVP (decisions/00-open-questions-resolved.md Q2);
39:     # POST /api/profile/reload re-reads it from this path.
40:     client_profile_path: str = "./demo/client-profile.yaml"
41: 
42:     # SimulatedCollector's fixture (specs/003-ingestion-and-context) — CWD-relative
43:     # like the two paths above, not `__file__`-relative: this repo's Docker image
44:     # flattens `backend/` away (WORKDIR /app *is* the backend tree), so a
45:     # `__file__`-relative path computed from `scripts/run_collector.py` would resolve
46:     # differently in the container than it does when run locally from `backend/`.
47:     collector_fixture_path: str = "./demo/fixtures/meridian-week.json"
48: 
49:     # Recurrence reader's embedding provider (specs/005-deterministic-findings,
50:     # architecture/03-technology-stack.md) — no safe default; an empty value fails
51:     # honestly at the adapter (spec.md's Edge Cases), never a silent skip.
52:     openai_api_key: str = ""
53: 
54:     # Tone/Intent readers' model provider (specs/007-model-findings,
55:     # decisions/02-repo-and-tooling.md) — no safe default for the key, same
56:     # honest-failure discipline as openai_api_key above.
57:     anthropic_api_key: str = ""
58:     reader_model_id: str = "claude-haiku-4-5-20251001"
59: 
60:     # Narrator/Ask agent's model tier (specs/008-narrator-and-ask-agent,
61:     # decisions/02-repo-and-tooling.md's Claude model ID pinning table) — same
62:     # anthropic_api_key above, a different pinned model ID for higher-stakes
63:     # generation than the readers' Haiku-class calls.
64:     generation_model_id: str = "claude-sonnet-5"
65: 
66:     # Retention/crypto-shredding (specs/011-production-hardening, REQ-NFR-13/14,
67:     # FR-001) — configurable per deployment since the 90-day figure is described as
68:     # "pending final legal sign-off with the client" (decisions/00-open-questions-
69:     # resolved.md Q5), not hardcoded.
70:     retention_window_days: int = 90
71: 
72:     # Daily key-rotation buckets for crypto-shredding (research.md Decision 1) — one
73:     # Fernet key file per UTC calendar day under this directory, replacing the single
74:     # static `encryption_key_path` key above for new writes. `encryption_key_path`
75:     # above is kept only so any pre-migration "local-v1"-tagged row can still be
76:     # decrypted (data-model.md's documented one-time manual exception).
77:     data_keys_dir: str = "./secrets/data-keys"
78: 
79:     # Observability (specs/011-production-hardening, FR-009..012) — empty means the
80:     # OTel SDK initializes with a console/no-op exporter, never a hard failure
81:     # (FR-012's "unaffected if the observability backend itself is unreachable").
82:     # Field name matches the OTel-standard env var (`OTEL_EXPORTER_OTLP_ENDPOINT`,
83:     # docker-compose.yml) exactly, so pydantic-settings' default case-insensitive
84:     # env-var mapping picks it up with no alias needed.
85:     otel_exporter_otlp_endpoint: str = ""
86: 
87: 
88: settings = Settings()

(End of file - total 88 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 3.0s)

_Thinking:_

Now I have a very complete picture. Let me look at one more thing - the README to understand how to run the project, and check what backend/demo scripts exist for running the collector end-to-end.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/README.md"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/README.md</path>
<type>file</type>
<content>
1: # Agentic Churn
2: 
3: A dedicated monitoring agent for **one client relationship**. It reads signals that
4: already exist across email, chat, tickets, and product usage, notices when the
5: relationship is deteriorating, explains why with evidence, and proposes what to do next.
6: A human always decides and always sends.
7: 
8: ## Where things live
9: 
10: Read `AGENTS.md` first if you're touching code — it points at the actual specification
11: and lists which rules are non-negotiable. In short:
12: 
13: | Looking for... | Go to |
14: |---|---|
15: | What a module (M1–M10) is supposed to do | `requirements/<module>.md` |
16: | Why a technical decision was made | `architecture/`, `decisions/` |
17: | Exact table schemas | `data-base/10-ddl-appendix.md` |
18: | The full product brief | `base/Churn-Sentiment-Agent-Product-Specification.md` |
19: | Project principles and governance | `.specify/memory/constitution.md` |
20: | The build order and current feature status | `specs/001-project-foundation/` (this repo's first spec-kit feature; see `AGENTS.md` and the constitution for how later features are structured) |
21: 
22: This repository currently contains **Project Foundation** (build-order Phase 1 — repo
23: scaffold, CI pipeline, Docker Compose stack, database schema), **Dashboard Shell**
24: (Phase 2 — full authentication and a dashboard shell proving the stack works end to
25: end), **Ingestion and Context** (Phase 3 — the event ledger, client profile, and
26: signal collectors: the first modules with real business logic), **Score Engine**
27: (Phase 4 — "the checkpoint": per-finding weighting, issue-relative ranking, band
28: classification with hysteresis, all proven against a hand-authored fixture before any
29: reader module exists), and **Deterministic Findings** (Phase 5 — the five non-LLM
30: readers: Commitment, Usage, Recurrence, Absence, Relationship — the first features
31: to write real, non-fixture `findings` rows). See `specs/ROADMAP.md` for the full
32: feature-by-feature status.
33: 
34: ## Quickstart
35: 
36: Prerequisites: Docker. Nothing else — that's the entire point of this feature
37: (`specs/001-project-foundation/spec.md` User Story 1).
38: 
39: ```bash
40: git clone <repo> && cd agentic-churn
41: cp .env.example .env   # edit values for a real deployment; defaults work for local dev
42: docker compose up --build
43: ```
44: 
45: **Expected**: the `api`, `worker`, `db`, and `web` containers all report healthy —
46: `docker compose ps` shows `healthy` for each. `web` is served at
47: `http://localhost:${WEB_PORT:-5173}`, the API health check at
48: `http://localhost:${API_PORT:-8000}/health`.
49: 
50: ### Verify the schema
51: 
52: ```bash
53: docker compose exec api alembic current
54: docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"
55: ```
56: 
57: The table list should match `data-base/10-ddl-appendix.md`'s `CREATE TABLE` statements
58: 1:1. Seed data (`data-base/11-seed-data.sql`) is applied separately:
59: 
60: ```bash
61: docker compose exec api python scripts/seed.py
62: ```
63: 
64: ```bash
65: docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
66:   -c "SELECT count(*) FROM finding_type_config;"   # non-zero once seeded
67: ```
68: 
69: ### Login
70: 
71: Once seeded, log in at `http://localhost:${WEB_PORT:-5173}` with username `marta`,
72: password `agentic-demo-2026` — a local/demo-only credential, never treated as a secret
73: (`specs/002-dashboard-shell/research.md` §Decision: Regenerating the seeded demo
74: password hash). You'll land on a dashboard shell showing the seeded client's name and
75: an honest "still learning" state — see `specs/002-dashboard-shell/quickstart.md` for the
76: full auth flow (token issuance, revocation, rate limiting) exercised via `curl`.
77: 
78: ### Persistence
79: 
80: ```bash
81: docker compose down && docker compose up
82: ```
83: 
84: Schema and seed data persist across a restart — no manual migration step required.
85: 
86: ### Reset cleanly
87: 
88: ```bash
89: docker compose down -v   # drops the db_data volume — full reprovision on next `up`
90: ```
91: 
92: See `specs/001-project-foundation/quickstart.md` for the full validation walkthrough,
93: including the CI-gate and test-harness checks (User Stories 2 and 3).
94: 
95: ## Ingestion and Context (Phase 3)
96: 
97: One extra one-time setup step beyond the base quickstart above: a local encryption key
98: for message-body encryption (REQ-M1-P4 — never optional, never deferred).
99: 
100: ```bash
101: mkdir -p secrets
102: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/data.key
103: docker compose up --build -d   # picks up the new ./secrets and ./demo mounts
104: ```
105: 
106: The CS lead's hand-authored client profile lives at `demo/client-profile.yaml`; the
107: signal-collector fixture lives at `demo/fixtures/meridian-week.json`. See
108: `specs/003-ingestion-and-context/quickstart.md` for the full validation walkthrough —
109: profile versioning, hash-chain/business-hours arithmetic, `SimulatedCollector` runs
110: (idempotency, identity resolution, redaction), and absence detection.
111: 
112: ## Score Engine (Phase 4)
113: 
114: Findings are still hand-authored/fixture-seeded here — no reader module exists yet
115: (that's build-order Phase 5). This feature proves `score_runs`/`score_contributions`/
116: `band_history` computation for real: per-finding weighting, issue-relative ranking with
117: diminishing rank weight, recency by lifecycle state, the positive-signal cap, the
118: saturating points→score conversion, and band classification with hysteresis and
119: 2-consecutive-run stickiness.
120: 
121: ```bash
122: docker compose exec api python scripts/run_collector.py --source simulated
123: docker compose exec api python scripts/seed_score_fixture.py
124: docker compose exec api python scripts/compute_score.py   # run twice to settle the band
125: ```
126: 
127: Three real recomputation triggers are wired: `manual` (the script above),
128: `hourly_heartbeat` (`app/worker.py`'s APScheduler job), and `profile_edit_replay`
129: (fires automatically after a profile edit via `SubmitProfileUseCase`). See
130: `specs/004-score-engine/quickstart.md` for the full validation walkthrough, including
131: the exact worked-example numbers and the source-degraded freeze path.
132: 
133: ## Deterministic Findings (Phase 5)
134: 
135: Real findings, no model call: Commitment, Usage, Recurrence, Absence, and
136: Relationship each read the real ledger and emit `Finding`s deterministically —
137: `ValidationGate`/Tone/Intent (M5a/the LLM-based readers, feature 007 below) now
138: gate and persist every finding this phase's five readers emit too; Meeting
139: stays unbuilt (sent to Phase 2, `decisions/01-mvp-scope-and-phasing.md`). One
140: new environment prerequisite — Recurrence's embedding provider:
141: 
142: ```bash
143: echo "OPENAI_API_KEY=sk-..." >> .env
144: docker compose up --build -d   # picks up the new env var
145: ```
146: 
147: ```bash
148: docker compose exec api python scripts/run_collector.py --source simulated
149: docker compose exec api python scripts/run_readers.py
150: ```
151: 
152: **Expected**: a per-reader summary — findings persisted, or (if `OPENAI_API_KEY` is
153: missing/invalid) Recurrence's own isolated failure message, while the other four
154: readers' counts are unaffected (FR-014a). Every finding now passes through the
155: validation gate (feature 007) before persisting — see the next section. Re-running
156: over an unchanged ledger adds nothing (the REQ-M5-15 cache). See
157: `specs/005-deterministic-findings/quickstart.md` for the full validation
158: walkthrough, including the exact worked-example table and the failure-isolation
159: and cache checks.
160: 
161: ## Model Findings (Phase 7)
162: 
163: Tone and Intent — the two LLM-based readers — plus the M5a validation gate that
164: now runs on every finding from all eight readers, not just these two: schema
165: valid, cited events real, enough evidence, confidence at or above the type's
166: floor. A finding that fails is quarantined, tagged with the specific reason, and
167: never repaired or resubmitted (REQ-M5A-01..04). One new environment
168: prerequisite — Tone/Intent's model provider:
169: 
170: ```bash
171: echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
172: echo "READER_MODEL_ID=claude-haiku-4-5-20251001" >> .env
173: docker compose up --build -d   # picks up the new env vars
174: ```
175: 
176: Tone needs a human-confirmed baseline before it will ever emit a finding for a
177: given stakeholder — REQ-M6-CAL-04's "no history, no opinion" abstention floor
178: (at least 5 prior messages in the confirmed window):
179: 
180: ```bash
181: docker compose exec api python scripts/run_collector.py --source simulated
182: docker compose exec api python scripts/confirm_baseline.py --stakeholder ana \
183:   --metric email_style --window-days 60
184: docker compose exec api python scripts/run_readers.py
185: ```
186: 
187: **Expected**: a per-reader summary including `findings_quarantined` alongside
188: `findings_persisted`; a missing `ANTHROPIC_API_KEY` reports Tone/Intent's own
189: isolated failure, the same as Recurrence's missing `OPENAI_API_KEY` — never a
190: silently-empty, misleadingly-healthy run. `GET /api/coverage`'s `quarantine`
191: field is real for the first time, reflecting whatever the gate actually
192: rejected. See `specs/007-model-findings/quickstart.md` for the full validation
193: walkthrough.
194: 
195: ## Narrator and Ask Agent (Phase 8)
196: 
197: The explanation layer: the Narrator turns a score run's ranked findings into a
198: fact-checked headline/reasons/actions, and the Ask agent — the one genuinely
199: agentic component, a compiled LangGraph `StateGraph` — answers questions by
200: looking up already-computed data, never recalculating the score. One new
201: environment prerequisite — Narrator/Ask agent's model tier (same
202: `ANTHROPIC_API_KEY` as Tone/Intent, a higher-stakes model):
203: 
204: ```bash
205: echo "GENERATION_MODEL_ID=claude-sonnet-5" >> .env
206: docker compose up --build -d   # picks up the new env var
207: ```
208: 
209: Narrate the latest score run (a separate manual script, mirroring
210: `compute_score.py`/`run_readers.py` — no live/chained trigger path exists yet
211: anywhere in this pipeline):
212: 
213: ```bash
214: docker compose exec api python scripts/compute_score.py
215: docker compose exec api python scripts/run_narrator.py
216: ```
217: 
218: **Expected**: a headline/reasons/actions summary printed, with `narrator_outputs`
219: now real for the first time (this table existed, unpopulated, since feature
220: 001) — `GET /api/dashboard`'s `narrator` field renders it, closing the gap
221: feature 006 explicitly deferred. If every LLM-generated headline candidate
222: fails its own mechanical fact-check, the dashboard falls back to a
223: deterministic, non-LLM headline built from the score/band/top-issue alone
224: (`fact_check_passed = false`) — never a blank dashboard, never an unverified
225: claim.
226: 
227: Ask a question — `POST /api/ask` is real for the first time since
228: `architecture/07-api-spec.md` documented it:
229: 
230: ```bash
231: TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
232:   -H "Content-Type: application/json" \
233:   -d '{"username":"marta","password":"agentic-demo-2026"}' \
234:   | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
235: curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
236:   -d '{"question": "why did the score go up?"}' \
237:   http://localhost:${API_PORT:-8000}/api/ask
238: ```
239: 
240: **Expected**: a rendered component (`delta_breakdown`, `stakeholder_cards`,
241: etc.) for one of the 7 lookup-and-render intents, a `draft_handoff` response
242: for "write to X about this," or an honest decline/fallback — a prediction
243: question always declines rather than guessing, a colleague-judgment question
244: always refuses, and a stakeholder with fewer than 5 confirmed-baseline
245: messages declines with `insufficient_history`, distinct from
246: `source_not_connected`. `GET /api/coverage`'s new `ask_intent_coverage` field
247: shows the fallback rate without querying the database directly. See
248: `specs/008-narrator-and-ask-agent/quickstart.md` for the full validation
249: walkthrough, including the now-real `tests/golden_replay/` suite.
250: 
251: ## Draft Composer (Phase 9)
252: 
253: "The closer." Generates a client-facing message from a requested issue's own
254: evidence, the client profile's communication norms, real thread history, and
255: the latest run's already-agreed actions — then runs it through five
256: mechanical pre-display checks (facts, dates, invented causes, internal
257: leaks, commercial concessions) before it can ever be persisted or displayed.
258: **No new environment prerequisite** — reuses the same `GENERATION_MODEL_ID`
259: Sonnet tier the Narrator and Ask agent already use, and no migration: the
260: `draft_messages` table has existed, unpopulated, since feature 001.
261: 
262: Generate a draft for the worked example's top issue:
263: 
264: ```bash
265: TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
266:   -H "Content-Type: application/json" \
267:   -d '{"username":"marta","password":"agentic-demo-2026"}' \
268:   | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
269: curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
270:   -d '{"issue_id":"<issue-id>","stakeholder_id":"<stakeholder-id>","tone_variant":"direct"}' \
271:   http://localhost:${API_PORT:-8000}/api/drafts
272: ```
273: 
274: **Expected**: `200`, `checks_passed: true`, a message opening with the
275: specific evidence-backed failure, exactly one ask, and every fact traceable
276: back to real evidence/thread history/profile data. A draft that fails any of
277: the five checks returns `422` with the same generic message
278: `architecture/06-error-handling.md` already defines for a generation
279: error — never a partial draft, never a message naming which check failed.
280: 
281: Copy or log a generated draft as manually sent:
282: 
283: ```bash
284: curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
285:   http://localhost:${API_PORT:-8000}/api/drafts/<draft-id>/copy
286: curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
287:   http://localhost:${API_PORT:-8000}/api/drafts/<draft-id>/log-as-sent
288: ```
289: 
290: **There is no `/send` route — anywhere, in any form (REQ-M10-P1).** A
291: request against `.../send` returns `404` because no such route is ever
292: registered; `tests/experience/test_no_external_transport.py` mechanically
293: confirms no file this feature touches even imports an outbound-transport
294: client (SMTP, HTTP client used for a third-party send, chat/CRM SDK) — a
295: structural guarantee, not just an absent route. The Ask agent's
296: `draft_handoff` response (feature 008) now opens a real panel in the
297: dashboard instead of a placeholder message. See
298: `specs/009-draft-composer/quickstart.md` for the full validation walkthrough,
299: including the scripted red-team case per check.
300: 
301: ## Feedback Memory (Phase 10)
302: 
303: "The learning loop." A single-click verdict (`correct`/`false_alarm`/
304: `resolved`) on any finding-bearing card — the evidence trace panel, reached
305: from the dashboard or an Ask-agent answer — recomputes that pattern's
306: damping weight, which every future scoring run reads as a multiplicative
307: term. No retraining, no fine-tuning: one stored number, always shown with a
308: plain-language reason. **No new environment prerequisite, no migration** —
309: `feedback_verdicts`/`damping_weights` have existed, unpopulated, since
310: feature 001.
311: 
312: Mark a finding a false alarm, twice, then confirm the pattern later:
313: 
314: ```bash
315: TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
316:   -H "Content-Type: application/json" \
317:   -d '{"username":"marta","password":"agentic-demo-2026"}' \
318:   | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
319: 
320: curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
321:   -H "Content-Type: application/json" \
322:   -d '{"finding_id":"<finding-id>","verdict":"false_alarm"}' \
323:   http://localhost:${API_PORT:-8000}/api/feedback
324: curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
325:   -H "Content-Type: application/json" \
326:   -d '{"finding_id":"<finding-id>","verdict":"false_alarm"}' \
327:   http://localhost:${API_PORT:-8000}/api/feedback
328: curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
329:   -H "Content-Type: application/json" \
330:   -d '{"finding_id":"<finding-id>","verdict":"correct"}' \
331:   http://localhost:${API_PORT:-8000}/api/feedback
332: ```
333: 
334: **Expected**: three `204`s; `damping_weights` for that finding's pattern
335: (`reader_type+finding_type`) shows `weight` at `0.500` → `0.250` → `0.2875`
336: (REQ-M6-CAL-03a's worked values) — losing trust is faster than regaining
337: it, by design. The pattern's evidence trace (`GET /api/evidence/{id}`) now
338: carries a non-null `disclosure_text`; a fresh scoring run reads the new
339: weight, but the `score_run` that existed before any of these calls stays
340: byte-identical. `false_alarm`/`correct` submitted with only an `issue_id`
341: (no `finding_id`) return `422` — one click on a multi-reader issue can
342: never touch several different readers' weights at once (FR-005a). See
343: `specs/010-feedback-memory/quickstart.md` for the full validation
344: walkthrough.

(End of file - total 344 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/run_readers.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/run_readers.py</path>
<type>file</type>
<content>
1: """Manual `RunReadersUseCase` trigger, mirroring `scripts/run_collector.py`/
2: `compute_score.py`'s pattern — runs all eight M5 readers over the ledger's
3: current state, gates every finding through M5a before persisting (feature
4: 007), and prints a per-reader summary, including any isolated failure
5: (FR-014a).
6: 
7: Run after ``scripts/run_collector.py`` (and, for a real Tone finding,
8: ``scripts/confirm_baseline.py``):
9:     uv run python scripts/run_readers.py
10: """
11: 
12: import asyncio
13: import sys
14: from pathlib import Path
15: 
16: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
17: 
18: from app.config import settings  # noqa: E402
19: from app.db import async_session_factory  # noqa: E402
20: from app.ingestion.adapters.encryption import BucketedFernetEncryption  # noqa: E402
21: from app.ingestion.adapters.key_store import FileKeyStore  # noqa: E402
22: from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter  # noqa: E402
23: from app.readers.adapters.openai_embedding import OpenAIEmbeddingAdapter  # noqa: E402
24: from app.readers.adapters.sqlalchemy_repository import (  # noqa: E402
25:     SqlAlchemyAbsenceEventRepository,
26:     SqlAlchemyCandidateCorpusRepository,
27:     SqlAlchemyConfirmedBaselineRepository,
28:     SqlAlchemyEventExistenceRepository,
29:     SqlAlchemyFindingRepository,
30:     SqlAlchemyFindingTypeConfigRepository,
31:     SqlAlchemyMeetingTranscriptRepository,
32:     SqlAlchemyMessageEventRepository,
33:     SqlAlchemyQuarantineRepository,
34:     SqlAlchemyRelationshipContext,
35:     SqlAlchemyResponsePairRepository,
36:     SqlAlchemyRollupRepository,
37: )
38: from app.readers.application.absence_reader import AbsenceReader  # noqa: E402
39: from app.readers.application.commitment_reader import CommitmentReader  # noqa: E402
40: from app.readers.application.intent_reader import IntentReader  # noqa: E402
41: from app.readers.application.meeting_reader import MeetingReader  # noqa: E402
42: from app.readers.application.recurrence_reader import RecurrenceReader  # noqa: E402
43: from app.readers.application.relationship_reader import RelationshipReader  # noqa: E402
44: from app.readers.application.tone_reader import ToneReader  # noqa: E402
45: from app.readers.application.usage_reader import UsageReader  # noqa: E402
46: from app.readers.application.use_cases import RunReadersUseCase  # noqa: E402
47: from app.readers.application.validation_gate import ValidationGate  # noqa: E402
48: 
49: 
50: async def run() -> None:
51:     encryption = BucketedFernetEncryption(
52:         FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
53:     )
54:     async with async_session_factory() as session:
55:         findings = SqlAlchemyFindingRepository(session)
56:         messages = SqlAlchemyMessageEventRepository(session, encryption)
57:         gate = ValidationGate(
58:             finding_type_config=SqlAlchemyFindingTypeConfigRepository(session),
59:             event_existence=SqlAlchemyEventExistenceRepository(session),
60:         )
61:         quarantine = SqlAlchemyQuarantineRepository(session)
62:         llm = AnthropicLLMAdapter(settings.anthropic_api_key, settings.reader_model_id)
63: 
64:         readers = [
65:             CommitmentReader(SqlAlchemyResponsePairRepository(session), findings),
66:             UsageReader(SqlAlchemyRollupRepository(session), findings),
67:             AbsenceReader(SqlAlchemyAbsenceEventRepository(session), findings),
68:             RelationshipReader(SqlAlchemyRelationshipContext(session), findings),
69:             RecurrenceReader(
70:                 SqlAlchemyCandidateCorpusRepository(session),
71:                 OpenAIEmbeddingAdapter(settings.openai_api_key),
72:                 findings,
73:             ),
74:             ToneReader(
75:                 messages,
76:                 SqlAlchemyConfirmedBaselineRepository(session, encryption),
77:                 llm,
78:                 findings,
79:             ),
80:             IntentReader(messages, llm, findings),
81:             MeetingReader(
82:                 SqlAlchemyMeetingTranscriptRepository(session, encryption), llm, findings
83:             ),
84:         ]
85:         use_case = RunReadersUseCase(
86:             readers=readers, findings=findings, gate=gate, quarantine=quarantine
87:         )
88:         results = await use_case.execute()
89: 
90:         for result in results:
91:             if result.error is None:
92:                 print(
93:                     f"{result.reader_type}: findings_persisted={result.findings_persisted} "
94:                     f"findings_quarantined={result.findings_quarantined}"
95:                 )
96:             else:
97:                 print(
98:                     f"{result.reader_type}: findings_persisted={result.findings_persisted} "
99:                     f"findings_quarantined={result.findings_quarantined} "
100:                     f"FAILED — {result.error}"
101:                 )
102: 
103: 
104: if __name__ == "__main__":
105:     asyncio.run(run())

(End of file - total 105 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/compute_score.py"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/compute_score.py</path>
<type>file</type>
<content>
1: """Manual `RecomputeScoreUseCase` trigger (`trigger = manual`), mirroring
2: `scripts/run_collector.py`'s pattern.
3: 
4: Run after ``scripts/seed_score_fixture.py``:
5:     uv run python scripts/compute_score.py
6: """
7: 
8: import asyncio
9: import sys
10: from pathlib import Path
11: 
12: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
13: 
14: from app.db import async_session_factory  # noqa: E402
15: from app.scoring.adapters.sqlalchemy_repository import (  # noqa: E402
16:     SqlAlchemyClientProfileMultipliers,
17:     SqlAlchemyCoverageCheck,
18:     SqlAlchemyDampingRepository,
19:     SqlAlchemyFindingRepository,
20:     SqlAlchemyScoreRunRepository,
21: )
22: from app.scoring.application.use_cases import RecomputeScoreUseCase  # noqa: E402
23: 
24: 
25: async def run() -> None:
26:     async with async_session_factory() as session:
27:         use_case = RecomputeScoreUseCase(
28:             findings=SqlAlchemyFindingRepository(session),
29:             score_runs=SqlAlchemyScoreRunRepository(session),
30:             profile=SqlAlchemyClientProfileMultipliers(session),
31:             damping=SqlAlchemyDampingRepository(session),
32:             coverage=SqlAlchemyCoverageCheck(session),
33:         )
34:         run_result = await use_case.execute(trigger="manual")
35:         print(
36:             f"score={run_result.score:.2f} band={run_result.band} "
37:             f"total_points={run_result.total_points:.2f}"
38:         )
39: 
40: 
41: if __name__ == "__main__":
42:     asyncio.run(run())

(End of file - total 42 lines)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 4.4s)

_Thinking:_

Now I have a very thorough understanding of the project. Let me synthesize this into a comprehensive plan for adding new events to test the functionality.

Let me also quickly check the .env.example and how the docker-compose is set up to confirm the running pattern.

Tengo una visión completa del proyecto. Déjame verificar un par de detalles finales sobre la configuración.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/.env.example"
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/.env.example</path>
<type>file</type>
<content>
1: # One deployment = one client = one .env file — never shared across stacks, never
2: # committed with real values (architecture/03-technology-stack.md, constitution
3: # "Isolation model"). Copy this file to .env and fill in real values for local dev.
4: 
5: # --- Database ---
6: POSTGRES_USER=postgres
7: POSTGRES_PASSWORD=postgres
8: POSTGRES_DB=agentic_churn
9: DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/agentic_churn
10: 
11: # app_role / shredder_role grants (data-base/10-ddl-appendix.md §Roles and grants) —
12: # change these for any non-local deployment.
13: APP_ROLE_PASSWORD=app_role_dev_password
14: SHREDDER_ROLE_PASSWORD=shredder_role_dev_password
15: 
16: # --- Encryption (Phase 1: manual key file; Phase 2: Cloud KMS — architecture/03) ---
17: # Path to the per-deployment data key used for pgcrypto column-level encryption of
18: # message bodies. Never commit the key file itself.
19: ENCRYPTION_KEY_PATH=./secrets/data.key
20: # Identifier stored in events.data_key_ref / raw_envelopes.data_key_ref (never the key
21: # itself) — one active key per deployment in Phase 1 (specs/003-ingestion-and-context/
22: # research.md), so a static identifier is enough until Phase 11 key rotation.
23: ENCRYPTION_KEY_ID=local-v1
24: 
25: # --- Client profile (specs/003-ingestion-and-context) ---
26: # The CS lead edits this YAML file directly (MVP) — POST /api/profile/reload re-reads it.
27: CLIENT_PROFILE_PATH=./demo/client-profile.yaml
28: 
29: # --- Host-side port overrides (FR-010) ---
30: # Defaults below match docker-compose.yml's fallback values — override only if one of
31: # these ports is already in use on your machine (spec.md Edge Cases: port conflicts).
32: API_PORT=8000
33: DB_PORT=5432
34: WEB_PORT=5173
35: 
36: # --- Auth (specs/002-dashboard-shell) ---
37: # Must match the host-side URL the browser actually loads the frontend from — if you
38: # override WEB_PORT above, update this too.
39: WEB_ORIGIN=http://localhost:5173
40: TOKEN_LIFETIME_HOURS=12
41: 
42: # --- Readers (specs/005-deterministic-findings, specs/007-model-findings) ---
43: # Recurrence reader's embedding provider — no default, must be set for real use.
44: OPENAI_API_KEY=
45: # Tone/Intent readers' model provider — no default, must be set for real use.
46: ANTHROPIC_API_KEY=
47: READER_MODEL_ID=claude-haiku-4-5-20251001
48: 
49: # --- Narrator / Ask agent (specs/008-narrator-and-ask-agent) ---
50: # Same ANTHROPIC_API_KEY above, a higher-stakes-generation model tier.
51: GENERATION_MODEL_ID=claude-sonnet-5

(End of file - total 51 lines)
</content>
```

**Tool: grep**

**Input:**
```json
{
  "pattern": "collector_fixture_path|COLLECTOR_FIXTURE_PATH"
}
```

**Output:**
```
Found 8 matches
/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/scripts/run_collector.py:
  Line 44:         collector = SimulatedCollector(Path(settings.collector_fixture_path))


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/specs/004-score-engine/quickstart.md:
  Line 110: COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \

  Line 169: COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/specs/010-feedback-memory/tasks.md:
  Line 414:       `ENCRYPTION_KEY_PATH`/`CLIENT_PROFILE_PATH`/`COLLECTOR_FIXTURE_PATH`


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/specs/008-narrator-and-ask-agent/quickstart.md:
  Line 162: COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/specs/005-deterministic-findings/quickstart.md:
  Line 115: COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/specs/007-model-findings/quickstart.md:
  Line 190: COLLECTOR_FIXTURE_PATH="../demo/fixtures/meridian-week.json" \


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/config.py:
  Line 47:     collector_fixture_path: str = "./demo/fixtures/meridian-week.json"

```

---

## Assistant (Plan · GLM-5.2 · 113.3s)

_Thinking:_

Now I have a comprehensive picture. Let me put together a plan for the user.

Key findings about the project:

1. **Architecture**: This is "Agentic Churn" - a customer health monitoring agent. It has 4 tiers: Ingestion (M1) → Context (M3) → Reasoning (M5/M6) → Experience (M8-M10).

2. **How events get into the system**: There's exactly one concrete collector: `SimulatedCollector` which reads a JSON fixture file. The fixture path is configurable via `settings.collector_fixture_path` (env: `COLLECTOR_FIXTURE_PATH`, default `./demo/fixtures/meridian-week.json`).

3. **The fixture format**: A JSON array of events. Each event has a `source_type` field. The currently supported source types in `SimulatedCollector`:
   - `gmail` → `_normalize_gmail` → requires `source_native_id`, `occurred_at`, `from`, `text`
   - `zendesk` → `_normalize_zendesk` → requires `source_native_id`, `occurred_at`, `reporter`, `ticket_number`, `title`, `product_area`, `state`, optionally `reopen_count`
   - `warehouse` → `_normalize_warehouse` → requires `source_native_id`, `occurred_at`, `metric`, `product_area`, `value_delta_pct`
   - `slack` → `_normalize_slack` → requires `source_native_id`, `occurred_at`, `from`, `text`
   - `csat` → `_normalize_csat` → requires `source_native_id`, `occurred_at`, `respondent`, `score`, optionally `comment`
   - `calendar` → `_normalize_calendar` → requires `source_native_id`, `occurred_at`, `attendee`, `series_id`, `consent_documented`, `transcript`

4. **The event types mapping** (`_event_type_for_source`):
   - zendesk → `ticket_state_change`
   - warehouse → `usage_measurement`
   - csat → `survey_response`
   - transcripts (from calendar) → `meeting`
   - gmail, slack → `message`

5. **The pipeline to run after adding events**:
   - `python scripts/run_collector.py --source simulated` — ingests events from the fixture, appends to ledger, runs replay (rebuilds projections)
   - `python scripts/confirm_baseline.py` — (only for Tone reader, needs a confirmed baseline window)
   - `python scripts/run_readers.py` — runs all 8 readers, gates findings
   - `python scripts/compute_score.py` — computes the score (run twice to settle the band)
   - `python scripts/run_narrator.py` — generates the explanation

6. **Idempotency**: The `idempotency_key` is derived from `(source_type, source_native_id)`. So if you re-run the same fixture, duplicates are skipped. To add NEW events, you must use new `source_native_id` values.

7. **Identity resolution**: The `from`/`reporter`/`respondent`/`attendee` field is matched against stakeholders in the client profile (`demo/client-profile.yaml`). Currently `ana.reyes@meridian.com` → `stk_ana`, `diego@meridian.com` → `stk_diego`. If you add an event from a new address, it'll be `unresolved` (which is fine - the system abstains, doesn't guess).

8. **Phase 1 sources** (always expected): gmail, zendesk, warehouse. Phase 2 sources (slack, csat, transcripts) only count as "expected" in coverage if the fixture actually contains them.

9. **Product principles to respect** (P1-P7): 
   - Evidence or it doesn't exist (every finding cites event IDs)
   - Model interprets, code calculates (scoring engine has no LLM)
   - Each component refuses to do the next one's job
   - A human always sends (no send capability)
   - Admit what we cannot see
   - Silence is a success state
   - Context over sentiment (Tone is per-stakeholder baseline, not generic)

So the way to "add new Gmail events or events from another source" to test the application is:

**Option A (simplest, no code changes)**: Add new entries to the existing fixture `demo/fixtures/meridian-week.json` (or create a new fixture file and point `COLLECTOR_FIXTURE_PATH` at it). Each new Gmail event needs: `source_type: "gmail"`, a unique `source_native_id`, `occurred_at`, `from`, `text`. Then re-run the pipeline scripts.

**Option B (new fixture file)**: Create a new fixture file (e.g. `demo/fixtures/my-test-events.json`) with a mix of events, and run the collector with `COLLECTOR_FIXTURE_PATH` env var pointed at it.

**Option C (new source type)**: If they want a source type not yet supported (e.g. jira, intercom), they'd need to:
1. Add a new normalizer function `_normalize_<source>` in `simulated_collector.py`
2. Register it in `_NORMALIZERS`
3. Add the display name in `_SOURCE_DISPLAY_NAMES`
4. Add the event_type mapping in `_event_type_for_source` in `use_cases.py` (if it shouldn't default to "message")
5. Possibly update `_MVP_SOURCE_TYPES` or `_POST_MVP_SOURCE_TYPES` in `RunCollectorUseCase`
6. Update the `sources.source_type` enum in the DDL (data-base/10-ddl-appendix.md) + an Alembic migration — per AGENTS.md, schema changes go through the DDL appendix first.

I should clarify with the user what they want, since "adicionar nuevos eventos de gmail, u otra fuente" is a bit ambiguous:
- Do they want to add more Gmail messages to the existing test scenario? (Option A — easiest)
- Do they want to test with a completely different set of events (different scenario/client)? (Option B)
- Do they want to add a brand new source type that doesn't exist yet (e.g. Jira, Teams)? (Option C — requires code + schema changes)

Let me present a plan and ask the clarifying question. Since I'm in plan mode, I must NOT make any edits. Let me present a well-researched plan.

Actually, let me ask the clarifying question first since the intent is ambiguous, then I can give the tailored plan. But I can also present the plan with all three options and let them pick. Let me present the plan covering the options clearly and ask which path they want.

I'll keep it concise but complete. Let me structure the answer in Spanish since the user wrote in Spanish (but note AGENTS.md says repo content stays in English — that applies to files/commits, not to my conversational response with the user).

Let me write the plan.

He revisado el proyecto a fondo. Aquí está mi análisis y plan.

## Cómo entra un evento al sistema hoy

El proyecto tiene **un único colector concreto**: `SimulatedCollector` (`backend/app/ingestion/adapters/simulated_collector.py:152`), que lee un archivo JSON de fixtures en vez de una API real. La ruta se configura con `COLLECTOR_FIXTURE_PATH` (por defecto `./demo/fixtures/meridian-week.json`, ver `backend/app/config.py:47`).

El flujo completo para probar funcionalidad (según `README.md` y `demo/01-live-demo-runbook.md`):

```
scripts/run_collector.py --source simulated   # ingesta + append al ledger + replay
scripts/confirm_baseline.py                    # solo si quieres que Tone dispare
scripts/run_readers.py                         # 8 readers + validation gate
scripts/compute_score.py                       # scoring (corre 2x para asentar banda)
scripts/run_narrator.py                        # explicación
```

## Formato del fixture

Cada evento es un objeto JSON con `source_type` + campos por fuente. Los `source_type` soportados hoy en `SimulatedCollector` (`simulated_collector.py:142-149`) y sus campos obligatorios:

| `source_type` | Requiere | Se convierte en `event_type` |
|---|---|---|
| `gmail` | `source_native_id`, `occurred_at`, `from`, `text` | `message` |
| `slack` | `source_native_id`, `occurred_at`, `from`, `text` | `message` |
| `zendesk` | `source_native_id`, `occurred_at`, `reporter`, `ticket_number`, `title`, `product_area`, `state` (+ `reopen_count` opt) | `ticket_state_change` |
| `warehouse` | `source_native_id`, `occurred_at`, `metric`, `product_area`, `value_delta_pct` | `usage_measurement` |
| `csat` | `source_native_id`, `occurred_at`, `respondent`, `score` (+ `comment` opt) | `survey_response` |
| `calendar` | `source_native_id`, `occurred_at`, `attendee`, `series_id`, `consent_documented`, `transcript` | `meeting` |

**Reglas críticas que ya aprendí del código (no negociables):**
- **Idempotency**: la llave es `hash(source_type, source_native_id)`. Para añadir eventos *nuevos* debes usar `source_native_id` *nuevos*; si repites uno, se cuenta como duplicado y se salta (`use_cases.py:382-384`).
- **Identidad**: `from`/`reporter`/`respondent`/`attendee` se resuelve contra `demo/client-profile.yaml`. Hoy solo `ana.reyes@meridian.com`→`stk_ana` y `diego@meridian.com`→`stk_diego`. Un correo nuevo queda `unresolved` (lo cual es válido — el sistema se abstiene, no adivina, REQ-M1-05).
- **`product_area`** debe existir en el perfil (`tracking_api` o `reporting`) o se ignora.
- **Exclusiones** del perfil (`legal_threads`, `commercial_negotiation`) redactan el body si aparece una frase marcadora (`use_cases.py:219-236`).
- **Calendar** sin `consent_documented: true` se descarta antes de llegar al ledger (`simulated_collector.py:168-172`).
- Fuentes Phase 1 (`gmail`, `zendesk`, `warehouse`) siempre se esperan; las Phase 2 solo si el fixture las trae (`use_cases.py:283-297`).

## Tres caminos posibles para añadir eventos

Necesito que elijas uno antes de ejecutar, porque el alcance es muy distinto:

**Tool: question**

**Input:**
```json
{
  "questions": [
    {
      "question": "¿Qué quieres hacer exactamente? El alcance cambia bastante segun la opcion.",
      "header": "Tipo de adicion de eventos",
      "options": [
        {
          "label": "Mas eventos Gmail/Zendesk/etc al escenario Meridian",
          "description": "Anadir filas al fixture existente demo/fixtures/meridian-week.json (o crear uno nuevo apuntado por COLLECTOR_FIXTURE_PATH) usando source_type ya soportados. Solo editas JSON, no tocas codigo ni esquema. Es lo mas rapido para probar la app."
        },
        {
          "label": "Un escenario nuevo con otro cliente",
          "description": "Crear un fixture + client-profile.yaml nuevos (otro cliente, otros stakeholders) y levantarlos con env vars. Mas trabajo de autoría pero sigue sin tocar codigo ni DB."
        },
        {
          "label": "Una fuente nueva no soportada (ej. Jira, Teams)",
          "description": "Requiere anadir un normalizador en simulated_collector.py, mapear event_type en use_cases.py, actualizar _MVP/_POST_MVP_SOURCE_TYPES, y — segun AGENTS.md — cambiar el enum sources.source_type en data-base/10-ddl-appendix.md + migracion Alembic. Es lo mas invasivo."
        }
      ]
    }
  ]
}
```

**Output:**
```
User has answered your questions: "¿Qué quieres hacer exactamente? El alcance cambia bastante segun la opcion."="Mas eventos Gmail/Zendesk/etc al escenario Meridian". You can now continue with the user's answers in mind.
```

---

## Assistant (Plan · GLM-5.2 · 11.0s)

_Thinking:_

The user chose Option 1: add more Gmail/Zendesk/etc events to the existing Meridian scenario. This is the easiest path - just edit JSON, no code changes.

Let me put together the concrete plan. I'm still in Plan Mode, so I must NOT make any edits. I just present the plan.

Let me think about what events would be useful to add to test the functionality more thoroughly. Looking at the existing fixture and the walkthrough, I can suggest:

1. **More Gmail messages from Ana** — to give the Tone reader more samples (it needs ≥5 in a confirmed baseline window). Currently the fixture has only 2 gmail messages from Ana (msg-8831, msg-8845) and 1 from Diego (msg-8790). To exercise Tone properly you want more history in the baseline window.

2. **More Zendesk ticket state changes** — to test the Commitment reader (broken promises, recurrence). You could add a ticket that's resolved within SLA, a ticket that's still open, a third reopen of ticket 456, etc.

3. **More warehouse measurements** — the Usage reader compares against an 8-week baseline. You could add weeks w35, w36 with different deltas to test the deviation logic.

4. **More Slack messages** — to test Absence (Diego going quiet) and Relationship readers. The Absence/Relationship readers in Phase 2 need a participant graph.

5. **More CSAT responses** — to test the usage deviation on CSAT scores.

6. **More calendar/transcripts** — to test the Meeting reader (needs consent_documented: true).

Let me also check what testing approach exists — `tests/strategy.md` mentions golden replay tests. Let me also confirm the test strategy to mention it in the plan.

Actually, I think I have enough. Let me present the concrete plan with:
- The exact file to edit
- The JSON schema per source type
- Example events to add (with realistic content matching the Meridian scenario)
- The idempotency caveat (use new source_native_id)
- The exact commands to run the pipeline
- The verification steps
- A note about keeping the walkthrough/seed/fixture in sync (per demo/03-environment-and-fixtures-checklist.md, three consumers must be regenerated together — but if they're just testing, not changing the canonical scenario, they can use a separate fixture file to avoid breaking the golden tests)

Important note: the demo/03 doc says the scenario, seed data, and fixture are kept in sync via a single regeneration script, and there are golden-replay tests (`tests/golden_replay/`). If the user edits `meridian-week.json` directly, those golden tests might break. So a safer approach is to create a *new* fixture file and point `COLLECTOR_FIXTURE_PATH` at it. Let me verify the golden test exists.

Permíteme verificar una cosa importante antes de finalizar el plan: si editar el fixture de Meridian rompería los golden tests.

**Tool: glob**

**Input:**
```json
{
  "pattern": "tests/golden_replay/**/*"
}
```

**Output:**
```
No files found
```

**Tool: glob**

**Input:**
```json
{
  "pattern": "tests/fixtures/golden-dashboard.json"
}
```

**Output:**
```
No files found
```

**Tool: grep**

**Input:**
```json
{
  "pattern": "meridian-week\\.json",
  "include": "*.py"
}
```

**Output:**
```
Found 4 matches
/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/app/config.py:
  Line 47:     collector_fixture_path: str = "./demo/fixtures/meridian-week.json"


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/tests/ingestion/test_post_mvp_sources_real_db.py:
  Line 43: _FIXTURE = Path(__file__).resolve().parents[2] / "demo" / "fixtures" / "meridian-week.json"

  Line 182:     this regression check (`meridian-week.json` itself was extended in place


/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/tests/unit/test_simulated_collector.py:
  Line 33: _FIXTURE = Path(__file__).resolve().parents[3] / "demo" / "fixtures" / "meridian-week.json"

```

---

## Assistant (Plan · GLM-5.2 · 4.7s)

_Thinking:_

Important finding: `meridian-week.json` is referenced by tests directly (not just by config). So editing it in place would break:
- `tests/ingestion/test_post_mvp_sources_real_db.py` (which has a regression check — line 182 says "meridian-week.json itself was extended in place")
- `tests/unit/test_simulated_collector.py`

So the **safer** approach is to create a *new* fixture file (e.g. `demo/fixtures/meridian-week-extra.json` or `demo/fixtures/meridian-test-events.json`) and point `COLLECTOR_FIXTURE_PATH` at it via env var, rather than editing the canonical `meridian-week.json` in place. This way golden/unit tests stay green and the user can experiment freely.

Let me check the test files briefly to understand what they assert.

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/tests/ingestion/test_post_mvp_sources_real_db.py",
  "offset": 1,
  "limit": 60
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/tests/ingestion/test_post_mvp_sources_real_db.py</path>
<type>file</type>
<content>
1: """Real-DB: Slack/CSAT/Calendar (specs/011-production-hardening, User Story 6,
2: FR-020/021/022/023) actually reach the ledger and the readers designed to
3: consume them.
4: 
5: Deliberately stops short of asserting a statistically-triggered `csat_
6: deviation`/chat-silence `contact_absence` Finding: those readers' own
7: decision logic (`z_score`, cadence math) is already exhaustively covered by
8: `tests/readers/test_usage_reader.py`/`test_absence_reader.py`'s pure
9: domain-function tests and `tests/readers/test_run_readers_use_case.py`'s
10: real-DB pass — forcing enough synthetic historical samples here just to
11: cross a statistical threshold would duplicate that coverage without adding
12: confidence. What genuinely is new and untested elsewhere is whether
13: Post-MVP-sourced *data* actually reaches each reader's own input port at
14: all (FR-021/022) and whether FR-023's consent gate holds end to end — that's
15: what this file asserts, directly against each reader's real adapter.
16: """
17: 
18: import json
19: import uuid
20: from datetime import UTC, datetime, timedelta
21: from pathlib import Path
22: 
23: from sqlalchemy import text
24: 
25: from app.config import settings
26: from app.db import async_session_factory, engine
27: from app.ingestion.adapters.encryption import BucketedFernetEncryption
28: from app.ingestion.adapters.key_store import FileKeyStore
29: from app.ingestion.adapters.simulated_collector import SimulatedCollector
30: from app.ingestion.adapters.sqlalchemy_repositories import (
31:     SqlAlchemyClientProfileContext,
32:     SqlAlchemyCollectorRunRepository,
33:     SqlAlchemyEventRepository,
34: )
35: from app.ingestion.application.use_cases import ComputeRollupsUseCase, RunCollectorUseCase
36: from app.readers.adapters.sqlalchemy_repository import (
37:     SqlAlchemyMeetingTranscriptRepository,
38:     SqlAlchemyMessageEventRepository,
39:     SqlAlchemyRollupRepository,
40: )
41: from tests.conftest import ledger_floor
42: 
43: _FIXTURE = Path(__file__).resolve().parents[2] / "demo" / "fixtures" / "meridian-week.json"
44: _PHASE1_ONLY_FIXTURE = (
45:     Path(__file__).resolve().parents[2] / "demo" / "fixtures" / "meridian-week-phase1-only.json"
46: )
47: 
48: 
49: async def _build_fixture(tmp_path: Path, suffix: str, session, source: Path = _FIXTURE) -> Path:
50:     items = json.loads(source.read_text())
51:     floor = await ledger_floor(session)
52:     earliest = min(datetime.fromisoformat(item["occurred_at"]) for item in items)
53:     offset = floor - earliest + timedelta(seconds=1)
54:     ticket_offset = int(suffix, 16) % 900000 + 100000
55:     for item in items:
56:         item["source_native_id"] = f"{item['source_native_id']}-{suffix}"
57:         item["occurred_at"] = (datetime.fromisoformat(item["occurred_at"]) + offset).isoformat()
58:         if "ticket_number" in item:
59:             item["ticket_number"] += ticket_offset
60:     fixture_path = tmp_path / "fixture.json"

(Showing lines 1-60 of 199. Use offset=61 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/tests/unit/test_simulated_collector.py",
  "offset": 1,
  "limit": 60
}
```

**Output:**
```
<path>/Users/juanhuarachicoderoad/Projects/hackaton/agentic-churn/backend/tests/unit/test_simulated_collector.py</path>
<type>file</type>
<content>
1: """Run `SimulatedCollector` against the Meridian fixture twice (idempotency, FR-010);
2: confirm identity resolution matches Ana and leaves the Zendesk reporter unresolved
3: (REQ-M1-04/05); confirm the sixth fixture item's `legal_threads` content is redacted
4: (H1 remediation, REQ-M1-09); confirm a simulated source failure produces an honest
5: coverage report (G1 remediation, REQ-M1-07/08).
6: 
7: Each test builds its own copy of the committed fixture with uuid-suffixed native IDs
8: so repeated test-suite runs never collide on `idempotency_key` (tests/conftest.py's
9: docstring explains why: `events` can't be deleted, so isolation comes from
10: uniqueness, not cleanup).
11: """
12: 
13: import json
14: import uuid
15: from datetime import UTC, datetime, timedelta
16: from pathlib import Path
17: 
18: from sqlalchemy import text
19: 
20: from app.config import settings
21: from app.db import async_session_factory, engine
22: from app.ingestion.adapters.encryption import BucketedFernetEncryption
23: from app.ingestion.adapters.key_store import FileKeyStore
24: from app.ingestion.adapters.simulated_collector import SimulatedCollector
25: from app.ingestion.adapters.sqlalchemy_repositories import (
26:     SqlAlchemyClientProfileContext,
27:     SqlAlchemyCollectorRunRepository,
28:     SqlAlchemyEventRepository,
29: )
30: from app.ingestion.application.use_cases import RunCollectorUseCase
31: from tests.conftest import ledger_floor
32: 
33: _FIXTURE = Path(__file__).resolve().parents[3] / "demo" / "fixtures" / "meridian-week.json"
34: 
35: 
36: async def _build_fixture(tmp_path: Path, suffix: str, session) -> Path:
37:     items = json.loads(_FIXTURE.read_text())
38:     # Shift every item's occurred_at forward by the same offset, past the ledger's
39:     # current floor, preserving relative spacing exactly (ticket #398's 2-hour
40:     # created->resolved gap must stay 2 hours) — EventRepositoryPort.append requires
41:     # global occurred_at-order appends (tests/conftest.py's `ledger_floor` docstring),
42:     # but the fixture's own timestamps are fixed 2026 dates that would otherwise
43:     # collide with whatever later-dated data other tests have already appended.
44:     floor = await ledger_floor(session)
45:     earliest = min(datetime.fromisoformat(item["occurred_at"]) for item in items)
46:     offset = floor - earliest + timedelta(seconds=1)
47:     # ticket_number offset, not just source_native_id's suffix: _rebuild_projections
48:     # (app/ingestion/application/use_cases.py) keys its open_pairs tracking by
49:     # ticket_number across the WHOLE ledger's history, not by source_native_id — a
50:     # uuid-suffixed native_id alone still lets this test's ticket #456 shadow (or be
51:     # shadowed by) any other real or synthetic ticket #456 elsewhere in the ledger.
52:     # 100000+ stays well clear of the demo fixture's own real ticket numbers (398,
53:     # 456).
54:     ticket_offset = int(suffix, 16) % 900000 + 100000
55:     for item in items:
56:         item["source_native_id"] = f"{item['source_native_id']}-{suffix}"
57:         item["occurred_at"] = (datetime.fromisoformat(item["occurred_at"]) + offset).isoformat()
58:         if "ticket_number" in item:
59:             item["ticket_number"] += ticket_offset
60:     fixture_path = tmp_path / "fixture.json"

(Showing lines 1-60 of 193. Use offset=61 to continue.)
</content>
```

---

## Assistant (Plan · GLM-5.2 · 40.2s)

_Thinking:_

Critical finding confirmed: Both test files read `meridian-week.json` directly (not via `COLLECTOR_FIXTURE_PATH`), and they assert specific things about its contents (e.g., the 6th item's `legal_threads` content is redacted — that's `gmail-msg-8845` with "contract dispute"). The tests build their own copies with suffixed IDs/timestamps shifted, but they assert on **structural** properties that depend on the fixture's content (item count, redaction of the legal_threads item, identity resolution of Ana, etc.).

So **editing `meridian-week.json` in place would break these tests**. The safe approach is definitively: **create a new fixture file** and point `COLLECTOR_FIXTURE_PATH` at it.

Now I have everything I need. Let me write the final plan.

The plan:

1. **Create a new fixture file** `demo/fixtures/meridian-extra.json` (don't edit `meridian-week.json` — it's pinned by 2 test files).
2. Point `COLLECTOR_FIXTURE_PATH` env var at it (via `.env` or inline when running the script).
3. Author events using the existing `source_type` values and their required fields, with **new** `source_native_id` values (idempotency).
4. Keep `from`/`respondent`/`attendee` either as `ana.reyes@meridian.com` or `diego@meridian.com` (resolved) or a new address (unresolved — valid).
5. Keep `product_area` to `tracking_api` or `reporting` (or null).
6. Respect exclusion markers (legal_threads / commercial_negotiation) if you want to test redaction.
7. For calendar: `consent_documented: true` or it's dropped.
8. Run the pipeline scripts in order.
9. Verify via the API endpoints (`/api/dashboard`, `/api/coverage`, `/api/ask`) and DB queries.

I should give concrete example events the user can copy. Let me draft a few realistic ones matching the Meridian scenario, that exercise different readers:
- A new Gmail from Ana (Tone + Intent) — maybe an escalation phrase
- A new Gmail from a new unresolved address (tests REQ-M1-05)
- A new Zendesk ticket reopened a 3rd time (Recurrence)
- A new Zendesk ticket resolved fast (positive Commitment)
- A new warehouse week w35 with a further drop (Usage)
- A new CSAT from Diego (Usage on CSAT)
- A new Slack message from Diego after his silence (Absence/Relationship reset)
- A new calendar transcript with consent (Meeting reader)

I'll present the plan concisely. Since I'm in plan mode, no edits. Let me write the final answer in Spanish (matching user), with concrete examples and the exact commands.

Let me also note: the user might want to test against the same DB where meridian-week was already ingested, OR a fresh DB. Since idempotency is keyed on (source_type, source_native_id), new IDs in the new fixture will append cleanly alongside the existing events. That's actually a nice property — the score will reflect the combined history. But if they want a clean run, `docker compose down -v && up` resets.

One more thing: the `run_collector.py` script hardcodes `window_start=window_end=now` (it's a bit of a no-op window — the SimulatedCollector ignores the window and returns all items). So the fixture's own timestamps are what matter, not the window. Good to know and mention.

Also note: to actually get a Tone finding, you need `confirm_baseline.py` first (needs ≥5 messages in the window). The current fixture only has 2 from Ana. If the user adds several more Ana gmail messages dated in a ~60-day window, they can then confirm a baseline and Tone will fire. I should mention this since "test the functionality" likely includes the Tone reader.

Let me write the final plan now.

Hallazgo clave: `meridian-week.json` está **fijado por dos tests** (`tests/unit/test_simulated_collector.py:33` y `tests/ingestion/test_post_mvp_sources_real_db.py:43`), que asertan propiedades estructurales (redacción del item legal, resolución de Ana, conteos). **Editarlo en sitio rompería los tests.** La ruta segura es crear un fixture nuevo.

## Plan concreto

### 1. Crear un fixture nuevo (sin tocar `meridian-week.json`)

Archivo: `demo/fixtures/meridian-extra.json` — un array JSON con eventos usando los `source_type` ya soportados. Ejemplos realistas que ejercitan distintos readers:

```json
[
  {
    "source_type": "gmail",
    "source_native_id": "gmail-msg-9001",
    "occurred_at": "2026-08-15T10:00:00-05:00",
    "from": "ana.reyes@meridian.com",
    "text": "Any update on the tracking API fix? Renewal is coming up and I need to brief the board again."
  },
  {
    "source_type": "gmail",
    "source_native_id": "gmail-msg-9002",
    "occurred_at": "2026-08-16T11:30:00-05:00",
    "from": "carlos.it@meridian.com",
    "text": "Heard about the API issues from Ana — is there a workaround?"
  },
  {
    "source_type": "zendesk",
    "source_native_id": "zendesk-456-reopened-3rd",
    "occurred_at": "2026-08-15T08:00:00-05:00",
    "reporter": "support-desk@meridian.zendesk.com",
    "ticket_number": 456,
    "title": "Slow API response",
    "reopen_count": 3,
    "product_area": "tracking_api",
    "state": "reopened"
  },
  {
    "source_type": "zendesk",
    "source_native_id": "zendesk-600-resolved",
    "occurred_at": "2026-08-16T09:00:00-05:00",
    "reporter": "support-desk@meridian.zendesk.com",
    "ticket_number": 600,
    "title": "Cannot login from mobile",
    "product_area": "reporting",
    "state": "resolved"
  },
  {
    "source_type": "warehouse",
    "source_native_id": "usage-tracking_api-w35",
    "occurred_at": "2026-08-19T00:00:00-05:00",
    "metric": "weekly_active_usage",
    "product_area": "tracking_api",
    "value_delta_pct": -28
  },
  {
    "source_type": "csat",
    "source_native_id": "csat-resp-2300",
    "occurred_at": "2026-08-17T12:00:00-05:00",
    "respondent": "ana.reyes@meridian.com",
    "score": 5,
    "comment": "Still waiting on the API fix, this is getting hard to defend internally."
  },
  {
    "source_type": "slack",
    "source_native_id": "slack-msg-4600",
    "occurred_at": "2026-08-18T10:00:00-05:00",
    "from": "diego@meridian.com",
    "text": "back from leave — checking in on the tracking_api incident, where are we?"
  },
  {
    "source_type": "calendar",
    "source_native_id": "calendar-series-qbr-2026w34",
    "occurred_at": "2026-08-18T15:00:00-05:00",
    "attendee": "ana.reyes@meridian.com",
    "series_id": "meridian-qbr",
    "consent_documented": true,
    "transcript": "Ana: The API reliability is now a board-level concern. Diego: Engineering is prioritizing the root cause fix, ETA end of next week."
  }
]
```

Qué ejercita cada uno:
- `gmail-msg-9001` → Tone (Ana, "board"/"renewal") + Intent (escalation language)
- `gmail-msg-9002` → identidad **unresolved** (carlos.it@meridian.com no está en el perfil — prueba REQ-M1-05)
- `zendesk-456-reopened-3rd` → Recurrence (3er reopen) + Commitment (sigue overdue)
- `zendesk-600-resolved` → Commitment positivo (resuelto rápido)
- `usage-tracking_api-w35` → Usage deviation (-28%)
- `csat-resp-2300` → CSAT deviation (6→5)
- `slack-msg-4600` → Relationship/Absence (Diego vuelve tras ausencia)
- `calendar-...-w34` → Meeting reader (consent true, transcript con compromiso verbal)

### 2. Reglas a respetar al autorar eventos

- **`source_native_id` únicos** — la idempotency key es `hash(source_type, source_native_id)` (`use_cases.py:382`). Repetir un ID → se cuenta como duplicado y se salta.
- **`from`/`respondent`/`attendee`** → `ana.reyes@meridian.com` o `diego@meridian.com` (resueltos) o uno nuevo (unresolved, válido). El sistema **nunca adivina** (REQ-M1-05).
- **`product_area`** → `tracking_api` o `reporting` (de `demo/client-profile.yaml`); cualquier otro se ignora.
- **Frases marcadoras** que disparan redacción (`use_cases.py:219-222`): "legal team", "contract dispute", "lawsuit" → `legal_threads`; "discount", "renewal price", "contract terms", "negotiat" → `commercial_negotiation`. Úsalas a propósito para probar redacción, o evítalas si no quieres que el body quede `[REDACTED]`.
- **Calendar** sin `consent_documented: true` se descarta antes del ledger (`simulated_collector.py:168-172`).
- **Orden** — no importa; `fetch()` ordena por `occurred_at` antes de append (requisito del hash chain).

### 3. Apuntar el colector al fixture nuevo

En `.env` (junto a `demo/`):

```
COLLECTOR_FIXTURE_PATH=./demo/fixtures/meridian-extra.json
```

O inyectarlo solo al correr el script (sin tocar `.env`):

```bash
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/meridian-extra.json api \
  python scripts/run_collector.py --source simulated
```

Nota: `run_collector.py:46-49` pasa `window_start=window_end=now` — la ventana es no-op; `SimulatedCollector.fetch()` la ignora y devuelve todos los items del archivo. Lo que importa son los `occurred_at` del JSON.

### 4. Decidir: DB limpia o acumular

- **Acumular sobre la corrida existente**: los eventos nuevos se append al ledger junto a los de `meridian-week.json` ya ingeridos (idempotency los separa por `source_native_id`). El score refleja la historia combinada. Más realista.
- **DB limpia**: `docker compose down -v && docker compose up -d --build`, luego `python scripts/seed.py`, luego corres solo el fixture nuevo. Más reproducible.

### 5. Ejecutar el pipeline completo

```bash
# Ingesta + append al ledger + replay (rebuilds response_pairs/event_threads)
docker compose exec api python scripts/run_collector.py --source simulated

# SOLO si quieres que Tone dispare: confirma baseline con >=5 mensajes de Ana
# en una ventana de 60 días (REQ-M6-CAL-04). El fixture extra aporta más samples.
docker compose exec api python scripts/confirm_baseline.py --stakeholder ana \
  --metric email_style --window-days 60

# 8 readers + validation gate
docker compose exec api python scripts/run_readers.py

# Scoring (corre 2x para que la banda asiente con hysteresis)
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py

# Narrador (explicación con fact-check)
docker compose exec api python scripts/run_narrator.py
```

Requisitos previos ya cubiertos por el README: `OPENAI_API_KEY` (Recurrence) y `ANTHROPIC_API_KEY` (Tone/Intent/Narrator) en `.env`.

### 6. Verificar

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Dashboard (score, contribuciones, narrator)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/dashboard | python3 -m json.tool

# Coverage (cuántas fuentes, cuántos findings en quarantine)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/coverage | python3 -m json.tool

# Pregunta al ask agent
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"why did the score go up?"}' http://localhost:8000/api/ask | python3 -m json.tool
```

Y a nivel DB, para ver los eventos nuevos realmente appendados:

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT id, event_type, occurred_at, stakeholder_id, product_area_id FROM events ORDER BY occurred_at DESC LIMIT 20;"
```

### 7. Caveat sobre el walkthrough/seed/fixture sync

`demo/03-environment-and-fixtures-checklist.md` documenta que el escenario canónico (`examples/01-end-to-end-walkthrough.md`), `data-base/11-seed-data.sql` y `demo/fixtures/meridian-week.json` se regeneran juntos. **Tu fixture nuevo es para prueba/experimentación, no parte del escenario canónico** — por eso lo mantenemos como archivo separado y no tocamos `meridian-week.json` ni el seed. Así los golden/unit tests siguen verdes y no rompes la consistencia documentada.

---

¿Quieres que proceda a crear `demo/fixtures/meridian-extra.json` con los eventos de ejemplo de arriba, o prefieres ajustar el contenido (más eventos, otro cliente, scores distintos) antes de que lo escriba?

---

