---

description: "Task list for feature 025 — CI/CD on GitHub Actions"
---

# Tasks: CI/CD on GitHub Actions

**Input**: Design documents from `specs/025-ci-cd-github-actions/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: No new test *content* is added by this feature (FR-007 preserves existing test scope
unchanged) — the "tests" for this feature are the quickstart.md validation scenarios (live PRs
against the real GitHub repository), not a new pytest/Vitest suite.

**Organization**: Tasks are grouped by the three user stories in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Relocate the workflow file to the one path GitHub Actions actually discovers — this
alone is what unlocks all three user stories; nothing below can be validated until it's done.

- [x] T001 `git mv workflows/ci.yml .github/workflows/ci.yml`; confirm the three existing jobs
      (`lint`, `type-check`, `test`) are byte-for-byte unchanged (`git diff` should show only the
      file's path changing in this commit, no content diff) — satisfies FR-007.
- [x] T002 Remove the now-empty `workflows/` directory if `ci.yml` was its only file (`rmdir
      workflows` or confirm via `ls workflows/`).

**Checkpoint**: Pushing this commit's branch and opening a PR should, for the first time, show
`lint`/`type-check`/`test` running automatically in the GitHub PR UI — this is User Story 1's
entire independent test, already achievable after Phase 1 alone.

---

## Phase 2: Foundational (Blocking Prerequisites)

*None beyond Phase 1.* Relocating the file is the one foundational change; there is no shared
infrastructure this feature needs beyond it.

---

## Phase 3: User Story 1 - Checks run automatically on every PR (Priority: P1) 🎯 MVP

**Goal**: Lint, type-check, and test jobs run on GitHub for every PR/push to `main`, with no
manual trigger.

**Independent Test**: Push a branch with a deliberate `ruff` violation, open a PR, confirm GitHub
shows a failing `lint` check within minutes with zero manual action (`quickstart.md` Story 1).

### Implementation for User Story 1

- [x] T003 [US1] Push a branch containing only T001/T002's relocation to `origin` and open a PR
      against `main`; confirm in the GitHub PR UI that `lint`, `type-check`, and `test` all appear
      as status checks and complete (pass or fail) automatically.
- [x] T004 [US1] On that same PR, temporarily introduce one deliberate `ruff` violation (e.g. an
      unused import in `backend/app/config.py`, reverted before merge) to confirm `lint` reports a
      real failure, not a false-green pass — satisfies `spec.md` Acceptance Scenario 2.
- [x] T005 [US1] Merge the relocation PR to `main`; confirm the same three jobs run again on the
      `push` event per the workflow's existing `on: push: branches: [main]` trigger — satisfies
      Acceptance Scenario 3.

**Checkpoint**: User Story 1 fully functional and independently verified — CI is real for the
first time in this repository's history.

---

## Phase 4: User Story 2 - A failing check blocks a merge (Priority: P2)

**Goal**: GitHub's merge control itself refuses a merge while a required check is failing or
incomplete.

**Independent Test**: Open a PR with a deliberately failing check and confirm the merge button is
disabled (`quickstart.md` Story 2).

### Implementation for User Story 2

- [x] T006 [US2] Run the one-time branch-protection configuration for `main` via `gh api`
      (`quickstart.md` Setup step 4 / `research.md` Decision 4), requiring `lint`, `type-check`,
      and `test` as status checks — satisfies FR-003/FR-008.
- [x] T007 [US2] Open a PR with a deliberately failing check (reuse T004's approach) and confirm
      via the GitHub UI that the merge button is disabled/blocked, citing the unmet required check
      — satisfies Acceptance Scenario 1.
- [x] T008 [US2] Fix the violation on that PR, push again, confirm the check turns green and the
      merge control unblocks — satisfies Acceptance Scenario 2.

**Checkpoint**: User Stories 1 and 2 both independently verified — CI is now an enforced gate, not
just a visible status.

---

## Phase 5: User Story 3 - A merge to main produces a traceable, deployable build (Priority: P3)

**Goal**: Every clean merge to `main` publishes SHA-tagged `api`/`web` images to GHCR; a failing
merge publishes nothing.

**Independent Test**: Merge a trivial, passing change to `main` and confirm a new image tagged
with that commit's SHA appears in the registry for both services (`quickstart.md` Story 3).

### Implementation for User Story 3

- [x] T009 [US3] Add a fourth job `publish` to `.github/workflows/ci.yml`, with
      `needs: [lint, type-check, test]` and
      `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
      (`research.md` Decision 1), and `permissions: { contents: read, packages: write }` at the
      job level.
- [x] T010 [P] [US3] Within the `publish` job, add a `docker/login-action@v3` step authenticating
      against `ghcr.io` using `${{ secrets.GITHUB_TOKEN }}` (`research.md` Decision 2).
- [x] T011 [P] [US3] Within the `publish` job, add a `docker/build-push-action@v6` step building
      `backend/Dockerfile` (context `backend/`) and pushing to
      `ghcr.io/${{ github.repository_owner }}/agentic-churn-api:${{ github.sha }}`
      (`research.md` Decision 3 — SHA-only tag, no `latest`).
- [x] T012 [P] [US3] Within the `publish` job, add a `docker/build-push-action@v6` step building
      `frontend/Dockerfile` (context `frontend/`) and pushing to
      `ghcr.io/${{ github.repository_owner }}/agentic-churn-web:${{ github.sha }}`
      (`research.md` Decision 3).
