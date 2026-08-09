# 08 · Schema — Experience (M7, M8, M9, M10)

See `requirements/07-narrator.md`, `08-health-dashboard.md`, `09-ask-agent.md`, `10-draft-composer.md`.

## `narrator_outputs`

One row per `score_runs` row — the readable explanation layer.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `score_run_id` | UUID FK → `score_runs.id` UNIQUE | |
| `headline` | TEXT | |
| `reasons` | JSONB | `[{text, points, evidence_event_ids}]` (REQ-M7-02/03) |
| `actions` | JSONB | `[{text, owner, due_date, playbook_id}]` — every entry has both owner and due_date (REQ-M7-05) |
| `fact_check_passed` | BOOLEAN | Result of the mechanical no-new-facts check (REQ-M7-06) |
| `prompt_version` | TEXT | Versioned prompt used (architecture Rule 5) |
| `created_at` | TIMESTAMPTZ | |

## `playbook_actions`

Human-authored library of standard actions the Narrator personalizes from (REQ-M7-04) — never invents outside this set.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `template_text` | TEXT | e.g. "Escalate {ticket_ref} with {owner}" |
| `applies_to_finding_type` | TEXT | |
| `default_owner_role` | TEXT | |
| `default_sla_days` | INTEGER | |
| `signed_off_by` | TEXT | Per spec §17 Q7 — playbook owner |
| `is_active` | BOOLEAN | |

## `ask_queries`

Log of every Ask agent interaction — also the dataset for measuring the ~90% intent-coverage target.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `question_text` | TEXT | |
| `matched_intent` | TEXT NULL | One of the closed enum values from REQ-M9-02, or NULL/`fallback` |
| `rendered_component` | TEXT NULL | Which UI component was built |
| `declined_reason` | ENUM(`prediction`,`colleague_judgment`,`source_not_connected`,`unclear`) NULL | REQ-M9-05/06/07 |
| `response_time_ms` | INTEGER | Must stay < 3000 (REQ-M9-08) |
| `asked_by` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

## `draft_messages`

**Note the absence of any `sent_at` field — by design (REQ-M10-P1).**

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `issue_id` | UUID FK → `issues.id` | Top issue this draft addresses |
| `stakeholder_id` | UUID FK → `stakeholders.id` | Intended recipient (for context only — never used to send) |
| `draft_text` | TEXT | |
| `tone_variant` | ENUM(`direct`,`formal`,`brief`) | REQ-M10-05 |
| `evidence_event_ids` | UUID[] | |
| `checks_passed` | BOOLEAN | Result of REQ-M10-07 pre-display checks; a FALSE row is never rendered |
| `logged_to_crm_at` | TIMESTAMPTZ NULL | Set only when the user clicks "Log to CRM" (REQ-M10-08) — an activity record, not a transmission |
| `copied_at` | TIMESTAMPTZ NULL | Set when the user clicks "Copy draft" |
| `created_at` | TIMESTAMPTZ | |

## `notifications`

Band-change and digest notifications (spec §15 "over-notification" mitigation: band changes only, daily digest otherwise, no weekend alerts).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `type` | ENUM(`band_change`,`daily_digest`) | |
| `score_run_id` | UUID FK → `score_runs.id`, NULL | |
| `channel` | ENUM(`email`,`slack`,`in_app`) | Per spec §17 Q6 — open question, schema supports all three |
| `sent_at` | TIMESTAMPTZ NULL | *(This is an internal system notification to the CS team, not a client-facing send — does not conflict with REQ-M10-P1, which governs client-facing messages only)* |
| `suppressed_reason` | TEXT NULL | e.g. "weekend" |

## Notes

- The deliberate absence of a `sent_at`/`sent_by` field on `draft_messages` is a **schema-level enforcement** of the no-send boundary — there is no column to populate even if application logic were bypassed.
- `notifications.sent_at` is unrelated to client-facing sending: it tracks *internal* CS-team alerting (e.g. "Slack the CS lead that the band changed"), which is in scope per spec §7 M8 experience layer.
