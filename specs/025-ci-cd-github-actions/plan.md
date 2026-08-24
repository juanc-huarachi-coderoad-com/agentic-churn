# Implementation Plan: CI/CD on GitHub Actions

**Branch**: `main` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/025-ci-cd-github-actions/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Relocate the already-written, already-correct `workflows/ci.yml` to `.github/workflows/ci.yml` so
GitHub Actions actually discovers and runs it (confirmed today it does not — the repo has a real
`origin` remote on GitHub, but no `.github/workflows/` directory exists at all), configure
`main`'s branch protection to require the three existing jobs (lint, type-check, test) as merge
gates, and add a fourth job that builds and publishes `api`/`web` images to GHCR, tagged by
commit SHA, only for commits where the other three jobs passed. This is a relocation +
configuration + one new CD job — no new backend/frontend dependency, no architecture change, no
code under `backend/app/` or `frontend/src/` is touched. First feature in the seven-feature
production-readiness roadmap (`specs/025`–`031`, per the approved plan referenced in this
feature's own `spec.md`); chosen to go first because it is the lowest-risk item and gives every
later feature in the roadmap a CI gate that is actually enforced, not just present as a file.

## Technical Context

**Language/Version**: YAML (GitHub Actions workflow syntax) — no application language changes.
The workflow's own steps still run Python 3.12/`uv` and Node 20/`pnpm`, unchanged from today.

**Primary Dependencies**: None new for CI itself. The CD job adds `docker/build-push-action` and
`docker/login-action` (both official GitHub Actions, no new backend/frontend package) to build
from the already-existing, unmodified `backend/Dockerfile` and `frontend/Dockerfile`.

**Storage**: N/A for this feature — the test job's ephemeral `postgres:16` service container is
unchanged from the existing workflow.

**Testing**: The existing three jobs' test commands are preserved byte-for-byte (ruff,
import-linter, mypy, eslint, tsc, and `pytest tests/golden_replay/ tests/scoring/ tests/unit/`
against a migrated+seeded ephemeral Postgres). This feature adds no new test *content* — it makes
the existing tests actually run automatically and become a real merge gate for the first time.

**Target Platform**: GitHub Actions (`ubuntu-latest` runners, matching the existing workflow) —
no change to the Docker Compose deployment target itself; the new CD job publishes images that a
later roadmap feature (`production-deployment-hardening-ii`) will consume for redeploys, but
consuming them is out of scope here.

**Project Type**: Web application (Python/FastAPI backend + React/TypeScript frontend) — this
feature only touches CI/CD configuration, not either application's source.

**Performance Goals**: No new latency/throughput target. SC-003 sets a 15-minute ceiling from
merge to image availability, generous relative to the existing test job's real-world runtime
(migrate + seed + `pytest tests/golden_replay/ tests/scoring/ tests/unit/` against a fresh
ephemeral Postgres, historically well under that on `ubuntu-latest`).

**Constraints**: No new secrets beyond the automatically-provided `GITHUB_TOKEN` (Assumptions,
`spec.md`) — GHCR authenticates against the same repository's token, avoiding a new credential to
provision and rotate for a first CD pass.

**Scale/Scope**: One workflow file relocated, one new job added to it, one GitHub repository
setting (branch protection) configured once. No fan-out to other files beyond
`specs/ROADMAP.md` (new row) and `CLAUDE.md`'s spec-kit context pointer.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| P1 Evidence or It Does Not Exist | No | Not a findings/evidence feature. |
| P2 The Model Interprets, Code Calculates | No | No scoring/LLM code touched. |
| P3 Each Component Refuses to Do the Next One's Job | No | No module boundary touched. |
| P4 A Human Always Sends | No | No send capability involved. |
| P5 Admit What We Cannot See | No | Not a data-completeness feature. |
| P6 Silence Is a Success State | No | Not a dashboard/UI feature. |
| P7 Context Over Sentiment | No | Not a reader feature. |
| P8 Clean Architecture — the Dependency Rule Is Law | No | No `backend/app/` code changes; `.importlinter` contracts are unaffected because the jobs that run `lint-imports` are preserved unchanged, only relocated. |
| **P9 Test-First Determinism** | **Yes — this feature is what fulfills it for the first time.** | The constitution already states golden-replay, decimal reconciliation, monotonicity, and the static no-LLM-in-scoring check are "CI-blocking merge" (`Development Workflow & Quality Gates`). Today that claim is **false in practice** — `workflows/ci.yml` lives outside `.github/workflows/`, so GitHub never runs it and nothing blocks a merge. This feature makes the existing, already-correct gate real; it adds no new gate and changes no test content (`spec.md` FR-007). |
| P10 Simplicity Over Speculative Generality (YAGNI) | Yes | The CD job is the smallest addition that satisfies User Story 3 — a single `docker/build-push-action` step per service, no build matrix, no multi-registry publishing, no new abstraction layer. |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | No | No frontend source code changes; the frontend's existing `eslint`/`tsc`/build steps are preserved, not modified. |

**Result**: PASS. This feature closes a gap between the constitution's stated CI-gate claim and
reality — it does not introduce a new principle, violate an existing one, or require a Complexity
Tracking justification.

## Project Structure

### Documentation (this feature)

```text
specs/025-ci-cd-github-actions/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `data-model.md` or `contracts/` — this feature introduces no new data entity and no new
application-facing interface (API endpoint, CLI command); its only "contract" is the GitHub
Actions workflow file itself and a repository setting, both fully specified in `quickstart.md`.

### Source Code (repository root)

```text
workflows/ci.yml                    # DELETED — relocated, not duplicated
.github/
└── workflows/
    └── ci.yml                      # NEW — relocated file; jobs lint/type-check/test unchanged,
                                     #        plus a new 4th job `publish` (needs: [lint, type-check, test])
specs/ROADMAP.md                    # UPDATED — new row for this feature
```

**Structure Decision**: Pure infrastructure-configuration change under `.github/workflows/` (the
one location GitHub Actions actually discovers workflows from) plus the removal of the old,
never-discovered `workflows/ci.yml`. No `backend/` or `frontend/` source directory changes. Per
`research.md` Decision 1, the publish/CD step is a fourth job in the **same** file, gated by a
native `needs:` dependency on the three existing jobs plus an `if:` restricting it to pushes on
`main` — not a second `cd.yml` file triggered by `workflow_run`, which would map one commit to two
separate workflow runs and complicate FR-008's required-checks configuration.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
