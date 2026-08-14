"""Message-body encryption (REQ-M1-P4) — Fernet (AES-128-CBC + HMAC), keyed from a
file on disk. Not domain logic (it's an I/O boundary: reading a key file), so it lives
in adapters, not ingestion/domain — see research.md's Decision: Message-body encryption.
"""

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.ingestion.application.ports import EncryptionPort


class EncryptionKeyError(Exception):
    """The key file is missing or not a valid Fernet key — the app must fail to start
    rather than silently fall back to storing plaintext (spec.md Edge Cases)."""


def load_key(key_path: str) -> Fernet:
    path = Path(key_path)
    if not path.is_file():
        raise EncryptionKeyError(f"Encryption key file not found at {key_path!r}")
    try:
        return Fernet(path.read_text().strip().encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionKeyError(f"Encryption key file at {key_path!r} is invalid") from exc


class FernetEncryption(EncryptionPort):
    """Loads and fails loudly at construction time — composition-root code (app.main)
    constructs this once at import time, so a missing/invalid key file prevents the
    app from starting at all, never a silent plaintext fallback."""

    def __init__(self, key_path: str) -> None:
        self._fernet = load_key(key_path)

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise EncryptionKeyError(
                "Ciphertext could not be decrypted with the active key"
            ) from exc
