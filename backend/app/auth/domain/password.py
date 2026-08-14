"""Pure password/token logic — no I/O, no database, no framework imports.

Argon2id per REQ-AUTH-02; opaque (non-JWT) bearer tokens per research.md's decision
(specs/002-dashboard-shell/research.md §Decision: Opaque bearer tokens, not JWTs).
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def generate_token() -> str:
    """The raw bearer token — shown to the client exactly once, never stored
    server-side in this form (REQ-AUTH-03)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """SHA-256 of the raw token, for storage/lookup in auth_tokens.token_hash."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
