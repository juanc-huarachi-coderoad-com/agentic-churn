# Contract: Health/Readiness Endpoint

The only external interface this feature exposes. Every real product endpoint (M8/M9/M10)
is documented in `architecture/07-api-spec.md` and does not exist yet at this phase — this
contract exists solely so Docker Compose's healthcheck (and this feature's own acceptance
scenarios, spec.md User Story 1) has something to poll (`research.md` §Decision: Health/
readiness endpoint).

## `GET /health`

**Purpose**: Liveness/readiness probe for the `api` service.

**Request**: No parameters, no auth (this endpoint exists before `requirements/14-
authentication.md`'s auth flow is built in Phase 2, and must remain unauthenticated since
Compose's healthcheck has no credentials to present).

**Response** (200 OK):

```json
{
  "status": "ok",
  "database": "ok"
}
```

- `status`: always `"ok"` if the process is running and able to respond.
- `database`: `"ok"` if a trivial query (`SELECT 1`) against the configured PostgreSQL
  connection succeeds, `"unreachable"` otherwise. This distinguishes "process is up" from
  "process is up but the database it depends on is not" — the same "admit what we cannot
  see" discipline (constitution P5) applied to the platform layer itself, not yet to any
  client-facing score.

**Response** (503 Service Unavailable): returned when `database` would be `"unreachable"`
— Docker Compose's healthcheck treats a non-200 response as unhealthy, which is the
intended behavior (the container should not be marked ready if it cannot reach its
database).

## Out of scope for this contract

No other route exists yet. Authentication (Phase 2), the dashboard read API, the ask
agent, and the draft composer (`architecture/07-api-spec.md`) are all later-phase work and
are explicitly not part of this feature (spec.md §Assumptions).
