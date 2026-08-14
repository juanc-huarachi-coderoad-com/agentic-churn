# Contract: Authentication

Full shape already specified in `architecture/07-api-spec.md`'s OpenAPI block
(`LoginRequest`/`LoginResponse` schemas) — not reproduced here. This document states only
what's specific to this feature's implementation of that contract.

## `POST /auth/login`

- **Auth**: none (`security: []` in the OpenAPI spec) — one of exactly two unauthenticated
  routes in the whole system, the other being `GET /health`.
- **Success (200)**: `{token, expires_at}` — `token` is the raw opaque value
  (`research.md` §Decision: Opaque bearer tokens), shown exactly once, here.
- **Failure (401)**: identical body for unknown username, wrong password, and a
  deactivated user (`is_active = false`) — `{"detail": "Invalid credentials"}`, always the
  same string, per `REQ-AUTH-08` and spec.md FR-010.
- **Rate limited (429)**: after repeated *failed* attempts from the same source IP in a
  short window — 2 per 5 minutes (`research.md` §Decision: In-process rate limiting,
  including why this is keyed by IP and counts failures only) — `slowapi`, `REQ-AUTH-09`
  — generic message, no detail about the threshold or window (spec.md Edge Cases). A
  successful login never counts against this budget.

## `POST /auth/logout`

- **Auth**: bearer token required.
- **Effect**: `auth_tokens.revoked_at` set for the presented token's row. Idempotent —
  logging out an already-revoked or expired token still returns success, since the end
  state (rejected on next use) is identical either way.
- **Response**: `204`.

## Every other route in this feature

`GET /api/dashboard` (see `contracts/dashboard.md`) requires
`Authorization: Bearer <token>`. Missing, malformed, expired, or revoked → `401`, body
`{"detail": "Not authenticated"}` — never a different message per failure reason
(`REQ-AUTH-08`'s "don't reveal" principle applied consistently, spec.md Edge Cases).
