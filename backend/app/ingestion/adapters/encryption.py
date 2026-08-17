"""Message-body encryption (REQ-M1-P4) — Fernet (AES-128-CBC + HMAC), keyed from a
file on disk. Not domain logic (it's an I/O boundary: reading a key file), so it lives
in adapters, not ingestion/domain — see research.md's Decision: Message-body encryption.
"""

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.ingestion.application.ports import EncryptionPort, KeyStorePort


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


class BucketedFernetEncryption(EncryptionPort):
    """Daily key-rotation key ring (specs/011-production-hardening, research.md
    Decision 1) — replaces `FernetEncryption` at every composition-root call site.
    `EncryptionPort`'s signature is unchanged: `encrypt()` always uses today's
    bucket key (`KeyStorePort.current_bucket_id()`); `decrypt()` tries every
    currently-active bucket key in turn (`KeyStorePort.list_active_buckets()`)
    until one succeeds. This is what makes crypto-shredding real without
    threading a `data_key_ref` parameter through every caller of `decrypt()`:
    once the retention job destroys a bucket's key (`KeyStorePort.destroy()`),
    that key stops appearing in `list_active_buckets()`, so any ciphertext
    encrypted under it becomes unrecoverable here, uniformly, on the very next
    call — not because this class does anything bucket-aware at read time beyond
    trying what's still available.

    `legacy_key_path` is the one remaining reason this class still knows about
    the pre-migration single-key scheme: any row written before this feature
    shipped carries `data_key_ref = "local-v1"` forever (insert-only,
    `data-model.md`) and was encrypted under `settings.encryption_key_path`,
    never a bucket. Without this fallback, shipping this feature would make
    every already-ingested message body permanently unreadable the moment it
    deployed — found as a real, reproducible failure against this repo's own
    shared dev database while implementing this feature, not a hypothetical
    edge case. `encrypt()` never uses the legacy key — only new bucket keys.
    """

    def __init__(self, key_store: KeyStorePort, legacy_key_path: str | None = None) -> None:
        self._key_store = key_store
        self._legacy_key_path = legacy_key_path

    def encrypt(self, plaintext: str) -> bytes:
        fernet = self._key_store.resolve(self._key_store.current_bucket_id())
        return fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        for bucket_id in self._key_store.list_active_buckets():
            try:
                return self._key_store.resolve(bucket_id).decrypt(ciphertext).decode()
            except InvalidToken:
                continue
        if self._legacy_key_path is not None:
            try:
                return load_key(self._legacy_key_path).decrypt(ciphertext).decode()
            except (InvalidToken, EncryptionKeyError):
                pass
        raise EncryptionKeyError(
            "Ciphertext could not be decrypted with any currently active key, "
            "including the legacy pre-migration key "
            "(its bucket's key may have been crypto-shredded)"
        )
