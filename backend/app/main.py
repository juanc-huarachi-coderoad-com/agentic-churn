from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.adapters.router import router as auth_router
from app.auth.adapters.sqlalchemy_repository import SqlAlchemyTokenRepository
from app.auth.application.dependencies import provide_token_repository
from app.auth.application.ports import TokenRepositoryPort
from app.config import settings
from app.context.adapters.feedback_router import router as feedback_router
from app.context.adapters.profile_router import router as profile_router
from app.db import engine, get_session
from app.experience.adapters.ask_router import router as ask_router
from app.experience.adapters.coverage_router import router as coverage_router
from app.experience.adapters.dashboard_router import router as dashboard_router
from app.experience.adapters.draft_router import router as draft_router
from app.experience.adapters.evidence_router import router as evidence_router
from app.ingestion.adapters.audio_refresh_router import router as audio_refresh_router
from app.ingestion.adapters.consent_router import router as consent_router
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.observability.adapters.tracing import setup_tracing
from app.scoring.adapters.weight_router import router as weight_router

# Module-level, like `engine` above — a missing/invalid encryption key file MUST fail
# app startup, never fall back to storing plaintext (REQ-M1-P4, spec.md Edge Cases).
# Importing app.main at all (uvicorn, or any test importing `from app.main import app`)
# is exactly the "app startup" moment this needs to guard. `BucketedFernetEncryption`
# replaces the single-static-key `FernetEncryption` here (specs/011-production-
# hardening, research.md Decision 1) — `FileKeyStore` creates `data_keys_dir` on
# construction if missing, so this never fails the way a missing single key file did.
encryption = BucketedFernetEncryption(
    FileKeyStore(settings.data_keys_dir), settings.encryption_key_path
)

# User Story 3 — configured once, at import time, alongside the encryption setup
# above; FR-012 guarantees this can never fail app startup (research.md Decision 6).
setup_tracing()

app = FastAPI(title="Agentic Churn API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No app.state.limiter / RateLimitExceeded handler needed — the login route (auth/
# adapters/router.py) drives slowapi's limiter manually (test()/hit()) instead of via
# the @limiter.limit(...) decorator, so it never raises slowapi's own exception type.


# Composition root: the concrete adapter is wired here, not inside application/
# dependencies.py, so Application never imports Adapters (constitution P8) — see
# app/auth/application/dependencies.py's docstring, and decisions/02-repo-and-
# tooling.md's "concrete adapter is chosen once, at composition-root time" note.
async def _provide_token_repository(
    session: AsyncSession = Depends(get_session),
) -> TokenRepositoryPort:
    return SqlAlchemyTokenRepository(session)


app.dependency_overrides[provide_token_repository] = _provide_token_repository

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(evidence_router)
app.include_router(coverage_router)
app.include_router(profile_router)
app.include_router(ask_router)
app.include_router(draft_router)
app.include_router(feedback_router)
app.include_router(weight_router)
app.include_router(consent_router)
app.include_router(audio_refresh_router)


@app.get("/health")
async def health(response: Response) -> dict[str, str]:
    """Liveness/readiness probe for the Docker Compose healthcheck.

    See specs/001-project-foundation/contracts/health-check.md: distinguishes "process is
    up" from "process is up but its database is not" (constitution P5, applied to the
    platform layer) — 503 when the database is unreachable, so Compose marks the container
    unhealthy rather than reporting a false "ok".
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "ok", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
