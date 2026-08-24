# Quickstart: CI/CD on GitHub Actions

## Prerequisites

- Push access to `origin` (`github.com/.../agentic-churn`).
- `gh` CLI authenticated against the same repository (`gh auth status`), for the one-time branch
  protection step (FR-008).
- No new secrets to configure — the workflow uses the automatically-provided `GITHUB_TOKEN`.

## Setup

1. `git mv workflows/ci.yml .github/workflows/ci.yml` (creates `.github/workflows/`).
2. Add the `publish` job to `.github/workflows/ci.yml` per `tasks.md`, with:
   - `needs: [lint, type-check, test]`
   - `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
   - `permissions: { packages: write, contents: read }`
   - Steps: `docker/login-action` against `ghcr.io` using `GITHUB_TOKEN`, then
     `docker/build-push-action` for `backend/Dockerfile` tagged
     `ghcr.io/<owner>/<repo>-api:${{ github.sha }}`, and for `frontend/Dockerfile` tagged
     `ghcr.io/<owner>/<repo>-web:${{ github.sha }}`.
3. Commit and push to a branch, open a PR against `main`.
4. Once merged, run the one-time branch-protection setup (FR-008):
   ```bash
   gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
     -f required_status_checks.strict=true \
     -f 'required_status_checks.contexts[]=lint' \
     -f 'required_status_checks.contexts[]=type-check' \
     -f 'required_status_checks.contexts[]=test' \
     -f enforce_admins=true \
     -f required_pull_request_reviews=null \
     -f restrictions=null
   ```
   (Adjust the exact flags to whatever the `gh` CLI's current protection schema requires at
   implementation time — verify against `gh api --help` / GitHub's REST API docs rather than
   assuming this exact invocation is still current.)

## Validation

**Story 1 (checks run automatically)**:
1. Push a branch with a deliberate `ruff` violation (e.g. an unused import) and open a PR.
2. Confirm in the GitHub PR UI, within a few minutes and with no manual action: `lint` shows
   failing, `type-check`/`test` show their own independent results.

**Story 2 (failing check blocks merge)**:
1. With the same PR still failing `lint`, attempt to merge via the GitHub UI.
2. Confirm the merge button is disabled/blocked, citing the required check.
3. Fix the violation, push again, confirm the check turns green and the merge button unblocks.

**Story 3 (merge produces a tagged image)**:
1. Merge a trivial, passing change to `main`.
2. Note the merge commit SHA.
3. Within 15 minutes, confirm via `gh api /orgs/{owner}/packages` (or the repository's Packages
   tab) that an image tagged with that exact SHA exists for both the `api` and `web` packages.

**Negative case (FR-006)**:
1. Push a commit directly to a test branch with a failing `test` job, merge it to `main` (or
   simulate via a PR with an admin override, if branch protection is already active).
2. Confirm no new image is published for that commit's SHA — the `publish` job shows as skipped
   or failed, never green with no image behind it.

## Expected outcome

All four jobs (`lint`, `type-check`, `test`, `publish`) visible as GitHub status checks on every
PR and on `main`; `main` unmergeable-around for a failing PR; every clean merge to `main`
producing two freshly tagged, traceable images within minutes.
