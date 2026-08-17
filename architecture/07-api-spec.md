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
| `/api/profile` | POST | **Implemented (specs/011-production-hardening, User Story 5).** The Post-MVP editor route — accepts `ClientProfileInput` directly (the same domain model `/api/profile/reload` builds from YAML), creates a new `client_profile_versions` row, triggers replay. `require_full_access`-gated. See `specs/011-production-hardening/contracts/profile-editor.md`. |
| `/api/profile/reload` | POST | The CS lead edits the YAML file directly (`decisions/00-open-questions-resolved.md` Q2) and calls this to trigger validation + a new `client_profile_versions` row + full replay. **Not removed** now that `POST /api/profile` exists — a deployment that still prefers direct YAML editing keeps using this route (`contracts/profile-editor.md`'s note). |

## Weight recalibration (M6, admin only)

| Route | Method | Body |
|---|---|---|
| `/api/admin/finding-types/{finding_type}` | PATCH | `{base_points}` — `require_admin`-gated (specs/011-production-hardening, User Story 4, FR-014). Writes `finding_type_config.base_points` + an audit row (`finding_type_config_changes`). See `specs/011-production-hardening/contracts/weight-recalibration.md`. |

## Ingestion webhooks (M1)

| Route | Method | Source |
|---|---|---|
| `/webhooks/gmail` | POST | Gmail push notifications (MVP) |
| `/webhooks/zendesk` | POST | Zendesk ticket events (MVP) |
| `/webhooks/slack` | POST | Slack Events API (Post-MVP — route exists in the collector interface from day one per `architecture/02-component-catalog.md`, but is not wired to a live Slack app until Post-MVP) |

Warehouse telemetry and CSAT are poll-only sources (no inbound webhook) per `decisions/01-mvp-scope-and-phasing.md` — they don't need a route here; the collector fetches on a schedule.

Webhook routes are authenticated differently from the routes above: each source's own signature/secret scheme (e.g. Gmail's pub/sub token, Zendesk's webhook signing secret), verified before the payload is trusted — never a user bearer token, since no human is on the other end of a webhook call.

## OpenAPI contract

Not a sketch — every path below has a real `requestBody`/`parameters` and a real `responses` block pointing at a schema in `components.schemas`, so client and server code can actually be generated from this file rather than from the prose tables above. The prose tables stay as the human-readable summary; this YAML is the machine-readable source of truth for shapes.

```yaml
openapi: 3.0.3
info:
  title: Churn Prediction & Sentiment Agent API
  version: 1.1.0
security:
  - bearerAuth: []
paths:
  /auth/login:
    post:
      security: []
      summary: Exchange username/password for a bearer token (REQ-AUTH-01)
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/LoginRequest' }
      responses:
        '200':
          description: Token issued
          content:
            application/json:
              schema: { $ref: '#/components/schemas/LoginResponse' }
        '401':
          description: Generic failure — never reveals whether the username exists (REQ-AUTH-08)
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ErrorResponse' }
  /auth/logout:
    post:
      summary: Revoke the presented token (REQ-AUTH-06)
      responses:
        '204': { description: Token revoked }
  /health:
    get:
      security: []
      summary: Liveness/readiness check, no client data (REQ-AUTH-P1)
      responses:
        '200': { description: OK }
  /api/dashboard:
    get:
      summary: Precomputed dashboard state (REQ-M8-01)
      responses:
        '200':
          description: Full dashboard payload
          content:
            application/json:
              schema: { $ref: '#/components/schemas/DashboardResponse' }
  /api/evidence/{score_contribution_id}:
    get:
      summary: Evidence trace panel for one contribution bar (spec §11.4)
      parameters:
        - name: score_contribution_id
          in: path
          required: true
          schema: { type: string, format: uuid }
      responses:
        '200':
          description: Evidence trace detail
          content:
            application/json:
              schema: { $ref: '#/components/schemas/EvidenceTraceResponse' }
        '404': { description: Not found, content: { application/json: { schema: { $ref: '#/components/schemas/ErrorResponse' } } } }
  /api/coverage:
    get:
      summary: System health screen — sources, coverage, quarantine
      responses:
        '200':
          description: Coverage and quarantine state
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CoverageResponse' }
  /api/ask:
    post:
      summary: Ask-agent question, answered by looking up already-computed data (REQ-M9-03)
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/AskRequest' }
      responses:
        '200':
          description: Either a rendered component or a marked fallback (REQ-M9-04)
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: '#/components/schemas/AskComponentResponse'
                  - $ref: '#/components/schemas/AskFallbackResponse'
  /api/drafts:
    post:
      summary: Generate a draft (REQ-M10-01). No corresponding /send route exists anywhere in this spec.
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/DraftRequest' }
      responses:
        '200':
          description: Generated draft, all pre-display checks passed
          content:
            application/json:
              schema: { $ref: '#/components/schemas/DraftResponse' }
        '422':
          description: REQ-M10-07 pre-display checks failed — no partial draft is ever returned
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ErrorResponse' }
  /api/drafts/{id}/copy:
    post:
      summary: Stamp copied_at (REQ-M10-08)
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string, format: uuid }
      responses:
        '204': { description: Stamped }
  /api/drafts/{id}/log-as-sent:
    post:
      summary: Stamp logged_manually_at — an internal flag only, never a write to any external system (REQ-M10-08, REQ-NFR-18)
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string, format: uuid }
      responses:
        '204': { description: Stamped }
  /api/feedback:
    post:
      summary: Record a verdict (REQ-M4-01)
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/FeedbackRequest' }
      responses:
        '204': { description: Verdict recorded, damping_weights updated }
  /api/profile:
    get:
      summary: Current client profile, read-only
      responses:
        '200':
          description: Current profile
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ProfileResponse' }
  /api/profile/reload:
    post:
      summary: MVP-only — validate the edited YAML file, create a new client_profile_versions row, trigger full replay
      responses:
        '200':
          description: New profile version accepted and replay triggered
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ProfileResponse' }
        '422':
          description: Schema validation failed (REQ-M3-07) — rejected before it can affect scoring
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ErrorResponse' }
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
  schemas:
    ErrorResponse:
      type: object
      required: [detail]
      properties:
        detail: { type: string }

    LoginRequest:
      type: object
      required: [username, password]
      properties:
        username: { type: string }
        password: { type: string, format: password }

    LoginResponse:
      type: object
      required: [token, expires_at]
      properties:
        token: { type: string, description: "Raw bearer token — shown once, never stored server-side in reversible form (REQ-AUTH-03)" }
        expires_at: { type: string, format: date-time }

    ClientHeader:
      type: object
      properties:
        client_name: { type: string }
        band: { $ref: '#/components/schemas/Band' }
        days_to_renewal: { type: integer }

    Band:
      type: string
      enum: [healthy, watch, at_risk]

    ScoreBlock:
      type: object
      properties:
        score: { type: number, format: float, minimum: 0, maximum: 100 }
        band: { $ref: '#/components/schemas/Band' }
        trend: { type: array, items: { type: number } }

    ContributionBar:
      type: object
      properties:
        score_contribution_id: { type: string, format: uuid }
        label: { type: string }
        points: { type: number, format: float }
        is_positive: { type: boolean }

    PulseEvent:
      type: object
      properties:
        event_id: { type: string, format: uuid }
        occurred_at: { type: string, format: date-time }
        severity: { type: string, enum: [info, watch, at_risk] }
        quoted_text: { type: string, nullable: true }

    StakeholderCard:
      type: object
      properties:
        stakeholder_id: { type: string, format: uuid }
        name: { type: string }
        role: { type: string }
        tone_trajectory: { type: string, enum: [stable, deteriorating, improving, unknown] }
        last_seen_at: { type: string, format: date-time, nullable: true }
        status: { type: string, enum: [active, quiet, unresolved_identity] }

    CoverageLine:
      type: object
      properties:
        sources_read: { type: integer }
        sources_expected: { type: integer }
        complete_to: { type: string, format: date-time }
        status: { type: string, enum: [ok, degraded, disconnected] }

    DashboardResponse:
      type: object
      properties:
        client_header: { $ref: '#/components/schemas/ClientHeader' }
        score_block: { $ref: '#/components/schemas/ScoreBlock' }
        contribution_bars: { type: array, items: { $ref: '#/components/schemas/ContributionBar' } }
        pulse_timeline: { type: array, items: { $ref: '#/components/schemas/PulseEvent' } }
        stakeholder_cards: { type: array, items: { $ref: '#/components/schemas/StakeholderCard' } }
        coverage_line: { $ref: '#/components/schemas/CoverageLine' }
        narrator: { $ref: '#/components/schemas/NarratorSummary', nullable: true, description: "specs/008-narrator-and-ask-agent — null when no narrator_outputs row exists yet for the latest score run (REQ-M8-P2 'absent, not empty')" }

    NarratorSummary:
      type: object
      required: [headline, reasons, actions]
      properties:
        headline: { type: string }
        reasons:
          type: array
          items:
            type: object
            properties:
              text: { type: string }
              points: { type: number, format: float }
              evidence_event_ids: { type: array, items: { type: string, format: uuid } }
        actions:
          type: array
          items:
            type: object
            properties:
              text: { type: string }
              owner: { type: string }
              due_date: { type: string, format: date }

    EvidenceTraceResponse:
      type: object
      properties:
        finding_id: { type: string, format: uuid }
        finding_type: { type: string }
        points: { type: number, format: float }
        baseline_value: { type: string }
        current_value: { type: string }
        what_changed: { type: array, items: { type: string } }
        quoted_messages: { type: array, items: { type: object, properties: { event_id: { type: string, format: uuid }, text: { type: string }, occurred_at: { type: string, format: date-time } } } }
        arithmetic_explanation: { type: string, description: "The maths in plain sentences, spec §11.4" }
        disclosure_text: { type: string, nullable: true, description: "REQ-M4-04, specs/010-feedback-memory. Present only when this finding's pattern currently has damping_weights.weight < 1.0; null otherwise — never an empty string." }

    CoverageResponse:
      type: object
      properties:
        sources:
          type: array
          items:
            type: object
            properties:
              source_type: { type: string }
              status: { type: string, enum: [connected, degraded, disconnected] }
              last_successful_sync_at: { type: string, format: date-time, nullable: true }
        quarantine:
          type: array
          items:
            type: object
            properties:
              finding_id: { type: string, format: uuid }
              failed_check: { type: string, enum: [schema_invalid, cited_event_missing, insufficient_evidence, confidence_below_floor] }
        ask_intent_coverage:
          type: object
          nullable: true
          description: "specs/008-narrator-and-ask-agent — null when no ask_queries rows exist yet"
          properties:
            total_questions: { type: integer }
            fallback_count: { type: integer }
            fallback_rate: { type: number, format: float }

    AskRequest:
      type: object
      required: [question]
      properties:
        question: { type: string }

    AskComponentResponse:
      type: object
      required: [intent, component, component_props]
      properties:
        intent: { type: string }
        component: { type: string, enum: [delta_breakdown, baseline_comparison, stakeholder_cards, ranked_issues, action_checklist, commitments_status, filtered_timeline, draft_handoff] }
        component_props: { type: object, description: "For component=draft_handoff: {issue_id, stakeholder_id} — feature 009's draft composer consumes this later (specs/008-narrator-and-ask-agent, Clarifications)" }

    AskFallbackResponse:
      type: object
      required: [fallback_text, sources]
      properties:
        fallback_text: { type: string }
        sources: { type: array, items: { type: string, format: uuid } }
        declined_reason: { type: string, enum: [prediction, colleague_judgment, source_not_connected, unclear, insufficient_history], nullable: true, description: "insufficient_history added by specs/008-narrator-and-ask-agent — distinct from source_not_connected" }

    DraftRequest:
      type: object
      required: [issue_id, stakeholder_id, tone_variant]
      properties:
        issue_id: { type: string, format: uuid }
        stakeholder_id: { type: string, format: uuid }
        tone_variant: { type: string, enum: [direct, formal, brief] }

    DraftResponse:
      type: object
      properties:
        id: { type: string, format: uuid }
        draft_text: { type: string }
        tone_variant: { type: string, enum: [direct, formal, brief] }
        evidence_event_ids: { type: array, items: { type: string, format: uuid }, minItems: 1 }
        checks_passed: { type: boolean }

    FeedbackRequest:
      type: object
      required: [verdict]
      description: "At least one of finding_id/issue_id is required (data-base/10-ddl-appendix.md CHECK verdict_has_a_target)"
      properties:
        finding_id: { type: string, format: uuid, nullable: true }
        issue_id: { type: string, format: uuid, nullable: true }
        verdict: { type: string, enum: [correct, false_alarm, resolved] }

    ProfileResponse:
      type: object
      properties:
        version_number: { type: integer }
        client_name: { type: string }
        renewal_date: { type: string, format: date }
        contract_value_band: { type: string, enum: [strategic, standard, smb] }
        stakeholders:
          type: array
          items:
            type: object
            properties:
              name: { type: string }
              role: { type: string }
              influence: { type: string, enum: [sponsor, daily_user, unknown] }
              signs_renewal: { type: boolean }
        product_areas:
          type: array
          items:
            type: object
            properties:
              key: { type: string }
              criticality: { type: string, enum: [critical, standard, peripheral] }
        commitments:
          type: array
          items:
            type: object
            properties:
              type: { type: string, enum: [first_response, recurring_sync, milestone] }
              threshold_business_hours: { type: number, nullable: true }
```

## Non-functional constraints

- Dashboard reads: < 1s (REQ-NFR-01). Ask agent: < 3s (REQ-M9-08). Both measured at the API layer, not just the database.
- Every response body is JSON; every request/response pair is logged with `asked_by_user_id`/`submitted_by_user_id`/`requested_by_user_id` as applicable — never a raw token, never a raw password (REQ-AUTH-P2).
- Rate limiting: applied to `/auth/login` per REQ-AUTH-09; not yet applied elsewhere in the MVP (a Post-MVP hardening item, not a functional gap).

## Traceability

`requirements/08-health-dashboard.md`, `requirements/09-ask-agent.md`, `requirements/10-draft-composer.md`, `requirements/04-feedback-memory.md`, `requirements/03-client-profile.md`, `requirements/01-signal-collectors.md`, `requirements/14-authentication.md`.
