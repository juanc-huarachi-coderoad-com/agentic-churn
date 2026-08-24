# Feature Specification: CI/CD on GitHub Actions

**Feature Branch**: `025-ci-cd-github-actions`

**Created**: 2026-08-24

**Status**: Draft

**Input**: User description: "Move workflows/ci.yml to .github/workflows/ci.yml so the existing lint/type-check/test CI pipeline actually runs on GitHub (verify first whether it currently runs at all), configure branch-protection required checks, and add a CD job that builds and pushes the api/web images to GHCR tagged by git SHA on merge to main. Cites requirements/11-non-functional-requirements.md REQ-NFR-08/09 (determinism/replay) and constitution P9 (golden-replay, decimal reconciliation, monotonicity, no-LLM-in-scoring). First feature in a 7-feature production-readiness roadmap; no dependency on prior features; lowest-risk item, intentionally first."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A pull request is automatically checked before it can be merged (Priority: P1)

A contributor opens a pull request against `main`. Without them doing anything beyond pushing their branch, the project's lint, type-check, and test suite (including the golden-replay, decimal-reconciliation, monotonicity, and no-LLM-in-scoring gates already defined in the existing CI workflow) run automatically and report pass/fail status directly on the pull request.

**Why this priority**: This is the entire point of CI existing at all. Today, `workflows/ci.yml` is a real, working GitHub Actions workflow file that GitHub never actually discovers or runs, because it lives outside `.github/workflows/`. Every prior feature in this repository (001–024) was verified by manually running these same checks locally — this story is what makes that verification automatic and visible to anyone reviewing a change, not just the person who happened to run the commands.

**Independent Test**: Open a pull request that intentionally fails one check (e.g., a ruff violation) and confirm the PR shows a failing status check within minutes, with no manual workflow dispatch.

**Acceptance Scenarios**:

1. **Given** a pull request is opened against `main`, **When** the branch is pushed, **Then** GitHub Actions runs the lint, type-check, and test jobs automatically and reports their status on the pull request.
2. **Given** a pull request whose test job would fail (e.g., a golden-replay mismatch), **When** the workflow runs, **Then** the pull request shows a failing check, not a silently-skipped or missing one.
3. **Given** a push directly to `main` (e.g., a merge commit), **When** the workflow runs, **Then** the same lint/type-check/test jobs execute against that commit.

---

### User Story 2 - A failing check blocks a merge (Priority: P2)

A CS-lead-facing or engineering reviewer cannot merge a pull request into `main` while any of lint, type-check, or test is failing or still running — the merge button itself is disabled until the required checks pass.

**Why this priority**: Running checks that nobody is required to look at is only marginally better than not running them. This is what turns "CI exists" into "CI is actually a gate," matching how every one of this repository's constitution-mandated blocking checks (P9: golden-replay, decimal reconciliation, monotonicity, the static no-LLM-in-scoring check) is described as "CI-blocking" today — a claim that isn't true until this story ships.

**Independent Test**: Open a pull request with a deliberately failing check and attempt to merge it through the GitHub UI; confirm the merge control is blocked/disabled.

**Acceptance Scenarios**:

1. **Given** a pull request with a failing or in-progress required check, **When** a reviewer attempts to merge it, **Then** GitHub prevents the merge until the check passes.
2. **Given** a pull request where all required checks have passed, **When** a reviewer merges it, **Then** the merge proceeds normally.

---

### User Story 3 - A merge to main produces a traceable, deployable build (Priority: P3)

Once a change is merged into `main` and passes every check, a versioned container image for the `api` service and the `web` service is built and published automatically, tagged with the exact commit it was built from — so deploying "what's on `main`" to a client's deployment never requires a person to manually build images on their laptop.

