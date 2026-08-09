# 00 · Requirements overview & glossary

| | |
|---|---|
| **Document** | Requirements overview (spec-driven development root document) |
| **Version** | 1.0 |
| **Source of truth** | `base/Churn-Sentiment-Agent-Product-Specification.md` v1.0 |
| **Status** | Ready for technical review |

This folder turns the product specification into engineering-ready, testable requirements — one file per module, plus this overview and a traceability matrix. It follows a **spec-driven development (SDD)** discipline:

1. Every requirement has a stable ID and traces back to a section of the source spec.
2. Every requirement is written in **EARS syntax** (Easy Approach to Requirements Syntax): `WHEN <trigger>, THE SYSTEM SHALL <behavior>`, or `THE SYSTEM SHALL ALWAYS/NEVER <behavior>` for invariants.
3. Every module also lists explicit **prohibitions** — what it must never do — because the product's core discipline (spec P3) is components refusing each other's jobs.
4. Nothing is marked "done" without an acceptance criterion that can be mechanically checked.

## Requirement ID scheme

`REQ-<MODULE>-<NN>` — e.g. `REQ-M6-04` is the fourth requirement of the Scoring Engine module. Cross-cutting, non-functional requirements use `REQ-NFR-<NN>`. IDs are never reused or renumbered once assigned; a removed requirement is marked `RETIRED`, not deleted, so historical traceability holds.

## Module map

| File | Module(s) | Tier |
|---|---|---|
| `01-signal-collectors.md` | M1 · Signal collectors (incl. absence collector) | 1 · Ingestion |
| `02-event-ledger.md` | M2 · Event ledger | 1 · Ingestion |
| `03-client-profile.md` | M3 · Client profile | 2 · Context |
| `04-feedback-memory.md` | M4 · Feedback memory | 2 · Context |
| `05-interpreters-readers.md` | M5 · Interpreters, M5a · Validation gate | 3 · Reasoning |
| `06-scoring-engine.md` | M6 · Scoring engine | 3 · Reasoning |
| `07-narrator.md` | M7 · Narrator | 3 · Reasoning |
| `08-health-dashboard.md` | M8 · Health dashboard | 4 · Experience |
| `09-ask-agent.md` | M9 · Ask agent | 4 · Experience |
| `10-draft-composer.md` | M10 · Draft composer | 4 · Experience |
| `11-non-functional-requirements.md` | Cross-cutting (performance, privacy, security, determinism) | — |
| `12-traceability-matrix.md` | REQ-ID → spec section → module → acceptance test | — |

## Scope (from spec §3.2–3.3)

| In scope | Out of scope (v1) |
|---|---|
| One client relationship per deployment | Multi-client portfolio dashboard |
| Reading signals from connected sources | Writing to those sources |
| Producing a risk score with reasons | Automated actions of any kind |
| Drafting messages | **Sending messages — no send capability exists anywhere in the product** |
| Suggesting a plan | Executing a plan |
| Business-to-business account health | Individual consumer churn |

Explicit non-goals: not a helpdesk/CRM replacement; not a cancellation predictor; not an employee-performance tool; never surfaced to the client.

> **Resolved product decision:** the reference mockup (`base/mockup-mainPage.jpg`) shows a "Send & Log to CRM" button in the Action & Draft Hub. This conflicts with product principle **P4** and module **M10**. Requirement `REQ-M10-08` resolves this: the UI offers **"Log to CRM"** (writes an activity record only) and **"Copy draft"**, and contains no action that transmits the message to the client. See `10-draft-composer.md`.

## Personas (spec §3.1)

| Persona | Primary need | Requirements they drive |
|---|---|---|
| Customer Success lead *(primary)* | "Is this account safe? What needs me today?" | M8, M9 |
| Support lead | "Which of my forty tickets actually matters?" | M8, M9, M5 (Commitment reader) |
| Account executive | "What do I need to know before the renewal call?" | M8, M9 |
| Engineering manager *(occasional)* | "Is a technical issue damaging a commercial relationship?" | M5 (Recurrence reader), M9 |

## Product principles — the tie-breakers (spec §4)

| # | Principle | Enforced by |
|---|---|---|
| P1 | Evidence or it does not exist | M5a validation gate; `REQ-M5A-*` |
| P2 | The model interprets, code calculates | M6 has no model calls; `REQ-M6-01` |
| P3 | Each component refuses to do the next one's job | "Must never" clauses in every module file |
| P4 | A human always sends | `REQ-M10-08`; no send endpoint anywhere in the architecture |
| P5 | Admit what we cannot see | Coverage reporting; `REQ-M1-07`, `REQ-M8-06` |
| P6 | Silence is a success state | Healthy-state requirements; `REQ-M8-05` |
| P7 | Context over sentiment | Baseline-relative Tone reader; `REQ-M5-06` |

## Glossary (spec §5)

| Term | Meaning |
|---|---|
| Signal | Anything observable from a connected source |
| Event | One recorded fact in the ledger — a message, a state change, a measurement |
| Envelope | The standard wrapper a collector puts around a raw signal |
| Finding | A structured observation produced by a reader |
| Issue | A group of findings that share one underlying cause |
| Client profile | The hand-authored context card: people, priorities, promises |
| Score | 0–100 severity aggregate, recalculated from scratch every run |
| Band | Healthy / Watch / At risk |
| Trace | The clickable path from a number back to the original message |
| Baseline | How a person or metric normally behaves, drawn from a healthy period |
| Coverage | What the system could and could not see during a window |

## How to read a module requirements file

Each file (`01`–`10`) follows this template:

```
## Purpose
## User stories
## Functional requirements   (REQ-M#-01 ...)
## Explicit prohibitions     (must never)
## Inputs / Outputs
## Non-functional constraints
## Acceptance criteria
## Traceability
```
