"""Pure unit test for `require_admin` (specs/011-production-hardening, User
Story 4) — `TokenRepositoryPort` faked, no DB, no HTTP client."""

import logging

import pytest
from fastapi import HTTPException

from app.auth.application.dependencies import get_current_user, require_admin
from tests.auth.test_require_full_access import _creds, _FakeTokenRepository, _record


async def _resolve(repo: _FakeTokenRepository):
    return await get_current_user(credentials=_creds(), token_repository=repo)


@pytest.mark.parametrize(
    "role", ["cs_lead", "support_lead", "engineering_manager", "account_executive", None]
)
async def test_every_non_admin_role_is_denied(role):
    repo = _FakeTokenRepository(_record(role))
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=await _resolve(repo))
    assert exc_info.value.status_code == 403


async def test_admin_passes_through_unchanged():
    repo = _FakeTokenRepository(_record("admin"))
    current_user = await _resolve(repo)
    result = await require_admin(current_user=current_user)
    assert result is current_user


async def test_access_decision_is_logged_for_both_outcomes(caplog):
    caplog.set_level(logging.INFO, logger="app.auth.application.dependencies")

    denied_repo = _FakeTokenRepository(_record("cs_lead"))
    with pytest.raises(HTTPException):
        await require_admin(current_user=await _resolve(denied_repo))
    assert any(
        getattr(r, "outcome", None) == "denied" and getattr(r, "role", None) == "cs_lead"
        for r in caplog.records
    )

    caplog.clear()
    allowed_repo = _FakeTokenRepository(_record("admin"))
    await require_admin(current_user=await _resolve(allowed_repo))
    assert any(
        getattr(r, "outcome", None) == "allowed" and getattr(r, "role", None) == "admin"
        for r in caplog.records
    )
