from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.auth.application.ports import TokenRepositoryPort, UserRepositoryPort
from app.auth.domain.password import generate_token, hash_password, hash_token, verify_password

# A real Argon2id hash of a value nobody will ever type, used to keep the login path's
# timing identical whether the username exists or not — REQ-AUTH-08's "don't reveal"
# principle extended to timing, not just response body.
_DUMMY_HASH = hash_password(generate_token())


class InvalidCredentialsError(Exception):
    """Wrong password, unknown username, or a deactivated user — always the same
    exception, so the router can never accidentally leak which case occurred
    (REQ-AUTH-08, spec.md FR-010)."""


@dataclass(frozen=True)
class LoginResult:
    token: str
    expires_at: datetime


class LoginUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        token_repository: TokenRepositoryPort,
        token_lifetime_hours: int,
    ) -> None:
        self._users = user_repository
        self._tokens = token_repository
        self._token_lifetime_hours = token_lifetime_hours

    async def execute(self, username: str, password: str) -> LoginResult:
        user = await self._users.get_by_username(username)

        if user is None:
            verify_password(password, _DUMMY_HASH)  # constant-time-ish, see module docstring
            raise InvalidCredentialsError

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InvalidCredentialsError

        raw_token = generate_token()
        expires_at = datetime.now(UTC) + timedelta(hours=self._token_lifetime_hours)
        await self._tokens.create(user.id, hash_token(raw_token), expires_at)
        return LoginResult(token=raw_token, expires_at=expires_at)


class LogoutUseCase:
    def __init__(self, token_repository: TokenRepositoryPort) -> None:
        self._tokens = token_repository

    async def execute(self, raw_token: str) -> None:
        # Idempotent: revoking an already-revoked or unknown token still ends in the
        # same state (rejected on next use), so this never needs to report failure.
        await self._tokens.revoke(hash_token(raw_token))
