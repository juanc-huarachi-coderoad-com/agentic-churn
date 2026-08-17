"""`FileKeyStore` (specs/011-production-hardening, research.md Decision 1) — one
Fernet key file per daily UTC bucket under `settings.data_keys_dir`. Crypto-
shredding a bucket is `destroy()` deleting its file; nothing else in this adapter
(or `BucketedFernetEncryption`, which uses it) ever needs to know how key
material is actually stored — a later Cloud KMS-backed `KeyStorePort`
implementation (`architecture/03-technology-stack.md`'s noted Phase 2 upgrade)
can replace this file entirely without touching any caller.
"""

from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet

from app.ingestion.application.ports import KeyStorePort


class FileKeyStore(KeyStorePort):
    def __init__(self, data_keys_dir: str) -> None:
        self._dir = Path(data_keys_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def current_bucket_id(self) -> str:
        return datetime.now(UTC).date().isoformat()

    def _path(self, bucket_id: str) -> Path:
        return self._dir / f"{bucket_id}.key"

    def resolve(self, bucket_id: str) -> Fernet:
        path = self._path(bucket_id)
        if not path.is_file():
            path.write_bytes(Fernet.generate_key())
        return Fernet(path.read_bytes())

    def list_active_buckets(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.key"))

    def destroy(self, bucket_id: str) -> None:
        path = self._path(bucket_id)
        path.unlink(missing_ok=True)
