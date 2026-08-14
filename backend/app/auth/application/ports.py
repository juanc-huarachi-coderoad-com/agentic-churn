"""Ports (interfaces) the auth use cases depend on — implemented by
app.auth.adapters.sqlalchemy_repository. Application depends on these, never on the
concrete adapter directly (constitution P8, Dependency Inversion)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class UserRecord:
    id: UUID
    username: str
    password_hash: str
    is_active: bool


@dataclass(frozen=True)
class TokenRecord:
    user_id: UUID
    expires_at: datetime
    revoked_at: datetime | None


class UserRepositoryPort(ABC):
    @abstractmethod
    async def get_by_username(self, username: str) -> UserRecord | None: ...


class TokenRepositoryPort(ABC):
    @abstractmethod
    async def create(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> TokenRecord | None: ...

    @abstractmethod
    async def revoke(self, token_hash: str) -> None: ...
