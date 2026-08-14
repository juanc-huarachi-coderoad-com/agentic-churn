from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.adapters.router import router as auth_router
from app.auth.adapters.sqlalchemy_repository import SqlAlchemyTokenRepository
from app.auth.application.dependencies import provide_token_repository
from app.auth.application.ports import TokenRepositoryPort
from app.config import settings
from app.db import engine, get_session
from app.experience.adapters.dashboard_router import router as dashboard_router

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
