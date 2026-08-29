"""Real-DB: `RunBackupUseCase` actually produces a restorable dump, prunes old ones, and
records failures (specs/031-production-deployment-hardening-ii, User Story 1 —
FR-001..004). Requires `pg_dump`/`pg_restore`/`createdb`/`dropdb` on PATH, matching the
running server's major version (`quickstart.md` Prerequisites) — the CI/production image
has these via `backend/Dockerfile`'s new `postgresql-client` install; local runs need them
on the host too.
"""

import os
import subprocess
import time
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.db import async_session_factory, engine
from app.ingestion.adapters.backup_destination import FilesystemBackupDestination
from app.ingestion.adapters.sqlalchemy_repositories import SqlAlchemyBackupJobRepository
from app.ingestion.application.ports import BackupDestinationPort
from app.ingestion.application.use_cases import RunBackupUseCase


async def _run(destination: BackupDestinationPort):
    async with async_session_factory() as session:
        use_case = RunBackupUseCase(
            destination=destination, backup_repo=SqlAlchemyBackupJobRepository(session)
        )
        return await use_case.execute()


async def test_backup_succeeds_and_is_restorable(tmp_path):
    destination = FilesystemBackupDestination(
        database_url=settings.database_url,
        backup_dir=str(tmp_path),
        retention_days=30,
    )

    await _run(destination)

    dump_files = list(tmp_path.glob("*.dump"))
    assert len(dump_files) == 1
    assert dump_files[0].stat().st_size > 0

    async with engine.begin() as conn:
        run_row = (
            await conn.execute(
                text(
                    "SELECT status, destination_path, file_size_bytes FROM backup_job_runs "
                    "ORDER BY started_at DESC LIMIT 1"
                )
            )
        ).one()
    assert run_row.status == "succeeded"
    assert run_row.destination_path == str(dump_files[0])
    assert run_row.file_size_bytes > 0

    # SC-002: the dump restores into a fresh database and reproduces the source's
    # own event count (a value guaranteed nonzero — earlier tests/seed data in this
    # shared, cumulative test database always leave at least one real event).
    async with engine.begin() as conn:
        source_count = (
            await conn.execute(text("SELECT count(*) FROM events"))
        ).scalar_one()

    scratch_db = f"backup_restore_test_{uuid4().hex[:8]}"
    parsed = urlparse(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
    scratch_url = f"postgresql://{parsed.netloc}/{scratch_db}"

    admin_engine = create_async_engine(
        settings.database_url.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(text(f'CREATE DATABASE "{scratch_db}"'))

        subprocess.run(
            ["pg_restore", "--no-owner", "--no-privileges", "-d", scratch_url, str(dump_files[0])],
            check=True,
            capture_output=True,
            text=True,
        )

        restore_engine = create_async_engine(
            scratch_url.replace("postgresql://", "postgresql+asyncpg://")
        )
        try:
            async with restore_engine.begin() as conn:
                restored_count = (
                    await conn.execute(text("SELECT count(*) FROM events"))
                ).scalar_one()
            assert restored_count == source_count
        finally:
            await restore_engine.dispose()

        async with admin_engine.connect() as conn:
            # Terminate any lingering connections to the scratch DB before dropping it.
            await conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid != pg_backend_pid()"
                ),
                {"db": scratch_db},
            )
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{scratch_db}"'))
    finally:
        await admin_engine.dispose()


async def test_old_backups_are_pruned_and_new_ones_kept(tmp_path):
    destination = FilesystemBackupDestination(
        database_url=settings.database_url,
        backup_dir=str(tmp_path),
        retention_days=30,
    )

    old_file = tmp_path / "20200101T000000Z.dump"
    old_file.write_bytes(b"synthetic old dump")
    old_time = time.time() - 31 * 86400
    os.utime(old_file, (old_time, old_time))

    await _run(destination)

    remaining = {p.name for p in tmp_path.glob("*.dump")}
    assert old_file.name not in remaining
    assert len(remaining) == 1


async def test_backup_failure_is_recorded_and_propagates(tmp_path):
    unwritable_dir = tmp_path / "readonly"
    unwritable_dir.mkdir()
    unwritable_dir.chmod(0o500)  # no write permission

    destination = FilesystemBackupDestination(
        database_url=settings.database_url,
        backup_dir=str(unwritable_dir),
        retention_days=30,
    )

    raised = False
    try:
        await _run(destination)
    except Exception:
        raised = True
    assert raised

    async with engine.begin() as conn:
        run_row = (
            await conn.execute(
                text(
                    "SELECT status, error_detail FROM backup_job_runs "
                    "ORDER BY started_at DESC LIMIT 1"
                )
            )
        ).one()
    assert run_row.status == "failed"
    assert run_row.error_detail is not None
