# 10 · DDL appendix

Runnable PostgreSQL 16 DDL for every table described in `02`–`08` and `12`. This revision (v1.1) closes seven gaps found in a full-repo consistency review: missing indexes, roles/grants that were placeholders, an unspecified hash-chain algorithm, a replay-vs-human-confirmation contradiction on `rollups.is_baseline`, a crypto-shredding contradiction on `data_key_ref`, free-text "who did this" columns with no real identity behind them, and four enum columns that were left as plain `TEXT`.

```sql
-- ============================================================
-- Extensions
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 00 · Authentication & identity (backs requirements/14-authentication.md)
-- Created first: every "who did this" column below references users(id).
-- ============================================================
CREATE TYPE user_role AS ENUM ('cs_lead','support_lead','account_executive','engineering_manager','admin');
-- MVP note: role is informational only. Every authenticated user has full
-- functional access at this stage (REQ-AUTH-05) — role-based restriction
-- (e.g. read-only account_executive) is a Post-MVP refinement, not built yet.

CREATE TABLE users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,          -- argon2id hash, never plaintext or reversible (REQ-AUTH-02)
    display_name   TEXT NOT NULL,
    role           user_role,
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at  TIMESTAMPTZ
);

CREATE TABLE auth_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id),
    token_hash   TEXT NOT NULL UNIQUE,     -- SHA-256 of the bearer token; the raw token is never stored (REQ-AUTH-03)
    issued_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked_at   TIMESTAMPTZ
);

CREATE INDEX idx_auth_tokens_user_id ON auth_tokens(user_id);

-- ============================================================
-- 02 · Ingestion
-- ============================================================
CREATE TYPE source_type AS ENUM (
    'zendesk','jira','intercom','gmail','microsoft365','slack','teams',
    'warehouse','csat','nps','calendar','transcripts','salesforce','contracts'
);
CREATE TYPE source_status AS ENUM ('connected','degraded','disconnected');

CREATE TABLE sources (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type             source_type NOT NULL,
    display_name            TEXT NOT NULL,
    auth_scope              TEXT NOT NULL,
    status                  source_status NOT NULL DEFAULT 'connected',
    last_successful_sync_at TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE collector_trigger AS ENUM ('webhook','poll','manual');

CREATE TABLE collector_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           UUID NOT NULL REFERENCES sources(id),
    trigger             collector_trigger NOT NULL,
    window_start        TIMESTAMPTZ NOT NULL,
    window_end          TIMESTAMPTZ NOT NULL,
    envelopes_emitted   INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped  INTEGER NOT NULL DEFAULT 0,
    error               TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ
);

CREATE TABLE coverage_reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collector_run_id  UUID NOT NULL REFERENCES collector_runs(id),
    sources_expected  INTEGER NOT NULL,
    sources_read      INTEGER NOT NULL,
    gap_reason        TEXT,
    complete_to       TIMESTAMPTZ NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE identity_resolution AS ENUM ('exact_match','human_confirmed','unresolved');

CREATE TABLE identity_map (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_identifier  TEXT NOT NULL,
    source_type        source_type NOT NULL,
    stakeholder_id     UUID,               -- FK added after stakeholders table exists
    match_confidence   NUMERIC(3,2),
    resolved_by        identity_resolution NOT NULL,
    first_seen_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_identifier, source_type)
);

CREATE TYPE identity_status AS ENUM ('resolved','unresolved');

-- Crypto-shredding model (resolves the data_key_ref contradiction):
-- data_key_ref is a PERMANENT, NOT NULL reference to a key ID — it is never
-- cleared, because raw_envelopes is an insert-only table. Deletion happens by
-- destroying the referenced key in the key store (.env file in the MVP, KMS
-- Post-MVP); once destroyed, payload_encrypted is cryptographically
-- unrecoverable even though this row and its data_key_ref value are untouched.
CREATE TABLE raw_envelopes (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collector_run_id   UUID NOT NULL REFERENCES collector_runs(id),
    source_native_id   TEXT NOT NULL,
    idempotency_key    TEXT NOT NULL UNIQUE,
    occurred_at        TIMESTAMPTZ NOT NULL,
    identity_status    identity_status NOT NULL,
    redacted_fields    TEXT[] NOT NULL DEFAULT '{}',
    payload_encrypted  BYTEA NOT NULL,
    data_key_ref       TEXT NOT NULL,       -- permanent reference; see crypto-shredding note above
    ledger_event_id    UUID,                -- FK added after events table exists; NULL if quarantined pre-ledger
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 03 · Event ledger
-- ============================================================
CREATE TYPE event_type AS ENUM (
    'message','ticket_state_change','usage_measurement','survey_response',
    'meeting','absence','crm_change'
);

-- Hash chain specification (was previously unspecified):
--   Algorithm: SHA-256, via pgcrypto's digest().
--   Canonical serialization (pipe-delimited, NULLs as empty string):
--     id | envelope_id | event_type | occurred_at | recorded_at |
--     stakeholder_id | product_area_id | structured_payload::text |
--     supersedes_event_id | thread_key | prev_event_hash
--   (body_encrypted/data_key_ref are deliberately excluded from the hashed
--   payload — they are ciphertext/key-management fields, not the fact being
--   chained, and excluding them means crypto-shredding a body never breaks
--   the hash chain's own integrity check.)
--   Genesis value: prev_event_hash = repeat('0', 64) for the very first event
--   ever inserted into this deployment's ledger.
--   Verification: see verify_hash_chain() at the bottom of this file.
CREATE TABLE events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    envelope_id         UUID NOT NULL REFERENCES raw_envelopes(id),
    event_type          event_type NOT NULL,
    occurred_at         TIMESTAMPTZ NOT NULL,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    stakeholder_id      UUID,               -- FK added after stakeholders table exists
    product_area_id     UUID,               -- FK added after product_areas table exists
    body_encrypted      BYTEA,               -- nulled by the retention job once the key is destroyed (see role grant below)
    data_key_ref        TEXT NOT NULL,       -- permanent reference; never cleared (see crypto-shredding note above)
    structured_payload  JSONB NOT NULL DEFAULT '{}',
    supersedes_event_id UUID REFERENCES events(id),
    thread_key          TEXT,
    prev_event_hash     TEXT NOT NULL,
    event_hash          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE raw_envelopes  ADD CONSTRAINT fk_raw_envelopes_event  FOREIGN KEY (ledger_event_id) REFERENCES events(id);

CREATE TYPE stitch_method AS ENUM ('participant_subject','ticket_reference','timing_heuristic','manual');

CREATE TABLE event_threads (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_key        TEXT NOT NULL,
    event_id          UUID NOT NULL REFERENCES events(id),
    stitch_confidence NUMERIC(3,2) NOT NULL,
    stitch_method     stitch_method NOT NULL
);

CREATE TYPE response_pair_state AS ENUM ('open','resolved','open_overdue');

CREATE TABLE response_pairs (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_event_id          UUID NOT NULL REFERENCES events(id),
    reply_event_id           UUID REFERENCES events(id),
    commitment_id            UUID,          -- FK added after commitments table exists
    business_hours_elapsed   NUMERIC(10,2),
    state                    response_pair_state NOT NULL DEFAULT 'open',
    profile_version_id       UUID           -- FK added after client_profile_versions table exists
);

CREATE TYPE rollup_subject_type AS ENUM ('stakeholder','product_area','account');

CREATE TABLE rollups (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type  rollup_subject_type NOT NULL,
    subject_id    UUID,
    metric        TEXT NOT NULL,
    window_start  TIMESTAMPTZ NOT NULL,
    window_end    TIMESTAMPTZ NOT NULL,
    value         NUMERIC NOT NULL,
    is_baseline   BOOLEAN NOT NULL DEFAULT false,   -- set FROM baseline_confirmations on every replay; see below
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Replay-vs-human-confirmation fix: rollups is a PROJECTION — it gets
-- TRUNCATEd and rebuilt from events on every replay (data-base/01, principle
-- 3). If is_baseline lived only on the rollup row, a human's baseline
-- confirmation would be silently lost the next time replay runs. It doesn't:
-- the confirmation is stored durably here instead, and the replay job sets
-- rollups.is_baseline = true for any window that matches a confirmed row.
CREATE TABLE baseline_confirmations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type      rollup_subject_type NOT NULL,
    subject_id        UUID NOT NULL,
    metric            TEXT NOT NULL,
    window_start      TIMESTAMPTZ NOT NULL,
    window_end        TIMESTAMPTZ NOT NULL,
    confirmed_by_user_id UUID NOT NULL REFERENCES users(id),
    confirmed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (subject_type, subject_id, metric, window_start, window_end)
);

-- Audit trail for replay itself (previously nonexistent — every replay was
-- invisible after the fact). One row per replay job run.
CREATE TYPE replay_trigger AS ENUM ('profile_edit','weight_edit','manual');
CREATE TYPE replay_status AS ENUM ('running','succeeded','failed');

CREATE TABLE replay_runs (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger                replay_trigger NOT NULL,
    triggered_by_user_id   UUID REFERENCES users(id),    -- NULL for automated triggers
    started_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at            TIMESTAMPTZ,
    projections_rebuilt    TEXT[] NOT NULL DEFAULT '{event_threads,response_pairs,rollups}',
    events_replayed_count  INTEGER,
    status                 replay_status NOT NULL DEFAULT 'running',
    error                  TEXT
);

-- ============================================================
-- 04 · Client profile & context
-- ============================================================
CREATE TYPE contract_value_band AS ENUM ('strategic','standard','smb');

CREATE TABLE client_profile_versions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_number        INTEGER NOT NULL,
    client_name           TEXT NOT NULL,
    renewal_date          DATE NOT NULL,
    contract_value_band   contract_value_band NOT NULL,
    business_goals        TEXT[] NOT NULL DEFAULT '{}',
    working_hours_start   TIME NOT NULL,
    working_hours_end     TIME NOT NULL,
    timezone              TEXT NOT NULL,
    languages              TEXT[] NOT NULL DEFAULT '{}',
    communication_norms   TEXT,
    exclusions            TEXT[] NOT NULL DEFAULT '{}',
    authored_by_user_id   UUID NOT NULL REFERENCES users(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current             BOOLEAN NOT NULL DEFAULT false
);

CREATE UNIQUE INDEX one_current_profile ON client_profile_versions (is_current) WHERE is_current;

CREATE TYPE influence_level AS ENUM ('sponsor','daily_user','unknown');

CREATE TABLE stakeholders (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_version_id   UUID NOT NULL REFERENCES client_profile_versions(id),
    external_id          TEXT NOT NULL,
    name                 TEXT NOT NULL,
    role                 TEXT,
    influence            influence_level NOT NULL,
    influence_multiplier NUMERIC(3,2) NOT NULL,
    signs_renewal        BOOLEAN NOT NULL DEFAULT false,
    identifiers          TEXT[] NOT NULL DEFAULT '{}'
);

ALTER TABLE identity_map ADD CONSTRAINT fk_identity_map_stakeholder FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id);
ALTER TABLE events        ADD CONSTRAINT fk_events_stakeholder       FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id);

CREATE TYPE criticality_level AS ENUM ('critical','standard','peripheral');

CREATE TABLE product_areas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_version_id      UUID NOT NULL REFERENCES client_profile_versions(id),
    key                     TEXT NOT NULL,
    criticality             criticality_level NOT NULL,
    criticality_multiplier  NUMERIC(3,2) NOT NULL
);

ALTER TABLE events ADD CONSTRAINT fk_events_product_area FOREIGN KEY (product_area_id) REFERENCES product_areas(id);

CREATE TYPE commitment_type AS ENUM ('first_response','recurring_sync','milestone');

CREATE TABLE commitments (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_version_id       UUID NOT NULL REFERENCES client_profile_versions(id),
    type                     commitment_type NOT NULL,
    priority                 TEXT,
    threshold_business_hours NUMERIC(6,2),
    cadence                  TEXT
);

ALTER TABLE response_pairs ADD CONSTRAINT fk_response_pairs_commitment FOREIGN KEY (commitment_id) REFERENCES commitments(id);
ALTER TABLE response_pairs ADD CONSTRAINT fk_response_pairs_profile    FOREIGN KEY (profile_version_id) REFERENCES client_profile_versions(id);

CREATE TABLE profile_history_entries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_version_id  UUID NOT NULL REFERENCES client_profile_versions(id),
    event_date          DATE NOT NULL,
    description         TEXT NOT NULL
);

-- ============================================================
-- 05 · Reasoning
-- ============================================================
CREATE TYPE reader_type AS ENUM (
    'commitment','usage','recurrence','absence','relationship','tone','intent','meeting'
);
CREATE TYPE finding_status AS ENUM ('pending_validation','validated','quarantined');
CREATE TYPE finding_state  AS ENUM ('open','resolved','open_overdue');

CREATE TABLE finding_type_config (
    finding_type       TEXT PRIMARY KEY,
    base_points        NUMERIC(6,2) NOT NULL,
    confidence_floor   NUMERIC(3,2) NOT NULL,
    min_evidence_count INTEGER NOT NULL,
    half_life_days     NUMERIC(6,2),
    version            TEXT NOT NULL
);

CREATE TABLE findings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reader_type       reader_type NOT NULL,
    reader_version    TEXT NOT NULL,
    finding_type      TEXT NOT NULL REFERENCES finding_type_config(finding_type),
    magnitude         NUMERIC(3,2) NOT NULL CHECK (magnitude BETWEEN 0 AND 1),
    confidence        NUMERIC(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    cited_event_ids   UUID[] NOT NULL CHECK (array_length(cited_event_ids, 1) >= 1),
    stakeholder_id    UUID REFERENCES stakeholders(id),
    product_area_id   UUID REFERENCES product_areas(id),
    status            finding_status NOT NULL DEFAULT 'pending_validation',
    state             finding_state,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE cluster_method AS ENUM ('embedding_similarity','shared_entity','manual');

CREATE TABLE issues (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label          TEXT NOT NULL,
    cluster_method cluster_method NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE finding_issue_map (
    finding_id         UUID NOT NULL REFERENCES findings(id),
    issue_id           UUID NOT NULL REFERENCES issues(id),
    rank_within_issue  INTEGER NOT NULL,
    PRIMARY KEY (finding_id, issue_id)
);

CREATE TYPE validation_check AS ENUM (
    'schema_invalid','cited_event_missing','insufficient_evidence','confidence_below_floor'
);

-- UNIQUE(finding_id): a finding is quarantined at most once — it is never
-- re-submitted for another validation attempt (REQ-M5A-03: never repaired,
-- never retried). This also makes the ERD's FINDINGS ||--o| QUARANTINE
-- (one-to-zero-or-one) cardinality actually true in the schema, not just the diagram.
CREATE TABLE quarantine (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id    UUID NOT NULL UNIQUE REFERENCES findings(id),
    failed_check  validation_check NOT NULL,
    detail        TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE validation_failures (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quarantine_id  UUID NOT NULL REFERENCES quarantine(id),
    check_name     TEXT NOT NULL,
    expected       TEXT,
    actual         TEXT
);

-- ============================================================
-- 06 · Scoring
-- ============================================================
CREATE TYPE score_trigger AS ENUM (
    'new_event','burst_batch','urgent_fast_path','hourly_heartbeat',
    'profile_edit_replay','weight_edit_replay','manual'
);
CREATE TYPE band AS ENUM ('healthy','watch','at_risk');

CREATE TABLE score_runs (
    id                             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger                        score_trigger NOT NULL,
    profile_version_id             UUID NOT NULL REFERENCES client_profile_versions(id),
    finding_type_config_version    TEXT NOT NULL,
    total_negative_points          NUMERIC(10,3) NOT NULL,
    total_positive_points          NUMERIC(10,3) NOT NULL DEFAULT 0,
    positive_points_applied        NUMERIC(10,3) NOT NULL DEFAULT 0,
    total_points                   NUMERIC(10,3) NOT NULL,
    score                          NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score < 100),
    band                           band NOT NULL,
    raw_band                       band NOT NULL,
    stakes                         NUMERIC(6,3),
    source_degraded                BOOLEAN NOT NULL DEFAULT false,
    is_frozen                      BOOLEAN NOT NULL DEFAULT false,
    computed_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE score_contributions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    score_run_id                UUID NOT NULL REFERENCES score_runs(id),
    finding_id                  UUID NOT NULL REFERENCES findings(id),
    issue_id                    UUID REFERENCES issues(id),
    base                        NUMERIC(8,3) NOT NULL,
    influence                   NUMERIC(4,3) NOT NULL,
    criticality                 NUMERIC(4,3) NOT NULL,
    confidence                  NUMERIC(4,3) NOT NULL,
    magnitude                   NUMERIC(4,3) NOT NULL,
    recency                     NUMERIC(4,3) NOT NULL,
    damping                     NUMERIC(4,3) NOT NULL CHECK (damping BETWEEN 0 AND 1.000),
    rank_within_issue_factor    NUMERIC(4,3) NOT NULL DEFAULT 1.000,
    points_contributed          NUMERIC(8,3) NOT NULL,
    is_positive                 BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE band_history (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    score_run_id              UUID NOT NULL REFERENCES score_runs(id),
    band                      band NOT NULL,
    consecutive_runs_in_band  INTEGER NOT NULL DEFAULT 1,
    notified                  BOOLEAN NOT NULL DEFAULT false,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 07 · Feedback memory
-- ============================================================
CREATE TYPE verdict_type AS ENUM ('correct','false_alarm','resolved');

CREATE TABLE feedback_verdicts (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id            UUID REFERENCES findings(id),
    issue_id              UUID REFERENCES issues(id),
    verdict               verdict_type NOT NULL,
    submitted_by_user_id  UUID NOT NULL REFERENCES users(id),
    pattern_signature     TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT verdict_has_a_target CHECK (finding_id IS NOT NULL OR issue_id IS NOT NULL)
);

CREATE TABLE damping_weights (
    pattern_signature   TEXT PRIMARY KEY,
    weight               NUMERIC(4,3) NOT NULL DEFAULT 1.000 CHECK (weight BETWEEN 0 AND 1.000),
    false_alarm_count    INTEGER NOT NULL DEFAULT 0,
    resolved_count        INTEGER NOT NULL DEFAULT 0,
    correct_count          INTEGER NOT NULL DEFAULT 0,
    last_updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    disclosure_text        TEXT
);

-- ============================================================
-- 08 · Experience
-- ============================================================
CREATE TABLE playbook_actions (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_text            TEXT NOT NULL,
    applies_to_finding_type  TEXT NOT NULL,
    default_owner_role       TEXT NOT NULL,
    default_sla_days         INTEGER NOT NULL,
    signed_off_by_user_id    UUID REFERENCES users(id),
    is_active                BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE narrator_outputs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    score_run_id      UUID NOT NULL UNIQUE REFERENCES score_runs(id),
    headline          TEXT NOT NULL,
    reasons           JSONB NOT NULL,
    actions           JSONB NOT NULL,
    fact_check_passed BOOLEAN NOT NULL,
    prompt_version    TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE declined_reason AS ENUM ('prediction','colleague_judgment','source_not_connected','unclear');

CREATE TABLE ask_queries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_text       TEXT NOT NULL,
    matched_intent      TEXT,
    rendered_component  TEXT,
    declined_reason     declined_reason,
    response_time_ms    INTEGER,
    asked_by_user_id    UUID NOT NULL REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE tone_variant AS ENUM ('direct','formal','brief');

CREATE TABLE draft_messages (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id             UUID NOT NULL REFERENCES issues(id),
    stakeholder_id       UUID NOT NULL REFERENCES stakeholders(id),
    requested_by_user_id UUID NOT NULL REFERENCES users(id),
    draft_text           TEXT NOT NULL,
    tone_variant         tone_variant NOT NULL,
    evidence_event_ids   UUID[] NOT NULL CHECK (array_length(evidence_event_ids, 1) >= 1),
    checks_passed        BOOLEAN NOT NULL,
    logged_manually_at   TIMESTAMPTZ,
    copied_at            TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
    -- NOTE: no sent_at / sent_by column exists, and no column here writes to any
    -- external system (including the CRM) — architectural enforcement of REQ-M10-P1 / REQ-NFR-18
);

CREATE TYPE notification_type AS ENUM ('band_change','daily_digest');
CREATE TYPE notification_channel AS ENUM ('email','slack','in_app');

CREATE TABLE notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type                notification_type NOT NULL,
    score_run_id        UUID REFERENCES score_runs(id),
    channel             notification_channel NOT NULL,
    sent_at             TIMESTAMPTZ,
    suppressed_reason   TEXT
);

-- ============================================================
-- Indexes (performance)
-- Beyond the unique indexes implied by UNIQUE/PK constraints above.
-- ============================================================
-- Explicitly required (consistency review, section B #14):
CREATE INDEX idx_events_occurred_at              ON events(occurred_at);
CREATE INDEX idx_events_recorded_at               ON events(recorded_at);
CREATE INDEX idx_findings_status                  ON findings(status);
CREATE INDEX idx_score_contributions_score_run_id ON score_contributions(score_run_id);
CREATE INDEX idx_findings_cited_event_ids         ON findings USING GIN (cited_event_ids);

-- Also recommended — same justification (hot FK columns on tables read by
-- the dashboard/ask-agent on every request), added while touching this file:
CREATE INDEX idx_response_pairs_client_event_id ON response_pairs(client_event_id);
CREATE INDEX idx_score_runs_computed_at         ON score_runs(computed_at);
CREATE INDEX idx_draft_messages_issue_id        ON draft_messages(issue_id);

-- ============================================================
-- Roles and grants (real, not a comment)
-- "Append-only except status columns": most Tier 1/3 tables get zero UPDATE/
-- DELETE. findings is the one exception — its status/state columns are
-- genuinely mutable (pending_validation -> validated/quarantined; open ->
-- resolved/open_overdue) — so it gets a column-level grant instead of a
-- blanket one. A separate, narrowly-scoped shredder_role is the ONLY role
-- allowed to touch events.body_encrypted, and only that one column.
-- ============================================================
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_role') THEN
        CREATE ROLE app_role LOGIN PASSWORD :'app_role_password';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'shredder_role') THEN
        CREATE ROLE shredder_role LOGIN PASSWORD :'shredder_role_password';
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO app_role, shredder_role;

-- app_role: read everything, insert-only on the append-only tables.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_role;
GRANT INSERT ON
    events, raw_envelopes, findings, quarantine, validation_failures,
    score_runs, score_contributions, band_history,
    feedback_verdicts, damping_weights, replay_runs, baseline_confirmations,
    narrator_outputs, ask_queries, draft_messages, notifications,
    users, auth_tokens
    TO app_role;

REVOKE UPDATE, DELETE ON
    events, raw_envelopes, score_runs, score_contributions, band_history,
    feedback_verdicts, quarantine, validation_failures, replay_runs
    FROM app_role;

-- findings: append-only except its own lifecycle columns.
REVOKE UPDATE, DELETE ON findings FROM app_role;
GRANT UPDATE (status, state) ON findings TO app_role;

-- damping_weights, users, auth_tokens: genuinely mutable rows (running
-- tallies, login state, revocation) — normal UPDATE rights, never DELETE
-- on the audit-relevant ones.
GRANT UPDATE ON damping_weights, users, auth_tokens TO app_role;

-- shredder_role: the retention job's only privilege, anywhere.
GRANT UPDATE (body_encrypted) ON events TO shredder_role;

-- ============================================================
-- Trigger: defense in depth on the single most important table.
-- Grants above are the primary control; this trigger is a second,
-- independent guard so a role misconfiguration doesn't silently
-- reopen the append-only guarantee on `events`.
-- ============================================================
CREATE OR REPLACE FUNCTION reject_update_delete() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.body_encrypted IS NULL AND OLD.body_encrypted IS NOT NULL THEN
        -- the one permitted transition: retention job clearing body_encrypted
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'events is append-only: % is not permitted (event id %)', TG_OP, OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_append_only
    BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION reject_update_delete();

-- ============================================================
-- Hash chain verification job
-- Run on a schedule (e.g. nightly) or on demand; returns one row per broken
-- link found, empty result set means the chain is intact end to end.
-- ============================================================
CREATE OR REPLACE FUNCTION verify_hash_chain() RETURNS TABLE(broken_at_event_id UUID, reason TEXT) AS $$
DECLARE
    rec RECORD;
    prev_hash TEXT := repeat('0', 64);
    computed TEXT;
BEGIN
    FOR rec IN SELECT * FROM events ORDER BY occurred_at, id LOOP
        IF rec.prev_event_hash != prev_hash THEN
            broken_at_event_id := rec.id;
            reason := 'prev_event_hash does not match the prior event''s event_hash';
            RETURN NEXT;
        END IF;
        computed := encode(digest(
            rec.id::text || '|' || rec.envelope_id::text || '|' || rec.event_type::text || '|' ||
            rec.occurred_at::text || '|' || rec.recorded_at::text || '|' ||
            coalesce(rec.stakeholder_id::text, '') || '|' || coalesce(rec.product_area_id::text, '') || '|' ||
            rec.structured_payload::text || '|' || coalesce(rec.supersedes_event_id::text, '') || '|' ||
            coalesce(rec.thread_key, '') || '|' || rec.prev_event_hash,
            'sha256'), 'hex');
        IF computed != rec.event_hash THEN
            broken_at_event_id := rec.id;
            reason := 'event_hash does not match the recomputed hash';
            RETURN NEXT;
        END IF;
        prev_hash := rec.event_hash;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

## Deployment note

This DDL is written for a **single client deployment's schema**. When provisioning a new deployment, run this script against a fresh, dedicated Postgres schema/database (per `architecture/03-technology-stack.md` isolation model) — never add a `client_id` column and share tables across clients. `app_role_password` and `shredder_role_password` are `psql` variables — pass them via `-v` at deploy time, never hardcode them in this file.

## What changed in this revision (v1.1)

| Gap | Fix |
|---|---|
| No indexes beyond PK/UNIQUE | Added the 5 required (`events.occurred_at`/`recorded_at`, `findings.status`, `score_contributions.score_run_id`, GIN on `findings.cited_event_ids`) + 3 more on the same justification |
| Append-only was a commented-out `REVOKE` | Real `CREATE ROLE`/`GRANT`/`REVOKE` block, plus a `BEFORE UPDATE OR DELETE` trigger on `events` as a second, independent guard |
| Hash chain algorithm unspecified | Documented (SHA-256, canonical field order, genesis value) and given a runnable `verify_hash_chain()` function |
| `rollups.is_baseline` lost on replay | Moved the durable confirmation to a new `baseline_confirmations` table; added `replay_runs` as a replay audit trail |
| `data_key_ref` NOT NULL vs. "set NULL to delete" | Reconciled: `data_key_ref` is permanent, `body_encrypted` is the column that gets nulled, by a narrowly-scoped `shredder_role` only |
| No `users` table | Added `users` + `auth_tokens`; rewired `submitted_by`, `asked_by`, `authored_by`, `signed_off_by` from free text to real FKs |
| 4 enums left as `TEXT` | `stitch_method`, `subject_type` (→ `rollup_subject_type`), `cluster_method`, `declined_reason` are now real Postgres `ENUM` types |
| Missing `CHECK`s | `draft_messages.evidence_event_ids` non-empty, `feedback_verdicts` has at least one target, `damping_weights.weight`/`score_contributions.damping` both have a `>= 0` floor |
| `quarantine.finding_id` had no `UNIQUE` | Added — makes the ERD's 1:0..1 cardinality actually true in the schema |
