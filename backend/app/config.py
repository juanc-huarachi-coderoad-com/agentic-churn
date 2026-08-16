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


settings = Settings()
