# 10 · DDL appendix

Runnable PostgreSQL 16 DDL for every table described in `02`–`08`. Grants and triggers that enforce the append-only/no-send guarantees are included inline where they matter most; a full grants script belongs in the deployment repo, not this document.

```sql
-- ============================================================
-- Extensions
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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

CREATE TABLE raw_envelopes (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collector_run_id   UUID NOT NULL REFERENCES collector_runs(id),
    source_native_id   TEXT NOT NULL,
    idempotency_key    TEXT NOT NULL UNIQUE,
    occurred_at        TIMESTAMPTZ NOT NULL,
    identity_status    identity_status NOT NULL,
    redacted_fields    TEXT[] NOT NULL DEFAULT '{}',
    payload_encrypted  BYTEA NOT NULL,
    data_key_ref       TEXT NOT NULL,
    ledger_event_id    UUID,               -- FK added after events table exists
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 03 · Event ledger
-- ============================================================
CREATE TYPE event_type AS ENUM (
    'message','ticket_state_change','usage_measurement','survey_response',
    'meeting','absence','crm_change'
);

CREATE TABLE events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    envelope_id         UUID NOT NULL REFERENCES raw_envelopes(id),
    event_type          event_type NOT NULL,
    occurred_at         TIMESTAMPTZ NOT NULL,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    stakeholder_id      UUID,               -- FK added after stakeholders table exists
    product_area_id     UUID,               -- FK added after product_areas table exists
    body_encrypted      BYTEA,
    data_key_ref        TEXT,
    structured_payload  JSONB NOT NULL DEFAULT '{}',
    supersedes_event_id UUID REFERENCES events(id),
    thread_key          TEXT,
    prev_event_hash     TEXT NOT NULL,
    event_hash          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE raw_envelopes  ADD CONSTRAINT fk_raw_envelopes_event  FOREIGN KEY (ledger_event_id) REFERENCES events(id);

-- Append-only enforcement: revoke UPDATE/DELETE from the application role.
-- REVOKE UPDATE, DELETE ON events FROM app_role;

CREATE TABLE event_threads (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_key        TEXT NOT NULL,
    event_id          UUID NOT NULL REFERENCES events(id),
    stitch_confidence NUMERIC(3,2) NOT NULL,
    stitch_method     TEXT NOT NULL
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

CREATE TABLE rollups (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type  TEXT NOT NULL,
    subject_id    UUID,
    metric        TEXT NOT NULL,
    window_start  TIMESTAMPTZ NOT NULL,
    window_end    TIMESTAMPTZ NOT NULL,
    value         NUMERIC NOT NULL,
    is_baseline   BOOLEAN NOT NULL DEFAULT false,
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
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
    authored_by           TEXT NOT NULL,
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

CREATE TABLE issues (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label         TEXT NOT NULL,
    cluster_method TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
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

CREATE TABLE quarantine (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id    UUID NOT NULL REFERENCES findings(id),
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
    damping                     NUMERIC(4,3) NOT NULL CHECK (damping <= 1.000),
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
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id         UUID REFERENCES findings(id),
    issue_id           UUID REFERENCES issues(id),
    verdict            verdict_type NOT NULL,
    submitted_by       TEXT NOT NULL,
    pattern_signature  TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE damping_weights (
    pattern_signature   TEXT PRIMARY KEY,
    weight               NUMERIC(4,3) NOT NULL DEFAULT 1.000 CHECK (weight <= 1.000),
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
    signed_off_by            TEXT,
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

CREATE TABLE ask_queries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_text       TEXT NOT NULL,
    matched_intent      TEXT,
    rendered_component  TEXT,
    declined_reason     TEXT,
    response_time_ms    INTEGER,
    asked_by            TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE tone_variant AS ENUM ('direct','formal','brief');

CREATE TABLE draft_messages (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id             UUID NOT NULL REFERENCES issues(id),
    stakeholder_id       UUID NOT NULL REFERENCES stakeholders(id),
    draft_text           TEXT NOT NULL,
    tone_variant         tone_variant NOT NULL,
    evidence_event_ids   UUID[] NOT NULL,
    checks_passed        BOOLEAN NOT NULL,
    logged_to_crm_at     TIMESTAMPTZ,
    copied_at            TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
    -- NOTE: no sent_at / sent_by column exists — architectural enforcement of REQ-M10-P1
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
```

## Deployment note

This DDL is written for a **single client deployment's schema**. When provisioning a new deployment, run this script against a fresh, dedicated Postgres schema/database (per `architecture/03-technology-stack.md` isolation model) — never add a `client_id` column and share tables across clients.
