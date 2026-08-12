# 08 · Schema — Experience (M7, M8, M9, M10)

See `requirements/07-narrator.md`, `08-health-dashboard.md`, `09-ask-agent.md`, `10-draft-composer.md`. Examples below continue directly from `examples/01-end-to-end-walkthrough.md` §10–13.

**Why this schema exists, in plain terms:** everything up to this point computed a number. These five tables are where that number becomes something a person can actually read, ask questions about, and act on — and, just as importantly, where the system's hard "no send" boundary is enforced not by a UI rule but by a column that simply does not exist.

## `narrator_outputs`

**In plain terms:** the readable explanation for one scoring run — a headline, a few reasons with their point values, and a short action list. Exactly one row per `score_runs` row; if there's no narration yet, the dashboard has nothing to show, ever, even though the number itself already exists.

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

**Example row** — the narration for `run-score-1` (score 85.30):

| score_run_id | headline | fact_check_passed |
|---|---|---|
| `run-score-1` | "We took 19 hours to reply to a P1 ticket — we promised 4 — and Ana is pulling back at the same time." | **true** |

Every number and name in that headline — "19 hours," "4," "Ana" — exists verbatim in `score_contributions` and `stakeholders`. If the model had instead written "…and the account is likely to churn," the fact-check would fail (that's a prediction, not a fact in the input) and the sentence would be dropped before this row is ever written.

## `playbook_actions`

**In plain terms:** the fixed menu of standard actions the narrator is allowed to suggest. It personalizes these templates with real names and dates — it cannot invent a new kind of action that isn't in this table.

Human-authored library of standard actions the Narrator personalizes from (REQ-M7-04) — never invents outside this set.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `template_text` | TEXT | e.g. "Escalate {ticket_ref} with {owner}" |
| `applies_to_finding_type` | TEXT | |
| `default_owner_role` | TEXT | |
| `default_sla_days` | INTEGER | |
| `signed_off_by_user_id` | UUID FK → `users.id`, NULL | Per `decisions/00-open-questions-resolved.md` Q7 — playbook owner, a real identity (`data-base/12-users-and-auth.md`) |
| `is_active` | BOOLEAN | |

**Example rows** — two of the Phase 1 playbook's 3–5 actions (`decisions/00-open-questions-resolved.md` Q7):

| id | template_text | applies_to_finding_type | default_owner_role | signed_off_by_user_id |
|---|---|---|---|---|
| `pb-escalate-p1` | "Escalate {ticket_ref} with engineering {when}" | `broken_response_promise` | Support lead | Marta's user row |
| `pb-call-sponsor` | "Call {stakeholder_name} before {deadline} — don't email" | `escalation_language` | CS lead | Marta's user row |

## `ask_queries`

**In plain terms:** a log of every question typed into the Ask box, what the system understood it to mean, and what it showed back — this doubles as the dataset for measuring whether the small, fixed set of question types is actually covering what people ask (spec's ~90% target).

Log of every Ask agent interaction — also the dataset for measuring the ~90% intent-coverage target.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `question_text` | TEXT | |
| `matched_intent` | TEXT NULL | One of the closed enum values from REQ-M9-02, or NULL/`fallback` |
| `rendered_component` | TEXT NULL | Which UI component was built |
| `declined_reason` | ENUM(`prediction`,`colleague_judgment`,`source_not_connected`,`unclear`) NULL | REQ-M9-05/06/07 |
| `response_time_ms` | INTEGER | Must stay < 3000 (REQ-M9-08) |
| `asked_by_user_id` | UUID FK → `users.id` | A real identity, not free text — see `data-base/12-users-and-auth.md` |
| `created_at` | TIMESTAMPTZ | |

**Example rows** — one answered normally, one declined:

| question_text | matched_intent | rendered_component | declined_reason | response_time_ms |
|---|---|---|---|---|
| "Why did the score go up?" | `score_delta` | Delta breakdown | *(null)* | 1,840 |
| "Will Meridian actually cancel?" | *(null)* | *(null)* | `prediction` | 210 |

The second row shows the decline path: the agent recognized this as a forecasting question, refused to guess, and answered fast (210ms) precisely because it didn't have to look anything up — declining is cheap and immediate.

## `draft_messages`

**In plain terms:** every message the draft composer has ever written, together with whether the human copied it and whether they told the system they'd sent it themselves. **There is no column here that means "sent to the client," and no column that writes anywhere outside this system — not even the CRM.** That's not an oversight — look at the field list below and you'll notice both are genuinely missing.

**Note the absence of any `sent_at` field, and the absence of any external-system write (including CRM) — both by design (REQ-M10-P1, REQ-NFR-18).**

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `issue_id` | UUID FK → `issues.id` | Top issue this draft addresses |
| `stakeholder_id` | UUID FK → `stakeholders.id` | Intended recipient (for context only — never used to send) |
| `requested_by_user_id` | UUID FK → `users.id` | Who clicked "Write to X about this" (`data-base/12-users-and-auth.md`) |
| `draft_text` | TEXT | |
| `tone_variant` | ENUM(`direct`,`formal`,`brief`) | REQ-M10-05 |
| `evidence_event_ids` | UUID[], `array_length >= 1` | Non-empty by constraint — a draft with zero cited evidence is structurally unrepresentable, same discipline as `findings.cited_event_ids` |
| `checks_passed` | BOOLEAN | Result of REQ-M10-07 pre-display checks; a FALSE row is never rendered |
| `logged_manually_at` | TIMESTAMPTZ NULL | Set only when the user clicks "Log as sent (manual)" (REQ-M10-08) — an internal flag in *this* table only, never a write to the CRM or any other external system |
| `copied_at` | TIMESTAMPTZ NULL | Set when the user clicks "Copy draft" |
| `created_at` | TIMESTAMPTZ | |

**Example row** — the draft to Ana from the worked example:

| id | issue_id | stakeholder_id | requested_by_user_id | draft_text (excerpt) | checks_passed | logged_manually_at | copied_at |
|---|---|---|---|---|---|---|---|
| `draft-1` | `iss-A` | `stk-ana` | Marta's user row | "Ana — we took 19 hours to respond to ticket #456; we promised 4. Engineering is on it today…" | **true** | *(null)* | 2026-08-10 09:02 |

The CS lead copied this draft (`copied_at` is stamped) and pasted it into their own email client to actually send it — an action that happened entirely outside this system's boundary, which is exactly why no row, anywhere in this database, ever records "sent," and no external system — CRM included — is ever contacted by this table.

## `notifications`

**In plain terms:** internal alerts *to the CS team* (never to the client) — a band change or a daily summary landing in-app, email, or Slack, depending on what Phase the deployment is in (`decisions/00-open-questions-resolved.md` Q6).

Band-change and digest notifications (spec §15 "over-notification" mitigation: band changes only, daily digest otherwise, no weekend alerts).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `type` | ENUM(`band_change`,`daily_digest`) | |
| `score_run_id` | UUID FK → `score_runs.id`, NULL | |
| `channel` | ENUM(`email`,`slack`,`in_app`) | Phase 1 uses `in_app` only; `email`/`slack` activate in Phase 2 (`decisions/00-open-questions-resolved.md` Q6) |
| `sent_at` | TIMESTAMPTZ NULL | *(This is an internal system notification to the CS team, not a client-facing send — does not conflict with REQ-M10-P1, which governs client-facing messages only)* |
| `suppressed_reason` | TEXT NULL | e.g. "weekend" |

**Example row** — the Phase 1 notification for this run's band change:

| type | score_run_id | channel | sent_at | suppressed_reason |
|---|---|---|---|---|
| `band_change` | `run-score-1` | `in_app` | 2026-08-07 10:16 | *(null)* |

## Notes

- The deliberate absence of a `sent_at`/`sent_by` field on `draft_messages` is a **schema-level enforcement** of the no-send boundary — there is no column to populate even if application logic were bypassed.
- `notifications.sent_at` is unrelated to client-facing sending: it tracks *internal* CS-team alerting (e.g. "Slack the CS lead that the band changed"), which is in scope per spec §7 M8 experience layer.
