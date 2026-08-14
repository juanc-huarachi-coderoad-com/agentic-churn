from fastapi import APIRouter, Depends, HTTPException, Request
from limits import parse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.adapters.sqlalchemy_repository import (
    SqlAlchemyTokenRepository,
    SqlAlchemyUserRepository,
)
from app.auth.application.dependencies import get_bearer_token
from app.auth.application.use_cases import InvalidCredentialsError, LoginUseCase, LogoutUseCase
from app.config import settings
from app.db import get_session

router = APIRouter()

# Keyed by source IP (slowapi's built-in get_remote_address), not by username as
# research.md originally proposed: slowapi's key_func is called synchronously, never
# awaited, so extracting the username would require reading the async request body from
# a sync context — fragile and reliant on Starlette's private body-caching internals.
# Per-IP is slowapi's well-supported path and still satisfies REQ-AUTH-09's actual
# purpose (resisting brute-force/credential-stuffing) — it additionally blocks one
# attacker from rotating through many usernames, which per-username keying alone
# wouldn't. quickstart.md's test is unaffected: it runs from one client, one IP.
limiter = Limiter(key_func=get_remote_address)

# Only *failed* attempts count toward this limit (spec.md Acceptance Scenario 5: "repeated
# failed login attempts... third attempt... rate-limited") — driven manually via
# limiter.limiter.test()/hit() rather than the @limiter.limit(...) decorator, which counts
# every call including successes and would otherwise rate-limit a legitimately busy user.
_login_failure_limit = parse("2/5minutes")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_at: str


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    request: Request, body: LoginRequest, session: AsyncSession = Depends(get_session)
) -> LoginResponse:
    identity = get_remote_address(request)
    if not limiter.limiter.test(_login_failure_limit, identity):
        raise HTTPException(status_code=429, detail="Too many attempts — try again shortly")

    use_case = LoginUseCase(
        user_repository=SqlAlchemyUserRepository(session),
        token_repository=SqlAlchemyTokenRepository(session),
        token_lifetime_hours=settings.token_lifetime_hours,
    )
    try:
        result = await use_case.execute(body.username, body.password)
    except InvalidCredentialsError:
        limiter.limiter.hit(_login_failure_limit, identity)
        raise HTTPException(status_code=401, detail="Invalid credentials") from None
    return LoginResponse(token=result.token, expires_at=result.expires_at.isoformat())


@router.post("/auth/logout", status_code=204)
async def logout(
    raw_token: str = Depends(get_bearer_token), session: AsyncSession = Depends(get_session)
) -> None:
    use_case = LogoutUseCase(token_repository=SqlAlchemyTokenRepository(session))
    await use_case.execute(raw_token)
