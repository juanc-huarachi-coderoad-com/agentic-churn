from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Per-deployment configuration, sourced from the environment (.env in Compose).

    One deployment = one client = one .env file, never shared across stacks
    (architecture/03-technology-stack.md, constitution "Isolation model").
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_churn"

    # Role passwords for the app_role/shredder_role grants in
    # data-base/10-ddl-appendix.md — that document's psql :'var' syntax is a psql-client
    # substitution feature with no asyncpg equivalent, so the initial migration
    # (migrations/versions/0001_initial_schema.py) substitutes these client-side instead,
    # replicating exactly what psql would have done before sending the DDL to the server.
    app_role_password: str = "app_role_dev_password"
    shredder_role_password: str = "shredder_role_dev_password"

    # The frontend's origin, for CORS (specs/002-dashboard-shell T004) — `api` and `web`
    # are served on different ports (docker-compose.yml), so the browser enforces CORS
    # on every request from the dashboard to the API.
    web_origin: str = "http://localhost:5173"

    # Bearer token lifetime — requirements/14-authentication.md's default (12 hours).
    token_lifetime_hours: int = 12

    # Message-body encryption (specs/003-ingestion-and-context, REQ-M1-P4). One active
    # Fernet key per deployment in Phase 1 — encryption_key_id is a fixed label stored
    # in data_key_ref columns, never the key itself (research.md).
    encryption_key_path: str = "./secrets/data.key"
    encryption_key_id: str = "local-v1"

    # Client profile YAML (specs/003-ingestion-and-context, REQ-M3-01) — the CS lead
    # edits this file directly in the MVP (decisions/00-open-questions-resolved.md Q2);
    # POST /api/profile/reload re-reads it from this path.
    client_profile_path: str = "./demo/client-profile.yaml"

    # SimulatedCollector's fixture (specs/003-ingestion-and-context) — CWD-relative
    # like the two paths above, not `__file__`-relative: this repo's Docker image
    # flattens `backend/` away (WORKDIR /app *is* the backend tree), so a
    # `__file__`-relative path computed from `scripts/run_collector.py` would resolve
    # differently in the container than it does when run locally from `backend/`.
    collector_fixture_path: str = "./demo/fixtures/meridian-week.json"

    # Recurrence reader's embedding provider (specs/005-deterministic-findings,
    # architecture/03-technology-stack.md) — no safe default; an empty value fails
    # honestly at the adapter (spec.md's Edge Cases), never a silent skip.
    openai_api_key: str = ""

    # Meeting audio ingestion's diarization provider (specs/019-meeting-audio-
    # ingestion, research.md Decision 7's correction) — the pyannote.ai hosted API,
    # not a locally-run pyannote.audio/PyTorch pipeline (that pipeline's PyTorch
    # dependency alone dragged the deployed image to ~20GB via its CUDA wheel
    # closure). Same honest-empty-default discipline as openai_api_key above.
    pyannoteai_api_key: str = ""

    # Tone/Intent readers' model provider (specs/007-model-findings,
    # decisions/02-repo-and-tooling.md) — no safe default for the key, same
    # honest-failure discipline as openai_api_key above.
    anthropic_api_key: str = ""
    reader_model_id: str = "claude-haiku-4-5-20251001"

    # Narrator/Ask agent's model tier (specs/008-narrator-and-ask-agent,
    # decisions/02-repo-and-tooling.md's Claude model ID pinning table) — same
    # anthropic_api_key above, a different pinned model ID for higher-stakes
    # generation than the readers' Haiku-class calls.
    generation_model_id: str = "claude-sonnet-5"

    # Retention/crypto-shredding (specs/011-production-hardening, REQ-NFR-13/14,
    # FR-001) — configurable per deployment since the 90-day figure is described as
    # "pending final legal sign-off with the client" (decisions/00-open-questions-
    # resolved.md Q5), not hardcoded.
    retention_window_days: int = 90

    # Daily key-rotation buckets for crypto-shredding (research.md Decision 1) — one
    # Fernet key file per UTC calendar day under this directory, replacing the single
    # static `encryption_key_path` key above for new writes. `encryption_key_path`
    # above is kept only so any pre-migration "local-v1"-tagged row can still be
    # decrypted (data-model.md's documented one-time manual exception).
    data_keys_dir: str = "./secrets/data-keys"

    # Observability (specs/011-production-hardening, FR-009..012) — empty means the
    # OTel SDK initializes with a console/no-op exporter, never a hard failure
    # (FR-012's "unaffected if the observability backend itself is unreachable").
    # Field name matches the OTel-standard env var (`OTEL_EXPORTER_OTLP_ENDPOINT`,
    # docker-compose.yml) exactly, so pydantic-settings' default case-insensitive
    # env-var mapping picks it up with no alias needed.
    otel_exporter_otlp_endpoint: str = ""

    # Meeting audio ingestion (specs/019-meeting-audio-ingestion, research.md
    # Decision 9) — the scheduled poll's cadence, configurable per deployment like
    # every other timing knob above.
    audio_poll_interval_hours: int = 4

    # Meeting audio's local storage location (specs/019-meeting-audio-ingestion,
    # research.md Decision 12 — supersedes the prior Google Drive OAuth design).
    # CWD-relative like client_profile_path/collector_fixture_path above; lands inside
    # the ./demo directory both the api and worker services already mount read-only
    # (docker-compose.yml), so no new mount is needed. No secret to configure — a
    # subdirectory's name is the meeting series it maps to (FR-015).
    meeting_audio_storage_path: str = "./demo/meeting-audio"


settings = Settings()
