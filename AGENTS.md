# AGENTS.md

Conventions for anyone — human or AI — working in this repository. If you're an AI coding agent, read this file before touching code; it tells you where the actual specification lives and which rules are non-negotiable versus stylistic.

## Where things live

| You're looking for... | Go to |
|---|---|
| What a module (M1–M10) is supposed to do | `requirements/<module>.md` — EARS-syntax, testable, one file per module |
| Why a technical decision was made | `architecture/`, `decisions/` |
| Exact table schemas | `data-base/10-ddl-appendix.md` is the source of truth; `data-base/02`–`data-base/12` are the annotated, example-driven companion docs |
| A worked example of the whole pipeline running once | `examples/01-end-to-end-walkthrough.md` — read this first if you're new here |
| What's in the first buildable release vs. deferred | `decisions/01-mvp-scope-and-phasing.md` |
| Sequence/flow diagrams | `sequences/` |

**`base/Churn-Sentiment-Agent-Product-Specification.md` is the original product brief (v1.2).** Everything else in this repo derives from it. If a requirement and the base spec ever seem to disagree, that's a bug to fix, not a judgment call to make silently — flag it.

## Non-negotiable rules (product principles P1–P7)

These break every tie. Do not "improve" around them:

1. **Evidence or it does not exist.** Every finding cites real event IDs. A finding with zero citations must be structurally impossible to insert, not just discouraged by convention (`findings.cited_event_ids` has a non-empty `CHECK` — see `data-base/10-ddl-appendix.md`).
2. **The model interprets, code calculates.** `backend/app/scoring/` (M6) must never import an LLM client, directly or transitively. This is enforced by a CI static check (`workflows/ci.yml`), not just a lint rule — don't route around it.
3. **Each component refuses to do the next one's job.** Collectors don't judge importance. Readers don't rank. The scoring engine doesn't call a model. If you're tempted to have one module do a neighboring module's job "just this once," don't — read `requirements/00-overview-and-glossary.md` §Product principles first.
4. **A human always sends.** There is no send capability anywhere in this product, for any module, to any external system — not hidden, not feature-flagged, not admin-only. If a task description implies adding one, stop and flag it; it contradicts the spec.
5. **Admit what we cannot see.** A degraded/incomplete data state must look visibly different from a complete one, everywhere it matters (dashboard, scores, coverage lines).
6. **Silence is a success state.** A healthy account should produce a near-empty screen. Don't add UI elements that manufacture the appearance of concern.
7. **Context over sentiment.** The Tone reader compares against a specific stakeholder's own baseline, never a generic sentiment scale. Don't "simplify" this into a universal threshold.

## Working in this repo

- **Requirements are numbered and stable.** `REQ-<MODULE>-<NN>` IDs are never reused or renumbered. If a requirement is retired, mark it `RETIRED` in place — don't delete it and don't reuse its number.
- **Schema changes go through `data-base/10-ddl-appendix.md` first**, then get reflected in the matching prose file (`02`–`09`, `12`) and an Alembic migration (`decisions/02-repo-and-tooling.md`). Don't let the DDL and the running schema drift — that's exactly the class of bug a full-repo consistency review exists to catch, and it's expensive to catch late.
- **Every table's "who did this" column is a foreign key to `users`, never free text.** See `data-base/12-users-and-auth.md`. If you're adding a new "authored by" / "submitted by" style column, wire it to `users.id` from the start.
- **Full replay must stay exact.** If you touch anything in `backend/app/ledger/` or `backend/app/scoring/`, run the golden-replay test (`tests/strategy.md`) before opening a PR — a change that makes replay non-deterministic breaks the audit story the entire architecture is built around.

## Mermaid diagrams in this repo

This repository has been bitten by the same two Mermaid parser gotchas enough times that they're worth stating explicitly:

- **Never put a semicolon (`;`) inside diagram text** (node labels, sequence messages, edge labels). Mermaid treats it as a statement terminator and silently truncates the diagram — use an em dash or a comma instead.
- **Never put a bare `<`, `>`, `<=`, or `>=` inside diagram text.** Mermaid tries to parse `<` as the start of an HTML tag. Spell out "at least," "below," "at most" instead, or use the multi-character unicode `≤`/`≥` only in prose *outside* a `mermaid` code fence, never inside one.

Before committing a new or edited diagram, a quick self-check that catches both:

```bash
awk '/^```mermaid/{f=1;next} /^```$/{f=0} f && (/;/ || /<=|>=/){print FILENAME":"FNR": "$0}' path/to/file.md
```

Empty output means clean.

## Commit and documentation style

- Keep everything in English, matching the rest of the repository, regardless of what language a request arrives in.
- No emoji unless explicitly asked for.
- When you fix a cross-file inconsistency, fix it everywhere it appears — a grep for the stale term/field name across the whole repo before considering the fix done is standard practice here, not extra credit.
