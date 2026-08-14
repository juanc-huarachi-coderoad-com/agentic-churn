# Feature Specification: Dashboard Shell

**Feature Branch**: `002-dashboard-shell` *(no `before_specify` git hook is configured in `.specify/extensions.yml`, so no dedicated branch was auto-created — this work continues on `feature/setup-sdd`, same as feature 001)*

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "Vertical-slice walking skeleton: real login issuing a real token, a dashboard screen rendering against seeded data through the real API, deployed end to end — build-order Phase 2 (`base/Churn-Sentiment-Agent-Product-Specification.md` §16). Proves the full stack — auth, API contract, frontend build, deployment — works before any real business logic exists, so an integration problem here is never confused with a scoring-logic problem later."

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement cites the
`REQ-<ID>` or architecture document that is its source of truth. Two deliberate scope
boundaries, both because no scoring/reader code exists yet (that's build-order Phases
4–7):

- **This is a shell, not the full dashboard.** `requirements/08-health-dashboard.md`
  REQ-M8-02's full component set (score block, contribution bars, pulse timeline,
  stakeholder cards, coverage line, ask bar) needs `score_runs`/`narrator_outputs`/
  `rollups` data that won't exist until build-order Phase 6 (`specs/ROADMAP.md` feature
  006). This feature renders only what can be shown honestly today: the client's name and
  the spec's own "Learning" state (REQ-M8-07) — never fabricated score data.
- **Authentication is full-strength, not a shell.** `requirements/14-authentication.md`'s
  login/token/revocation requirements (REQ-AUTH-01..09) are implemented completely in
  this feature, because every later feature depends on the auth gate already working.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log in and out with a real, revocable token (Priority: P1)

A CS lead authenticates with a username and password and receives a bearer token; that
token can be revoked (logout) before its natural expiry, and a wrong password never
reveals whether the username itself exists.

**Why this priority**: Every other route this feature (and every later feature) adds sits
behind this gate. It's independently valuable and independently testable without a
dashboard existing yet — a login/logout API round-trip is a complete, demoable unit on
its own.

**Independent Test**: Call the login endpoint with valid and invalid credentials directly
(no UI needed) and confirm the token lifecycle (issuance, expiry, revocation) behaves per
`requirements/14-authentication.md`.

**Acceptance Scenarios**:

1. **Given** a user with valid credentials, **When** they log in, **Then** they receive a
   bearer token with a hard expiry (`REQ-AUTH-01`, `REQ-AUTH-04`).
2. **Given** a user submits a wrong password, or a username that doesn't exist, **When**
   they attempt to log in, **Then** both cases return the identical generic failure
   response (`REQ-AUTH-08`).
3. **Given** a deactivated user (`users.is_active = false`,
   `data-base/12-users-and-auth.md`), **When** they attempt to log in with otherwise
   correct credentials, **Then** they receive the same generic failure response as an
   unknown username — deactivation status is never revealed either.
4. **Given** a user has an issued token, **When** they log out, **Then** that token is
   rejected on its very next use, even though its `expires_at` hasn't passed
   (`REQ-AUTH-06`).
5. **Given** repeated failed login attempts for the same username, **When** a third
   attempt follows in quick succession, **Then** it is rate-limited (`REQ-AUTH-09`).

---

### User Story 2 - Authenticated dashboard shell renders real seeded data (Priority: P2)

An authenticated CS lead opens the dashboard and sees the real, seeded client's name and
an honest "still learning" message — proving the full React → FastAPI → Postgres pipeline
works end to end, without a single fabricated number anywhere on the screen.

**Why this priority**: This is the actual "vertical slice" the build order names — it
depends on User Story 1's gate existing first, and it's the payoff that proves the whole
stack (frontend build, API contract, deployment, auth) is wired together correctly before
any scoring logic exists to confuse an integration bug with a logic bug.

**Independent Test**: Open the dashboard without a token (expect a login redirect), then
with a valid token (expect the seeded client's name and the Learning-state message,
sourced from a real API call against the database provisioned in feature 001).

**Acceptance Scenarios**:

1. **Given** no bearer token, **When** a request is made for the dashboard data, **Then**
   it is rejected — no route in this feature (or any other) is reachable without one,
   except `/auth/login` and `/health` (`REQ-AUTH-P1`,
   `architecture/07-api-spec.md` §Authentication).
2. **Given** a valid token, **When** the CS lead opens the dashboard, **Then** they see
   the seeded client's name (from the current `client_profile_versions` row,
   `data-base/11-seed-data.sql`) and the "still learning" state message (`REQ-M8-07`) —
   the dashboard renders purely from stored data, never a client-side computation
   (`REQ-M8-01`).
3. **Given** the CS lead is authenticated and the browser is closed and reopened within
   the token's lifetime, **When** they return to the dashboard, **Then** they remain
   logged in without re-entering credentials (the stored token is still valid).