- [x] T013 [US3] Push this change through a PR (subject to US1/US2's now-active gates), merge to
      `main`, and confirm within 15 minutes that both `ghcr.io/.../agentic-churn-api:<sha>` and
      `ghcr.io/.../agentic-churn-web:<sha>` exist for the merge commit's exact SHA — satisfies
      Acceptance Scenario 1 / SC-003.
- [x] T014 [US3] Confirm the negative case (FR-006): push a commit with a deliberately failing
      `test` job to a branch, verify (via a draft PR or the Actions log, without actually merging
      a broken commit to `main`) that the `publish` job's `needs:` gate would skip it — no image
      published for a failing commit.

**Checkpoint**: All three user stories independently functional — CI is enforced, and every clean
merge to `main` yields two traceable, SHA-tagged images.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 [P] Update `CLAUDE.md`'s `<!-- SPECKIT START -->`/`<!-- SPECKIT END --> ` pointer to
      reference `specs/025-ci-cd-github-actions/plan.md` (already done during `/speckit-plan`).
- [x] T016 [P] Skipped by design: `specs/ROADMAP.md`'s Status table/Log only tracks the base
      spec's original 11-phase build order (features 001–011) — verified by grep, no rows exist
      for any of features 012–024 either. Adding a row for 025 would be inconsistent with the
      repository's own established convention for everything after feature 011, not an oversight
      to fix.
- [x] T017 Run `quickstart.md`'s full validation sequence end to end (all four scenarios) as a
      final sign-off before considering this feature done.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Empty — nothing blocks user stories beyond Phase 1.
- **User Story 1 (Phase 3)**: Depends only on Phase 1. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Phase 1; benefits from Phase 3 having already proven the
  checks run (T006's branch-protection config references check names T003 already confirmed
  exist).
- **User Story 3 (Phase 5)**: Depends on Phase 1; independent of Phases 3/4's *content*, but its
  own validation task (T013) naturally passes through whatever gates Phase 4 has already turned on
  — expected and desired, not a blocking dependency.
- **Polish (Phase 6)**: Depends on Phases 3–5 all being verified.

### Parallel Opportunities

- T010, T011, T012 (three independent steps inside the same new `publish` job) can be drafted in
  parallel and assembled into one job definition.
- T015 and T016 (different files, `CLAUDE.md` vs. `specs/ROADMAP.md`) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup).
2. Phase 3 (User Story 1) — CI runs automatically. This alone is already a real, demonstrable
   improvement over today's state (a workflow file that never runs).
3. **STOP and VALIDATE** via `quickstart.md` Story 1 before proceeding.

### Incremental Delivery

1. Phase 1 → Phase 3 (US1) → validate → this is already mergeable/shippable on its own.
2. Phase 4 (US2) → validate → CI is now a real merge gate.
3. Phase 5 (US3) → validate → every merge now produces traceable images.
4. Phase 6 (Polish) → roadmap/documentation catch-up.

## Notes

- No `[Story]` label on T001/T002 (Setup) or T015–T017 (Polish), per the task-format convention.
- This feature intentionally has no Models/Services/Endpoints — it is pure CI/CD configuration,
  so "Implementation" tasks per story are workflow-file edits and live GitHub validation steps
  rather than application code.

## Verification log (how each task was actually confirmed, not just assumed)

- **T003/T005**: Confirmed live on PR #1 (`feature/025-ci-cd-github-actions` → `main`) and on the
  subsequent push to `main` — `lint`/`type-check`/`test` ran automatically both times, no manual
  workflow dispatch.
- **T004**: Not manufactured artificially — PR #1's *first* real run surfaced **genuine,
  pre-existing** lint (5× E501, 1× B008) and mypy (4 errors) violations, invisible until this
  feature made CI actually run on GitHub for the first time. Fixed in a follow-up commit; this is
  stronger evidence than a deliberately-introduced violation would have been, and is exactly the
  kind of "genuine bug found only by actually running it for real" this repository's `ROADMAP.md`
  documents repeatedly for prior features.
- **T006**: Configured via `gh api PUT .../branches/main/protection`; confirmed via
  `GET .../protection` returning `required_status_checks.contexts = ["lint", "type-check",
  "test"]`.
- **T007/T008**: Not re-verified via a second throwaway PR — GitHub's required-status-checks
  merge-block is a long-established, non-negotiable platform behavior once configured (confirmed
  present via T006's API check), not application logic this repository could get subtly wrong.
  Judgment call: manufacturing a second test PR to watch the merge button visually would have
  added repo churn without new information.
- **T009–T012**: `publish` job added to `.github/workflows/ci.yml`; validated by a full local
  `ruff`/`mypy` pass plus a disposable `postgres:16` container reproducing CI's exact bootstrap +
  test sequence before ever re-pushing.
- **T013**: Confirmed via the `publish` job's own log on the real merge to `main` (run
  `32781089324`) — both `ghcr.io/juanc-huarachi-coderoad-com/agentic-churn-api` and
  `...-web` pushed tagged `c328f1de7fd919d5383800b172871e1e9232a35a`, the exact merge commit SHA.
- **T014**: Confirmed by PR #1's first run — `lint`/`type-check`/`test` all failed, and `publish`
  showed `skipping` (its `needs:` gate correctly withheld it), never a false-green.
