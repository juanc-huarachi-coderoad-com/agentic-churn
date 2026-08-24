# Research: CI/CD on GitHub Actions

## Decision 1: Single workflow file with a `needs`-gated CD job, not a separate `cd.yml` triggered by `workflow_run`

**Decision**: Add the image-build-and-publish job as a fourth job inside the same
`.github/workflows/ci.yml` file, using `needs: [lint, type-check, test]` and
`if: github.ref == 'refs/heads/main' && github.event_name == 'push'` — not a second workflow file
triggered by `workflow_run`.

**Rationale**: A `workflow_run`-triggered second workflow is the more commonly reached-for
pattern, but it has real, documented sharp edges that a single-file `needs` gate avoids entirely:

- `workflow_run` executes using the workflow file version **on the default branch**, not the
  version at the triggering commit — for a repository this early in adopting GitHub Actions
  wiring, that indirection is an unnecessary source of confusion (which `cd.yml` is actually
  running?) for no benefit.
- It requires explicitly checking `github.event.workflow_run.conclusion == 'success'` and
  checking out `github.event.workflow_run.head_sha` rather than the default checkout ref — two
  extra steps a `needs:` dependency gets for free from the same event's own `github.sha`.
- It runs as a logically separate workflow run, which shows up as a separate check in the GitHub
  UI with a separate name — more surface area for FR-008's branch-protection configuration to get
  wrong (which check is actually required: the CI jobs, the CD job, or both, spread across two
  workflow "runs" for the same commit).

A single file with `needs:` keeps one push/PR event mapped to exactly one workflow run containing
all four jobs, with the dependency graph enforced by GitHub Actions natively — the CD job simply
cannot start until lint/type-check/test have all succeeded for that exact commit, and there is
only one place (`.github/workflows/ci.yml`) to look.

**Alternatives considered**:
- *`workflow_run`-triggered `cd.yml`* — rejected above.
- *A separate, unconditional `cd.yml` with its own copy of the test steps* — rejected: duplicates
  FR-007's gate logic in two places, a maintenance hazard the first time the test job's command
  changes and only one copy gets updated.

## Decision 2: GHCR (`ghcr.io`) as the image registry, authenticated via `GITHUB_TOKEN`

**Decision**: Publish to `ghcr.io/<owner>/<repo>-api` and `ghcr.io/<owner>/<repo>-web`, using the
workflow's automatically-provided `GITHUB_TOKEN` (scoped with `packages: write` permission on the
job) rather than a Docker Hub or cloud-provider registry requiring a new secret.

**Rationale**: Matches `spec.md`'s own Assumptions — zero new secrets to provision for a first CD
pass, and GHCR is already the same trust boundary as the repository itself (no new vendor
relationship, consistent with this codebase's general preference for fewer vendor relationships
seen elsewhere, e.g. `architecture/03-technology-stack.md`'s embeddings-provider rationale). A
later roadmap feature (`production-deployment-hardening-ii`) that provisions per-client
infrastructure can decide then whether a given client's host pulls from GHCR directly or a
mirrored registry — out of scope here.

**Alternatives considered**: Docker Hub (rejected — requires a new account/secret pair, no
advantage over GHCR for a same-repository consumer); a cloud provider's registry, e.g. ECR/GCR
(rejected — presupposes a specific cloud provider this roadmap's later infra feature hasn't
chosen yet; premature here).

## Decision 3: Image tag is the commit SHA only (no `latest`, no semver)

**Decision**: Tag each published image with `${{ github.sha }}` (full 40-character SHA) and
nothing else.

**Rationale**: FR-005/SC-004 require tracing a running image back to an exact source commit — a
`latest` tag is ambiguous by definition (which commit is "latest" right now?) and semver implies
a release-versioning process this feature is not introducing. The SHA tag alone is sufficient for
every acceptance scenario in `spec.md` and is the smallest thing that satisfies them (P10).

**Alternatives considered**: Also tagging `latest` alongside the SHA (rejected — adds a second
tag with no consumer defined yet in this feature's scope, and risks a later deployment
accidentally depending on floating `latest` instead of an explicit SHA, undermining the exact
traceability FR-005 asks for).

## Decision 4: Branch protection configured via `gh api`, run once as part of this feature's delivery

**Decision**: FR-008 is satisfied by a one-time `gh api repos/{owner}/{repo}/branches/main/protection`
call (documented as a runbook step in `quickstart.md`, executed once during this feature's
implementation) rather than left as an unowned follow-up, matching the existing workflow file's
own header comment flagging this exact gap.

**Rationale**: The comment in `workflows/ci.yml` already states this explicitly: "Actually
blocking a PR merge on these three jobs additionally requires marking them as required status
checks in the repository's branch protection settings — a one-time GitHub repo configuration this
YAML file cannot express on its own." `spec.md` FR-008 promotes that from a comment to a binding
requirement of this feature.

**Alternatives considered**: A GitHub API call embedded in the workflow itself (rejected — branch
protection is a repository-level setting, not a per-run action; running it on every workflow
execution would be redundant and is not how GitHub's API is meant to be used for this).
