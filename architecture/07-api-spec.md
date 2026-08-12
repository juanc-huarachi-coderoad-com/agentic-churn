# 07 · API specification

The one contract between the FastAPI backend and everything that talks to it: the React dashboard (M8/M9/M10), the ingestion webhooks (M1), and — new in this revision — the login flow (`requirements/14-authentication.md`).

## Authentication (backs `requirements/14-authentication.md`)

**Every route below requires a bearer token except `/health` and `/auth/login`.** There is no other exception, per REQ-AUTH-P1.

| Route | Method | Auth | Purpose |
|---|---|---|---|
| `/auth/login` | POST | None | `{username, password}` → `{token, expires_at}`. Generic 401 on failure (REQ-AUTH-08) — never reveals whether the username exists. |
| `/auth/logout` | POST | Bearer | Revokes the presented token (`auth_tokens.revoked_at`). |
| `/health` | GET | None | Liveness/readiness only — no client data, ever (REQ-AUTH-P1). |

Every other route below expects `Authorization: Bearer <token>`. A missing, expired, or revoked token gets `401 Unauthorized` with no further detail (matches REQ-AUTH-08's spirit: don't leak information in the failure). At this stage (MVP), any valid token grants access to every route — there is no per-route role check yet (REQ-AUTH-05, REQ-AUTH-P3). The `role` claim is present in the token's associated user record for forward compatibility, not enforced.

## Dashboard reads (M8)

Pure reads — no route in this section computes anything; every response is a direct read of `score_runs`/`narrator_outputs`/`rollups`/`coverage_reports` (REQ-M8-01, REQ-M8-P1).

| Route | Method | Returns |
|---|---|---|
| `/api/dashboard` | GET | Client header, current score block, contribution bars, pulse timeline, stakeholder cards, coverage line — everything in `requirements/08-health-dashboard.md` REQ-M8-02 in one payload |
| `/api/evidence/{score_contribution_id}` | GET | The evidence trace panel: finding detail, baseline-vs-current comparison, cited events, arithmetic in words (spec §11.4) |
| `/api/coverage` | GET | System health screen: per-source status, last successful sync, quarantine list |

## Ask agent (M9)

| Route | Method | Body → Response |
|---|---|---|
| `/api/ask` | POST | `{question}` → `{intent, component, props}` on a match, or `{fallback_text, sources}` on no match (REQ-M9-04). Logs to `ask_queries` with `asked_by_user_id` taken from the bearer token, never from the request body. |

## Draft composer (M10)

| Route | Method | Body → Response |
|---|---|---|
| `/api/drafts` | POST | `{issue_id, stakeholder_id, tone_variant}` → the generated draft, or `422` if REQ-M10-07's pre-display checks fail |
| `/api/drafts/{id}/copy` | POST | Stamps `copied_at`. No response body needed beyond `204`. |
| `/api/drafts/{id}/log-as-sent` | POST | Stamps `logged_manually_at` (REQ-M10-08). **There is no `/send` route, in any form — not rate-limited, not feature-flagged, not admin-only. It does not exist in this file because it does not exist in the system (REQ-M10-P1).** |

## Feedback (M4)

| Route | Method | Body |
|---|---|---|
| `/api/feedback` | POST | `{finding_id or issue_id, verdict}` — one click, no confirmation step (spec §11.6). `submitted_by_user_id` comes from the bearer token. |

## Client profile (M3)

| Route | Method | Purpose |
|---|---|---|
| `/api/profile` | GET | Current profile, read-only |
| `/api/profile/reload` | POST | **MVP only.** The CS lead edits the YAML file directly (`decisions/00-open-questions-resolved.md` Q2) and calls this to trigger validation + a new `client_profile_versions` row + full replay. Post-MVP replaces this with a real editor UI writing through `POST /api/profile` directly. |

## Ingestion webhooks (M1)

| Route | Method | Source |
|---|---|---|
| `/webhooks/gmail` | POST | Gmail push notifications (MVP) |
| `/webhooks/zendesk` | POST | Zendesk ticket events (MVP) |
| `/webhooks/slack` | POST | Slack Events API (Post-MVP — route exists in the collector interface from day one per `architecture/02-component-catalog.md`, but is not wired to a live Slack app until Post-MVP) |

Warehouse telemetry and CSAT are poll-only sources (no inbound webhook) per `decisions/01-mvp-scope-and-phasing.md` — they don't need a route here; the collector fetches on a schedule.

Webhook routes are authenticated differently from the routes above: each source's own signature/secret scheme (e.g. Gmail's pub/sub token, Zendesk's webhook signing secret), verified before the payload is trusted — never a user bearer token, since no human is on the other end of a webhook call.

## Minimal OpenAPI skeleton

```yaml
openapi: 3.0.3
info:
  title: Churn Prediction & Sentiment Agent API
  version: 1.1.0
security:
  - bearerAuth: []
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
paths:
  /auth/login:
    post:
      security: []
      summary: Exchange username/password for a bearer token
  /health:
    get:
      security: []
      summary: Liveness/readiness check, no client data
  /api/dashboard:
    get:
      summary: Precomputed dashboard state (REQ-M8-01)
  /api/ask:
    post:
      summary: Ask-agent question, answered by looking up already-computed data (REQ-M9-03)
  /api/drafts:
    post:
      summary: Generate a draft (REQ-M10-01). No corresponding /send route exists anywhere in this spec.
```

## Non-functional constraints

- Dashboard reads: < 1s (REQ-NFR-01). Ask agent: < 3s (REQ-M9-08). Both measured at the API layer, not just the database.
- Every response body is JSON; every request/response pair is logged with `asked_by_user_id`/`submitted_by_user_id`/`requested_by_user_id` as applicable — never a raw token, never a raw password (REQ-AUTH-P2).
- Rate limiting: applied to `/auth/login` per REQ-AUTH-09; not yet applied elsewhere in the MVP (a Post-MVP hardening item, not a functional gap).

## Traceability

`requirements/08-health-dashboard.md`, `requirements/09-ask-agent.md`, `requirements/10-draft-composer.md`, `requirements/04-feedback-memory.md`, `requirements/03-client-profile.md`, `requirements/01-signal-collectors.md`, `requirements/14-authentication.md`.