4. **Given** the CS lead's token expires while the dashboard is open, **When** the next
   API call is made, **Then** they are returned to the login screen rather than shown a
   silently-broken page.

---

### Edge Cases

- What happens when a client-side stored token is malformed or tampered with? Treated
  identically to a missing token — rejected, no detail leaked (`REQ-AUTH-08`'s "don't
  reveal" principle applied consistently).
- What happens when the rate limit is hit? The client sees a generic "too many attempts,
  try again shortly" message — no detail about the underlying threshold or window.
- What happens when the seeded `client_profile_versions` row is somehow absent (a fresh,
  unseeded database)? The dashboard must show an explicit "no client profile configured"
  state rather than a blank or broken screen — the same "admit what we cannot see"
  discipline (constitution P5) already applied to source coverage, applied here to the
  profile itself.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST implement `POST /auth/login` exactly per `REQ-AUTH-01` and
  `REQ-AUTH-08` (`architecture/07-api-spec.md` §Authentication).
- **FR-002**: The system MUST hash passwords with Argon2id and never store, log, or
  transmit a plaintext password after the initial login request (`REQ-AUTH-02`,
  `REQ-AUTH-P2`).
- **FR-003**: The system MUST issue bearer tokens with a hard expiry and store only a
  SHA-256 hash of each issued token, never the raw value (`REQ-AUTH-03`, `REQ-AUTH-04`).
- **FR-004**: The system MUST implement `POST /auth/logout`, revoking the presented token
  immediately (`REQ-AUTH-06`).
- **FR-005**: The system MUST reject any request to a protected route with a missing,
  expired, or revoked token, returning `401` with no further detail — every route except
  `/auth/login` and `/health` is protected (`REQ-AUTH-05`, `REQ-AUTH-P1`).
- **FR-006**: The authentication middleware MUST resolve the requesting user's identity
  from the bearer token and make it available to every route handler, so later features
  can populate their `*_user_id` "who did this" columns from it directly (`REQ-AUTH-07`)
  — this feature itself adds no such column, since `/api/dashboard` is read-only.
- **FR-007**: The system MUST rate-limit login attempts per username (`REQ-AUTH-09`).
- **FR-008**: The system MUST implement `GET /api/dashboard`, returning the client header
  (name, populated from the current `client_profile_versions` row) and the "Learning"
  state message — the full `REQ-M8-02` component set is out of scope for this feature
  (`REQ-M8-01`, `REQ-M8-05`, `REQ-M8-07`).
- **FR-009**: The login screen MUST be the only reachable screen without a valid token;
  every other screen MUST redirect to it when no valid token is present.
- **FR-010**: The system MUST reject login for a deactivated user
  (`users.is_active = false`) with the identical generic failure response used for an
  unknown username or wrong password (`data-base/12-users-and-auth.md`; extends
  `REQ-AUTH-08`'s "don't reveal" principle to deactivation status).

### Key Entities

This feature adds no new tables — `users` and `auth_tokens`
(`data-base/12-users-and-auth.md`) and `client_profile_versions`
(`data-base/04-schema-context.md`) already exist and are seeded from feature 001. This
feature is the first to actually read and write them at runtime.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with valid credentials goes from the login screen to seeing the
  dashboard in under 5 seconds.
- **SC-002**: 100% of requests to a protected route without a valid token are rejected —
  zero paths bypass authentication.
- **SC-003**: An unknown-username attempt and a wrong-password attempt are indistinguishable
  to the end user in 100% of cases.
- **SC-004**: A revoked or logged-out token is rejected on its very next use, 100% of the
  time.
- **SC-005**: The dashboard never displays fabricated or placeholder score/finding data —
  every value shown is either real (the seeded client's name) or an explicit "not yet
  available" state.

## Assumptions

- **The seeded `users.password_hash` values in `data-base/11-seed-data.sql` are explicit
  placeholders** (`'$argon2id$...REPLACE_ME_DEMO_ONLY'`) — that file's own comment says
  to replace them before any real use. This feature replaces them with a real Argon2id
  hash of a documented demo password so login can actually be exercised end to end
  locally; the demo password is documented in `quickstart.md`, never treated as a secret.
- Session persistence (staying logged in across a browser restart, within the token's
  lifetime) is a reasonable UX default, not itself a numbered `REQ-AUTH` requirement —
  implemented as ordinary client-side token storage.
- Role-based access control, password reset, MFA, and SSO are explicitly Post-MVP
  (`data-base/12-users-and-auth.md` §What this does not do yet) and out of scope here.
- The full `REQ-M8-02` dashboard component set (score block, contribution bars, pulse
  timeline, stakeholder cards, coverage line, ask bar) is out of scope — deferred to
  feature 006 (`specs/ROADMAP.md`), once `score_runs`/`narrator_outputs`/`rollups` data
  exists to render.
