# 14 · Authentication (cross-cutting)

Tier — cross-cutting, gates access to Tier 4 (Experience). New in this revision, at the user's explicit request. Backs `data-base/12-users-and-auth.md` and `architecture/07-api-spec.md`.

## Purpose

Every person who opens the dashboard, asks a question, or requests a draft is a real, authenticated identity — never an anonymous session and never a shared credential. **At this stage, authentication answers "who are you," not "what are you allowed to do."** Every active, authenticated user has access to every functionality the product offers (dashboard, ask agent, draft composer, profile editing, feedback verdicts). Role-based restriction — e.g. a read-only account executive (`decisions/00-open-questions-resolved.md` Q8) — is a Post-MVP refinement layered on top of this same identity system, not a reason to delay shipping identity itself.

## User stories

- As a **CS lead**, I want to log in with a username and password, so that the system knows who I am without me sharing a credential with the whole team.
- As an **engineer**, I want every "who did this" record in the database (a profile edit, a feedback verdict, a draft request) to point at a real user, so that the audit trail in `data-base/12-users-and-auth.md` means something.
- As a **security reviewer**, I want a stolen bearer token to be revocable and to expire on its own, so that a leaked token isn't a permanent backdoor.

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-AUTH-01 | THE SYSTEM SHALL require a valid username and password to obtain a bearer token; no functionality is reachable without one (`POST /auth/login`, `architecture/07-api-spec.md`). |
| REQ-AUTH-02 | THE SYSTEM SHALL store passwords only as an Argon2id hash — plaintext or reversibly-encrypted passwords SHALL NEVER be stored, logged, or transmitted after the initial login request. |
| REQ-AUTH-03 | THE SYSTEM SHALL store only a SHA-256 hash of each issued bearer token (`auth_tokens.token_hash`); the raw token SHALL exist only in the login response body and the client's own storage. |
| REQ-AUTH-04 | Every issued token SHALL carry a hard expiry (`auth_tokens.expires_at`); THE SYSTEM SHALL NEVER issue a token with no expiry. |
| REQ-AUTH-05 | WHEN a request presents a valid, unexpired, unrevoked token, THE SYSTEM SHALL grant access to every functionality in the product (dashboard reads, ask agent, draft composer, profile edits, feedback verdicts) — there is no per-user functional restriction at this stage. |
| REQ-AUTH-06 | THE SYSTEM SHALL allow a token to be revoked before its natural expiry (logout, or manual revocation by an admin), and SHALL reject any request presenting a revoked token even if `expires_at` has not passed. |
| REQ-AUTH-07 | THE SYSTEM SHALL record the authenticated user's identity on every action that creates a "who did this" record: profile edits, feedback verdicts, ask-agent questions, draft-composer requests, baseline confirmations, and replay triggers (see the `*_user_id` columns catalogued in `data-base/12-users-and-auth.md`). |
| REQ-AUTH-08 | IF a login attempt fails (unknown username or wrong password), THEN THE SYSTEM SHALL return a generic failure response that does not reveal whether the username exists. |
| REQ-AUTH-09 | THE SYSTEM SHALL rate-limit login attempts per username to resist credential-stuffing/brute-force attempts, even in the MVP. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-AUTH-P1 | THE SYSTEM SHALL NEVER expose an unauthenticated endpoint that reads or writes client data — the health-check endpoint (`architecture/07-api-spec.md`) is the only unauthenticated route. |
| REQ-AUTH-P2 | THE SYSTEM SHALL NEVER log a raw password or raw bearer token, in any log level, anywhere. |
| REQ-AUTH-P3 | THE SYSTEM SHALL NOT implement per-role functional restrictions at this stage — building partial, untested access control is worse than building none and stating that plainly (this row itself is the honest statement; see Post-MVP note below). |

## Inputs / Outputs

- **Input:** username + password (login), bearer token (every subsequent request).
- **Output:** `users`, `auth_tokens` (`data-base/12-users-and-auth.md`); `*_user_id` foreign keys populated across `client_profile_versions`, `playbook_actions`, `feedback_verdicts`, `ask_queries`, `draft_messages`, `baseline_confirmations`, `replay_runs`.

## Non-functional constraints

- Password hashing: Argon2id, tuned to the OWASP-recommended minimum work factor for the deployment's hosting environment.
- Token lifetime: 12 hours by default (configurable per deployment), balancing "not so short that a CS lead is repeatedly logged out mid-task" against "not so long that a leaked token is a long-lived risk."
- This module sits in front of every API route described in `architecture/07-api-spec.md` — it is middleware, not a separate screen, except for the login form itself.

## Acceptance criteria

- [ ] No API route other than `/auth/login` and the health check responds without a valid token.
- [ ] A revoked token is rejected immediately, even before its `expires_at`.
- [ ] Two failed login attempts in a row for the same username trigger rate-limiting on the third.
- [ ] `grep`-ing application logs for a known test password or test token after a full login/logout cycle returns nothing.
- [ ] Every row in `client_profile_versions`, `feedback_verdicts`, `ask_queries`, and `draft_messages` created during a test session resolves its `*_user_id` to the session's authenticated user.

## Post-MVP note

`users.role` is populated from day one but enforces nothing yet. The Post-MVP work is adding a permission check per role — most concretely, giving the account executive persona (`requirements/00-overview-and-glossary.md`, `decisions/00-open-questions-resolved.md` Q8) read-only access to the dashboard while keeping the ask agent, draft composer, and profile editor CS-lead-only. That is an additive authorization layer on top of this authentication system, not a rebuild of it.

## Traceability

New in spec v1.1 (not present in the original product specification — added per explicit build-start request). Backs `data-base/12-users-and-auth.md`, `architecture/07-api-spec.md` §Authentication, `decisions/00-open-questions-resolved.md` Q8.
