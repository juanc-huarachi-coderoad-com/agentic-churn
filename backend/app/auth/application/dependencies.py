"""FastAPI dependencies for the auth gate. Depends only on Ports, never on the
concrete SQLAlchemy adapter — constitution P8 (Dependency Rule), enforced mechanically
by `.importlinter`'s global-dependency-rule contract. The concrete repository is wired
in at the composition root (app.main) via FastAPI's `dependency_overrides`, exactly the
pattern decisions/02-repo-and-tooling.md describes for LLMPort/EmbeddingPort."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.application.ports import TokenRepositoryPort
from app.auth.domain.password import hash_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def provide_token_repository() -> TokenRepositoryPort:
    """Placeholder — app.main overrides this with a real SqlAlchemyTokenRepository via
    `app.dependency_overrides`. Raising here means a missing override fails loudly
    instead of silently returning no data."""
    raise RuntimeError(
        "TokenRepositoryPort has no override configured — see app.main's startup wiring"
    )


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_repository: TokenRepositoryPort = Depends(provide_token_repository),
) -> CurrentUser:
    """Rejects a missing, expired, or revoked token with an identical 401 — every
    protected route depends on this (REQ-AUTH-05, REQ-AUTH-P1). Resolves and returns
    the authenticated user's identity (REQ-AUTH-07) for the route handler to use."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    record = await token_repository.get_by_hash(hash_token(credentials.credentials))
    if record is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if record.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if record.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Not authenticated")

    return CurrentUser(user_id=record.user_id)


async def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """The raw presented token, for the one route (logout) that needs to act on the
    token itself rather than the identity it resolves to. Requires presence only, not
    full validity — revoking an already-expired token is harmless and still honors
    contracts/auth.md's idempotent-logout guarantee."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return credentials.credentials