**Why this priority**: This is the bridge between "CI passes" and "there is something a deployment can actually run." It depends on Stories 1 and 2 already existing (there is no point publishing an image built from a commit that hasn't been verified), which is why it is the third and lowest-priority story here, but it is still required for this feature to deliver production-deployment value rather than just a passing checkmark.

**Independent Test**: Merge a trivial, passing change to `main` and confirm a new image tagged with that merge commit's SHA appears in the registry for both `api` and `web` shortly after.

**Acceptance Scenarios**:

1. **Given** a pull request merges into `main` and all required checks pass, **When** the merge completes, **Then** a container image for `api` and a container image for `web`, each tagged with the merge commit's SHA, are published to the registry.
2. **Given** a commit on `main` where the test job fails, **When** the workflow runs, **Then** no image is published for that commit.

---

### Edge Cases

- What happens when the test job's PostgreSQL service container doesn't become healthy in time? The job must fail visibly (not hang indefinitely) — the existing `pg_isready` healthcheck with retries already bounds this; the relocated workflow must preserve that bound unchanged.
- What happens when the image build (Story 3) fails for a reason unrelated to the test suite (e.g., a Dockerfile syntax error)? The commit's checks may all show green while no image is published — this must be visibly reported (a failing CD job status), not a silent no-op.
- What happens if someone pushes directly to `main`, bypassing a pull request entirely? Branch protection's required-checks rule alone does not prevent a direct push with sufficient permissions — this is a known limitation of the chosen mechanism, not a gap in this feature's implementation, and should be documented rather than silently assumed away.
- What happens to the existing local/manual way of running these checks (e.g., a contributor running `pytest` by hand before pushing)? It continues to work unchanged — this feature adds an automatic, authoritative copy of the same checks, it does not remove or replace the ability to run them locally.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CI workflow (lint, type-check, test jobs, unchanged in scope from their current definitions) MUST execute automatically on GitHub for every pull request targeting `main` and every push to `main`.
- **FR-002**: Every job's pass/fail result MUST be visible as a status check on the associated pull request or commit within GitHub's own UI, with no manual trigger required.
- **FR-003**: A pull request MUST NOT be mergeable through GitHub's merge UI while any of the lint, type-check, or test jobs is failing or has not yet completed for the latest pushed commit.
- **FR-004**: On every successful merge to `main` (all required checks passing), the system MUST build and publish a container image for the `api` service and a container image for the `web` service.
- **FR-005**: Each published image MUST be tagged with the exact git commit SHA it was built from, so a running deployment's image tag can be traced back to a specific commit and its CI run.
- **FR-006**: The system MUST NOT publish `api`/`web` images for a commit whose lint, type-check, or test job has failed.
- **FR-007**: The relocated workflow MUST preserve every check currently defined in `workflows/ci.yml` without reducing its coverage — specifically the backend ruff/import-linter/mypy checks, the frontend eslint/tsc checks, and the `tests/golden_replay/`, `tests/scoring/`, `tests/unit/` test run with its existing migrate-then-seed setup. This is what makes `requirements/11-non-functional-requirements.md` REQ-NFR-08 (same ledger + same versions → identical score) and REQ-NFR-09 (dropping all projections and replaying the ledger reproduces the current dashboard exactly) — already asserted by the golden-replay test — an actually-enforced merge gate for the first time, not a check that exists on disk but never runs.
- **FR-008**: The one-time GitHub repository configuration required to make required-checks branch protection effective (already flagged in the existing workflow file's own header comment as something the YAML file cannot express on its own) MUST be completed as part of delivering this feature, not left as an undocumented follow-up.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A pull request opened against `main` shows all three CI job statuses (lint, type-check, test) resolved (pass or fail) in the GitHub UI without any person manually starting a workflow run.
- **SC-002**: 100% of pull requests carrying a failing required check are blocked from merging via GitHub's own merge control, verified by a deliberate test case.
- **SC-003**: Within 15 minutes of a qualifying merge to `main` completing, a container image tagged with that merge commit's SHA is retrievable from the registry for both the `api` and `web` services.
- **SC-004**: Given only a running deployment's image tag, a person can identify the exact source commit and its CI run results in under 2 minutes.

## Assumptions

- The project's existing `origin` remote (`github.com/.../agentic-churn`) is the GitHub repository this workflow is meant to run against — confirmed to be a real GitHub remote, not a placeholder.
- The container registry used for published images is GitHub Container Registry (GHCR), authenticated via the automatically-provided repository token — this avoids provisioning a new credential/secret for a first CD pass, consistent with this feature's "lowest-risk, do first" role in the roadmap.
- Branch protection's required-checks rule is configured for the `main` branch, matching the existing workflow's own `push: branches: [main]` scope.
- The three existing CI jobs (lint, type-check, test) keep their current scope exactly as defined today — this feature relocates and gates them, it does not expand what they check (e.g., the test job's current `tests/golden_replay/ tests/scoring/ tests/unit/` selection is unchanged).
- No new secrets are required for the CD job beyond the repository's automatically-provided token, which is sufficient to publish images to GHCR for the same repository.
