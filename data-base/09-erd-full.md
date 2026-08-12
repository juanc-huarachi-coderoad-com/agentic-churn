# 09 · Entity-relationship diagram — full schema

Consolidated view of every table defined in `02-schema-ingestion.md` through `08-schema-experience.md`.

```mermaid
erDiagram
    USERS ||--o{ AUTH_TOKENS : "issued to"
    USERS ||--o{ CLIENT_PROFILE_VERSIONS : authors
    USERS ||--o{ PLAYBOOK_ACTIONS : "signs off"
    USERS ||--o{ FEEDBACK_VERDICTS : submits
    USERS ||--o{ ASK_QUERIES : asks
    USERS ||--o{ DRAFT_MESSAGES : requests
    USERS ||--o{ BASELINE_CONFIRMATIONS : confirms
    USERS ||--o{ REPLAY_RUNS : triggers

    SOURCES ||--o{ COLLECTOR_RUNS : "runs against"
    COLLECTOR_RUNS ||--o{ COVERAGE_REPORTS : produces
    COLLECTOR_RUNS ||--o{ RAW_ENVELOPES : emits
    RAW_ENVELOPES }o--o| EVENTS : "appended as (optional - NULL if quarantined pre-ledger)"
    IDENTITY_MAP }o--o| STAKEHOLDERS : resolves_to

    EVENTS ||--o{ EVENT_THREADS : "stitched into"
    EVENTS ||--o{ RESPONSE_PAIRS : "measured as"
    EVENTS ||--o{ EVENTS : supersedes
    STAKEHOLDERS ||--o{ ROLLUPS : "baseline for"
    PRODUCT_AREAS ||--o{ ROLLUPS : "baseline for"
    BASELINE_CONFIRMATIONS ||--o{ ROLLUPS : "sets is_baseline on replay"

    CLIENT_PROFILE_VERSIONS ||--o{ STAKEHOLDERS : defines
    CLIENT_PROFILE_VERSIONS ||--o{ PRODUCT_AREAS : defines
    CLIENT_PROFILE_VERSIONS ||--o{ COMMITMENTS : defines
    CLIENT_PROFILE_VERSIONS ||--o{ PROFILE_HISTORY_ENTRIES : defines
    COMMITMENTS ||--o{ RESPONSE_PAIRS : "measured against"

    EVENTS ||--o{ FINDINGS : "cited by (many-to-many via array)"
    FINDINGS }o--o{ ISSUES : "grouped via"
    FINDINGS ||--o| QUARANTINE : "rejected as"
    QUARANTINE ||--o{ VALIDATION_FAILURES : logs
    FINDING_TYPE_CONFIG ||--o{ FINDINGS : configures

    CLIENT_PROFILE_VERSIONS ||--o{ SCORE_RUNS : "used by"
    FINDINGS ||--o{ SCORE_CONTRIBUTIONS : "contributes to"
    ISSUES ||--o{ SCORE_CONTRIBUTIONS : groups
    SCORE_RUNS ||--o{ SCORE_CONTRIBUTIONS : contains
    SCORE_RUNS ||--o{ BAND_HISTORY : tracked_in

    FINDINGS ||--o{ FEEDBACK_VERDICTS : receives
    ISSUES ||--o{ FEEDBACK_VERDICTS : receives
    FEEDBACK_VERDICTS }o--|| DAMPING_WEIGHTS : "updates (via pattern_signature)"
    DAMPING_WEIGHTS ||--o{ SCORE_CONTRIBUTIONS : "damps"

    SCORE_RUNS ||--|| NARRATOR_OUTPUTS : explains
    PLAYBOOK_ACTIONS ||--o{ NARRATOR_OUTPUTS : "personalized into"
    ISSUES ||--o{ DRAFT_MESSAGES : "addressed by"
    STAKEHOLDERS ||--o{ DRAFT_MESSAGES : "intended for"
    SCORE_RUNS ||--o{ NOTIFICATIONS : triggers

    USERS {
        uuid id PK
        text username
        text password_hash
        enum role
        bool is_active
    }
    AUTH_TOKENS {
        uuid id PK
        uuid user_id FK
        text token_hash
        timestamptz expires_at
    }
    BASELINE_CONFIRMATIONS {
        uuid id PK
        enum subject_type
        uuid subject_id
        text metric
        uuid confirmed_by_user_id FK
    }
    REPLAY_RUNS {
        uuid id PK
        enum trigger
        enum status
        int events_replayed_count
    }
    SOURCES {
        uuid id PK
        enum source_type
        enum status
    }
    EVENTS {
        uuid id PK
        enum event_type
        timestamptz occurred_at
        timestamptz recorded_at
        uuid stakeholder_id FK
        uuid supersedes_event_id FK
        text event_hash
    }
    CLIENT_PROFILE_VERSIONS {
        uuid id PK
        int version_number
        date renewal_date
        bool is_current
    }
    STAKEHOLDERS {
        uuid id PK
        uuid profile_version_id FK
        enum influence
        numeric influence_multiplier
        bool signs_renewal
    }
    FINDINGS {
        uuid id PK
        enum reader_type
        numeric magnitude
        numeric confidence
        uuid_array cited_event_ids
        enum status
    }
    ISSUES {
        uuid id PK
        text label
    }
    SCORE_RUNS {
        uuid id PK
        enum trigger
        numeric score
        enum band
        numeric stakes
    }
    SCORE_CONTRIBUTIONS {
        uuid id PK
        uuid score_run_id FK
        uuid finding_id FK
        numeric points_contributed
        numeric damping
    }
    DAMPING_WEIGHTS {
        text pattern_signature PK
        numeric weight
    }
    NARRATOR_OUTPUTS {
        uuid id PK
        uuid score_run_id FK
        text headline
        jsonb reasons
        jsonb actions
    }
    DRAFT_MESSAGES {
        uuid id PK
        uuid issue_id FK
        text draft_text
        timestamptz logged_manually_at
    }
```

## Reading notes

- `EVENTS ||--o{ FINDINGS` is drawn as one-to-many for diagram simplicity; the real relationship is many-to-many via `findings.cited_event_ids UUID[]` (a finding cites several events, an event can support several findings). See `05-schema-reasoning.md`.
- `DRAFT_MESSAGES` has no relationship line to any outbound-transport entity — none exists in this schema (REQ-M10-P1).
- `FINDINGS ||--o| QUARANTINE` is a real 1-to-0-or-1 relationship, not just a diagram convention — `quarantine.finding_id` carries a `UNIQUE` constraint in the DDL, so a finding cannot be quarantined twice.
- `RAW_ENVELOPES }o--o| EVENTS` is optional on the events side — not every raw envelope becomes an event (some are rejected before reaching the ledger), matching `raw_envelopes.ledger_event_id` being nullable.
- `USERS` is the identity behind every "who did this" column in the schema (`data-base/12-users-and-auth.md`) — before this table existed, those columns were free text with no real referential integrity.
- Full column lists live in `02`–`08` and `12`; this diagram shows primary keys, foreign keys, and the columns most relevant to the product's core guarantees (evidence citation, damping, hysteresis, no-send, identity).
