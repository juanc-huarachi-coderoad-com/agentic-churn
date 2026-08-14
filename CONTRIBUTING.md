# Contributing

Read `AGENTS.md` in full before touching code — it is the authoritative contributor guide
and this file is only a summary of it. If anything here and `AGENTS.md` ever disagree,
`AGENTS.md` wins.

## Non-negotiable rules

These break every tie (`AGENTS.md` §Non-negotiable rules, mirrored in
`.specify/memory/constitution.md` P1–P7):

1. **Evidence or it does not exist.** Every finding cites real event IDs — enforced by a
   database `CHECK`, not convention.
2. **The model interprets, code calculates.** `backend/app/scoring/` must never import an
   LLM client, directly or transitively — enforced by CI (`.importlinter`,
   `workflows/ci.yml`).
3. **Each component refuses to do the next one's job.** Collectors don't judge. Readers
   don't rank. The scoring engine doesn't call a model.
4. **A human always sends.** There is no send capability anywhere in this product, for any
   module, to any external system. If a task implies adding one, stop and flag it.
5. **Admit what we cannot see.** A degraded/incomplete data state must look visibly
   different from a complete one, everywhere it matters.
6. **Silence is a success state.** A healthy account produces a near-empty screen. Don't
   add UI elements that manufacture the appearance of concern.
7. **Context over sentiment.** The Tone reader compares against a stakeholder's own
   baseline, never a generic sentiment scale.

## Before you open a PR

- **Requirement IDs are permanent.** `REQ-<MODULE>-<NN>` IDs are never reused or
  renumbered; retire in place, don't delete.
- **Schema changes go through `data-base/10-ddl-appendix.md` first**, then the matching
  prose file, then an Alembic migration — never let the DDL and the running schema drift.
- **Every "who did this" column is a foreign key to `users`, never free text.**
- **If you touch `backend/app/ledger/` or `backend/app/scoring/`**, the golden-replay test
  (`tests/strategy.md`) must pass before you open a PR.
- **CI must pass**: `ruff`, `mypy`, `lint-imports` (backend); `eslint`, `tsc --noEmit`
  (frontend); the test-harness job — see `workflows/ci.yml`.
- **No emoji, English only**, matching the rest of the repository, regardless of what
  language a request arrives in.
- **Fix a cross-file inconsistency everywhere it appears** — grep the whole repo for the
  stale term before considering the fix done.

## Local setup

See `README.md` §Quickstart — `docker compose up --build` is the whole setup.
