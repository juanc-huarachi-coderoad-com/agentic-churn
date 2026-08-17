"""FastAPI dependencies for the auth gate. Depends only on Ports, never on the
concrete SQLAlchemy adapter — constitution P8 (Dependency Rule), enforced mechanically
by `.importlinter`'s global-dependency-rule contract. The concrete repository is wired
in at the composition root (app.main) via FastAPI's `dependency_overrides`, exactly the
pattern decisions/02-repo-and-tooling.md describes for LLMPort/EmbeddingPort."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.application.ports import TokenRepositoryPort
from app.auth.domain.password import hash_token

logger = logging.getLogger(__name__)

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
    role: str | None


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

    return CurrentUser(user_id=record.user_id, role=record.role)


async def require_full_access(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Gates every write-capable route to every role except `account_executive`
    (specs/011-production-hardening, User Story 2, `contracts/rbac.md`). Every
    read-only route keeps depending on `get_current_user` directly, unchanged —
    this dependency only ever narrows the one route set an account executive can
    reach, never any other role's access to any route (FR-007).

    FR-008: logs one `access_decision` line per call, allowed or denied, with
    the role *as it was at this exact request* — `users.role` is mutable, so a
    later lookup couldn't reconstruct which role actually authorized a given
    past request."""
    allowed = current_user.role != "account_executive"
    logger.info(
        "access_decision",
        extra={
            "user_id": str(current_user.user_id),
            "role": current_user.role,
            "outcome": "allowed" if allowed else "denied",
        },
    )
    if not allowed:
        raise HTTPException(
            status_code=403, detail="This action is not available for your account."
        )
    return current_user


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Gates the weight-recalibration route to `role == "admin"` only — including
    `cs_lead`, unlike `require_full_access` (specs/011-production-hardening, User
    Story 4, `contracts/weight-recalibration.md`). Deliberately duplicates
    `require_full_access`'s few-line logging shape rather than sharing a helper
    across the two — keeps User Story 4 free of any dependency on User Story 2's
    delivery order (P10; safe to factor out later if both ship together).

    FR-008: logs one `access_decision` line per call, same shape as
    `require_full_access` — the role *as it was at this exact request*."""
    allowed = current_user.role == "admin"
    logger.info(
        "access_decision",
        extra={
            "user_id": str(current_user.user_id),
            "role": current_user.role,
            "outcome": "allowed" if allowed else "denied",
        },
    )
    if not allowed:
        raise HTTPException(
            status_code=403, detail="This action is not available for your account."
        )
    return current_user


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
