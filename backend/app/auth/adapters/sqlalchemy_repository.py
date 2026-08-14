"""SQLAlchemy implementations of the auth ports. Raw parameterized SQL against the
columns in data-base/10-ddl-appendix.md, not ORM declarative models — this project's
schema is DDL-first (migrations/env.py), so there's no separate model layer to keep in
sync with it for a handful of simple lookups."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports import (
    TokenRecord,
    TokenRepositoryPort,
    UserRecord,
    UserRepositoryPort,
)


class SqlAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> UserRecord | None:
        result = await self._session.execute(
            text(
                "SELECT id, username, password_hash, is_active FROM users "
                "WHERE username = :username"
            ),
            {"username": username},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return UserRecord(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            is_active=row.is_active,
        )


class SqlAlchemyTokenRepository(TokenRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        await self._session.execute(
            text(
                "INSERT INTO auth_tokens (user_id, token_hash, expires_at) "
                "VALUES (:user_id, :token_hash, :expires_at)"
            ),
            {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at},
        )
        await self._session.commit()

    async def get_by_hash(self, token_hash: str) -> TokenRecord | None:
        result = await self._session.execute(
            text(
                "SELECT user_id, expires_at, revoked_at FROM auth_tokens "
                "WHERE token_hash = :token_hash"
            ),
            {"token_hash": token_hash},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return TokenRecord(
            user_id=row.user_id, expires_at=row.expires_at, revoked_at=row.revoked_at
        )

    async def revoke(self, token_hash: str) -> None:
        await self._session.execute(
            text(
                "UPDATE auth_tokens SET revoked_at = now() "
                "WHERE token_hash = :token_hash AND revoked_at IS NULL"
            ),
            {"token_hash": token_hash},
        )
        await self._session.commit()
