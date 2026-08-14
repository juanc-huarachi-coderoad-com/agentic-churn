from fastapi import FastAPI, Response
from sqlalchemy import text

from app.db import engine

app = FastAPI(title="Agentic Churn API")


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
