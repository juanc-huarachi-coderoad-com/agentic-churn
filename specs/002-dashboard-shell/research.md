# Phase 0 Research: Dashboard Shell

Most of the stack is already decided (`architecture/03-technology-stack.md`,
`research.md` from feature 001). This resolves the handful of choices specific to
implementing auth and the dashboard shell for real.

## Decision: Opaque bearer tokens, not JWTs

**Decision**: A cryptographically random opaque token (`secrets.token_urlsafe(32)`),
hashed with SHA-256 before storage in `auth_tokens.token_hash`. Every request does a
database lookup to validate — no self-contained signature verification.

**Rationale**: `data-base/12-users-and-auth.md`'s schema already assumes lookup-based
validation (`token_hash`, `revoked_at` columns) — a JWT's whole value proposition is
*stateless* verification, which conflicts with `REQ-AUTH-06`'s "reject a revoked token
immediately, even before `expires_at`" requirement. Supporting instant revocation with a
JWT would mean maintaining a denylist anyway, at which point the JWT's statelessness is
fiction and an opaque token is simpler for the same guarantee. The schema was designed
for opaque tokens; this decision just makes that explicit.

**Alternatives considered**: JWT with a revocation denylist — rejected as strictly more
complexity (signing keys, denylist table that duplicates what `auth_tokens` already does)
for no benefit at this scale (a single API instance, no cross-service token verification
need).

## Decision: `argon2-cffi` for password hashing

**Decision**: `argon2-cffi` directly (not `passlib`).

**Rationale**: `argon2-cffi` is the reference Python binding for Argon2 (the PHC-winning
algorithm `REQ-AUTH-02` names specifically) and is actively maintained; `passlib`'s own
Argon2 backend wraps `argon2-cffi` anyway, so depending on it directly avoids an
unnecessary layer, consistent with the "remove the difficulty" principle already applied
to other tooling choices (`uv` over pip+venv, `Ruff` over flake8+isort+black).

## Decision: In-process rate limiting via `slowapi`, keyed by source IP

**Decision**: `slowapi` (FastAPI/Starlette-native rate limiting middleware, in-memory
backend) limiting `POST /auth/login`, keyed by client IP (`slowapi.util.
get_remote_address`) — revised during implementation from the originally-proposed
per-username keying; see "Implementation note" below.

**Rationale**: `REQ-AUTH-09` requires rate limiting; the deployment topology
(`architecture/03-technology-stack.md`) is one `api` container per client deployment, no
horizontal scaling — an in-memory limiter is correct at this scale and avoids adding
Redis or another shared store for a single-instance service (P10/YAGNI). `slowapi` is a
thin, well-maintained wrapper rather than hand-rolling sliding-window logic.

**Alternatives considered**: Hand-rolled in-memory counter — rejected only because
`slowapi` already solves this correctly (per-key windows, standard `429` response) with
less code to maintain.

**Concrete limit**: 2 *failed* attempts per source IP per 5 minutes — the 3rd
consecutive failure within that window returns `429`, matching spec.md's Acceptance
Scenario 5 ("repeated failed login attempts... third attempt... rate-limited") and
`quickstart.md`'s literal 3-request test.

**Implementation note (per-IP, not per-username)**: `slowapi`'s `key_func` is called
synchronously and never awaited — extracting the username would mean reading the async
request body from a sync context, which only works by relying on Starlette's private
body-caching internals (fragile, version-coupled). Per-IP is `slowapi`'s directly
supported path and still satisfies `REQ-AUTH-09`'s actual purpose: it resists
brute-force/credential-stuffing, and additionally blocks one attacker rotating through
many usernames from one address — a case per-username keying alone wouldn't catch.

**Implementation note (failures only, not every call)**: the `@limiter.limit(...)`
decorator counts every call including successful logins, which would incorrectly
penalize a legitimately busy user and — worse — made `quickstart.md`'s own test sequence
self-defeating (its one successful login plus two deliberate failures would exhaust the
budget before the 3rd deliberate failure is even sent). Implemented instead by calling
`limiter.limiter.test()`/`.hit()` directly from the route, incrementing only in the
`except InvalidCredentialsError` branch.

## Decision: React Hook Form + Zod for the login form

**Decision**: `react-hook-form` for form state, `zod` (+ `@hookform/resolvers`) for
schema validation on the login form's username/password fields.

**Rationale**: Constitution P11 / Full-Stack Engineering §2 mandates this pairing for
every form — this is the project's first real form, so it's the first place that MUST
applies concretely. Client-side validation is UX only; the backend's Pydantic models
remain the actual trust boundary (Full-Stack §5 "Zero Trust Validation").

## Decision: Frontend state — TanStack Query (server) + Zustand (client), React Router

**Decision**: `@tanstack/react-query` for the `/api/dashboard` call, a small `zustand`
store for the auth token, `react-router` for the `/login` ↔ `/dashboard` split.

**Rationale**: Constitution P11 already names TanStack Query and Zustand as this
project's frontend data/state layer — this feature is simply the first to actually use
them. React Router is the standard choice for a Vite + React SPA needing more than one
route; no project document suggests an alternative.

## Decision: Token storage — `localStorage`, `Authorization: Bearer` header

**Decision**: Store the raw token in `localStorage`; send it as
`Authorization: Bearer <token>` on every request. No cookies.

**Rationale**: spec.md's Assumptions call for surviving a browser restart within the
token's lifetime, which `localStorage` gives for free (unlike `sessionStorage`).
`api` and `web` are served on different ports in this Compose topology
(`docker-compose.yml`) — a cookie-based approach would need CORS-credentials and
`SameSite` configuration for what a header-based bearer token avoids entirely. The
accepted tradeoff (XSS can read `localStorage`) is standard for a bearer-token SPA at
this stage; Post-MVP hardening (build-order Phase 11) is the right place to revisit an
`httpOnly` cookie if warranted, not this feature.

## Decision: Regenerating the seeded demo password hash

**Decision**: `data-base/11-seed-data.sql`'s `marta` row gets a real Argon2id hash of a
documented demo password (`agentic-demo-2026`, chosen for this feature and recorded in
`quickstart.md` — never treated as a secret, since it's a local/demo-only credential).

**Rationale**: The seed file's own comment says the existing value is a placeholder to
replace before real use (`'$argon2id$...REPLACE_ME_DEMO_ONLY'`) — not a real hash of
anything, so User Story 1's login acceptance scenario is untestable without this change.
This is a seed-*data* edit, not a schema change, so it doesn't touch
`data-base/10-ddl-appendix.md` or the migration.

## Backend module placement

**Decision**: `backend/app/auth/` (three-ring: `domain/` for pure password/token
logic, `application/` for the login/logout use cases and the `get_current_user`
dependency, `adapters/` for the SQLAlchemy repository) and
`backend/app/experience/dashboard.py` for the `/api/dashboard` route — both already
named in `decisions/02-repo-and-tooling.md`'s module map, this feature is the first to
put real code in them.

## Outcome

No `NEEDS CLARIFICATION` markers remain. All Technical Context fields in `plan.md` are
resolved either by citing an existing document or by a decision recorded above.
