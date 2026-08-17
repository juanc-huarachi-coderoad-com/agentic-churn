"""Pure unit test for `require_full_access` (specs/011-production-hardening,
User Story 2) — `TokenRepositoryPort` faked, no DB, no HTTP client."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.application.dependencies import get_current_user, require_full_access
from app.auth.application.ports import TokenRecord, TokenRepositoryPort


class _FakeTokenRepository(TokenRepositoryPort):
    def __init__(self, record: TokenRecord | None) -> None:
        self._record = record

    async def create(self, user_id, token_hash, expires_at) -> None:  # pragma: no cover
        raise NotImplementedError

    async def get_by_hash(self, token_hash: str) -> TokenRecord | None:
        return self._record

    async def revoke(self, token_hash: str) -> None:  # pragma: no cover
        raise NotImplementedError


def _record(role: str | None) -> TokenRecord:
    return TokenRecord(
        user_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        revoked_at=None,
        role=role,
    )


def _creds() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="irrelevant-in-this-fake")


async def _resolve(repo: _FakeTokenRepository):
    """`require_full_access` depends on `get_current_user`, which depends on the
    bearer scheme/token repository — calling it directly with the same faked
    repository, bypassing FastAPI's DI container entirely (pure unit test, no
    HTTP layer)."""
    return await get_current_user(credentials=_creds(), token_repository=repo)


async def test_account_executive_is_denied():
    repo = _FakeTokenRepository(_record("account_executive"))
    with pytest.raises(HTTPException) as exc_info:
        await require_full_access(current_user=await _resolve(repo))
    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("role", ["cs_lead", "support_lead", "engineering_manager", "admin", None])
async def test_every_other_role_passes_through_unchanged(role):
    repo = _FakeTokenRepository(_record(role))
    current_user = await _resolve(repo)
    result = await require_full_access(current_user=current_user)
    assert result is current_user


async def test_access_decision_is_logged_for_both_outcomes(caplog):
    caplog.set_level(logging.INFO, logger="app.auth.application.dependencies")

    denied_repo = _FakeTokenRepository(_record("account_executive"))
    with pytest.raises(HTTPException):
        await require_full_access(current_user=await _resolve(denied_repo))
    assert any(
        getattr(r, "outcome", None) == "denied" and getattr(r, "role", None) == "account_executive"
        for r in caplog.records
    )

    caplog.clear()
    allowed_repo = _FakeTokenRepository(_record("cs_lead"))
    await require_full_access(current_user=await _resolve(allowed_repo))
    assert any(
        getattr(r, "outcome", None) == "allowed" and getattr(r, "role", None) == "cs_lead"
        for r in caplog.records
    )
