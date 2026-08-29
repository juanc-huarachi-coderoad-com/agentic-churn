"""`FilesystemBackupDestination` (specs/031-production-deployment-hardening-ii, research.md
Decision 1/2) — a real `pg_dump` run against this deployment's own database, written to a
configurable local/mounted directory, with retention cleanup as part of the same run. A later
cloud object-storage-backed `BackupDestinationPort` implementation (deferred per FR-014 — no
concrete provider chosen yet) can replace this file entirely without touching
`RunBackupUseCase`, the same "port now, cloud adapter later" shape `FileKeyStore` already set.
"""

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.application.ports import BackupDestinationPort, BackupResult

_SECONDS_PER_DAY = 86400


class FilesystemBackupDestination(BackupDestinationPort):
    def __init__(self, database_url: str, backup_dir: str, retention_days: int) -> None:
        self._database_url = database_url
        self._dir = Path(backup_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._retention_days = retention_days

    def _plain_url(self) -> str:
        # pg_dump understands postgresql://, not SQLAlchemy's driver-qualified
        # postgresql+asyncpg:// this app's own DATABASE_URL uses everywhere else
        # (research.md Decision 2).
        return self._database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    async def create_backup(self) -> BackupResult:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        destination = self._dir / f"{timestamp}.dump"
        # Custom format (-Fc), not plain SQL: pg_restore --clean --if-exists makes
        # restoring into a non-empty database safe to re-run (research.md Decision 2).
        # A blocking subprocess call is safe here — this coroutine always runs inside
        # its own dedicated asyncio.run() loop (worker.py's job-runner shape), never
        # alongside other concurrent work that would be starved by the block.
        subprocess.run(
            ["pg_dump", "-Fc", "-f", str(destination), self._plain_url()],
            check=True,
            capture_output=True,
            text=True,
        )
        self._prune_expired_backups()
        return BackupResult(
            destination_path=str(destination), file_size_bytes=destination.stat().st_size
        )

    def _prune_expired_backups(self) -> None:
        cutoff = time.time() - self._retention_days * _SECONDS_PER_DAY
        for path in self._dir.glob("*.dump"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
