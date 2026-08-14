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


settings = Settings()
